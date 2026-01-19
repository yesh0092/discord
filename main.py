import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ================== LOAD ENV ==================
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN environment variable not set")

# ================== CONFIG ==================
SUPPORT_ROLE_NAME = "Support"
ADMIN_ROLE_NAME = "Admin"
LOG_CHANNEL_NAME = "support-logs"

MODERATOR_ID = 123456789012345678  # 🔁 REPLACE WITH REAL USER ID

ROLE_KEYWORDS = ["role", "artist", "apply", "creative"]

# ================== INTENTS ==================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================== STATE ==================
active_support_rooms = {}      # user_id -> channel_id
event_opt_in_users = set()     # user_ids

# ================== READY ==================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="quietly 🌙"
        )
    )

# ================== WELCOME + ONBOARDING ==================
@bot.event
async def on_member_join(member: discord.Member):
    # Minimal public welcome
    if member.guild.system_channel:
        await member.guild.system_channel.send(f"Welcome, {member.mention}.")

    await asyncio.sleep(3)

    try:
        await member.send(
            "Welcome.\n"
            "I’ll help you find your way here.\n\n"
            "If you need **support**, just message me.\n"
            "If you’re interested in **roles**, say `artist` or `apply`.\n"
            "If you want **event updates**, say `events`."
        )
    except discord.Forbidden:
        pass  # User has DMs closed

# ================== DM HANDLER ==================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # -------- HANDLE DMs ONLY --------
    if isinstance(message.channel, discord.DMChannel):
        user = message.author
        content = message.content.lower()

        # Prevent duplicate rooms
        if user.id in active_support_rooms:
            return

        # -------- ROLE REDIRECT --------
        if any(keyword in content for keyword in ROLE_KEYWORDS):
            moderator = await bot.fetch_user(MODERATOR_ID)

            await user.send(
                "Some roles are handled personally.\n"
                "I’ll connect you with the right person."
            )
            await user.send(f"Please reach out to {moderator.mention}.")

            try:
                await moderator.send(f"{user} is interested in a role.")
            except discord.Forbidden:
                pass

            return

        # -------- EVENT OPT-IN --------
        if "event" in content:
            event_opt_in_users.add(user.id)
            await user.send("You’ll receive event updates here.")
            return

        # -------- SUPPORT FLOW --------
        await create_support_room(user)

    await bot.process_commands(message)

# ================== SUPPORT ROOM CREATION ==================
async def create_support_room(user: discord.User):
    guild = bot.guilds[0]  # Single-server bot assumption
    support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)

    if not support_role:
        await user.send("Support system is not configured yet.")
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    channel = await guild.create_text_channel(
        name=f"room-{user.name.lower()}",
        overwrites=overwrites
    )

    active_support_rooms[user.id] = channel.id

    await user.send("I’ve prepared a private space for you.")
    await channel.send("You’re safe here.\nTake your time.")

    log = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if log:
        await log.send(f"🕊 Support room opened for {user}")

# ================== CLOSE ROOM ==================
@bot.command()
@commands.has_role(SUPPORT_ROLE_NAME)
async def close(ctx: commands.Context):
    user_id = None

    for uid, cid in active_support_rooms.items():
        if cid == ctx.channel.id:
            user_id = uid
            break

    if not user_id:
        return

    await ctx.send("This space will fade now.")
    await asyncio.sleep(10)

    await ctx.channel.delete()
    active_support_rooms.pop(user_id, None)

# ================== EVENT ANNOUNCE ==================
@bot.command()
@commands.has_role(ADMIN_ROLE_NAME)
async def announce(ctx: commands.Context, *, message: str):
    sent = 0

    for uid in list(event_opt_in_users):
        try:
            user = await bot.fetch_user(uid)
            await user.send(message)
            sent += 1
            await asyncio.sleep(1)
        except discord.Forbidden:
            event_opt_in_users.discard(uid)

    await ctx.send(f"Event sent to {sent} members.")

# ================== ERROR HANDLING ==================
@bot.event
async def on_command_error(ctx, error):
    # Silent by design (luxury behavior)
    pass

# ================== RUN ==================
bot.run(TOKEN)
