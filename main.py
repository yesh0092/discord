import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

# ---------------- CONFIG ----------------
SUPPORT_ROLE_NAME = "Support"
LOG_CHANNEL_NAME = "support-logs"
MODERATOR_ID = 123456789012345678  # <-- replace with real ID

ROLE_KEYWORDS = ["role", "artist", "apply", "creative"]

# ---- Luxury GIFs (ONLY 4) ----
WELCOME_GIF = "https://media.discordapp.net/attachments/.../welcome.gif"
SUPPORT_GIF = "https://media.discordapp.net/attachments/.../support.gif"
ROLE_REDIRECT_GIF = "https://media.discordapp.net/attachments/.../redirect.gif"
CLOSE_GIF = "https://media.discordapp.net/attachments/.../fade.gif"

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

active_rooms = {}        # user_id -> channel_id
event_opt_in = set()     # users who want events

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="quietly 🌙"
        )
    )

# ---------------- WELCOME + ONBOARDING ----------------
@bot.event
async def on_member_join(member):
    if member.guild.system_channel:
        await member.guild.system_channel.send(f"Welcome, {member.mention}.")

    await asyncio.sleep(4)
    try:
        await member.send("Welcome.\nI’ll help you find your way here.")
        await member.send(WELCOME_GIF)
        await asyncio.sleep(3)
        await member.send(
            "Before anything else—\nwhat brings you here?\n\n"
            "✦ Support\n"
            "✦ Creative Roles\n"
            "✦ Events\n"
            "✦ Just exploring\n\n"
            "You can simply reply."
        )
    except:
        pass

# ---------------- DM HANDLER ----------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # -------- DM ONLY --------
    if isinstance(message.channel, discord.DMChannel):
        user = message.author
        content = message.content.lower()

        # Ignore if already in room
        if user.id in active_rooms:
            return

        # ----- ROLE REDIRECT -----
        if any(word in content for word in ROLE_KEYWORDS):
            moderator = await bot.fetch_user(MODERATOR_ID)
            await asyncio.sleep(2)
            await user.send(
                "Some roles are handled personally.\n"
                "I’ll connect you with the right person."
            )
            await user.send(ROLE_REDIRECT_GIF)
            await user.send(f"Please reach out to {moderator.mention}.")
            await moderator.send(f"{user} is interested in a creative role.")
            return

        # ----- EVENT OPT-IN -----
        if "event" in content:
            event_opt_in.add(user.id)
            await user.send("You’ll receive event updates here.")
            return

        # ----- SUPPORT FLOW -----
        await asyncio.sleep(2)
        await user.send("I’ve prepared a private space for you.")

        guild = bot.guilds[0]
        support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE_NAME)

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
        await channel.send("You’re safe here.\nTake your time.")
        await channel.send(SUPPORT_GIF)

        log = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if log:
            await log.send(f"🕊 Support room opened for {user}")

    await bot.process_commands(message)

# ---------------- CLOSE ROOM ----------------
@bot.command()
@commands.has_role(SUPPORT_ROLE_NAME)
async def close(ctx):
    for uid, cid in list(active_rooms.items()):
        if cid == ctx.channel.id:
            await ctx.send("This space will fade now.")
            await ctx.send(CLOSE_GIF)
            await asyncio.sleep(20)
            await ctx.channel.delete()
            active_rooms.pop(uid)
            break

# ---------------- EVENT ANNOUNCE ----------------
@bot.command()
@commands.has_role("Admin")
async def announce(ctx, *, message):
    sent = 0
    for uid in event_opt_in:
        try:
            user = await bot.fetch_user(uid)
            await user.send(message)
            sent += 1
            await asyncio.sleep(1)
        except:
            pass
    await ctx.send(f"Event sent to {sent} users.")

# ---------------- SILENT ERRORS ----------------
@bot.event
async def on_command_error(ctx, error):
    pass

bot.run(TOKEN)
