import os
import asyncio
import datetime
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ======================================================
# BASIC SETUP
# ======================================================

load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN not found")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# ======================================================
# GIF / IMAGE CONFIG (EDIT HERE ONLY)
# ======================================================

GIF_WELCOME_DM = ""
GIF_ONBOARDING = ""
GIF_SUPPORT_PANEL = ""
GIF_TICKET_CREATED = ""
GIF_PERSONAL_ASSIST = ""

# ======================================================
# CONFIG
# ======================================================

STAFF_ROLE_NAME = "Staff"
SUPPORT_CATEGORY_NAME = "SUPPORT"

WELCOME_CHANNEL_ID = None
SUPPORT_LOG_CHANNEL_ID = None

# ======================================================
# STATE
# ======================================================

ONBOARDING_MESSAGES = {}
TICKET_COOLDOWNS = {}
TICKET_BANS = {}
OPEN_TICKETS = set()

# ======================================================
# UTILITIES
# ======================================================

def utcnow():
    return datetime.datetime.utcnow()

def can_create_ticket(user_id):
    if user_id in OPEN_TICKETS:
        return False, "You already have an open ticket."

    if user_id in TICKET_BANS:
        ban = TICKET_BANS[user_id]
        if ban == "perm":
            return False, "You are restricted from creating tickets."
        if utcnow() < ban:
            return False, "You are temporarily restricted from creating tickets."
        del TICKET_BANS[user_id]

    last = TICKET_COOLDOWNS.get(user_id)
    if last and utcnow() - last < datetime.timedelta(hours=24):
        return False, "You can only create one ticket every 24 hours."

    return True, None

# ======================================================
# ONBOARDING VIEW
# ======================================================

class OnboardingView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    async def finish(self, interaction):
        msg_id = ONBOARDING_MESSAGES.pop(self.user.id, None)
        if msg_id:
            try:
                msg = await interaction.channel.fetch_message(msg_id)
                await msg.delete()
            except:
                pass

        await interaction.response.send_message(
            "Thank you ✨ Enjoy your time here.",
            ephemeral=True
        )

    @discord.ui.button(label="Friends", emoji="👥", style=discord.ButtonStyle.primary)
    async def friends(self, interaction, _):
        await self.finish(interaction)

    @discord.ui.button(label="Social Media", emoji="🌐", style=discord.ButtonStyle.secondary)
    async def social(self, interaction, _):
        await self.finish(interaction)

    @discord.ui.button(label="Other", emoji="✨", style=discord.ButtonStyle.success)
    async def other(self, interaction, _):
        await self.finish(interaction)

# ======================================================
# TICKET VIEW
# ======================================================

class TicketView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user

    @discord.ui.button(label="Open Support Ticket", emoji="🎟", style=discord.ButtonStyle.primary)
    async def open_ticket(self, interaction, _):
        allowed, reason = can_create_ticket(self.user.id)
        if not allowed:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        guild = bot.guilds[0]
        staff = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        category = discord.utils.get(guild.categories, name=SUPPORT_CATEGORY_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if staff:
            overwrites[staff] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            f"ticket-{self.user.name.lower()}",
            overwrites=overwrites,
            category=category
        )

        OPEN_TICKETS.add(self.user.id)
        TICKET_COOLDOWNS[self.user.id] = utcnow()

        await channel.send(
            embed=discord.Embed(
                title="Support Ticket",
                description=(
                    f"{self.user.mention}\n\n"
                    "This is a private support space.\n"
                    "Staff will assist you here."
                ),
                color=0x020617
            )
        )

        if GIF_TICKET_CREATED:
            await self.user.send(GIF_TICKET_CREATED)

        if SUPPORT_LOG_CHANNEL_ID:
            log = guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log:
                await log.send(
                    f"🎟 Ticket opened by {self.user.mention} → {channel.mention}"
                )

        await interaction.response.send_message(
            "Your ticket has been opened.",
            ephemeral=True
        )

# ======================================================
# MEMBER JOIN
# ======================================================

@bot.event
async def on_member_join(member):
    if WELCOME_CHANNEL_ID:
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            await channel.send(f"✨ {member.mention} joined the server")

    try:
        await member.send(
            f"👋 Welcome to **{member.guild.name}**!\n"
            "If you need help, DM me `support`."
        )
        if GIF_WELCOME_DM:
            await member.send(GIF_WELCOME_DM)

        embed = discord.Embed(
            title="One quick question",
            description="How did you find this server?",
            color=0x020617
        )
        msg = await member.send(embed=embed, view=OnboardingView(member))
        if GIF_ONBOARDING:
            await member.send(GIF_ONBOARDING)

        ONBOARDING_MESSAGES[member.id] = msg.id
    except:
        pass

# ======================================================
# DM HANDLER
# ======================================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        if message.author.id in ONBOARDING_MESSAGES:
            try:
                msg = await message.channel.fetch_message(
                    ONBOARDING_MESSAGES.pop(message.author.id)
                )
                await msg.delete()
            except:
                pass
            await message.channel.send("Thank you ✨")
            return

        if message.content.lower() == "support":
            await message.channel.send(
                "Support is handled through tickets.",
                view=TicketView(message.author)
            )
            if GIF_SUPPORT_PANEL:
                await message.channel.send(GIF_SUPPORT_PANEL)
            return

        if message.content.lower() == "personal":
            if SUPPORT_LOG_CHANNEL_ID:
                log = bot.guilds[0].get_channel(SUPPORT_LOG_CHANNEL_ID)
                if log:
                    await log.send(
                        f"🧑‍💼 Personal assistance requested by {message.author.mention}"
                    )
            await message.author.send(
                "A staff member will contact you within 24 hours."
            )
            if GIF_PERSONAL_ASSIST:
                await message.author.send(GIF_PERSONAL_ASSIST)
            return

    await bot.process_commands(message)

# ======================================================
# ADMIN COMMANDS
# ======================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    global WELCOME_CHANNEL_ID
    WELCOME_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ Welcome channel set.")

@bot.command()
@commands.has_permissions(administrator=True)
async def supportlog(ctx):
    global SUPPORT_LOG_CHANNEL_ID
    SUPPORT_LOG_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ Support log channel set.")

@bot.command()
async def help(ctx):
    await ctx.send(
        "**Commands**\n"
        "`support` – DM bot to open ticket\n"
        "`personal` – DM bot for private help\n"
        "`!welcome` – set welcome channel\n"
        "`!supportlog` – set support log channel"
    )

# ======================================================
# READY
# ======================================================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} online")

bot.run(TOKEN)
