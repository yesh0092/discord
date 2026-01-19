import os
import asyncio
import datetime
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# ======================================================
# ENV & BASIC SETUP
# ======================================================

load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN not set")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.presences = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None  # 🔴 FIXES YOUR ERROR
)

# ======================================================
# STATE (IN-MEMORY, CLEAN)
# ======================================================

WELCOME_CHANNEL_ID = None
SUPPORT_LOG_CHANNEL_ID = None
ANNOUNCE_USERS = set()
ONBOARDING_MESSAGES = {}

# ======================================================
# MEDIA CONFIG (OPTIONAL)
# ======================================================

WELCOME_GIF = ""
SUPPORT_CHOICE_GIF = ""
PERSONAL_SUPPORT_GIF = ""
TICKET_SUPPORT_GIF = ""

# ======================================================
# DYNAMIC STATUS SYSTEM
# ======================================================

@tasks.loop(minutes=30)
async def dynamic_status():
    hour = datetime.datetime.now().hour

    if 5 <= hour < 10:
        text = "Good morning ☀"
    elif 10 <= hour < 15:
        text = "Midday calm 🌤"
    elif 15 <= hour < 19:
        text = "Evening silence 🌇"
    elif 19 <= hour < 23:
        text = "Night mode 🌙"
    else:
        text = "Midnight stillness 🌑"

    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=text
        )
    )

# ======================================================
# READY
# ======================================================

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    dynamic_status.start()

# ======================================================
# ONBOARDING VIEW
# ======================================================

class OnboardingView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=120)
        self.user = user

    async def finish(self, interaction: discord.Interaction):
        msg_id = ONBOARDING_MESSAGES.pop(self.user.id, None)
        if msg_id:
            try:
                msg = await interaction.channel.fetch_message(msg_id)
                await msg.delete()
            except:
                pass

        await interaction.response.send_message(
            "Thank you ✨\nEnjoy your time here.",
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
# SUPPORT VIEW
# ======================================================

class SupportView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=120)
        self.user = user

    async def log(self, description: str):
        if SUPPORT_LOG_CHANNEL_ID:
            channel = bot.guilds[0].get_channel(SUPPORT_LOG_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="Support Request",
                    description=description,
                    color=0x1f2937
                )
                await channel.send(embed=embed)

    @discord.ui.button(label="Personal Assistance", emoji="🧑‍💼", style=discord.ButtonStyle.primary)
    async def personal(self, interaction, _):
        await self.log(
            f"👤 {self.user.mention}\n🆔 `{self.user.id}`\n\nPersonal assistance requested."
        )
        await interaction.response.send_message(
            "A staff member will contact you within **24 hours**.",
            ephemeral=True
        )
        if PERSONAL_SUPPORT_GIF:
            await self.user.send(PERSONAL_SUPPORT_GIF)

    @discord.ui.button(label="Open Server Ticket", emoji="🎟", style=discord.ButtonStyle.secondary)
    async def ticket(self, interaction, _):
        await self.log(
            f"👤 {self.user.mention}\n🆔 `{self.user.id}`\n\nServer ticket requested."
        )
        await interaction.response.send_message(
            "Staff will assist you shortly in the server.",
            ephemeral=True
        )
        if TICKET_SUPPORT_GIF:
            await self.user.send(TICKET_SUPPORT_GIF)

# ======================================================
# MEMBER JOIN
# ======================================================

@bot.event
async def on_member_join(member: discord.Member):
    ANNOUNCE_USERS.add(member.id)

    try:
        await member.send(
            f"👋 **Welcome to {member.guild.name}!**\n\n"
            "Enjoy your time here.\n"
            "If you ever need help, DM me `support`."
        )
        if WELCOME_GIF:
            await member.send(WELCOME_GIF)
    except:
        return

    embed = discord.Embed(
        title="One quick question",
        description="How did you find this server?",
        color=0x020617
    )
    msg = await member.send(embed=embed, view=OnboardingView(member))
    ONBOARDING_MESSAGES[member.id] = msg.id

    if WELCOME_CHANNEL_ID:
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            await channel.send(
                embed=discord.Embed(
                    description=f"✨ **{member.mention} joined the server**",
                    color=0x1f2937
                )
            )

# ======================================================
# DM HANDLER
# ======================================================

@bot.event
async def on_message(message: discord.Message):
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

            await message.channel.send("Thank you ✨ Enjoy your time here.")
            return

        if message.content.lower() == "support":
            await message.channel.send(
                "How would you like to proceed?",
                view=SupportView(message.author)
            )
            if SUPPORT_CHOICE_GIF:
                await message.channel.send(SUPPORT_CHOICE_GIF)
            return

    await bot.process_commands(message)

# ======================================================
# COMMANDS
# ======================================================

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong — system online.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="Command Menu",
        description=(
            "`!ping` – Bot status\n"
            "`!help` – This menu\n"
            "`!botinfo` – Bot information\n"
            "`!welcome` – Set welcome channel (Admin)\n"
            "`!support` – Set support logs channel (Admin)\n"
            "`!announce <msg>` – Send announcement (Admin)"
        ),
        color=0x1f2937
    )
    await ctx.send(embed=embed)

@bot.command()
async def botinfo(ctx):
    embed = discord.Embed(
        title="Bot Info",
        description="Luxury onboarding & support bot",
        color=0x020617
    )
    embed.add_field(name="Version", value="Ultimate v1.0")
    embed.add_field(name="Status", value="Operational")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    global WELCOME_CHANNEL_ID
    WELCOME_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ Welcome channel set.")

@bot.command()
@commands.has_permissions(administrator=True)
async def support(ctx):
    global SUPPORT_LOG_CHANNEL_ID
    SUPPORT_LOG_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ Support log channel set.")

@bot.command()
@commands.has_permissions(administrator=True)
async def announce(ctx, *, message):
    sent = 0
    for uid in list(ANNOUNCE_USERS):
        try:
            user = await bot.fetch_user(uid)
            await user.send(
                embed=discord.Embed(
                    title="📢 Announcement",
                    description=message,
                    color=0x020617
                )
            )
            sent += 1
            await asyncio.sleep(1)
        except:
            ANNOUNCE_USERS.discard(uid)

    await ctx.send(f"Announcement sent to {sent} users.")

# ======================================================
# RUN
# ======================================================

bot.run(TOKEN)
