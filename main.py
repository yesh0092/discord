import os
import asyncio
import datetime
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ================= BASIC SETUP =================
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN missing")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# ================= CONFIG =================
STAFF_ROLE = "Staff"
SUPPORT_CATEGORY = "SUPPORT"

WELCOME_CHANNEL_ID = None
PERSONAL_SUPPORT_LOG_ID = None

# ================= STATE =================
TICKET_BANS = {}   # user_id -> datetime | "perm"
OPEN_TICKETS = set()

# ================= HELPERS =================
def parse_duration(text):
    now = datetime.datetime.utcnow()
    if text == "perm":
        return "perm"
    if text.endswith("h"):
        return now + datetime.timedelta(hours=int(text[:-1]))
    if text.endswith("d"):
        return now + datetime.timedelta(days=int(text[:-1]))
    if text.endswith("w"):
        return now + datetime.timedelta(weeks=int(text[:-1]))
    if text.endswith("m"):
        return now + datetime.timedelta(days=30*int(text[:-1]))
    return None

def is_banned(user_id):
    ban = TICKET_BANS.get(user_id)
    if not ban:
        return False
    if ban == "perm":
        return True
    if datetime.datetime.utcnow() > ban:
        del TICKET_BANS[user_id]
        return False
    return True

# ================= SUPPORT VIEW =================
class TicketView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=60)
        self.user = user

    @discord.ui.button(label="Open Support Ticket", emoji="🎟", style=discord.ButtonStyle.primary)
    async def open_ticket(self, interaction, _):
        if is_banned(self.user.id):
            await interaction.response.send_message(
                "You are currently restricted from creating support tickets.",
                ephemeral=True
            )
            return

        guild = bot.guilds[0]
        staff = discord.utils.get(guild.roles, name=STAFF_ROLE)
        category = discord.utils.get(guild.categories, name=SUPPORT_CATEGORY)

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

        await channel.send(
            embed=discord.Embed(
                title="Support Ticket",
                description=(
                    f"{self.user.mention}\n\n"
                    "This is a private space.\n"
                    "Staff will assist you here.\n\n"
                    "*Describe your issue clearly.*"
                ),
                color=0x020617
            )
        )

        await interaction.response.send_message(
            "Your support ticket has been opened.",
            ephemeral=True
        )

# ================= DM HANDLER =================
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        if message.content.lower() == "support":
            await message.channel.send(
                "Support is handled through private tickets.",
                view=TicketView(message.author)
            )
            return

        if message.content.lower() == "personal":
            if PERSONAL_SUPPORT_LOG_ID:
                log = bot.guilds[0].get_channel(PERSONAL_SUPPORT_LOG_ID)
                if log:
                    await log.send(
                        embed=discord.Embed(
                            title="Personal Assistance Request",
                            description=f"{message.author.mention} | `{message.author.id}`",
                            color=0x7c2d12
                        )
                    )
            await message.author.send(
                "Your request has been received.\n"
                "A staff member will contact you within 24 hours."
            )
            return

    await bot.process_commands(message)

# ================= ADMIN COMMANDS =================
@bot.command()
@commands.has_permissions(administrator=True)
async def support(ctx):
    global PERSONAL_SUPPORT_LOG_ID
    PERSONAL_SUPPORT_LOG_ID = ctx.channel.id
    await ctx.send("✅ Personal support log channel set.")

@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    global WELCOME_CHANNEL_ID
    WELCOME_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ Welcome channel set.")

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketban(ctx, member: discord.Member, duration: str):
    ban = parse_duration(duration)
    if not ban:
        await ctx.send("Invalid duration.")
        return
    TICKET_BANS[member.id] = ban
    await ctx.send(f"🚫 {member} banned from tickets.")

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketunban(ctx, member: discord.Member):
    TICKET_BANS.pop(member.id, None)
    await ctx.send(f"✅ {member} can create tickets again.")

# ================= READY =================
@bot.event
async def on_ready():
    print(f"✅ {bot.user} online")

# ================= RUN =================
bot.run(TOKEN)
