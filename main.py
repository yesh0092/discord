import os
import asyncio
import datetime
import io
import json
import random
from typing import Dict, Optional, Set
import discord
from discord.ext import commands
from discord import app_commands, ui
from dotenv import load_dotenv

# ================= ULTIMATE LUXURY SETUP =================
load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guild_reactions = True
intents.guild_emojis_and_stickers = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# ================= PREMIUM CONFIGURATION =================
STAFF_ROLE_NAME = "Staff"
SUPPORT_CATEGORY_NAME = "SUPPORT"
ADMIN_ROLE_NAME = "Admin"
MOD_ROLE_NAME = "Moderator"

GIF_WELCOME = "https://cdn.discordapp.com/attachments/1458877508886855925/1460863224630218752/GIF_20260114_103833_065.gif?ex=6974fca6&is=6973ab26&hm=40a9ac40e118a4542ed23528c5977ba9b8c0b1fae8d03d02ce9115342d7be875&"
GIF_ONBOARDING = ""
GIF_SUPPORT = ""
MOON_ICON = "https://cdn.discordapp.com/emojis/🌙.png"
GOLD_COLOR = 0xD4AF37
NAVY_COLOR = 0x0C1445
PREMIUM_COLORS = [0xD4AF37, 0xB8860B, 0xFFD700, 0xFFA500]

# ================= COMPREHENSIVE STATE MANAGEMENT =================
MAIN_GUILD_ID = None
WELCOME_CHANNEL_ID = None
SUPPORT_LOG_CHANNEL_ID = None
AUTO_ROLE_ID = None
REACTION_ROLES_MSG_ID = None
PANEL_CHANNEL_ID = None
FAQ_CHANNEL_ID = None

ONBOARDING_MESSAGES: Dict[int, int] = {}
OPEN_TICKETS: Dict[int, int] = {}
TICKET_BANNED_USERS: Set[int] = set()
TICKET_STATS: Dict[str, int] = {}
REACTION_ROLES: Dict[str, int] = {}
SERVER_STATS = {"total_members": 0, "tickets_created": 0}

# ================= ULTIMATE LUXURY EMBED SYSTEM =================
class LuxuryEmbed(discord.Embed):
    """Premium embed system with gold/navy theme and moon branding"""
    def __init__(self, title: str, description: str = "", color: int = GOLD_COLOR):
        super().__init__(
            title=f"🌙 {title}",
            description=description or "✨ Premium Service Active",
            color=random.choice(PREMIUM_COLORS) if color == GOLD_COLOR else color,
            timestamp=datetime.datetime.utcnow()
        )
        self.set_footer(
            text="Sawal Jawab Elite Assistant | Premier Support System", 
            icon_url=MOON_ICON
        )
        self.set_thumbnail(url=MOON_ICON)

# ================= ADVANCED HELPER FUNCTIONS =================
def get_guild() -> Optional[discord.Guild]:
    """Get main guild with error handling"""
    return bot.get_guild(MAIN_GUILD_ID) if MAIN_GUILD_ID else None

def is_staff_or_admin(member: discord.Member) -> bool:
    """Check if user has staff/admin permissions"""
    staff_role = discord.utils.get(member.guild.roles, name=STAFF_ROLE_NAME)
    admin_role = discord.utils.get(member.guild.roles, name=ADMIN_ROLE_NAME)
    mod_role = discord.utils.get(member.guild.roles, name=MOD_ROLE_NAME)
    return (member.guild_permissions.administrator or 
            staff_role in member.roles or 
            admin_role in member.roles or 
            mod_role in member.roles)

