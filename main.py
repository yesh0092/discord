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

# ================= STATE =================
WELCOME_CHANNEL_ID = None  # set by !welcome command

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over the server 🌙"
        )
    )

# ================= ONBOARDING BUTTON VIEW =================
class OnboardingSourceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def thank_you(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "Thank you for letting us know 💫\n"
            "Enjoy your time in the server — we’re glad to have you here!",
            ephemeral=True
        )

    @discord.ui.button(label="Friends", emoji="👥", style=discord.ButtonStyle.primary)
    async def friends(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.thank_you(interaction)

    @discord.ui.button(label="Social Media", emoji="🌐", style=discord.ButtonStyle.secondary)
    async def social(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.thank_you(interaction)

    @discord.ui.button(label="Other", emoji="✨", style=discord.ButtonStyle.success)
    async def other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.thank_you(interaction)

# ================= MEMBER JOIN =================
@bot.event
async def on_member_join(member: discord.Member):
    # ---- DM WELCOME ----
    try:
        await asyncio.sleep(2)
        await member.send(
            f"👋 **Welcome to {member.guild.name}!**\n\n"
            "We’re happy to have you here 💖\n"
            "Enjoy your time with us and feel free to explore.\n\n"
            "🛟 If you ever need **support**, just DM me anytime.\n\n"
            "**Before you start — how did you find this server?** 👇"
        )
        await member.send(view=OnboardingSourceView())
    except discord.Forbidden:
        pass  # user has DMs closed

    # ---- SERVER JOIN MESSAGE ----
    if WELCOME_CHANNEL_ID:
        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                description=f"✨ **{member.mention} just joined the server!**\nWelcome aboard 💫",
                color=0x1f2937
            )
            await channel.send(embed=embed)

# ================= SET WELCOME CHANNEL COMMAND =================
@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    """
    Set the current channel as the welcome channel
    """
    global WELCOME_CHANNEL_ID
    WELCOME_CHANNEL_ID = ctx.channel.id

    embed = discord.Embed(
        title="Welcome Channel Set",
        description=(
            f"This channel will now receive join messages.\n\n"
            f"Channel: {ctx.channel.mention}"
        ),
        color=0x10b981
    )
    await ctx.send(embed=embed)

# ================= BASIC TEST COMMAND =================
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong! I’m online and working.")

# ================= ERROR HANDLING =================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need **Administrator** permission to use this command.")
    else:
        print(error)

# ================= RUN =================
bot.run(TOKEN)
