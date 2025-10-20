import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
from datetime import datetime, timezone, timedelta
from database import ShiftDatabase
from web_server import start_web_server
from dotenv import load_dotenv
import aiohttp
import logging

# Load environment variables (.env locally, Fly.io secrets in production)
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
db = ShiftDatabase()


def format_duration(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"


def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    
    if not ADMIN_ROLE_IDS:
        return False
    
    user_role_ids = [role.id for role in interaction.user.roles]
    return any(role_id in user_role_ids for role_id in ADMIN_ROLE_IDS)


async def update_shift_embed():
    if not SHIFT_CHANNEL_ID or not SHIFT_MESSAGE_ID:
        return
    
    try:
        channel = bot.get_channel(SHIFT_CHANNEL_ID)
        if not channel:
            return
        
        message = await channel.fetch_message(SHIFT_MESSAGE_ID)
        
        active_users = db.get_active_users()
        
        embed = discord.Embed(
            title="🕐 Shift Clock System",
            description="Click the buttons below to clock in or out of your shift.",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        if active_users:
            users_text = ""
            for user in active_users:
                clock_in_dt = datetime.fromisoformat(user['clock_in_time'])
                duration = int((datetime.utcnow() - clock_in_dt).total_seconds())
                users_text += f"• <@{user['user_id']}> - {format_duration(duration)}\n"
            
            embed.add_field(
                name=f"✅ Currently Clocked In ({len(active_users)})",
                value=users_text,
                inline=False
            )
        else:
            embed.add_field(
                name="✅ Currently Clocked In (0)",
                value="*No one is currently clocked in*",
                inline=False
            )
        
        embed.set_footer(text="Shift tracking system")
        
        await message.edit(embed=embed)
    except Exception as e:
        print(f"Error updating shift embed: {e}")


async def log_shift_action(user, action, duration=None):
    if not LOGS_CHANNEL_ID:
        return
    
    try:
        channel = bot.get_channel(LOGS_CHANNEL_ID)
        if not channel:
            return
        
        embed = discord.Embed(
            timestamp=datetime.now(timezone.utc)
        )
        
        if action == "clock_in":
            embed.title = "⏰ Clocked In"
            embed.color = discord.Color.green()
            embed.description = f"{user.mention} has clocked in"
        elif action == "clock_out":
            embed.title = "🏁 Clocked Out"
            embed.color = discord.Color.red()
            embed.description = f"{user.mention} has clocked out"
            if duration:
                embed.add_field(name="Shift Duration", value=format_duration(duration), inline=False)
                total_time = db.get_user_total_time(str(user.id))
                embed.add_field(name="Total Time Worked", value=format_duration(total_time), inline=False)
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Error logging shift action: {e}")


class ShiftButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Clock In", style=discord.ButtonStyle.green, custom_id="clock_in", emoji="⏰")
    async def clock_in_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        username = str(interaction.user)
        
        if db.is_clocked_in(user_id):
            await interaction.response.send_message(
                "❌ You are already clocked in! Clock out first.",
                ephemeral=True
            )
            return
        
        success = db.clock_in(user_id, username)
        if success:
            if SHIFT_ROLE_ID:
                try:
                    role = interaction.guild.get_role(SHIFT_ROLE_ID)
                    if role:
                        await interaction.user.add_roles(role)
                except Exception as e:
                    print(f"Error adding role: {e}")
            
            await interaction.response.send_message(
                "✅ Successfully clocked in! Your shift has started.",
                ephemeral=True
            )
            
            await log_shift_action(interaction.user, "clock_in")
            await update_shift_embed()
        else:
            await interaction.response.send_message(
                "❌ Failed to clock in. Please try again.",
                ephemeral=True
            )
    
    @discord.ui.button(label="Clock Out", style=discord.ButtonStyle.red, custom_id="clock_out", emoji="🏁")
    async def clock_out_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        
        if not db.is_clocked_in(user_id):
            await interaction.response.send_message(
                "❌ You are not clocked in!",
                ephemeral=True
            )
            return
        
        duration = db.clock_out(user_id)
        if duration is not None:
            if SHIFT_ROLE_ID:
                try:
                    role = interaction.guild.get_role(SHIFT_ROLE_ID)
                    if role:
                        await interaction.user.remove_roles(role)
                except Exception as e:
                    print(f"Error removing role: {e}")
            
            await interaction.response.send_message(
                f"✅ Successfully clocked out! Shift duration: {format_duration(duration)}",
                ephemeral=True
            )
            
            await log_shift_action(interaction.user, "clock_out", duration)
            await update_shift_embed()
        else:
            await interaction.response.send_message(
                "❌ Failed to clock out. Please try again.",
                ephemeral=True
            )


@tasks.loop(hours=168)
async def weekly_report():
    reports_channel_id = db.get_config('reports_channel_id')
    if not reports_channel_id:
        return
    
    try:
        channel = bot.get_channel(int(reports_channel_id))
        if not channel:
            return
        
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        leaderboard_data = db.get_leaderboard(limit=10)
        
        embed = discord.Embed(
            title="📊 Weekly Team Report",
            description=f"Team performance for the week ending {datetime.now(timezone.utc).strftime('%B %d, %Y')}",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )
        
        if leaderboard_data:
            total_hours = sum(entry['total_seconds'] for entry in leaderboard_data) / 3600
            embed.add_field(
                name="📈 Total Team Hours",
                value=f"{total_hours:.1f} hours this week",
                inline=False
            )
            
            top_contributors = ""
            medals = ["🥇", "🥈", "🥉"]
            for idx, entry in enumerate(leaderboard_data[:5], 1):
                medal = medals[idx - 1] if idx <= 3 else f"**#{idx}**"
                top_contributors += f"{medal} <@{entry['user_id']}> - {format_duration(entry['total_seconds'])}\n"
            
            embed.add_field(
                name="🏆 Top Contributors",
                value=top_contributors,
                inline=False
            )
        else:
            embed.add_field(
                name="📈 Total Team Hours",
                value="No data for this week",
                inline=False
            )
        
        embed.set_footer(text="Automated Weekly Report")
        
        await channel.send(embed=embed)
        print("Weekly report sent successfully")
    except Exception as e:
        print(f"Error sending weekly report: {e}")


@bot.event
async def on_ready():
    global SHIFT_ROLE_ID, LOGS_CHANNEL_ID, SHIFT_MESSAGE_ID, SHIFT_CHANNEL_ID, ADMIN_ROLE_IDS
    
    print(f"Bot logged in as {bot.user}")
    print(f"Bot ID: {bot.user.id}")
    
    config = db.get_all_config()
    if 'shift_role_id' in config:
        SHIFT_ROLE_ID = int(config['shift_role_id'])
        print(f"Loaded shift role ID: {SHIFT_ROLE_ID}")
    
    if 'logs_channel_id' in config:
        LOGS_CHANNEL_ID = int(config['logs_channel_id'])
        print(f"Loaded logs channel ID: {LOGS_CHANNEL_ID}")
    
    if 'shift_message_id' in config:
        SHIFT_MESSAGE_ID = int(config['shift_message_id'])
        print(f"Loaded shift message ID: {SHIFT_MESSAGE_ID}")
    
    if 'shift_channel_id' in config:
        SHIFT_CHANNEL_ID = int(config['shift_channel_id'])
        print(f"Loaded shift channel ID: {SHIFT_CHANNEL_ID}")
    
    if 'admin_role_ids' in config:
        ADMIN_ROLE_IDS = [int(rid) for rid in config['admin_role_ids'].split(',') if rid]
        print(f"Loaded admin role IDs: {ADMIN_ROLE_IDS}")
    
    bot.add_view(ShiftButtons())
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    
    asyncio.create_task(start_web_server(port=8080))
    
    if SHIFT_MESSAGE_ID and SHIFT_CHANNEL_ID:
        await update_shift_embed()
        print("Updated shift embed with current status")
    
    if not weekly_report.is_running():
        weekly_report.start()
        print("Started weekly report task")
    
    print("Bot is ready!")


@bot.tree.command(name="setup_shift", description="Set up the shift tracking system (Admin only)")
@app_commands.describe(
    shift_role="The role to assign when users clock in",
    logs_channel="The channel where shift logs will be sent"
)
async def setup_shift(
    interaction: discord.Interaction,
    shift_role: discord.Role,
    logs_channel: discord.TextChannel
):
    global SHIFT_ROLE_ID, LOGS_CHANNEL_ID, SHIFT_MESSAGE_ID, SHIFT_CHANNEL_ID
    
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need administrator permissions to use this command.",
            ephemeral=True
        )
        return
    
    SHIFT_ROLE_ID = shift_role.id
    LOGS_CHANNEL_ID = logs_channel.id
    SHIFT_CHANNEL_ID = interaction.channel.id
    
    embed = discord.Embed(
        title="🕐 Shift Clock System",
        description="Click the buttons below to clock in or out of your shift.",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="✅ Currently Clocked In (0)",
        value="*No one is currently clocked in*",
        inline=False
    )
    
    embed.set_footer(text="Shift tracking system")
    
    view = ShiftButtons()
    message = await interaction.channel.send(embed=embed, view=view)
    SHIFT_MESSAGE_ID = message.id
    
    db.save_config('shift_role_id', str(shift_role.id))
    db.save_config('logs_channel_id', str(logs_channel.id))
    db.save_config('shift_channel_id', str(interaction.channel.id))
    db.save_config('shift_message_id', str(message.id))
    
    await interaction.response.send_message(
        f"✅ Shift system set up successfully!\n"
        f"**Shift Role:** {shift_role.mention}\n"
        f"**Logs Channel:** {logs_channel.mention}\n"
        f"**Shift Message:** [Click here]({message.jump_url})",
        ephemeral=True
    )
    
    print(f"Shift system configured - Role: {shift_role.id}, Logs: {logs_channel.id}")


@bot.tree.command(name="set_admin", description="Set admin roles for the bot (Admin only)")
@app_commands.describe(
    role1="First admin role",
    role2="Second admin role (optional)",
    role3="Third admin role (optional)",
    role4="Fourth admin role (optional)",
    role5="Fifth admin role (optional)"
)
async def set_admin(
    interaction: discord.Interaction,
    role1: discord.Role,
    role2: discord.Role = None,
    role3: discord.Role = None,
    role4: discord.Role = None,
    role5: discord.Role = None
):
    global ADMIN_ROLE_IDS
    
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ You need administrator permissions to use this command.",
            ephemeral=True
        )
        return
    
    roles = [r for r in [role1, role2, role3, role4, role5] if r is not None]
    ADMIN_ROLE_IDS = [r.id for r in roles]
    
    db.save_config('admin_role_ids', ','.join(str(rid) for rid in ADMIN_ROLE_IDS))
    
    role_mentions = ', '.join(r.mention for r in roles)
    await interaction.response.send_message(
        f"✅ Admin roles set successfully!\n**Admin Roles:** {role_mentions}\n\n"
        f"Users with these roles can now use admin commands.",
        ephemeral=True
    )


