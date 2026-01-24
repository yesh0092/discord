import os
import asyncio
import datetime
import io
import json
import random
import logging
from typing import Dict, Optional, Set
import discord
from discord.ext import commands
from discord import app_commands, ui
from dotenv import load_dotenv

# ================= SETUP LOGGING =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================= LOAD CONFIG =================
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    logger.error("TOKEN not found in .env file!")
    raise ValueError("Bot token missing!")

# ================= ENHANCED INTENTS =================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guild_reactions = True
intents.guild_emojis_and_stickers = True

# ================= BOT INITIALIZATION =================
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    case_insensitive=True,
    max_messages=None,
    sync_commands_debug=True
)

# ================= CONFIGURATION =================
CONFIG = {
    "staff_roles": ["Staff", "Admin", "Moderator"],
    "support_category": "SUPPORT",
    "colors": [0xD4AF37, 0xB8860B, 0xFFD700, 0xFFA500],
    "moon_icon": "https://cdn.discordapp.com/emojis/🌙.png",
    "welcome_gif": "https://cdn.discordapp.com/attachments/1458877508886855925/1460863224630218752/GIF_20260114_103833_065.gif?ex=6974fca6&is=6973ab26&hm=40a9ac40e118a4542ed23528c5977ba9b8c0b1fae8d03d02ce9115342d7be875&"
}

# ================= STATE MANAGEMENT =================
guild_data: Dict[int, Dict] = {}
def get_guild_data(guild_id: int) -> Dict:
    """Safe guild data access with auto-init"""
    if guild_id not in guild_data:
        guild_data[guild_id] = {
            "welcome_channel": None,
            "support_log": None,
            "auto_role": None,
            "reaction_roles_msg": None,
            "panel_channel": None,
            "onboarding": {},
            "open_tickets": {},
            "ticket_banned": set(),
            "stats": {"tickets": 0, "members": 0}
        }
    return guild_data[guild_id]

# ================= ENHANCED EMBED CLASS =================
class SafeEmbed(discord.Embed):
    """Crash-proof embed with validation"""
    def __init__(self, title: str, description: str = "", color: int = 0xD4AF37):
        try:
            super().__init__(
                title=f"🌙 {title[:256]}",
                description=description[:4096] or "✨ Premium Service Active",
                color=random.choice(CONFIG["colors"]) if color == 0xD4AF37 else color,
                timestamp=datetime.datetime.utcnow()
            )
            self.set_footer(
                text="Sawal Jawab Elite Assistant | Premier Support System",
                icon_url=CONFIG["moon_icon"]
            )
            self.set_thumbnail(url=CONFIG["moon_icon"])
        except Exception as e:
            logger.error(f"Embed creation failed: {e}")
            super().__init__(title="System Error", color=0xFF4444)

# ================= SAFE UTILITY FUNCTIONS =================
async def safe_send(channel, **kwargs):
    """Safely send message with error handling"""
    try:
        if 'embed' in kwargs and not isinstance(kwargs['embed'], discord.Embed):
            kwargs['embed'] = SafeEmbed("Error", "Invalid embed format")
        
        if 'content' in kwargs:
            kwargs['content'] = kwargs['content'][:2000]
        
        return await channel.send(**kwargs)
    except discord.HTTPException as e:
        logger.error(f"Failed to send message: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected send error: {e}")
        return None

def is_authorized_member(member: discord.Member, guild_id: int) -> bool:
    """Enhanced permission check"""
    if not member or not member.guild:
        return False
    
    guild_data_guild = get_guild_data(guild_id)
    if member.guild_permissions.administrator:
        return True
    
    member_roles = [role.name for role in member.roles]
    return any(role in CONFIG["staff_roles"] for role in member_roles)

