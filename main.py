import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ================= LOAD ENV =================
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN not found in environment variables")

# ================= CONFIG =================
SUPPORT_ROLE = "Support"
ADMIN_ROLE = "Admin"
LOG_CHANNEL = "support-logs"
MODERATOR_ID = 123456789012345678  # 🔁 REPLACE WITH REAL USER ID

ROLE_KEYWORDS = ["artist", "role", "apply", "creative"]

# ================= INTENTS =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

active_rooms = {}
event_users = set()

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="quietly 🌙"
        )
    )

# ================= WELCOME EMBED =================
@bot.event
async def on_member_join(member: discord.Member):
    # ---- Server Welcome (Embed) ----
    if member.guild.system_channel:
        embed = discord.Embed(
            title="Welcome",
            description=(
                f"{member.mention}\n\n"
                "You’ve arrived in a calm space.\n"
                "Take your time. Explore at your pace."
            ),
            color=0x0f172a
        )
        embed.set_footer(text="HellFire • Private Community")
        await member.guild.system_channel.send(embed=embed)

    # ---- DM Onboarding ----
    await asyncio.sleep(3)
    try:
        await member.send(
            "Welcome.\n\n"
            "This space is designed to stay calm and intentional.\n"
            "I’ll quietly help you when you need it."
        )
        await asyncio.sleep(2)
        await member.send(
            "**Here’s how I can help:**\n\n"
            "• If you need **support**, just message me anytime.\n"
            "• If you’re interested in **creative roles**, say `artist` or `apply`.\n"
            "• If you want **event updates**, say `events`.\n\n"
            "No commands needed. Speak naturally."
        )
    except discord.Forbidden:
        pass  # User has DMs closed

# ================= BASIC COMMANDS =================

@bot.command()
async def ping(ctx):
    """Check if bot is alive"""
    await ctx.send("🏓 Pong. I’m here.")

@bot.command()
async def helpme(ctx):
    """Show help"""
    embed = discord.Embed(
        title="Bot Help",
        description=(
            "`!ping` → Check if bot is online\n"
            "`!support` → How to get support\n"
            "`!announce <message>` → Send event update (Admin)\n"
            "`!close` → Close support room (Support)"
        ),
        color=0x1f2937
    )
    await ctx.send(embed=embed)

@bot.command()
async def support(ctx):
    await ctx.send("📩 Please DM me directly to begin support.")

# ================= DM HANDLER =================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # -------- DM LOGIC --------
    if isinstance(message.channel, discord.DMChannel):
        user = message.author
        content = message.content.lower()

        # Prevent duplicate rooms
        if user.id in active_rooms:
            return

        # ---- ROLE REDIRECT ----
        if any(k in content for k in ROLE_KEYWORDS):
            moderator = await bot.fetch_user(MODERATOR_ID)
            await user.send(
                "Some roles are handled personally.\n"
                "I’ll connect you with the right person."
            )
            await user.send(f"Please reach out to {moderator.mention}.")
            await moderator.send(f"🔔 {user} is interested in a role.")
            return

        # ---- EVENT OPT-IN ----
        if "event" in content:
            event_users.add(user.id)
            await user.send("You’ll receive event updates here.")
            return

        # ---- SUPPORT FLOW ----
        await create_support_room(user)

    await bot.process_commands(message)

# ================= SUPPORT ROOM =================
async def create_support_room(user: discord.User):
    guild = bot.guilds[0]
    support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE)

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

    active_rooms[user.id] = channel.id

    await user.send("I’ve prepared a private space for you.")
    await channel.send(
        "**You’re safe here.**\n"
        "Explain what you need, and someone will assist you shortly."
    )

    log = discord.utils.get(guild.text_channels, name=LOG_CHANNEL)
    if log:
        await log.send(f"🕊 Support room opened for {user}")

# ================= CLOSE ROOM =================
@bot.command()
@commands.has_role(SUPPORT_ROLE)
async def close(ctx):
    for uid, cid in list(active_rooms.items()):
        if cid == ctx.channel.id:
            await ctx.send("This space will now close.")
            await asyncio.sleep(5)
            await ctx.channel.delete()
            active_rooms.pop(uid)
            break

# ================= ANNOUNCE EVENT =================
@bot.command()
@commands.has_role(ADMIN_ROLE)
async def announce(ctx, *, message):
    sent = 0
    for uid in list(event_users):
        try:
            user = await bot.fetch_user(uid)
            embed = discord.Embed(
                title="Event Update",
                description=message,
                color=0x111827
            )
            await user.send(embed=embed)
            sent += 1
            await asyncio.sleep(1)
        except discord.Forbidden:
            event_users.discard(uid)

    await ctx.send(f"Event sent to {sent} members.")

# ================= ERROR HANDLING =================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You don’t have permission for this command.")
    else:
        print(error)

# ================= RUN =================
bot.run(TOKEN)