@bot.tree.command(name="mystats", description="Check your shift statistics")
async def mystats(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    total_time = db.get_user_total_time(user_id)
    is_clocked = db.is_clocked_in(user_id)
    
    embed = discord.Embed(
        title=f"📊 Shift Stats for {interaction.user.display_name}",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="⏱️ Total Time Worked",
        value=format_duration(total_time),
        inline=False
    )
    
    status = "🟢 Clocked In" if is_clocked else "🔴 Clocked Out"
    embed.add_field(
        name="Status",
        value=status,
        inline=False
    )
    
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="leaderboard", description="Show the shift time leaderboard (Admin only)")
@app_commands.describe(top="Number of users to show (default: 10)")
async def leaderboard(interaction: discord.Interaction, top: int = 10):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    top = max(1, min(top, 25))
    
    leaderboard_data = db.get_leaderboard(limit=top)
    
    if not leaderboard_data:
        await interaction.response.send_message(
            "❌ No shift data available yet.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="🏆 Shift Time Leaderboard",
        description=f"Top {top} users by total time worked",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    
    medals = ["🥇", "🥈", "🥉"]
    
    for idx, entry in enumerate(leaderboard_data, 1):
        medal = medals[idx - 1] if idx <= 3 else f"**#{idx}**"
        time_formatted = format_duration(entry['total_seconds'])
        
        embed.add_field(
            name=f"{medal} {entry['username']}",
            value=f"⏱️ {time_formatted}",
            inline=False
        )
    
    embed.set_footer(text="Keep up the great work!")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="force_clockout", description="Force clock out a user (Admin only)")
