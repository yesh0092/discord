import os
import asyncio
import datetime
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ================= BASIC SETUP =================

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# ================= CONFIG =================

STAFF_ROLE_NAME = "Staff"
SUPPORT_CATEGORY_NAME = "SUPPORT"

GIF_WELCOME = ""
GIF_ONBOARDING = ""
GIF_SUPPORT = ""

# ================= STATE =================

MAIN_GUILD_ID = None
WELCOME_CHANNEL_ID = None
SUPPORT_LOG_CHANNEL_ID = None
AUTO_ROLE_ID = None

ONBOARDING_MESSAGES = {}
OPEN_TICKETS = {}              # user_id -> channel_id
TICKET_COOLDOWNS = {}          # user_id -> datetime
TICKET_BANS = {}               # user_id -> datetime | "perm"

# ================= HELPERS =================

def get_guild():
    return bot.get_guild(MAIN_GUILD_ID) if MAIN_GUILD_ID else None

def now():
    return datetime.datetime.utcnow()

def parse_duration(arg: str):
    if arg == "perm":
        return "perm"
    try:
        value = int(arg[:-1])
        unit = arg[-1]
        if unit == "m":
            return now() + datetime.timedelta(minutes=value)
        if unit == "h":
            return now() + datetime.timedelta(hours=value)
        if unit == "d":
            return now() + datetime.timedelta(days=value)
    except:
        pass
    return None

def can_create_ticket(user: discord.Member):
    # Admin bypass
    if user.guild_permissions.administrator:
        return True, None

    ban = TICKET_BANS.get(user.id)
    if ban:
        if ban == "perm":
            return False, "You are restricted from creating support tickets."
        if now() < ban:
            return False, "You are temporarily restricted from creating tickets."
        del TICKET_BANS[user.id]

    last = TICKET_COOLDOWNS.get(user.id)
    if last and now() - last < datetime.timedelta(hours=24):
        return False, "Please wait before creating another ticket."

    if user.id in OPEN_TICKETS:
        return False, "You already have an active ticket."

    return True, None

# ================= ONBOARDING VIEW =================

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
            "Thank you. Enjoy your time here ✨",
            ephemeral=True
        )

    @discord.ui.button(label="Friends", style=discord.ButtonStyle.primary)
    async def friends(self, interaction, _):
        await self.finish(interaction)

    @discord.ui.button(label="Social Media", style=discord.ButtonStyle.secondary)
    async def social(self, interaction, _):
        await self.finish(interaction)

    @discord.ui.button(label="Other", style=discord.ButtonStyle.success)
    async def other(self, interaction, _):
        await self.finish(interaction)

# ================= CLOSE TICKET VIEW =================

class CloseTicketView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="Close Ticket", emoji="🔒", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if (
            interaction.user.id != self.owner_id
            and not interaction.user.guild_permissions.administrator
            and (not staff_role or staff_role not in interaction.user.roles)
        ):
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="You don’t have permission to close this ticket.",
                    color=0x7c2d12
                ),
                ephemeral=True
            )
            return

        button.disabled = True
        await interaction.message.edit(view=self)

        OPEN_TICKETS.pop(self.owner_id, None)

        await interaction.response.send_message(
            embed=discord.Embed(
                description="Ticket closed. This channel will be deleted.",
                color=0x020617
            )
        )

        await asyncio.sleep(3)
        await interaction.channel.delete()

# ================= SUPPORT VIEW =================

class SupportView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    @discord.ui.button(label="Open Support Ticket", emoji="🎟", style=discord.ButtonStyle.primary)
    async def ticket(self, interaction, _):
        guild = get_guild()
        if not guild:
            await interaction.response.send_message(
                "Support system is not configured yet.",
                ephemeral=True
            )
            return

        allowed, reason = can_create_ticket(self.user)
        if not allowed:
            await interaction.response.send_message(reason, ephemeral=True)
            return

        staff = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        category = discord.utils.get(guild.categories, name=SUPPORT_CATEGORY_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if staff:
            overwrites[staff] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            f"ticket-{self.user.name}",
            overwrites=overwrites,
            category=category
        )

        OPEN_TICKETS[self.user.id] = channel.id
        TICKET_COOLDOWNS[self.user.id] = now()

        await channel.send(
            embed=discord.Embed(
                title="Support Ticket",
                description=f"{self.user.mention}\nA staff member will assist you shortly.",
                color=0x020617
            ),
            view=CloseTicketView(self.user.id)
        )

        if SUPPORT_LOG_CHANNEL_ID:
            log = guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log:
                await log.send(
                    embed=discord.Embed(
                        description=f"🎟 Ticket opened by {self.user.mention}",
                        color=0x1f2937
                    )
                )

        await interaction.response.send_message(
            "Your ticket has been created.",
            ephemeral=True
        )

    @discord.ui.button(label="Personal Assistance", emoji="🧑‍💼", style=discord.ButtonStyle.secondary)
    async def personal(self, interaction, _):
        guild = get_guild()
        if SUPPORT_LOG_CHANNEL_ID and guild:
            log = guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log:
                await log.send(
                    embed=discord.Embed(
                        title="Personal Assistance",
                        description=f"{self.user.mention} requested personal help.",
                        color=0x7c2d12
                    )
                )

        await interaction.response.send_message(
            "A staff member will contact you privately within 24 hours.",
            ephemeral=True
        )

# ================= ADMIN TICKET BAN =================

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketban(ctx, member: discord.Member, duration: str):
    parsed = parse_duration(duration)
    if not parsed:
        await ctx.send("Invalid duration. Use `1h`, `1d`, `perm`.")
        return

    TICKET_BANS[member.id] = parsed
    await ctx.send(
        embed=discord.Embed(
            description=f"{member.mention} has been restricted from creating tickets.",
            color=0x7c2d12
        )
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketunban(ctx, member: discord.Member):
    TICKET_BANS.pop(member.id, None)
    await ctx.send(
        embed=discord.Embed(
            description=f"{member.mention} can create tickets again.",
            color=0x020617
        )
    )

# ================= READY =================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online")

bot.run(TOKEN)