async def send_transcript(channel: discord.TextChannel):
    """Generate comprehensive ticket transcript"""
    try:
        log = io.StringIO()
        log.write(f"🕰️  Transcript for #{channel.name} - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        log.write("=" * 80 + "\n\n")
        
        async for msg in channel.history(limit=None, oldest_first=True):
            log.write(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] ")
            log.write(f"{msg.author.display_name} ({msg.author.id}): ")
            log.write(f"{msg.content or '[Attachment/Media]'}\n")
        
        transcript_bytes = io.BytesIO(log.getvalue().encode('utf-8'))
        file = discord.File(transcript_bytes, f"elite-transcript-{channel.name}-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}.txt")
        
        guild = channel.guild
        if SUPPORT_LOG_CHANNEL_ID:
            log_ch = guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log_ch:
                embed = LuxuryEmbed("📄 Elite Transcript", f"Generated from closed #{channel.name}")
                await log_ch.send(embed=embed, file=file)
    except Exception as e:
        print(f"Transcript error: {e}")

# ================= ENHANCED ONBOARDING SYSTEM =================
class OnboardingView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=600)  # Extended timeout
        self.user = user

    async def finish_onboarding(self, interaction: discord.Interaction):
        """Complete onboarding with cleanup"""
        msg_id = ONBOARDING_MESSAGES.pop(self.user.id, None)
        if msg_id:
            try:
                msg = await interaction.channel.fetch_message(msg_id)
                await msg.delete()
            except:
                pass
        
        embed = LuxuryEmbed("✨ Elite Access Granted", 
                           "Welcome to the premium realm. Your journey begins now.\n\n"
                           "💎 **Elite Services Available:**\n"
                           "• DM `support` for premium assistance\n"
                           "• React for roles in designated channels\n"
                           "• Use /elite_panel for full services")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="👥 Friends", style=discord.ButtonStyle.primary, emoji="⭐")
    async def friends(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish_onboarding(interaction)

    @discord.ui.button(label="📱 Social Media", style=discord.ButtonStyle.secondary, emoji="💎")
    async def social(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish_onboarding(interaction)

    @discord.ui.button(label="🔮 Other", style=discord.ButtonStyle.success, emoji="🌙")
    async def other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish_onboarding(interaction)

# ================= PREMIUM TICKET MANAGEMENT =================
class CloseTicketView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)  # Persistent
        self.owner_id = owner_id

    @discord.ui.button(label="🔒 Close Elite Ticket", emoji="👑", style=discord.ButtonStyle.danger)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        
        # Enhanced permission check
        if (interaction.user.id != self.owner_id and 
            not interaction.user.guild_permissions.administrator and
            (not staff_role or staff_role not in interaction.user.roles)):
            embed = LuxuryEmbed("❌ Access Denied", 
                               "Only ticket owner or staff can close this ticket.", 
                               0xFF4444)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Disable button and show closing status
        button.disabled = True
        await interaction.message.edit(view=self)
        
        embed = LuxuryEmbed("🔒 Ticket Sealed", 
                           "Generating premium transcript...\n"
                           "This channel will be archived in 5 seconds.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Remove from active tickets
        OPEN_TICKETS.pop(self.owner_id, None)
        
        # Generate and send transcript
        await send_transcript(interaction.channel)
        
        await asyncio.sleep(5)
        await interaction.channel.delete()

# ================= ADVANCED TICKET SELECTION =================
class TicketSelectView(discord.ui.View):
    """Premium ticket type selector"""
    def __init__(self, user: discord.User):
        super().__init__(timeout=600)
        self.user = user

    @discord.ui.select(
        placeholder="🎫 Select Elite Ticket Type...",
        options=[
            discord.SelectOption(label="❓ General Help", emoji="⭐", description="Account, rules, general questions"),
            discord.SelectOption(label="💳 Billing", emoji="💎", description="Payments, subscriptions, refunds"),
            discord.SelectOption(label="🔧 Technical", emoji="⚙️", description="Bugs, errors, technical issues"),
            discord.SelectOption(label="🚨 Report", emoji="👮", description="User reports, violations"),
            discord.SelectOption(label="📱 Mobile", emoji="📱", description="App-specific issues")
        ],
        max_values=1
    )
    async def ticket_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        ticket_type = select.values[0]
        await interaction.response.send_modal(TicketDetailModal(self.user, ticket_type))

class TicketDetailModal(ui.Modal, title="📝 Elite Ticket Details"):
    def __init__(self, user: discord.User, ticket_type: str):
        super().__init__(title=f"🌙 {ticket_type} Ticket")
        self.user = user
        self.ticket_type = ticket_type
        self.description = ui.TextInput(
            label="Detailed Issue Description",
            style=discord.TextStyle.paragraph,
            placeholder="Please provide full details of your issue...",
            max_length=2000,
            required=True
        )
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        guild = get_guild()
        if not guild:
            embed = LuxuryEmbed("⚠️ Configuration Error", 
                               "Support system not configured. Contact admin.", 
                               0xFFAA00)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Comprehensive checks
        if self.user.id in TICKET_BANNED_USERS:
            embed = LuxuryEmbed("🚫 Access Denied", 
                               "You are restricted from creating tickets.", 
                               0xFF4444)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if self.user.id in OPEN_TICKETS:
            active_channel = guild.get_channel(OPEN_TICKETS[self.user.id])
            embed = LuxuryEmbed("⏳ Active Ticket", 
                               f"You already have #{active_channel.name}", 
                               0xFFAA00)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # Create premium ticket channel
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        category = discord.utils.get(guild.categories, name=SUPPORT_CATEGORY_NAME)
        
        if not category:
            embed = LuxuryEmbed("⚠️ Setup Required", 
                               f"Please create '{SUPPORT_CATEGORY_NAME}' category.", 
                               0xFFAA00)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            staff_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True) if staff_role else None
        }

        # Create uniquely named channel
        channel_name = f"elite-{self.ticket_type.lower().replace(' ', '-')}-{self.user.name[:8]}"
        channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)
        OPEN_TICKETS[self.user.id] = channel.id
        
        # Track statistics
        TICKET_STATS[self.ticket_type] = TICKET_STATS.get(self.ticket_type, 0) + 1
        SERVER_STATS["tickets_created"] += 1

        # Send premium welcome message
        welcome_embed = LuxuryEmbed(
            f"🎟 {self.ticket_type} Support Ticket",
            f"**Elite User:** {self.user.mention} ({self.user.id})\n"
            f"**Issue:** {self.description.value[:500]}{'...' if len(self.description.value) > 500 else ''}\n\n"
            f"🌟 **Premium staff will assist you shortly.**\n"
            f"📊 **Status:** Waiting for elite response",
            NAVY_COLOR
        )
        welcome_embed.add_field(name="Ticket ID", value=str(channel.id)[-6:], inline=True)
        welcome_embed.add_field(name="Type", value=self.ticket_type, inline=True)
        
        await channel.send(embed=welcome_embed, view=CloseTicketView(self.user.id))

        # Log to support channel
        if SUPPORT_LOG_CHANNEL_ID:
            log_channel = guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = LuxuryEmbed(
                    "📊 Elite Ticket Log", 
                    f"**{self.user}** opened **{self.ticket_type}** ticket\n"
                    f"**Channel:** {channel.mention}\n"
                    f"**ID:** {channel.id}",
                    0xB8860B
                )
                await log_channel.send(embed=log_embed)

        embed = LuxuryEmbed("✅ Elite Ticket Created", 
                           f"Your premium support channel: **{channel.mention}**\n"
                           f"Staff assigned - elite response guaranteed.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= COMPREHENSIVE SUPPORT HUB =================
class SupportView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=1800)  # 30 minutes
        self.user = user

    @discord.ui.button(label="🎟 Create Elite Ticket", style=discord.ButtonStyle.primary, emoji="🌙")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = LuxuryEmbed("📋 Ticket Categories", 
                           "Please select the appropriate category for your issue:")
        await interaction.response.send_message(embed=embed, view=TicketSelectView(self.user), ephemeral=True)

    @discord.ui.button(label="🧑‍💼 Private Elite Assist", style=discord.ButtonStyle.secondary, emoji="💎")
    async def private_assist(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = get_guild()
        if SUPPORT_LOG_CHANNEL_ID and guild:
            log_channel = guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log_channel:
                embed = LuxuryEmbed("💎 Elite Private Request", 
                                   f"{self.user.mention} ({self.user.id}) requested private assistance.\n"
                                   f"**Priority:** High - 24h response guaranteed")
                await log_channel.send(embed=embed)
        
        embed = LuxuryEmbed("💎 Elite Request Received", 
                           "Your private assistance request has been logged.\n"
                           "An elite staff member will contact you within **24 hours**.\n"
                           "⏰ **Reference ID:** PRIV-{self.user.id}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📊 My Tickets", style=discord.ButtonStyle.success, emoji="📋")
    async def my_tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = get_guild()
        if self.user.id in OPEN_TICKETS and guild:
            channel = guild.get_channel(OPEN_TICKETS[self.user.id])
            if channel:
                embed = LuxuryEmbed("📊 Active Ticket", f"You have an active ticket: **{channel.mention}**")
                return await interaction.response.send_message(embed=embed, ephemeral=True)
        
        embed = LuxuryEmbed("📋 No Active Tickets", "Create a new elite ticket using the button above.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= ULTIMATE ELITE PANEL =================
class ElitePanelView(discord.ui.View):
    """Persistent premium support panel"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎟 Elite Tickets", style=discord.ButtonStyle.primary, emoji="🌙")
    async def tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = LuxuryEmbed("💎 Premium Support Hub", "Access elite ticket services")
        await interaction.response.send_message(embed=embed, view=SupportView(interaction.user), ephemeral=True)

    @discord.ui.button(label="❓ Elite FAQ", style=discord.ButtonStyle.secondary, emoji="📜")
    async def faq(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = LuxuryEmbed("❓ Elite FAQ",
                           "**Q: How do I get roles?**\n"
                           "A: Use `!reactionroles #channel` or react in #roles\n\n"
                           "**Q: Support wait time?**\n"
                           "A: Elite response within 1 hour\n\n"
                           "**Q: Ticket banned?**\n"
                           "A: Contact admin for appeal")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📊 Server Stats", style=discord.ButtonStyle.success, emoji="📈")
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        embed = LuxuryEmbed("📊 Elite Server Statistics",
                           f"**Members:** {guild.member_count}\n"
                           f"**Tickets Today:** {SERVER_STATS['tickets_created']}\n"
                           f"**Active Tickets:** {len(OPEN_TICKETS)}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= COMPREHENSIVE EVENT HANDLERS =================
@bot.event
async def on_member_join(member: discord.Member):
    """Enhanced member join with full automation"""
    guild = member.guild
    
    # Auto role assignment
    if AUTO_ROLE_ID:
        role = guild.get_role(AUTO_ROLE_ID)
        if role:
            await member.add_roles(role)

    # Server welcome
    if WELCOME_CHANNEL_ID:
        welcome_ch = guild.get_channel(WELCOME_CHANNEL_ID)
        if welcome_ch:
            embed = LuxuryEmbed("✨ Elite Member Arrival", 
                               f"{member.mention} has entered the realm.\n"
                               f"**Total Members:** {len(guild.members)}")
            await welcome_ch.send(embed=embed)

    # Premium DM welcome sequence
    try:
        welcome_text = f"🌙 **Welcome to {guild.name} Elite Realm**\n\n"
        welcome_text += "You have been granted **premium access**.\n"
        welcome_text += "DM `support` for **elite assistance** anytime.\n\n"
        welcome_text += "✨ Your elite journey begins now..."
        
        await member.send(welcome_text)
        
        if GIF_WELCOME:
            await member.send(GIF_WELCOME)
        
        # Onboarding question
        embed = LuxuryEmbed("🔮 Elite Discovery", 
                           "How did you find our premium server?\n"
                           "(Helps us improve)")
        msg = await member.send(embed=embed, view=OnboardingView(member))
        ONBOARDING_MESSAGES[member.id] = msg.id
        
        if GIF_ONBOARDING:
            await member.send(GIF_ONBOARDING)
            
        SERVER_STATS["total_members"] += 1
            
    except discord.Forbidden:
        pass  # User has DMs disabled

@bot.event
async def on_raw_reaction_add(payload):
    """Advanced reaction role system"""
    if payload.message_id == REACTION_ROLES_MSG_ID:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
            
        member = guild.get_member(payload.user_id)
        if member and not member.bot:
            # Dynamic role matching
            role_name = f"Role-{str(payload.emoji)}"
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                await member.add_roles(role)
                print(f"Assigned {role.name} to {member}")

@bot.event
async def on_message(message: discord.Message):
    """Enhanced message handler"""
    if message.author.bot:
        return

    # Premium DM handling
    if isinstance(message.channel, discord.DMChannel):
        user_id = message.author.id
        
        # Handle onboarding completion
        if user_id in ONBOARDING_MESSAGES:
            try:
                onboarding_msg = await message.channel.fetch_message(ONBOARDING_MESSAGES.pop(user_id))
                await onboarding_msg.delete()
            except:
                pass
            
            embed = LuxuryEmbed("✅ Onboarding Complete", 
                               "Thank you for verifying! ✨\nEnjoy elite access.")
            await message.channel.send(embed=embed)
            return

        # Elite support trigger
        if message.content.lower() in ["support", "help", "ticket"]:
            embed = LuxuryEmbed("💎 Elite Support Services", 
                               "Choose your premium assistance option:")
            await message.channel.send(embed=embed, view=SupportView(message.author))
            if GIF_SUPPORT:
                await message.channel.send(GIF_SUPPORT)
            return

    await bot.process_commands(message)

# ================= ULTIMATE SLASH COMMAND TREE =================
@bot.tree.command(name="elite_panel", description="🌙 Deploy persistent elite support hub")
@app_commands.describe(channel="Channel for the panel (optional)")
async def elite_panel(interaction: discord.Interaction, channel: discord.TextChannel = None):
    """Deploy premium persistent support panel"""
    target_channel = channel or interaction.channel
    embed = LuxuryEmbed("🌙 Elite Support Hub", 
                       "Welcome to premium services.\n"
                       "**Click buttons below for elite assistance.**\n\n"
                       "🎟 Tickets | ❓ FAQ | 📊 Stats")
    embed.set_image(url=GIF_WELCOME)
    
    view = ElitePanelView()
    await target_channel.send(embed=embed, view=view)
    
    success_embed = LuxuryEmbed("✅ Elite Panel Deployed", 
                               f"Premium hub active in {target_channel.mention}")
    await interaction.response.send_message(embed=success_embed, ephemeral=True)

@bot.tree.command(name="elite_stats", description="📊 View comprehensive server statistics")
async def elite_stats(interaction: discord.Interaction):
    """Display elite server statistics"""
    guild = interaction.guild
    embed = LuxuryEmbed("📊 Elite Server Statistics",
                       f"**Total Members:** {guild.member_count:,}\n"
                       f"**Active Tickets:** {len(OPEN_TICKETS)}\n"
                       f"**Tickets Created:** {SERVER_STATS['tickets_created']:,}\n"
                       f"**Banned Users:** {len(TICKET_BANNED_USERS)}")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="elite_faq", description="❓ Access elite FAQ")
async def elite_faq(interaction: discord.Interaction):
    """Quick access to premium FAQ"""
    embed = LuxuryEmbed("❓ Elite FAQ",
                       "**Common Questions:**\n"
                       "• **Roles:** `!reactionroles #roles`\n"
                       "• **Support:** `/elite_panel`\n"
                       "• **Tickets:** Click Tickets button\n"
                       "• **DM Bot:** `support`")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ================= COMPLETE ADMIN COMMAND SET =================
@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def complete_setup(ctx: commands.Context):
    """One-command elite setup"""
    global MAIN_GUILD_ID, WELCOME_CHANNEL_ID, SUPPORT_LOG_CHANNEL_ID
    
    MAIN_GUILD_ID = ctx.guild.id
    WELCOME_CHANNEL_ID = ctx.channel.id
    SUPPORT_LOG_CHANNEL_ID = ctx.channel.id
    
    embed = LuxuryEmbed("✅ Elite Setup Complete",
                       f"**All systems configured:**\n"
                       f"• Guild: {ctx.guild.name}\n"
                       f"• Welcome: {ctx.channel.mention}\n"
                       f"• Logs: {ctx.channel.mention}\n\n"
                       f"**Next steps:**\n"
                       "1. `!autorole @Member`\n"
                       "2. Create SUPPORT category\n"
                       "3. `/elite_panel`")
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx: commands.Context):
    """Enhanced help with all commands"""
    embed = LuxuryEmbed("📜 Elite Command Center",
                       "**User Commands:**\n"
                       "`support` (DM) | `/elite_panel` | `/elite_faq`\n\n"
                       "**Admin Commands:**\n"
                       "`!setup` | `!welcome` | `!supportlog` | `!autorole`\n"
                       "`!ticketban` | `!bulkclose` | `!reactionroles`\n\n"
                       "**Status:** Premium Active")
    embed.set_thumbnail(url=MOON_ICON)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx: commands.Context):
    global WELCOME_CHANNEL_ID, MAIN_GUILD_ID
    WELCOME_CHANNEL_ID = ctx.channel.id
    MAIN_GUILD_ID = ctx.guild.id
    await ctx.send(embed=LuxuryEmbed("✅ Welcome Channel Set", f"{ctx.channel.mention}"))

@bot.command()
@commands.has_permissions(administrator=True)
async def supportlog(ctx: commands.Context):
    global SUPPORT_LOG_CHANNEL_ID, MAIN_GUILD_ID
    SUPPORT_LOG_CHANNEL_ID = ctx.channel.id
    MAIN_GUILD_ID = ctx.guild.id
    await ctx.send(embed=LuxuryEmbed("✅ Support Log Set", f"{ctx.channel.mention}"))

@bot.command()
@commands.has_permissions(administrator=True)
async def autorole(ctx: commands.Context, role: discord.Role):
    global AUTO_ROLE_ID, MAIN_GUILD_ID
    AUTO_ROLE_ID = role.id
    MAIN_GUILD_ID = ctx.guild.id
    await ctx.send(embed=LuxuryEmbed("✅ Auto Role Set", f"{role.mention}"))

@bot.command()
@commands.has_permissions(administrator=True)
async def reactionroles(ctx: commands.Context, channel: discord.TextChannel):
    """Setup reaction role message"""
    global REACTION_ROLES_MSG_ID
    embed = LuxuryEmbed("👑 Elite Reaction Roles",
                       "React below to get premium roles:\n\n"
                       "😀 **Fun Role**\n"
                       "🔥 **Gamer Role**\n"
                       "⭐ **Elite Role**\n"
                       "💎 **VIP Role**")
    
    msg = await channel.send(embed=embed)
    await msg.add_reaction("😀")
    await msg.add_reaction("🔥")
    await msg.add_reaction("⭐")
    await msg.add_reaction("💎")
    
    REACTION_ROLES_MSG_ID = msg.id
    await ctx.send(embed=LuxuryEmbed("✅ Reaction Roles Active", f"{channel.mention}"))

@bot.command()
@commands.has_permissions(administrator=True)
async def bulkclose(ctx: commands.Context):
    """Close all open tickets"""
    guild = get_guild()
    if not guild:
        return await ctx.send(embed=LuxuryEmbed("❌ Error", "Guild not configured", 0xFF4444))
    
    closed_count = 0
    for user_id, channel_id in list(OPEN_TICKETS.items()):
        channel = guild.get_channel(channel_id)
        if channel:
            await channel.delete()
            closed_count += 1
    
    OPEN_TICKETS.clear()
    await ctx.send(embed=LuxuryEmbed("🧹 Bulk Close Complete", f"{closed_count} elite tickets sealed"))

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketban(ctx: commands.Context, user: discord.Member):
    TICKET_BANNED_USERS.add(user.id)
    await ctx.send(embed=LuxuryEmbed("🚫 Ticket Banned", f"{user.mention} restricted", 0xFF4444))

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketunban(ctx: commands.Context, user: discord.Member):
    TICKET_BANNED_USERS.discard(user.id)
    await ctx.send(embed=LuxuryEmbed("✅ Ticket Unbanned", f"{user.mention} restored"))

@bot.command()
@commands.has_permissions(administrator=True)
async def announce(ctx: commands.Context, *, message: str):
    """Enhanced announcement system"""
    guild = ctx.guild
    embed = LuxuryEmbed("📢 Elite Server Announcement", message)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else MOON_ICON)
    
    sent = 0
    failed = 0
    
    for member in guild.members:
        if not member.bot and not member.guild_permissions.administrator:
            try:
                await member.send(embed=embed)
                sent += 1
                await asyncio.sleep(1)  # Rate limit protection
            except:
                failed += 1
    
    stats_embed = LuxuryEmbed("📤 Announcement Complete",
                             f"**Delivered:** {sent}\n**Failed:** {failed}\n"
                             f"**Success Rate:** {(sent/(sent+failed)*100):.1f}%")
    await ctx.send(embed=stats_embed)

# ================= PREMIUM READY EVENT =================
@bot.event
async def on_ready():
    print("🌙" + "="*50)
    print(f"✅ {bot.user} - ELITE MODE ACTIVATED")
    print(f"🌟 Premium Features: Slash Commands, Luxury Embeds, Auto-Transcripts")
    print(f"📊 Guilds: {len(bot.guilds)} | Users: {sum(g.member_count for g in bot.guilds)}")
    print("="*50)
    
    if MAIN_GUILD_ID:
        guild = discord.Object(id=MAIN_GUILD_ID)
        synced = await bot.tree.sync(guild=guild)
        print(f"🌙 Synced {len(synced)} elite slash commands")
    else:
        print("⚠️  Set MAIN_GUILD_ID for slash commands")
    
    print("🚀 Ready for premium service!")

# ================= FINAL EXECUTION =================
if __name__ == "__main__":
    bot.run(TOKEN)
