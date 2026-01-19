import os
import asyncio
import datetime
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# ======================================================
# BASIC SETUP
# ======================================================

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

# ======================================================
# CONFIG (EDIT)
# ======================================================

STAFF_ROLE_NAME = "Staff"
SUPPORT_CATEGORY_NAME = "SUPPORT"

GIF_WELCOME_DM = ""
GIF_ONBOARDING = ""
GIF_SUPPORT_PANEL = ""
GIF_TICKET_CREATED = ""

# ======================================================
# STATE (IN-MEMORY)
# ======================================================

WELCOME_CHANNEL_ID = None
SUPPORT_LOG_CHANNEL_ID = None
AUTO_ROLE_ID = None

ONBOARDING_MESSAGES = {}
TICKET_COOLDOWNS = {}
OPEN_TICKETS = {}

# ======================================================
# UTILITIES
# ======================================================

def now():
    return datetime.datetime.utcnow()

def can_create_ticket(user_id):
    last = TICKET_COOLDOWNS.get(user_id)
    if last and now() - last < datetime.timedelta(hours=24):
        return False
    if user_id in OPEN_TICKETS:
        return False
    return True

# ======================================================
# ONBOARDING VIEW
# ======================================================

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

        for item in self.children:
            item.disabled = True

        await interaction.response.send_message(
            embed=discord.Embed(
                description="Thank you ✨ Enjoy your time here.",
                color=0x020617
            ),
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
# TICKET CLOSE VIEW
# ======================================================

class CloseTicketView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @discord.ui.button(label="Close Ticket", emoji="🔒", style=discord.ButtonStyle.danger)
    async def close(self, interaction, button):
        if interaction.user.id != self.owner_id and not any(
            r.name == STAFF_ROLE_NAME for r in interaction.user.roles
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

        # Transcript
        transcript = []
        async for msg in interaction.channel.history(oldest_first=True):
            transcript.append(f"[{msg.created_at}] {msg.author}: {msg.content}")

        text = "\n".join(transcript)[:1900]

        if SUPPORT_LOG_CHANNEL_ID:
            log = interaction.guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log:
                await log.send(
                    embed=discord.Embed(
                        title="Ticket Transcript",
                        description=f"```\n{text}\n```",
                        color=0x1f2937
                    )
                )

        OPEN_TICKETS.pop(self.owner_id, None)

        await interaction.response.send_message(
            embed=discord.Embed(
                description="Ticket closed. This channel will be deleted.",
                color=0x020617
            )
        )
        await asyncio.sleep(3)
        await interaction.channel.delete()

# ======================================================
# MEMBER JOIN
# ======================================================

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
            embed=discord.Embed(
                title=f"Welcome to {member.guild.name}",
                description="If you need help, DM me `support`.",
                color=0x020617
            )
        )
        if GIF_WELCOME_DM:
            await member.send(GIF_WELCOME_DM)

        embed = discord.Embed(
            title="One quick question",
            description="How did you find this server?",
            color=0x020617
        )
        msg = await member.send(embed=embed, view=OnboardingView(member))
        ONBOARDING_MESSAGES[member.id] = msg.id

        if GIF_ONBOARDING:
            await member.send(GIF_ONBOARDING)
    except:
        pass

# ======================================================
# DM HANDLER
# ======================================================

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
            await message.channel.send(
                embed=discord.Embed(
                    description="Thank you ✨",
                    color=0x020617
                )
            )
            return

        if message.content.lower() == "support":
            if not can_create_ticket(message.author.id):
                await message.channel.send(
                    embed=discord.Embed(
                        description="You can create one ticket per day.",
                        color=0x7c2d12
                    )
                )
                return

            guild = bot.guilds[0]
            staff = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
            category = discord.utils.get(guild.categories, name=SUPPORT_CATEGORY_NAME)

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                message.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                staff: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            channel = await guild.create_text_channel(
                f"ticket-{message.author.name}",
                overwrites=overwrites,
                category=category
            )

            OPEN_TICKETS[message.author.id] = channel.id
            TICKET_COOLDOWNS[message.author.id] = now()

            await channel.send(
                embed=discord.Embed(
                    title="Support Ticket",
                    description="Staff will assist you here.",
                    color=0x020617
                ),
                view=CloseTicketView(message.author.id)
            )

            if GIF_TICKET_CREATED:
                await message.author.send(GIF_TICKET_CREATED)

            if SUPPORT_LOG_CHANNEL_ID:
                log = guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
                if log:
                    await log.send(
                        embed=discord.Embed(
                            description=f"🎟 Ticket opened by {message.author.mention}",
                            color=0x1f2937
                        )
                    )
            return

    await bot.process_commands(message)

# ======================================================
# COMMANDS
# ======================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    global WELCOME_CHANNEL_ID
    WELCOME_CHANNEL_ID = ctx.channel.id
    await ctx.send(embed=discord.Embed(description="Welcome channel set.", color=0x020617))

@bot.command()
@commands.has_permissions(administrator=True)
async def supportlog(ctx):
    global SUPPORT_LOG_CHANNEL_ID
    SUPPORT_LOG_CHANNEL_ID = ctx.channel.id
    await ctx.send(embed=discord.Embed(description="Support log channel set.", color=0x020617))

@bot.command()
@commands.has_permissions(administrator=True)
async def autorole(ctx, role: discord.Role):
    global AUTO_ROLE_ID
    AUTO_ROLE_ID = role.id
    await ctx.send(embed=discord.Embed(description="Auto role set.", color=0x020617))

@bot.command()
async def help(ctx):
    await ctx.send(
        embed=discord.Embed(
            title="Help",
            description="DM `support` to open a ticket.",
            color=0x020617
        )
    )

# ======================================================
# SLASH COMMANDS
# ======================================================

@bot.tree.command(name="support")
async def slash_support(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=discord.Embed(
            description="Please DM me `support` to open a ticket.",
            color=0x020617
        ),
        ephemeral=True
    )

@bot.tree.command(name="ping")
async def slash_ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong.", ephemeral=True)

# ======================================================
# READY
# ======================================================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ {bot.user} online")

bot.run(TOKEN)
