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

# ================= CONFIG =================
SUPPORT_ROLE = "Support"
ADMIN_ROLE = "Admin"
LOG_CHANNEL = "support-logs"
MODERATOR_ID = 123456789012345678  # 🔁 REPLACE WITH REAL USER ID

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
            name="over HellFire 🌙"
        )
    )

# ================= HELPER: FIND WELCOME CHANNEL =================
def get_welcome_channel(guild: discord.Guild):
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        return guild.system_channel

    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            return channel

    return None

# ================= ONBOARDING BUTTON VIEW =================
class OnboardingView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=None)
        self.member = member

    @discord.ui.button(label="Support", emoji="🛟", style=discord.ButtonStyle.primary)
    async def support(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Only administrators can open support rooms using this button.",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            "A private support space is being prepared.",
            ephemeral=True
        )
        await create_support_room(self.member)

    @discord.ui.button(label="Creative Roles", emoji="🎨", style=discord.ButtonStyle.secondary)
    async def roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        moderator = await bot.fetch_user(MODERATOR_ID)
        await interaction.response.send_message(
            f"Roles are handled personally.\nPlease contact {moderator.mention}.",
            ephemeral=True
        )
        await moderator.send(f"🎨 {self.member} wants a creative role.")

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
            "Take your time. I’ll be here when you need me.",
            ephemeral=True
        )

# ================= MEMBER JOIN (FULLY FIXED) =================
@bot.event
async def on_member_join(member: discord.Member):
    # ---- SERVER WELCOME ----
    channel = get_welcome_channel(member.guild)
    if channel:
        embed = discord.Embed(
            title="Welcome to HellFire",
            description=(
                f"{member.mention}\n\n"
                "A space built on calm, control, and presence.\n"
                "Move at your own pace."
            ),
            color=0x020617
        )
        embed.set_footer(text="HellFire • Private Community")
        await channel.send(embed=embed)
    else:
        print("⚠ No channel available for welcome message")

    # ---- DM ONBOARDING ----
    await asyncio.sleep(2)
    try:
        dm_embed = discord.Embed(
            title="Welcome",
            description=(
                "You’ve entered a controlled space.\n\n"
                "Use the options below to begin.\n"
                "Nothing here is rushed."
            ),
            color=0x020617
        )
        await member.send(embed=dm_embed, view=OnboardingView(member))
    except discord.Forbidden:
        print(f"⚠ Cannot DM {member}")

# ================= SUPPORT ROOM =================
async def create_support_room(user: discord.Member):
    if user.id in active_rooms:
        return

    guild = user.guild
    support_role = discord.utils.get(guild.roles, name=SUPPORT_ROLE)

    if not support_role:
        await user.send("Support role is not configured.")
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
        "Explain what you need. Staff will assist you."
    )

    log = discord.utils.get(guild.text_channels, name=LOG_CHANNEL)
    if log:
        await log.send(f"🕊 Support room opened for {user}")

# ================= COMMANDS =================
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong — system online.")

@bot.command()
@commands.has_permissions(administrator=True)
async def announce(ctx, *, message):
    sent = 0
    for uid in list(event_users):
        try:
            user = await bot.fetch_user(uid)
            embed = discord.Embed(
                title="Event Update",
                description=message,
                color=0x020617
            )
            await user.send(embed=embed)
            sent += 1
            await asyncio.sleep(1)
        except:
            event_users.discard(uid)

    await ctx.send(f"Event sent to {sent} users.")

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

# ================= ERRORS =================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don’t have permission to use this command.")
    else:
        print(error)

# ================= RUN =================
bot.run(TOKEN)
