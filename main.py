import os
import asyncio
import discord
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ================= BASIC SETUP =================

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True  # ✨ REQUIRED: To monitor manual bans/kicks/timeouts

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

# ================= THEME (LUXURY) =================

COLOR_PRIMARY = 0x020617   # obsidian
COLOR_SECONDARY = 0x1f2937 # slate
COLOR_DANGER = 0x7c2d12    # deep red
COLOR_GOLD = 0xD4AF37      # premium gold accent

# ================= STATE =================

MAIN_GUILD_ID = None
WELCOME_CHANNEL_ID = None
SUPPORT_LOG_CHANNEL_ID = None
AUTO_ROLE_ID = None

ONBOARDING_MESSAGES = {}
OPEN_TICKETS = {}

# 🔹 ADDED FEATURE (unchanged)
TICKET_BANNED_USERS = set()

# ================= HELPERS =================

def get_guild():
    return bot.get_guild(MAIN_GUILD_ID) if MAIN_GUILD_ID else None

def luxury_embed(title=None, description=None, color=COLOR_PRIMARY):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow()
    )
    # ✨ BRANDING ENHANCEMENT: Hellfire Hangout
    embed.set_footer(text="🔥 Hellfire Hangout | Elite Support Services | Premium Automation")
    return embed

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
            embed=luxury_embed(
                title="✨ Welcome Aboard, Elite Member",
                description="Thank you for sharing how you discovered our exclusive community. "
                            "Your journey with us officially begins now. Explore the realms of premium "
                            "conversations, luxurious events, and unparalleled experiences ahead. "
                            "If assistance is ever required, our concierge support awaits via DM.",
                color=COLOR_GOLD
            ),
            ephemeral=True
        )

    @discord.ui.button(label="Friends", style=discord.ButtonStyle.primary, emoji="👥")
    async def friends(self, interaction, _):
        await self.finish(interaction)

    @discord.ui.button(label="Social Media", style=discord.ButtonStyle.secondary, emoji="📱")
    async def social(self, interaction, _):
        await self.finish(interaction)

    @discord.ui.button(label="Other", style=discord.ButtonStyle.success, emoji="🌐")
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

        if (
            interaction.user.id != self.owner_id
            and not interaction.user.guild_permissions.administrator
            and (not staff_role or staff_role not in interaction.user.roles)
        ):
            await interaction.response.send_message(
                embed=luxury_embed(
                    title="❌ Access Denied",
                    description="You lack the authorized privileges to conclude this premium support session. "
                                "Only the ticket originator, administrators, or designated Staff members may proceed. "
                                "Please await proper escalation if further action is required.",
                    color=COLOR_DANGER
                ),
                ephemeral=True
            )
            return

        button.disabled = True
        await interaction.message.edit(view=self)

        await interaction.response.send_message(
            embed=luxury_embed(
                title="🔒 Ticket Elegantly Concluded",
                description="Your support session has been gracefully archived within our premium system. "
                            "Thank you for utilizing our elite concierge services. Should your journey require "
                            "further assistance, our doors remain open 24/7. Farewell for now ✨",
                color=COLOR_SECONDARY
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
                embed=luxury_embed(
                    title="⚙️ System Configuration Pending",
                    description="Our premium support infrastructure is currently undergoing elite setup. "
                                "Please notify a Staff member to initialize via !setup command. "
                                "We apologize for this momentary pause in luxury service.",
                    color=COLOR_SECONDARY
                ),
                ephemeral=True
            )
            return

        if self.user.id in TICKET_BANNED_USERS:
            await interaction.response.send_message(
                embed=luxury_embed(
                    title="🚫 Restricted Access",
                    description="Your account has been temporarily restricted from premium ticket creation "
                                "due to prior policy guidelines. For review or appeal, kindly contact administration "
                                "directly. We maintain the highest standards of community excellence.",
                    color=COLOR_DANGER
                ),
                ephemeral=True
            )
            return

        if self.user.id in OPEN_TICKETS:
            await interaction.response.send_message(
                embed=luxury_embed(
                    title="⏳ Active Session Detected",
                    description="You currently maintain an open premium support channel. "
                                "Please utilize your existing ticket for seamless continuity. "
                                "Multiple sessions are reserved for escalated VIP matters only.",
                    color=COLOR_SECONDARY
                ),
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
            embed=luxury_embed(
                title="🌙 Premium Support Ticket Activated",
                description=f"**Esteemed Guest: {self.user.mention}**\n\n"
                            "Your exclusive support suite has been elegantly provisioned. "
                            "One of our elite Staff concierge specialists will attend to your matter "
                            "with utmost priority and sophistication. Kindly articulate your request "
                            "in detail below for optimal resolution. We appreciate your patronage ✨",
                color=COLOR_GOLD
            ),
            view=CloseTicketView(self.user.id)
        )

        if SUPPORT_LOG_CHANNEL_ID:
            log = guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log:
                await log.send(
                    embed=luxury_embed(
                        title="📊 Ticket Log Entry",
                        description=f"🎟 **New Premium Session Initiated**\n"
                                    f"**Client:** {self.user.mention} ({self.user.id})\n"
                                    f"**Channel:** {channel.mention}\n"
                                    f"**Timestamp:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                        color=COLOR_SECONDARY
                    )
                )

        await interaction.response.send_message(
            embed=luxury_embed(
                title="✅ Ticket Suite Provisioned",
                description="Your personalized support channel has been crafted with premium precision. "
                            "Navigate to it now for immediate elite assistance. Thank you for choosing "
                            "our luxury services—excellence awaits.",
                color=COLOR_GOLD
            ),
            ephemeral=True
        )

    @discord.ui.button(label="Personal Assistance", emoji="🧑‍💼", style=discord.ButtonStyle.secondary)
    async def personal(self, interaction, _):
        guild = get_guild()
        if SUPPORT_LOG_CHANNEL_ID and guild:
            log = guild.get_channel(SUPPORT_LOG_CHANNEL_ID)
            if log:
                await log.send(
                    embed=luxury_embed(
                        title="👑 VIP Personal Request",
                        description=f"{self.user.mention} has summoned elite personal concierge assistance. "
                                    f"**Priority:** High | **Response ETA:** Within 24 hours via DM.\n"
                                    f"A dedicated specialist will reach out with tailored solutions.",
                        color=COLOR_GOLD
                    )
                )

        await interaction.response.send_message(
            embed=luxury_embed(
                title="🛎️ Personal Concierge Dispatched",
                description="An elite Staff specialist has been notified and will contact you privately "
                            "within 24 hours with bespoke, white-glove assistance. Your comfort and "
                            "satisfaction remain our paramount commitment. Stand by for luxury service ✨",
                color=COLOR_GOLD
            ),
            ephemeral=True
        )

# ================= AUTOMATIC AUDIT LOG HANDLERS (NEW) =================

@bot.event
async def on_member_ban(guild, user):
    """Automatically DMs user when banned via Discord UI."""
    await asyncio.sleep(1) # Wait for Audit Log to sync
    async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
        if entry.target.id == user.id:
            try:
                await user.send(embed=luxury_embed(
                    title="⚖️ Imperial Banishment",
                    description=f"You have been permanently banished from **Hellfire Hangout**.\n\n"
                                f"**Moderator:** {entry.user}\n"
                                f"**Reason:** {entry.reason or 'Policy violation.'}",
                    color=COLOR_DANGER
                ))
            except: pass

@bot.event
async def on_member_remove(member):
    """Detects if a member was kicked (manually) and DMs them."""
    await asyncio.sleep(1)
    async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
        if entry.target.id == member.id:
            # Check if kick happened within the last 10 seconds to avoid false triggers
            if (datetime.utcnow() - entry.created_at.replace(tzinfo=None)).total_seconds() < 10:
                try:
                    await member.send(embed=luxury_embed(
                        title="🚫 Departure Notice",
                        description=f"Your presence at **Hellfire Hangout** has been concluded.\n\n"
                                    f"**Action:** Manual Kick\n"
                                    f"**Moderator:** {entry.user}\n"
                                    f"**Reason:** {entry.reason or 'Management decision.'}",
                        color=COLOR_DANGER
                    ))
                except: pass

@bot.event
async def on_member_update(before, after):
    """Detects when a user is timed out via Discord UI."""
    if before.timed_out_until != after.timed_out_until and after.timed_out_until is not None:
        await asyncio.sleep(1)
        async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_update, limit=1):
            if entry.target.id == after.id:
                try:
                    await after.send(embed=luxury_embed(
                        title="⏳ Silence Bestowed",
                        description=f"Your privileges at **Hellfire Hangout** have been temporarily suspended.\n\n"
                                    f"**Status:** Timed Out\n"
                                    f"**Moderator:** {entry.user}\n"
                                    f"**Until:** {after.timed_out_until.strftime('%Y-%m-%d %H:%M UTC')}\n"
                                    f"**Reason:** {entry.reason or 'Reflection period required.'}",
                        color=COLOR_SECONDARY
                    ))
                except: pass

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
                embed=luxury_embed(
                    title="🔥 Welcome to Hellfire Hangout",
                    description=f"✨ {member.mention} has gracefully entered our premium domain. "
                                f"Welcome to a realm of sophistication, exclusive events, and unparalleled "
                                f"community excellence. The stars align in your favor.",
                    color=COLOR_GOLD
                )
            )

    try:
        await member.send(
            f"🔥 **Welcome to Hellfire Hangout** 🔥\n\n"
            "You have arrived at an exclusive sanctuary of premium discourse and luxury experiences. "
            "To summon our elite support concierge at any moment, simply reply `support` within this DM. "
            "Your journey of excellence begins now ✨"
        )

        if GIF_WELCOME:
            await member.send(GIF_WELCOME)

        msg = await member.send(
            embed=luxury_embed(
                title="🌌 Discovery Inquiry",
                description="**Esteemed New Arrival,**\n\n"
                            "To tailor your premium onboarding, may we inquire: How did you discover "
                            "Hellfire Hangout? Your insight helps us refine our celestial invitation process. "
                            "Select below for a seamless continuation ✨",
                color=COLOR_SECONDARY
            ),
            view=OnboardingView(member)
        )
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

    # 🛡️ AUTO-SECURITY FEATURE: Invite Filter & Basic Spam
    if message.guild:
        # Check for unauthorized links
        if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
            if not message.author.guild_permissions.manage_messages:
                await message.delete()
                warning = await message.channel.send(f"{message.author.mention}, unauthorized invites are restricted in **Hellfire Hangout**.")
                await asyncio.sleep(5)
                await warning.delete()
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
                embed=luxury_embed(
                    title="✨ Onboarding Complete",
                    description="Thank you for your valued response. You are now fully integrated into "
                                "the **Hellfire Hangout** ecosystem. Dive into the wonders ahead—support remains "
                                "a whisper away via `support`. Welcome to excellence 🌙",
                    color=COLOR_GOLD
                )
            )
            return

        if message.content.lower() == "support":
            await message.channel.send(
                embed=luxury_embed(
                    title="🛎️ Elite Concierge Portal",
                    description="**How may we elevate your experience today?**\n\n"
                                "Access our premium support suite through the options below. "
                                "Whether ticketed precision or personal white-glove service, "
                                "your satisfaction is our eternal pursuit ✨",
                    color=COLOR_PRIMARY
                ),
                view=SupportView(message.author)
            )
            if GIF_SUPPORT:
                await message.channel.send(GIF_SUPPORT)
            return

    await bot.process_commands(message)

