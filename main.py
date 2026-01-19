import os
import asyncio
import datetime
import discord
import aiosqlite
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# ======================================================
# ENV / BOT SETUP
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

DB_PATH = "supportbot.db"

# ======================================================
# DATABASE
# ======================================================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS guilds (
            guild_id INTEGER PRIMARY KEY,
            welcome_channel INTEGER,
            support_log INTEGER,
            support_category INTEGER,
            staff_role INTEGER,
            auto_role INTEGER
        );

        CREATE TABLE IF NOT EXISTS tickets (
            user_id INTEGER,
            guild_id INTEGER,
            last_created TIMESTAMP,
            open INTEGER
        );

        CREATE TABLE IF NOT EXISTS ticket_bans (
            user_id INTEGER,
            guild_id INTEGER,
            until TIMESTAMP
        );
        """)
        await db.commit()

# ======================================================
# GIF CONFIG
# ======================================================

GIF_WELCOME = ""
GIF_ONBOARDING = ""
GIF_SUPPORT_PANEL = ""
GIF_TICKET_CREATED = ""
GIF_TICKET_CLOSED = ""

# ======================================================
# READY
# ======================================================

@bot.event
async def on_ready():
    await init_db()
    await bot.tree.sync()
    print(f"✅ {bot.user} online")

# ======================================================
# UTILITIES
# ======================================================

def now():
    return datetime.datetime.utcnow()

# ======================================================
# ONBOARDING VIEW
# ======================================================

class OnboardingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    async def disable(self, interaction):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Friends", style=discord.ButtonStyle.primary)
    async def friends(self, interaction, _):
        await self.disable(interaction)
        await interaction.response.send_message(
            "Thank you. Enjoy your time here.", ephemeral=True
        )

    @discord.ui.button(label="Social Media", style=discord.ButtonStyle.secondary)
    async def social(self, interaction, _):
        await self.disable(interaction)
        await interaction.response.send_message(
            "Thank you. Enjoy your time here.", ephemeral=True
        )

    @discord.ui.button(label="Other", style=discord.ButtonStyle.success)
    async def other(self, interaction, _):
        await self.disable(interaction)
        await interaction.response.send_message(
            "Thank you. Enjoy your time here.", ephemeral=True
        )

# ======================================================
# TICKET VIEW
# ======================================================

class TicketView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction, _):
        if not interaction.channel.name.startswith("ticket-"):
            return

        transcript = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            transcript.append(f"[{msg.created_at}] {msg.author}: {msg.content}")

        content = "\n".join(transcript)[:1900]

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE tickets SET open=0 WHERE user_id=?",
                (self.user_id,)
            )
            await db.commit()

        await interaction.channel.send("Ticket closed.")
        await asyncio.sleep(2)
        await interaction.channel.delete()

        if GIF_TICKET_CLOSED:
            user = await bot.fetch_user(self.user_id)
            await user.send(GIF_TICKET_CLOSED)

# ======================================================
# MEMBER JOIN
# ======================================================

@bot.event
async def on_member_join(member):
    async with aiosqlite.connect(DB_PATH) as db:
        row = await db.execute_fetchone(
            "SELECT welcome_channel, auto_role FROM guilds WHERE guild_id=?",
            (member.guild.id,)
        )

    if row:
        welcome_ch, auto_role = row
        if welcome_ch:
            channel = member.guild.get_channel(welcome_ch)
            if channel:
                await channel.send(f"✨ {member.mention} joined")

        if auto_role:
            role = member.guild.get_role(auto_role)
            if role:
                await member.add_roles(role)

    try:
        await member.send("Welcome. If you need help, type `support`.")
        if GIF_WELCOME:
            await member.send(GIF_WELCOME)

        embed = discord.Embed(
            title="One question",
            description="How did you find this server?"
        )
        await member.send(embed=embed, view=OnboardingView())
        if GIF_ONBOARDING:
            await member.send(GIF_ONBOARDING)
    except:
        pass

# ======================================================
# DM SUPPORT
# ======================================================

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if isinstance(message.channel, discord.DMChannel):
        if message.content.lower() == "support":
            await message.channel.send(
                "Support is handled through private tickets.",
                view=discord.ui.View().add_item(
                    discord.ui.Button(
                        label="Open Ticket",
                        style=discord.ButtonStyle.primary,
                        custom_id="open_ticket"
                    )
                )
            )
            if GIF_SUPPORT_PANEL:
                await message.channel.send(GIF_SUPPORT_PANEL)
            return

    await bot.process_commands(message)

# ======================================================
# SLASH COMMANDS
# ======================================================

@bot.tree.command(name="support")
async def slash_support(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Please DM me `support` to open a ticket.",
        ephemeral=True
    )

@bot.tree.command(name="help")
async def slash_help(interaction: discord.Interaction):
    await interaction.response.send_message(
        "This is a private support bot.\nUse DM commands.",
        ephemeral=True
    )

# ======================================================
# ADMIN COMMANDS
# ======================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx, welcome=None, log=None, category=None, staff=None, autorole=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "REPLACE INTO guilds VALUES (?,?,?,?,?,?)",
            (
                ctx.guild.id,
                ctx.channel.id if welcome else None,
                ctx.channel.id if log else None,
                category.id if category else None,
                staff.id if staff else None,
                autorole.id if autorole else None
            )
        )
        await db.commit()
    await ctx.send("Setup complete.")

# ======================================================
# RUN
# ======================================================

bot.run(TOKEN)