# ================= ENHANCED TRANSCRIPT SYSTEM =================
async def create_transcript(channel: discord.TextChannel, max_messages: int = 1000) -> Optional[discord.File]:
    """Safe transcript generation with limits"""
    try:
        log = io.StringIO()
        log.write(f"🕰️ Transcript for #{channel.name} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        log.write("=" * 80 + "\n\n")
        
        message_count = 0
        async for msg in channel.history(limit=max_messages, oldest_first=True):
            if message_count >= max_messages:
                log.write(f"[... {channel.history(limit=None).count() - max_messages} more messages ...]\n")
                break
                
            content = msg.content or '[Attachment/Media]'
            log.write(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] ")
            log.write(f"{msg.author.display_name} ({msg.author.id}): ")
            log.write(f"{content[:1000]}\n")
            message_count += 1
        
        transcript_bytes = io.BytesIO(log.getvalue().encode('utf-8'))
        return discord.File(transcript_bytes, f"transcript-{channel.name}-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}.txt")
    except Exception as e:
        logger.error(f"Transcript error: {e}")
        return None

# ================= ONBOARDING SYSTEM =================
class OnboardingView(ui.View):
    def __init__(self, user: discord.User, guild_id: int):
        super().__init__(timeout=1800)  # 30 minutes
        self.user = user
        self.guild_id = guild_id

    async def complete_onboarding(self, interaction: discord.Interaction):
        """Safely complete onboarding"""
        try:
            guild_data_guild = get_guild_data(self.guild_id)
            guild_data_guild["onboarding"].pop(self.user.id, None)
            
            embed = SafeEmbed("✨ Access Granted", 
                            "Welcome to premium services!\n\n"
                            "💎 DM `support` for assistance\n"
                            "⭐ React for roles\n"
                            "🎫 Use /elite_panel")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Onboarding completion error: {e}")

    @ui.button(label="👥 Friends", style=discord.ButtonStyle.primary)
    async def friends(self, interaction: discord.Interaction, button: ui.Button):
        await self.complete_onboarding(interaction)

    @ui.button(label="📱 Social", style=discord.ButtonStyle.secondary)
    async def social(self, interaction: discord.Interaction, button: ui.Button):
        await self.complete_onboarding(interaction)

    @ui.button(label="🔮 Other", style=discord.ButtonStyle.success)
    async def other(self, interaction: discord.Interaction, button: ui.Button):
        await self.complete_onboarding(interaction)

# ================= TICKET SYSTEM =================
class TicketModal(ui.Modal, title="Ticket Details"):
    def __init__(self, user: discord.User, ticket_type: str, guild_id: int):
        super().__init__(title=f"🌙 {ticket_type} Ticket")
        self.user = user
        self.ticket_type = ticket_type
        self.guild_id = guild_id
        self.description = ui.TextInput(
            label="Issue Description",
            style=discord.TextStyle.paragraph,
            placeholder="Describe your issue in detail...",
            max_length=2000,
            required=True
        )
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        await self.create_ticket_channel(interaction)

    async def create_ticket_channel(self, interaction: discord.Interaction):
        """Crash-safe ticket creation"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("❌ Guild not found", ephemeral=True)
                return

            guild_data_guild = get_guild_data(self.guild_id)
            
            # Safety checks
            if self.user.id in guild_data_guild["ticket_banned"]:
                embed = SafeEmbed("🚫 Banned", "Ticket creation restricted", 0xFF4444)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            if self.user.id in guild_data_guild["open_tickets"]:
                channel = guild.get_channel(guild_data_guild["open_tickets"][self.user.id])
                embed = SafeEmbed("⏳ Active Ticket", f"You have #{channel.name}", 0xFFAA00)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Create channel safely
            category = discord.utils.get(guild.categories, name=CONFIG["support_category"])
            if not category:
                embed = SafeEmbed("⚠️ Setup Required", f"Create '{CONFIG['support_category']}' category", 0xFFAA00)
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            
            # Add staff role permissions
            for role_name in CONFIG["staff_roles"]:
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True, manage_messages=True
                    )

            channel_name = f"ticket-{self.ticket_type[:10]}-{self.user.name[:8]}"
            channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)
            
            # Track ticket
            guild_data_guild["open_tickets"][self.user.id] = channel.id
            guild_data_guild["stats"]["tickets"] += 1

            # Send ticket message
            embed = SafeEmbed(
                f"🎫 {self.ticket_type} Ticket",
                f"**User:** {self.user.mention}\n**Issue:** {self.description.value[:500]}"
            )
            view = CloseTicketView(self.user.id, self.guild_id)
            await channel.send(embed=embed, view=view)

            embed = SafeEmbed("✅ Ticket Created", f"Support: {channel.mention}")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Ticket creation error: {e}")
            embed = SafeEmbed("❌ Error", "Ticket creation failed. Try again.", 0xFF4444)
            await interaction.response.send_message(embed=embed, ephemeral=True)

class CloseTicketView(ui.View):
    def __init__(self, owner_id: int, guild_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id
        self.guild_id = guild_id

    @ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        if not is_authorized_member(interaction.user, self.guild_id) and interaction.user.id != self.owner_id:
            embed = SafeEmbed("❌ Unauthorized", "Only owner/staff can close", 0xFF4444)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Disable button
        button.disabled = True
        await interaction.response.edit_message(view=self)

        # Generate transcript
        transcript = await create_transcript(interaction.channel)
        
        # Log and delete
        guild_data_guild = get_guild_data(self.guild_id)
        guild_data_guild["open_tickets"].pop(self.owner_id, None)
        
        if transcript and guild_data_guild["support_log"]:
            log_channel = interaction.guild.get_channel(guild_data_guild["support_log"])
            if log_channel:
                await safe_send(log_channel, embed=SafeEmbed("📄 Transcript", f"Closed #{interaction.channel.name}"), file=transcript)
        
        await asyncio.sleep(3)
        await interaction.channel.delete()

class TicketSelectView(ui.View):
    def __init__(self, user: discord.User, guild_id: int):
        super().__init__(timeout=600)
        self.user = user
        self.guild_id = guild_id

    @ui.select(
        placeholder="Select ticket type...",
        options=[
            discord.SelectOption(label="General Help", emoji="❓"),
            discord.SelectOption(label="Billing", emoji="💳"),
            discord.SelectOption(label="Technical", emoji="🔧"),
            discord.SelectOption(label="Report", emoji="🚨"),
            discord.SelectOption(label="Mobile", emoji="📱")
        ]
    )
    async def select_ticket(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.send_modal(TicketModal(self.user, select.values[0], self.guild_id))

# ================= MAIN SUPPORT PANEL =================
class SupportPanel(ui.View):
    def __init__(self, user: discord.User, guild_id: int):
        super().__init__(timeout=1800)
        self.user = user
        self.guild_id = guild_id

    @ui.button(label="🎫 Create Ticket", style=discord.ButtonStyle.primary)
    async def create_ticket(self, interaction: discord.Interaction, button: ui.Button):
        embed = SafeEmbed("📋 Ticket Types", "Select your issue category:")
        await interaction.response.send_message(embed=embed, view=TicketSelectView(self.user, self.guild_id), ephemeral=True)

    @ui.button(label="📊 My Tickets", style=discord.ButtonStyle.secondary)
    async def my_tickets(self, interaction: discord.Interaction, button: ui.Button):
        guild_data_guild = get_guild_data(self.guild_id)
        if self.user.id in guild_data_guild["open_tickets"]:
            channel = interaction.guild.get_channel(guild_data_guild["open_tickets"][self.user.id])
            embed = SafeEmbed("📊 Active", f"Your ticket: {channel.mention}")
        else:
            embed = SafeEmbed("📋 No Tickets", "Create a new ticket above")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= SLASH COMMANDS =================
@bot.tree.command(name="setup", description="🔧 Complete bot setup")
@app_commands.describe(channel="Set welcome/log channel")
async def setup(interaction: discord.Interaction, channel: discord.TextChannel = None):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Admin only", ephemeral=True)
        return

    guild_data_guild = get_guild_data(interaction.guild.id)
    target_channel = channel or interaction.channel
    
    guild_data_guild["welcome_channel"] = target_channel.id
    guild_data_guild["support_log"] = target_channel.id
    
    embed = SafeEmbed("✅ Setup Complete", 
                     f"Welcome: {target_channel.mention}\n"
                     f"Logs: {target_channel.mention}\n\n"
                     f"Next: `/panel` | `!autorole @role`")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="panel", description="🎫 Deploy support panel")
async def panel(interaction: discord.Interaction):
    embed = SafeEmbed("🌙 Support Hub", 
                     "Click buttons for premium support services")
    embed.set_image(url=CONFIG["welcome_gif"])
    view = SupportPanel(interaction.user, interaction.guild.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="stats", description="📊 Server stats")
async def stats(interaction: discord.Interaction):
    guild_data_guild = get_guild_data(interaction.guild.id)
    embed = SafeEmbed("📊 Statistics",
                     f"Members: {len(interaction.guild.members):,}\n"
                     f"Tickets: {guild_data_guild['stats']['tickets']}\n"
                     f"Active: {len(guild_data_guild['open_tickets'])}")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= EVENTS =================
@bot.event
async def on_ready():
    logger.info(f"✅ {bot.user} - ELITE MODE ACTIVE")
    logger.info(f"📊 Guilds: {len(bot.guilds)}")
    
    # Sync slash commands for main guild
    for guild in bot.guilds[:3]:  # Limit sync
        try:
            synced = await bot.tree.sync(guild=guild)
            logger.info(f"✅ Synced {len(synced)} commands to {guild.name}")
        except Exception as e:
            logger.error(f"Sync failed for {guild.name}: {e}")

@bot.event
async def on_member_join(member: discord.Member):
    """Safe welcome system"""
    try:
        guild_data_guild = get_guild_data(member.guild.id)
        
        # Auto role
        if guild_data_guild["auto_role"]:
            role = member.guild.get_role(guild_data_guild["auto_role"])
            if role:
                await member.add_roles(role)

        # Welcome channel
        if guild_data_guild["welcome_channel"]:
            channel = member.guild.get_channel(guild_data_guild["welcome_channel"])
            if channel:
                embed = SafeEmbed("✨ Welcome", f"{member.mention} joined!")
                await safe_send(channel, embed=embed)

        # DM welcome
        try:
            embed = SafeEmbed("🔮 Welcome", "DM `support` for help")
            view = SupportPanel(member, member.guild.id)
            await member.send(embed=embed, view=view)
        except discord.Forbidden:
            logger.info(f"DMs disabled for {member}")
            
    except Exception as e:
        logger.error(f"Join event error: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # DM Support trigger
    if isinstance(message.channel, discord.DMChannel):
        if message.content.lower() in ["support", "help", "ticket"]:
            embed = SafeEmbed("💎 Support", "Choose your service:")
            view = SupportPanel(message.author, 0)  # DM mode
            await safe_send(message.channel, embed=embed, view=view)

    await bot.process_commands(message)

# ================= PREFIX COMMANDS =================
@bot.command()
@commands.has_permissions(administrator=True)
async def autorole(ctx: commands.Context, *, role: discord.Role):
    get_guild_data(ctx.guild.id)["auto_role"] = role.id
    await safe_send(ctx, embed=SafeEmbed("✅ Auto Role", f"{role.mention}"))

@bot.command()
async def help(ctx: commands.Context):
    embed = SafeEmbed("📜 Commands",
                     "**Slash:** `/setup /panel /stats`\n"
                     "**Prefix:** `!autorole !help`\n"
                     "**DM:** `support`")
    await safe_send(ctx, embed=embed)

# ================= RUN BOT =================
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        logger.error("Invalid TOKEN!")
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
