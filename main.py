import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv

# ================= BASIC SETUP =================

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ================= CONFIG =================

STAFF_ROLE_NAME = "Staff"
SUPPORT_CATEGORY_NAME = "SUPPORT"

THEME_DARK = 0x020617
THEME_SOFT = 0x1f2937
THEME_ERROR = 0x7c2d12
THEME_SUCCESS = 0x064e3b

GIF_WELCOME = ""
GIF_ONBOARDING = ""
GIF_SUPPORT = ""

# ================= STATE =================

MAIN_GUILD_ID = None
WELCOME_CHANNEL_ID = None
SUPPORT_LOG_CHANNEL_ID = None
AUTO_ROLE_ID = None

ONBOARDING_MESSAGES = {}
OPEN_TICKETS = {}
TICKET_BANNED_USERS = set()

# ================= HELPERS =================

def guild():
    return bot.get_guild(MAIN_GUILD_ID) if MAIN_GUILD_ID else None

def embed(desc, color=THEME_DARK, title=None):
    e = discord.Embed(description=desc, color=color)
    if title:
        e.title = title
    return e

def is_staff_or_admin(member):
    if member.guild_permissions.administrator:
        return True
    staff = discord.utils.get(member.guild.roles, name=STAFF_ROLE_NAME)
    return staff in member.roles if staff else False

# ================= ONBOARDING =================

class OnboardingView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=120)
        self.user = user

    async def finish(self, interaction):
        msg_id = ONBOARDING_MESSAGES.pop(self.user.id, None)
        if msg_id:
            try:
                await interaction.channel.delete_messages(
                    [await interaction.channel.fetch_message(msg_id)]
                )
            except:
                pass

        await interaction.response.send_message(
            embed("✨ Thanks for joining — enjoy your stay!", THEME_SUCCESS),
            ephemeral=True
        )

    @discord.ui.button(label="Friends", style=discord.ButtonStyle.primary)
    async def friends(self, interaction, _): await self.finish(interaction)

    @discord.ui.button(label="Social Media", style=discord.ButtonStyle.secondary)
    async def social(self, interaction, _): await self.finish(interaction)

    @discord.ui.button(label="Other", style=discord.ButtonStyle.success)
    async def other(self, interaction, _): await self.finish(interaction)

# ================= CLOSE TICKET =================

class CloseTicketView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="Close Ticket", emoji="🔒", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button):
        if not (
            interaction.user.id == self.owner_id
            or is_staff_or_admin(interaction.user)
        ):
            await interaction.response.send_message(
                embed("🚫 You don’t have permission to close this ticket.", THEME_ERROR),
                ephemeral=True
            )
            return

        button.disabled = True
        await interaction.message.edit(view=self)

        await interaction.response.send_message(
            embed("✅ Ticket closed. Archiving channel…", THEME_SOFT)
        )

        OPEN_TICKETS.pop(self.owner_id, None)

        if SUPPORT_LOG_CHANNEL_ID:
            log = interaction.guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log:
                await log.send(
                    embed(
                        f"🔒 Ticket closed by **{interaction.user}**",
                        THEME_SOFT
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
    async def open_ticket(self, interaction, _):
        g = guild()
        if not g:
            return await interaction.response.send_message(
                embed("Support system not configured yet.", THEME_ERROR),
                ephemeral=True
            )

        if self.user.id in TICKET_BANNED_USERS:
            return await interaction.response.send_message(
                embed("🚫 You are restricted from creating tickets.", THEME_ERROR),
                ephemeral=True
            )

        if self.user.id in OPEN_TICKETS:
            return await interaction.response.send_message(
                embed("⚠ You already have an open ticket.", THEME_SOFT),
                ephemeral=True
            )

        staff = discord.utils.get(g.roles, name=STAFF_ROLE_NAME)
        category = discord.utils.get(g.categories, name=SUPPORT_CATEGORY_NAME)

        overwrites = {
            g.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if staff:
            overwrites[staff] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ch = await g.create_text_channel(
            f"ticket-{self.user.name}",
            overwrites=overwrites,
            category=category
        )

        OPEN_TICKETS[self.user.id] = ch.id

        await ch.send(
            embed(
                f"{self.user.mention}\n🧑‍💼 A staff member will assist you shortly.",
                THEME_DARK,
                "🎟 Support Ticket"
            ),
            view=CloseTicketView(self.user.id)
        )

        if SUPPORT_LOG_CHANNEL_ID:
            log = g.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log:
                await log.send(embed(f"🎟 Ticket opened by {self.user.mention}", THEME_SOFT))

        await interaction.response.send_message(
            embed("✅ Your ticket has been created.", THEME_SUCCESS),
            ephemeral=True
        )

# ================= TICKET BAN =================

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketban(ctx, user: discord.Member):
    TICKET_BANNED_USERS.add(user.id)
    await ctx.send(embed(f"🚫 {user.mention} is banned from tickets.", THEME_ERROR))

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketunban(ctx, user: discord.Member):
    TICKET_BANNED_USERS.discard(user.id)
    await ctx.send(embed(f"✅ {user.mention} can now create tickets.", THEME_SUCCESS))

# ================= READY =================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online")

bot.run(TOKEN)
