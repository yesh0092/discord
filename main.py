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
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

WELCOME_CHANNEL_ID = None
ONBOARDING_MESSAGES = {}  # user_id -> message_id

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="welcoming quietly 🌙"
        )
    )

# ================= ONBOARDING VIEW =================
class OnboardingView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=120)
        self.user = user

    async def finish_onboarding(self, interaction: discord.Interaction):
        # Delete onboarding message
        msg_id = ONBOARDING_MESSAGES.pop(self.user.id, None)
        if msg_id:
            try:
                msg = await interaction.channel.fetch_message(msg_id)
                await msg.delete()
            except:
                pass

        await interaction.response.send_message(
            "Thank you 💫\nEnjoy your time here — we’re glad you joined.",
            ephemeral=True
        )

    @discord.ui.button(label="Friends", emoji="👥", style=discord.ButtonStyle.primary)
    async def friends(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish_onboarding(interaction)

    @discord.ui.button(label="Social Media", emoji="🌐", style=discord.ButtonStyle.secondary)
    async def social(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish_onboarding(interaction)

    @discord.ui.button(label="Other", emoji="✨", style=discord.ButtonStyle.success)
    async def other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish_onboarding(interaction)

# ================= MEMBER JOIN =================
@bot.event
async def on_member_join(member: discord.Member):
    # ---- DM WELCOME (PERMANENT) ----
    try:
        await asyncio.sleep(2)
        await member.send(
            f"👋 **Welcome to {member.guild.name}!**\n\n"
            "Enjoy your time with us 💖\n"
            "This server is built to stay calm and friendly.\n\n"
            "🛟 If you ever need **support**, just DM me anytime."
        )
    except discord.Forbidden:
        return

    # ---- DM ONBOARDING (TEMPORARY) ----
    await asyncio.sleep(1)
    try:
        embed = discord.Embed(
            title="One quick question",
            description="How did you find this server?",
            color=0x020617
        )
        onboarding_msg = await member.send(
            embed=embed,
            view=OnboardingView(member)
        )
        ONBOARDING_MESSAGES[member.id] = onboarding_msg.id
    except discord.Forbidden:
        pass

    # ---- SERVER JOIN MESSAGE ----
    if WELCOME_CHANNEL_ID:
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                description=f"✨ **{member.mention} just joined the server!**\nWelcome 💫",
                color=0x1f2937
            )
            await channel.send(embed=embed)

# ================= DM TEXT REPLY HANDLER =================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # If user replies in DM instead of clicking
    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id

        if user_id in ONBOARDING_MESSAGES:
            try:
                msg = await message.channel.fetch_message(ONBOARDING_MESSAGES[user_id])
                await msg.delete()
            except:
                pass

            ONBOARDING_MESSAGES.pop(user_id, None)

            await message.channel.send(
                "Thank you 💫\nEnjoy your time here — we’re glad you joined."
            )
            return

    await bot.process_commands(message)

# ================= SET WELCOME CHANNEL =================
@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    global WELCOME_CHANNEL_ID
    WELCOME_CHANNEL_ID = ctx.channel.id

    embed = discord.Embed(
        title="Welcome Channel Set",
        description=f"Join messages will be sent in {ctx.channel.mention}",
        color=0x10b981
    )
    await ctx.send(embed=embed)

# ================= TEST =================
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong — all systems active.")

# ================= RUN =================
bot.run(TOKEN)
