import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ================= LOAD TOKEN =================
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN not found in environment variables")

# ================= CONFIG =================
SUPPORT_ROLE = "Support"
ADMIN_ROLE = "Admin"
LOG_CHANNEL = "support-logs"
MODERATOR_ID = 123456789012345678  # ← replace with real ID

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
        activity=discord.Game(name="DM me for support 🌙")
    )

# ================= BASIC COMMANDS =================

@bot.command()
async def ping(ctx):
    """Check if bot is alive"""
    await ctx.send("🏓 Pong! Bot is working.")

@bot.command()
async def helpme(ctx):
    """Show bot help"""
    await ctx.send(
        "**Bot Commands**\n"
        "`!ping` → check bot status\n"
        "`!support` → start support (DM only)\n"
        "`!announce <msg>` → send event DM (Admin)\n"
        "`!close` → close support room (Support)"
    )

# ================= WELCOME =================
@bot.event
async def on_member_join(member):
    if member.guild.system_channel:
        await member.guild.system_channel.send(f"Welcome, {member.mention}.")

    await asyncio.sleep(2)
    try:
        await member.send(
            "Welcome.\n"
            "DM me anytime for **support**.\n"
            "Say `artist` or `apply` for roles.\n"
            "Say `events` for updates."
        )
    except:
        pass

# ================= SUPPORT COMMAND =================
@bot.command()
async def support(ctx):
    """Tell user to DM bot"""
    await ctx.send("📩 Please DM me to start support.")

# ================= DM HANDLER =================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # -------- DM LOGIC --------
    if isinstance(message.channel, discord.DMChannel):
        user = message.author
        content = message.content.lower()

        # Already has room
        if user.id in active_rooms:
            return

        # ROLE REDIRECT
        if any(k in content for k in ROLE_KEYWORDS):
            mod = await bot.fetch_user(MODERATOR_ID)
            await user.send(
                "Roles are handled personally.\n"
                f"Please contact {mod.mention}."
            )
            await mod.send(f"{user} wants a role.")
            return

        # EVENT OPT-IN
        if "event" in content:
            event_users.add(user.id)
            await user.send("✅ You’ll receive event updates.")
            return

        # SUPPORT FLOW
        guild = bot.guilds[0]
        support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE)

        if not support_role:
            await user.send("Support role not configured.")
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        channel = await guild.create_text_channel(
            f"room-{user.name.lower()}",
            overwrites=overwrites
        )

        active_rooms[user.id] = channel.id

        await user.send("🕊 A private support room has been created.")
        await channel.send("You’re safe here. Explain your issue.")

        log = discord.utils.get(guild.text_channels, name=LOG_CHANNEL)
        if log:
            await log.send(f"Support room opened for {user}")

    await bot.process_commands(message)

# ================= CLOSE ROOM =================
@bot.command()
@commands.has_role(SUPPORT_ROLE)
async def close(ctx):
    for uid, cid in list(active_rooms.items()):
        if cid == ctx.channel.id:
            await ctx.send("Closing room…")
            await asyncio.sleep(5)
            await ctx.channel.delete()
            active_rooms.pop(uid)
            break

# ================= ANNOUNCE EVENT =================
@bot.command()
@commands.has_role(ADMIN_ROLE)
async def announce(ctx, *, msg):
    sent = 0
    for uid in list(event_users):
        try:
            user = await bot.fetch_user(uid)
            await user.send(f"📢 **Event Update**\n{msg}")
            sent += 1
            await asyncio.sleep(1)
        except:
            event_users.discard(uid)

    await ctx.send(f"✅ Event sent to {sent} users.")

# ================= ERROR HANDLING =================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("❌ You don’t have permission.")
    else:
        print(error)

# ================= RUN =================
bot.run(TOKEN)
