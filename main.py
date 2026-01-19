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
OPEN_TICKETS = {}

# 🔹 ADDED (ticket ban system – nothing removed)
TICKET_BANNED_USERS = set()

# ================= HELPERS =================

def get_guild():
    return bot.get_guild(MAIN_GUILD_ID) if MAIN_GUILD_ID else None

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
        guild = interaction.guild
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        # 🔹 ONLY ADDITION: administrator permission
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

        await interaction.response.send_message(
            embed=discord.Embed(
                description="Ticket closed. This space will be archived.",
                color=0x020617
            )
        )

        OPEN_TICKETS.pop(self.owner_id, None)

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

        # 🔹 ADDED: ticket ban check
        if self.user.id in TICKET_BANNED_USERS:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="You are restricted from creating support tickets.",
                    color=0x7c2d12
                ),
                ephemeral=True
            )
            return

        if self.user.id in OPEN_TICKETS:
            await interaction.response.send_message(
                "You already have an active ticket.",
                ephemeral=True
            )
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

# ================= MEMBER JOIN =================

@bot.event
async def on_member_join(member):
    if AUTO_ROLE_ID:
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role:
            await member.add_roles(role)

    if WELCOME_CHANNEL_ID:
        ch = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if ch:
            await ch.send(
                embed=discord.Embed(
                    description=f"✨ {member.mention} joined the server",
                    color=0x1f2937
                )
            )

    try:
        await member.send(
            f"Welcome to **{member.guild.name}**.\n"
            "If you need help, DM me `support`."
        )
        if GIF_WELCOME:
            await member.send(GIF_WELCOME)

        embed = discord.Embed(
            title="One quick question",
            description="How did you discover this server?",
            color=0x020617
        )
        msg = await member.send(embed=embed, view=OnboardingView(member))
        ONBOARDING_MESSAGES[member.id] = msg.id

        if GIF_ONBOARDING:
            await member.send(GIF_ONBOARDING)
    except:
        pass

# ================= DM HANDLER =================

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
                "How would you like to proceed?",
                view=SupportView(message.author)
            )
            if GIF_SUPPORT:
                await message.channel.send(GIF_SUPPORT)
            return

    await bot.process_commands(message)

# ================= COMMANDS =================

@bot.command()
async def help(ctx):
    await ctx.send(
        embed=discord.Embed(
            title="Bot Commands",
            description=(
                "`support` → DM the bot for support\n"
                "`!announce <message>` → DM announcement (Admin)\n"
                "`!welcome` → set welcome channel (Admin)\n"
                "`!supportlog` → set support log channel (Admin)\n"
                "`!autorole @role` → auto role on join"
            ),
            color=0x020617
        )
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    global WELCOME_CHANNEL_ID, MAIN_GUILD_ID
    WELCOME_CHANNEL_ID = ctx.channel.id
    MAIN_GUILD_ID = ctx.guild.id
    await ctx.send(embed=discord.Embed(description="Welcome channel set.", color=0x020617))

@bot.command()
@commands.has_permissions(administrator=True)
async def supportlog(ctx):
    global SUPPORT_LOG_CHANNEL_ID, MAIN_GUILD_ID
    SUPPORT_LOG_CHANNEL_ID = ctx.channel.id
    MAIN_GUILD_ID = ctx.guild.id
    await ctx.send(embed=discord.Embed(description="Support log channel set.", color=0x020617))

@bot.command()
@commands.has_permissions(administrator=True)
async def autorole(ctx, role: discord.Role):
    global AUTO_ROLE_ID, MAIN_GUILD_ID
    AUTO_ROLE_ID = role.id
    MAIN_GUILD_ID = ctx.guild.id
    await ctx.send(embed=discord.Embed(description="Auto role set.", color=0x020617))

# ================= ADDED COMMANDS =================

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketban(ctx, user: discord.Member):
    TICKET_BANNED_USERS.add(user.id)
    await ctx.send(embed=discord.Embed(
        description=f"{user.mention} has been banned from creating tickets.",
        color=0x7c2d12
    ))

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketunban(ctx, user: discord.Member):
    TICKET_BANNED_USERS.discard(user.id)
    await ctx.send(embed=discord.Embed(
        description=f"{user.mention} can create tickets again.",
        color=0x020617
    ))

# ================= DM ANNOUNCE =================

@bot.command()
@commands.has_permissions(administrator=True)
async def announce(ctx, *, message: str):
    guild = ctx.guild
    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=0x020617
    )
    embed.set_footer(text=guild.name)

    sent = 0
    failed = 0

    for member in guild.members:
        if member.bot:
            continue
        try:
            await member.send(embed=embed)
            sent += 1
            await asyncio.sleep(1)
        except:
            failed += 1

    await ctx.send(
        embed=discord.Embed(
            description=f"Announcement sent.\nDelivered: {sent}\nFailed: {failed}",
            color=0x1f2937
        )
    )

# ================= READY =================

@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Game("!help | Open ticket")
    )
    print(f"✅ {bot.user} is online (idle)")