# ================= MODERATION COMMANDS (NEW) =================

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    """DMs a luxury exit notice then kicks the member."""
    try:
        await member.send(embed=luxury_embed(
            title="🚫 Departure Notice",
            description=f"Your presence at **Hellfire Hangout** has been concluded.\n\n"
                        f"**Action:** Kick\n**Reason:** {reason}",
            color=COLOR_DANGER
        ))
    except:
        pass
    await member.kick(reason=reason)
    await ctx.send(embed=luxury_embed(title="Successfully Kicked", description=f"{member.mention} has been removed from the realm.", color=COLOR_GOLD))

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    """DMs a luxury exit notice then bans the member."""
    try:
        await member.send(embed=luxury_embed(
            title="⚖️ Imperial Banishment",
            description=f"You have been permanently banished from **Hellfire Hangout**.\n\n"
                        f"**Action:** Ban\n**Reason:** {reason}",
            color=COLOR_DANGER
        ))
    except:
        pass
    await member.ban(reason=reason)
    await ctx.send(embed=luxury_embed(title="Successfully Banned", description=f"{member.mention} has been permanently exiled.", color=COLOR_GOLD))

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason provided"):
    """DMs a luxury notice then silences the member."""
    duration = timedelta(minutes=minutes)
    try:
        await member.send(embed=luxury_embed(
            title="⏳ Silence Bestowed",
            description=f"Your privileges at **Hellfire Hangout** have been temporarily suspended.\n\n"
                        f"**Duration:** {minutes} minutes\n**Reason:** {reason}",
            color=COLOR_SECONDARY
        ))
    except:
        pass
    await member.timeout(duration, reason=reason)
    await ctx.send(embed=luxury_embed(title="Timeout Applied", description=f"{member.mention} is now in a period of reflection for {minutes}m.", color=COLOR_GOLD))