@app_commands.describe(user="The user to force clock out")
async def force_clockout(interaction: discord.Interaction, user: discord.Member):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    user_id = str(user.id)
    
    if not db.is_clocked_in(user_id):
        await interaction.response.send_message(
            f"❌ {user.mention} is not clocked in.",
            ephemeral=True
        )
        return
    
    duration = db.clock_out(user_id)
    
    if duration is not None:
        if SHIFT_ROLE_ID:
            try:
                role = interaction.guild.get_role(SHIFT_ROLE_ID)
                if role:
                    await user.remove_roles(role)
            except Exception as e:
                print(f"Error removing role: {e}")
        
        await interaction.response.send_message(
            f"✅ Successfully force clocked out {user.mention}. Duration: {format_duration(duration)}",
            ephemeral=True
        )
        
        await log_shift_action(user, "clock_out", duration)
        await update_shift_embed()
    else:
        await interaction.response.send_message(
            "❌ Failed to clock out user.",
            ephemeral=True
        )


@bot.tree.command(name="send_embed", description="Send a custom embedded message (Admin only)")
@app_commands.describe(
    channel="The channel to send the embed to",
    title="The title of the embed",
    description="The description/content of the embed",
    color="Hex color code (e.g., #5865F2) or color name (blue, red, green, gold, purple)"
)
async def send_embed(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    title: str,
    description: str,
    color: str = "blue"
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    color_map = {
        "blue": discord.Color.blue(),
        "red": discord.Color.red(),
        "green": discord.Color.green(),
        "gold": discord.Color.gold(),
        "purple": discord.Color.purple(),
        "orange": discord.Color.orange(),
        "teal": discord.Color.teal(),
    }
    
    embed_color = color_map.get(color.lower())
    if not embed_color:
        if color.startswith("#"):
            try:
                embed_color = discord.Color(int(color[1:], 16))
            except ValueError:
                embed_color = discord.Color.blue()
        else:
            embed_color = discord.Color.blue()
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color,
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.set_footer(text=f"Sent by {interaction.user.display_name}")
    
    try:
        await channel.send(embed=embed)
        await interaction.response.send_message(
            f"✅ Embed sent to {channel.mention}!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Failed to send embed: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="help", description="Show all available bot commands (Admin only)")
async def help_command(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title="🤖 Bot Commands",
        description="Here are all the available commands:",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    commands_list = await bot.tree.fetch_commands()
    
    for cmd in sorted(commands_list, key=lambda x: x.name):
        embed.add_field(
            name=f"/{cmd.name}",
            value=cmd.description or "No description available",
            inline=False
        )
    
    embed.set_footer(text=f"Total Commands: {len(commands_list)}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="team_status", description="Show current team member shift status (Admin only)")
async def team_status(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    active_users = db.get_active_users()
    leaderboard_data = db.get_leaderboard(limit=5)
    
    embed = discord.Embed(
        title="👥 Team Status Dashboard",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    if active_users:
        active_text = ""
        for user in active_users:
            clock_in_dt = datetime.fromisoformat(user['clock_in_time'])
            duration = int((datetime.utcnow() - clock_in_dt).total_seconds())
            active_text += f"• <@{user['user_id']}> - {format_duration(duration)}\n"
        
        embed.add_field(
            name=f"🟢 Currently Active ({len(active_users)})",
            value=active_text,
            inline=False
        )
    else:
        embed.add_field(
            name="🟢 Currently Active (0)",
            value="*No one is currently working*",
            inline=False
        )
    
    if leaderboard_data:
        top_text = ""
        for idx, entry in enumerate(leaderboard_data[:3], 1):
            medals = ["🥇", "🥈", "🥉"]
            top_text += f"{medals[idx-1]} <@{entry['user_id']}> - {format_duration(entry['total_seconds'])}\n"
        
        embed.add_field(
            name="🏆 Top Contributors (This Week)",
            value=top_text,
            inline=False
        )
    
    embed.set_footer(text="Keep up the great work!")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="set_goal", description="Set a team work goal for the day/week (Admin only)")
@app_commands.describe(
    hours="Target hours for the team",
    period="Time period (today, week, month)"
)
async def set_goal(
    interaction: discord.Interaction,
    hours: int,
    period: str = "today"
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    db.save_config(f'goal_{period}', str(hours))
    
    embed = discord.Embed(
        title="🎯 Team Goal Set!",
        description=f"New goal: **{hours} hours** for **{period}**",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.set_footer(text=f"Set by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="setup_weekly_reports", description="Set up automated weekly team reports (Admin only)")
@app_commands.describe(
    channel="The channel where weekly reports will be sent"
)
async def setup_weekly_reports(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    db.save_config('reports_channel_id', str(channel.id))
    
    await interaction.response.send_message(
        f"✅ Weekly reports will be sent to {channel.mention} every Monday at midnight UTC.\n\n"
        f"**What's included in weekly reports:**\n"
        f"📈 Total team hours for the week\n"
        f"🏆 Top 5 contributors\n"
        f"📊 Team statistics\n\n"
        f"The first report will be sent next Monday!",
        ephemeral=True
    )


@bot.tree.command(name="link_roblox_group", description="Link a Roblox group to this Discord server (Admin only)")
@app_commands.describe(
    group_id="Your Roblox group ID (found in the group URL)"
)
async def link_roblox_group(
    interaction: discord.Interaction,
    group_id: str
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://groups.roblox.com/v1/groups/{group_id}") as resp:
                if resp.status != 200:
                    await interaction.response.send_message(
                        f"❌ Could not find Roblox group with ID {group_id}. Please check the ID and try again.",
                        ephemeral=True
                    )
                    return
                
                data = await resp.json()
                group_name = data.get('name', 'Unknown')
                
                db.save_config('roblox_group_id', group_id)
                db.save_config('roblox_group_name', group_name)
                
                await interaction.response.send_message(
                    f"✅ Successfully linked Roblox group!\n"
                    f"**Group:** {group_name}\n"
                    f"**Group ID:** {group_id}\n\n"
                    f"Use `/roblox_group_info` to view group details.",
                    ephemeral=True
                )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error linking group: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="roblox_group_info", description="Display information about the linked Roblox group (Admin only)")
async def roblox_group_info(interaction: discord.Interaction):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    group_id = db.get_config('roblox_group_id')
    if not group_id:
        await interaction.response.send_message(
            "❌ No Roblox group linked! Use `/link_roblox_group` first.",
            ephemeral=True
        )
        return
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://groups.roblox.com/v1/groups/{group_id}") as resp:
                if resp.status != 200:
                    await interaction.response.send_message(
                        "❌ Error fetching group info. The group may no longer exist.",
                        ephemeral=True
                    )
                    return
                
                data = await resp.json()
                
                embed = discord.Embed(
                    title=f"🎮 {data.get('name', 'Unknown Group')}",
                    description=data.get('description', 'No description'),
                    color=discord.Color.blue(),
                    timestamp=datetime.now(timezone.utc)
                )
                
                embed.add_field(name="Group ID", value=group_id, inline=True)
                embed.add_field(name="Members", value=f"{data.get('memberCount', 0):,}", inline=True)
                embed.add_field(name="Owner", value=data.get('owner', {}).get('username', 'Unknown'), inline=True)
                
                if data.get('shout'):
                    shout_data = data['shout']
                    embed.add_field(
                        name="📢 Latest Shout",
                        value=f"{shout_data.get('body', 'No shout')}\n*- {shout_data.get('poster', {}).get('username', 'Unknown')}*",
                        inline=False
                    )
                
                embed.set_footer(text="Roblox Group Info")
                
                await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error fetching group info: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="ban_player", description="Ban a player from your Roblox game (Admin only)")
@app_commands.describe(
    roblox_username="The Roblox username to ban",
    duration_days="Ban duration in days (0 for permanent)",
    reason="Reason for the ban (shown to player)"
)
async def ban_player(
    interaction: discord.Interaction,
    roblox_username: str,
    duration_days: int = 0,
    reason: str = "Violation of game rules"
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    roblox_api_key = os.getenv("ROBLOX_API_KEY")
    universe_id = db.get_config('roblox_universe_id')
    
    if not roblox_api_key:
        await interaction.response.send_message(
            "❌ Roblox API key not configured. Please set ROBLOX_API_KEY environment variable.\n\n"
            "To set up:\n"
            "1. Go to https://create.roblox.com/credentials\n"
            "2. Create an API key with 'User Restrictions' permissions\n"
            "3. Add the key as ROBLOX_API_KEY in your environment secrets",
            ephemeral=True
        )
        return
    
    if not universe_id:
        await interaction.response.send_message(
            "❌ No Roblox universe linked! Please ask an admin to set the universe ID using the database.",
            ephemeral=True
        )
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://users.roblox.com/v1/usernames/users",
                json={"usernames": [roblox_username]}
            ) as resp:
                if resp.status != 200:
                    await interaction.followup.send(
                        f"❌ Could not find Roblox user '{roblox_username}'",
                        ephemeral=True
                    )
                    return
                
                user_data = await resp.json()
                if not user_data.get('data'):
                    await interaction.followup.send(
                        f"❌ Could not find Roblox user '{roblox_username}'",
                        ephemeral=True
                    )
                    return
                
                user_id = user_data['data'][0]['id']
            
            ban_payload = {
                "gameJoinRestriction": {
                    "active": True,
                    "displayReason": reason
                }
            }
            
            if duration_days > 0:
                ban_payload["gameJoinRestriction"]["duration"] = f"{duration_days * 86400}s"
            
            headers = {
                "x-api-key": roblox_api_key,
                "Content-Type": "application/json"
            }
            
            async with session.patch(
                f"https://apis.roblox.com/cloud/v2/universes/{universe_id}/user-restrictions/{user_id}",
                headers=headers,
                json=ban_payload
            ) as resp:
                if resp.status in [200, 201]:
                    duration_text = f"{duration_days} days" if duration_days > 0 else "permanent"
                    await interaction.followup.send(
                        f"✅ Successfully banned **{roblox_username}** (ID: {user_id})\n"
                        f"**Duration:** {duration_text}\n"
                        f"**Reason:** {reason}",
                        ephemeral=True
                    )
                else:
                    error_text = await resp.text()
                    await interaction.followup.send(
                        f"❌ Failed to ban user. API Error: {error_text}",
                        ephemeral=True
                    )
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error banning player: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="unban_player", description="Unban a player from your Roblox game (Admin only)")
@app_commands.describe(
    roblox_username="The Roblox username to unban"
)
async def unban_player(
    interaction: discord.Interaction,
    roblox_username: str
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    roblox_api_key = os.getenv("ROBLOX_API_KEY")
    universe_id = db.get_config('roblox_universe_id')
    
    if not roblox_api_key or not universe_id:
        await interaction.response.send_message(
            "❌ Roblox API not configured properly. Please check your setup.",
            ephemeral=True
        )
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://users.roblox.com/v1/usernames/users",
                json={"usernames": [roblox_username]}
            ) as resp:
                if resp.status != 200:
                    await interaction.followup.send(
                        f"❌ Could not find Roblox user '{roblox_username}'",
                        ephemeral=True
                    )
                    return
                
                user_data = await resp.json()
                if not user_data.get('data'):
                    await interaction.followup.send(
                        f"❌ Could not find Roblox user '{roblox_username}'",
                        ephemeral=True
                    )
                    return
                
                user_id = user_data['data'][0]['id']
            
            headers = {
                "x-api-key": roblox_api_key,
                "Content-Type": "application/json"
            }
            
            unban_payload = {
                "gameJoinRestriction": {
                    "active": False
                }
            }
            
            async with session.patch(
                f"https://apis.roblox.com/cloud/v2/universes/{universe_id}/user-restrictions/{user_id}",
                headers=headers,
                json=unban_payload
            ) as resp:
                if resp.status in [200, 201]:
                    await interaction.followup.send(
                        f"✅ Successfully unbanned **{roblox_username}** (ID: {user_id})",
                        ephemeral=True
                    )
                else:
                    error_text = await resp.text()
                    await interaction.followup.send(
                        f"❌ Failed to unban user. API Error: {error_text}",
                        ephemeral=True
                    )
    except Exception as e:
        await interaction.followup.send(
            f"❌ Error unbanning player: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="kick_member", description="Kick a member from the Discord server (Admin only)")
@app_commands.describe(
    member="The member to kick",
    reason="Reason for kicking the member"
)
async def kick_member(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    if member.top_role >= interaction.user.top_role and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ You cannot kick someone with a higher or equal role.",
            ephemeral=True
        )
        return
    
    try:
        await member.kick(reason=f"{reason} (by {interaction.user})")
        
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"**{member.mention}** has been kicked from the server.",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to kick this member.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error kicking member: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="timeout_member", description="Timeout a member (Admin only)")
@app_commands.describe(
    member="The member to timeout",
    duration="Duration in minutes",
    reason="Reason for the timeout"
)
async def timeout_member(
    interaction: discord.Interaction,
    member: discord.Member,
    duration: int,
    reason: str = "No reason provided"
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    if member.top_role >= interaction.user.top_role and not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ You cannot timeout someone with a higher or equal role.",
            ephemeral=True
        )
        return
    
    try:
        timeout_duration = timedelta(minutes=duration)
        await member.timeout(timeout_duration, reason=f"{reason} (by {interaction.user})")
        
        embed = discord.Embed(
            title="⏱️ Member Timed Out",
            description=f"**{member.mention}** has been timed out.",
            color=discord.Color.yellow(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to timeout this member.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error timing out member: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="warn_member", description="Warn a member (Admin only)")
@app_commands.describe(
    member="The member to warn",
    reason="Reason for the warning"
)
async def warn_member(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    try:
        db.add_warning(
            str(member.id),
            str(member),
            str(interaction.user.id),
            str(interaction.user),
            reason
        )
        
        warning_count = db.get_warning_count(str(member.id))
        
        embed = discord.Embed(
            title="⚠️ Member Warned",
            description=f"**{member.mention}** has been warned.",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=str(warning_count), inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await interaction.response.send_message(embed=embed)
        
        try:
            await member.send(
                f"⚠️ You have been warned in **{interaction.guild.name}**\n"
                f"**Reason:** {reason}\n"
                f"**Total Warnings:** {warning_count}\n\n"
                f"Please review the server rules to avoid further action."
            )
        except:
            pass
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error warning member: {str(e)}",
            ephemeral=True
        )


@bot.tree.command(name="warnings", description="View warnings for a member (Admin only)")
@app_commands.describe(
    member="The member to check warnings for"
)
async def view_warnings(
    interaction: discord.Interaction,
    member: discord.Member
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    warnings = db.get_user_warnings(str(member.id))
    
    if not warnings:
        await interaction.response.send_message(
            f"✅ {member.mention} has no warnings.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title=f"⚠️ Warnings for {member.display_name}",
        description=f"Total warnings: **{len(warnings)}**",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )
    
    for idx, warning in enumerate(warnings[:10], 1):
        timestamp = datetime.fromisoformat(warning['timestamp'])
        embed.add_field(
            name=f"Warning #{idx}",
            value=f"**Reason:** {warning['reason']}\n"
                  f"**By:** {warning['moderator_name']}\n"
                  f"**Date:** {timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
            inline=False
        )
    
    if len(warnings) > 10:
        embed.set_footer(text=f"Showing 10 of {len(warnings)} warnings")
    else:
        embed.set_footer(text=f"User ID: {member.id}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="clear_warnings", description="Clear all warnings for a member (Admin only)")
@app_commands.describe(
    member="The member to clear warnings for"
)
async def clear_warnings_cmd(
    interaction: discord.Interaction,
    member: discord.Member
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You need admin permissions to use this command.",
            ephemeral=True
        )
        return
    
    warning_count = db.get_warning_count(str(member.id))
    
    if warning_count == 0:
        await interaction.response.send_message(
            f"{member.mention} has no warnings to clear.",
            ephemeral=True
        )
        return
    
    db.clear_warnings(str(member.id))
    
    await interaction.response.send_message(
        f"✅ Cleared **{warning_count}** warning(s) for {member.mention}.",
        ephemeral=True
    )


async def main():
    discord_token = os.getenv("DISCORD_BOT_TOKEN")
    
    if not discord_token:
        print("ERROR: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please set your Discord bot token in Replit Secrets.")
        return
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("WARNING: DATABASE_URL not found! Database operations will fail.")
        print("Please set DATABASE_URL in Replit Secrets.")
    
    try:
        await bot.start(discord_token)
    except Exception as e:
        print(f"Error starting bot: {e}")


if __name__ == "__main__":
    asyncio.run(main())
