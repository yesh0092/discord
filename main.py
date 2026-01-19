import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ================= LOAD ENV =================
load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN not set")

# ================= CONFIG =================
SUPPORT_ROLE = "Support"
ADMIN_ROLE = "Admin"
LOG_CHANNEL = "support-logs"
MODERATOR_ID = 123456789012345678  # 🔁 replace

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

# ================= ONBOARDING BUTTON VIEW =================
class OnboardingView(discord.ui.View):
    def __init__(self, member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="Support", emoji="🛟", style=discord.ButtonStyle.primary)
    async def support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "I’ve prepared a private space for you.",
            ephemeral=True
        )
        await create_support_room(self.member)

    @discord.ui.button(label="Creative Roles", emoji="🎨", style=discord.ButtonStyle.secondary)
    async def roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        moderator = await bot.fetch_user(MODERATOR_ID)
        await interaction.response.send_message(
            f"Some roles are handled personally.\nPlease reach out to {moderator.mention}.",
            ephemeral=True
        )
        await moderator.send(f"🎨 {self.member} is interested in a creative role.")

    @discord.ui.button(label="Events", emoji="📅", style=discord.ButtonStyle.success)
    async def events(self, interaction: discord.Interaction, button: discord.ui.Button):
        event_users.add(self.member.id)
        await interaction.response.send_message(
            "You’ll receive event updates here.",
            ephemeral=True
        )

    @discord.ui.button(label="Just Exploring", emoji="🌫", style=discord.ButtonStyle.secondary)
    async def explore(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Take your time. I’ll be here if you need me.",
            ephemeral=True
        )

# ================= WELCOME EMBED + DM =================
@bot.event
async def on_member_join(member):
    # ---- Server Welcome Embed ----
    if member.guild.system_channel:
        embed = discord.Embed(
            title="Welcome to HellFire",
            description=(
                f"{member.mention}\n\n"
                "A calm place. A private space.\n"
                "Move at your own pace."
            ),
            color=0x0f172a
        )
        embed.set_footer(text="HellFire • Private Community")
        await member.guild.system_channel.send(embed=embed)

    # ---- DM Onboarding ----
    await asyncio.sleep(3)
    try:
        embed = discord.Embed(
            title="Welcome",
            description=(
                "I’ll quietly guide you if you need help.\n\n"
                "Choose how you’d like to begin."
            ),
            color=0x020617
        )
        await member.send(embed=embed, view=OnboardingView(member))
    except discord.Forbidden:
        pass

# ================= SUPPORT ROOM =================
async def create_support_room(user):
    if user.id in active_rooms:
        return

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

    await channel.send(
        "**You’re safe here.**\n"
        "Explain what you need, and someone will assist you shortly."
    )

    log = discord.utils.get(guild.text_channels, name=LOG_CHANNEL)
    if log:
        await log.send(f"🕊 Support room opened for {user}")

# ================= COMMANDS (DEBUG & STAFF) =================
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong. Bot is working.")

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
        except:
            event_users.discard(uid)

    await ctx.send(f"Event sent to {sent} members.")

# ================= ERROR HANDLING =================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You don’t have permission.")
    else:
        print(error)

# ================= RUN =================
bot.run(TOKEN)