# ================= COMMANDS =================

@bot.command()
async def help(ctx):
    await ctx.send(
        embed=luxury_embed(
            title="🌙 Elite Command Codex",
            description="**Premium Bot Arsenal:**\n"
                        "`support` → Summon concierge via DM for bespoke assistance\n"
                        "`!announce <msg>` → Broadcast gilded announcements (Admin Elite)\n"
                        "`!kick @user <reason>` → Soft departure with DM notice\n"
                        "`!ban @user <reason>` → Permanent exile with DM notice\n"
                        "`!timeout @user <mins> <reason>` → Temporary silence with DM notice\n"
                        "`!welcome` → Designate celestial welcome channel (Admin)\n"
                        "`!supportlog` → Establish premium audit ledger (Admin)\n"
                        "`!autorole @role` → Bestow automatic prestige\n"
                        "`!ticketban/@unban @user` → Manage access to luxury tickets\n\n"
                        "All crafted for **Hellfire Hangout** governance ✨",
            color=COLOR_GOLD
        )
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def welcome(ctx):
    global WELCOME_CHANNEL_ID, MAIN_GUILD_ID
    WELCOME_CHANNEL_ID = ctx.channel.id
    MAIN_GUILD_ID = ctx.guild.id
    await ctx.send(embed=luxury_embed(
        title="✅ Celestial Welcome Activated",
        description="This channel is now eternally attuned for premium member arrivals at **Hellfire Hangout**.",
        color=COLOR_GOLD
    ))

@bot.command()
@commands.has_permissions(administrator=True)
async def supportlog(ctx):
    global SUPPORT_LOG_CHANNEL_ID, MAIN_GUILD_ID
    SUPPORT_LOG_CHANNEL_ID = ctx.channel.id
    MAIN_GUILD_ID = ctx.guild.id
    await ctx.send(embed=luxury_embed(
        title="📊 Premium Ledger Initialized",
        description="Support sessions will now be immutably chronicled here for elite oversight.",
        color=COLOR_SECONDARY
    ))

@bot.command()
@commands.has_permissions(administrator=True)
async def autorole(ctx, role: discord.Role):
    global AUTO_ROLE_ID, MAIN_GUILD_ID
    AUTO_ROLE_ID = role.id
    MAIN_GUILD_ID = ctx.guild.id
    await ctx.send(embed=luxury_embed(
        title="🏅 Auto-Prestige Enabled",
        description=f"The prestigious **{role.name}** mantle shall now be automatically bestowed.",
        color=COLOR_GOLD
    ))

# ================= TICKET BAN =================

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketban(ctx, user: discord.Member):
    TICKET_BANNED_USERS.add(user.id)
    await ctx.send(
        embed=luxury_embed(
            title="🚫 Ticket Privilege Revoked",
            description=f"{user.mention} has been elegantly restricted from premium ticket creation.",
            color=COLOR_DANGER
        )
    )

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketunban(ctx, user: discord.Member):
    TICKET_BANNED_USERS.discard(user.id)
    await ctx.send(
        embed=luxury_embed(
            title="✅ Ticket Privileges Restored",
            description=f"{user.mention} may once again access our elite support suites.",
            color=COLOR_GOLD
        )
    )

# ================= ANNOUNCE =================

@bot.command()
@commands.has_permissions(administrator=True)
async def announce(ctx, *, message: str):
    guild = ctx.guild
    embed = luxury_embed(
        title="📜 Imperial Proclamation",
        description=message,
        color=COLOR_GOLD
    )
    embed.set_footer(text=f"From the Halls of Hellfire Hangout | Elite Broadcast")
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)

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
        embed=luxury_embed(
            title="📊 Broadcast Dispatch Complete",
            description=f"**Gilded Decree Delivered:**\n"
                        f"• **Successfully Transmitted:** {sent} elite recipients\n"
                        f"• **Undelivered:** {failed} (likely DMs closed)\n\n"
                        "Your imperial message has resonated across the realm ✨",
            color=COLOR_SECONDARY
        )
    )

# ================= READY =================

@bot.event
async def on_ready():
    print(f"🌙 {bot.user} | Hellfire Hangout Mode: ONLINE ✨")

bot.run(TOKEN)
