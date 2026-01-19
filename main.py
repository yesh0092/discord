import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ================= LOAD TOKEN =================
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN not set")

# ================= INTENTS =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= ADMIN-SET CHANNELS =================
WELCOME_CHANNEL_ID = None
SUPPORT_LOG_CHANNEL_ID = None

# ================= GIF / IMAGE CONFIG =================
WELCOME_GIF = ""   # optional
ONBOARDING_GIF = ""  # optional
SUPPORT_GIF = ""   # optional

# ================= ONBOARDING STATE =================
ONBOARDING_MESSAGES = {}

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

# ================= ONBOARDING VIEW =================
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
            "Thank you for sharing ✨\n"
            "Enjoy your time here — we’re glad to have you.",
            ephemeral=True
        )

    @discord.ui.button(label="Friends", emoji="👥", style=discord.ButtonStyle.primary)
    async def friends(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish(interaction)

    @discord.ui.button(label="Social Media", emoji="🌐", style=discord.ButtonStyle.secondary)
    async def social(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish(interaction)

    @discord.ui.button(label="Other", emoji="✨", style=discord.ButtonStyle.success)
    async def other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish(interaction)

# ================= MEMBER JOIN =================
@bot.event
async def on_member_join(member: discord.Member):
    # ---- DM WELCOME ----
    try:
        await asyncio.sleep(2)
        await member.send(
            f"👋 **Welcome to {member.guild.name}!**\n\n"
            "We’re happy to have you here.\n"
            "Take your time, explore freely, and enjoy the atmosphere ✨\n\n"
            "🛟 If you ever need **support**, just DM me `support`."
        )
        if WELCOME_GIF:
            await member.send(WELCOME_GIF)
    except:
        return

    # ---- DM ONBOARDING (TEMPORARY) ----
    await asyncio.sleep(1)
    embed = discord.Embed(
        title="One quick question",
        description="How did you find this server?",
        color=0x020617
    )
    msg = await member.send(embed=embed, view=OnboardingView(member))
    ONBOARDING_MESSAGES[member.id] = msg.id

    # ---- SERVER WELCOME MESSAGE ----
    if WELCOME_CHANNEL_ID:
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                description=f"✨ **{member.mention} joined the server**\nWelcome and enjoy your stay 💫",
                color=0x1f2937
            )
            await channel.send(embed=embed)

# ================= DM MESSAGE HANDLER =================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ---- DM SUPPORT ----
    if isinstance(message.channel, discord.DMChannel):
        content = message.content.lower()

        # Remove onboarding if user replies
        if message.author.id in ONBOARDING_MESSAGES:
            try:
                msg = await message.channel.fetch_message(
                    ONBOARDING_MESSAGES.pop(message.author.id)
                )
                await msg.delete()
            except:
                pass

            await message.channel.send(
                "Thank you ✨\nEnjoy your time here — we’re glad you joined."
            )
            return

        if content == "support":
            await handle_support_request(message.author)
            return

    await bot.process_commands(message)

# ================= SUPPORT HANDLER =================
async def handle_support_request(user: discord.User):
    if SUPPORT_LOG_CHANNEL_ID:
        guild = bot.guilds[0]
        log_channel = guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="New Support Request",
                description=(
                    f"👤 User: {user.mention}\n"
                    f"🆔 ID: `{user.id}`\n\n"
                    "User requested support via DM."
                ),
                color=0x7c2d12
            )
            await log_channel.send(embed=embed)

    await user.send(
        "🛟 **Support Request Received**\n\n"
        "A staff member from the server will contact you in your DMs\n"
        "**within 24 hours**.\n\n"
        "Thank you for your patience 💫"
    )

    if SUPPORT_GIF:
        await user.send(SUPPORT_GIF)

# ================= ADMIN COMMANDS =================
@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    global WELCOME_CHANNEL_ID
    WELCOME_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ This channel is now set for welcome messages.")

@bot.command()
@commands.has_permissions(administrator=True)
async def support(ctx):
    global SUPPORT_LOG_CHANNEL_ID
    SUPPORT_LOG_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ This channel is now set for support logs.")

# ================= TEST =================
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong — system online.")

# ================= RUN =================
bot.run(TOKEN)
