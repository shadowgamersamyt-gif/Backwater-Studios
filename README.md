# Discord Shift Tracking Bot for Roblox Game Development

A powerful Discord bot designed specifically for Roblox game development teams. Track work hours, manage shifts, moderate your Roblox game from Discord, and keep your team organized with real-time statistics and automated reports.

## 🎮 Features

### Core Shift System
- **Clock In/Out Buttons**: Interactive embedded message for easy shift tracking
- **Real-time Display**: Shows who's currently working with live durations
- **Automatic Role Management**: Assigns/removes roles when team members clock in/out
- **Shift Logging**: All actions logged to a dedicated channel with durations
- **Leaderboard**: Track top contributors
- **Personal Stats**: Team members can check their own statistics

### Team Management
- **Admin Role System**: Set multiple admin roles beyond Discord administrators
- **Team Status Dashboard**: See who's working and top contributors
- **Work Goal Setting**: Set daily/weekly/monthly work hour targets
- **Automated Weekly Reports**: Automatic team performance summaries every Monday
- **Custom Embeds**: Send beautiful embedded messages to any channel

### Roblox Integration
- **Group Integration**: Link your Roblox group and display info
- **Game Moderation**: Ban/unban players directly from Discord using Roblox Open Cloud API
- **Alt Account Detection**: Bans automatically extend to related accounts (Roblox feature)

### Technical Features
- **PostgreSQL Database**: Uses Neon.com for reliable, scalable data storage
- **Keep-Alive Server**: Built-in health check endpoint for monitoring
- **Automated Reports**: Weekly team statistics posted automatically
- **Permission System**: Flexible admin role configuration

## 📋 Commands

### Everyone Can Use
- `/mystats` - Check your personal shift statistics

### Admin Only
- `/setup_shift <shift_role> <logs_channel>` - Initial setup
- `/set_admin <role1> [role2] [role3] [role4] [role5]` - Configure admin roles
- `/help` - Show all available bot commands
- `/leaderboard [top]` - Show top workers (default: top 10)
- `/team_status` - View current team status dashboard
- `/set_goal <hours> [period]` - Set team work goals
- `/force_clockout <user>` - Force clock out a team member
- `/send_embed <channel> <title> <description> [color]` - Send custom embedded messages
- `/setup_weekly_reports <channel>` - Configure automated weekly reports
- `/link_roblox_group <group_id>` - Link a Roblox group
- `/roblox_group_info` - Display Roblox group information
- `/ban_player <roblox_username> [duration_days] [reason]` - Ban a player from your game
- `/unban_player <roblox_username>` - Unban a player

## 🚀 Quick Start

### Prerequisites
1. Discord bot token from [Discord Developer Portal](https://discord.com/developers/applications)
2. PostgreSQL database from [Neon.tech](https://neon.tech) (free tier available)
3. (Optional) Roblox API key for game moderation features

### Setup on Replit

1. **Add Secrets** (click Secrets in left sidebar):
   - `DISCORD_BOT_TOKEN`: Your Discord bot token
   - `DATABASE_URL`: Your Neon PostgreSQL connection string
   - `ROBLOX_API_KEY`: (Optional) Your Roblox Open Cloud API key

2. **Run the bot** - Click the Run button

3. **Invite to Discord**:
   - Use the OAuth2 URL from Discord Developer Portal
   - Make sure to include `bot` and `applications.commands` scopes
   - See SETUP_GUIDE.md for detailed instructions

4. **Configure in Discord**:
   ```
   /setup_shift shift_role:@Developer logs_channel:#shift-logs
   /set_admin role1:@Admin
   ```

### Important Discord Developer Portal Settings

**Required Intents** (Bot tab):
- ✅ Server Members Intent
- ✅ Message Content Intent

**For Private Bots** (Installation tab):
- ⚙️ Authorization Methods: **NONE** (This fixes the "Private application cannot have a default authorization link" error!)

**OAuth2 Scopes**:
- ✅ `bot`
- ✅ `applications.commands`

**Bot Permissions**:
- ✅ Manage Roles
- ✅ Send Messages
- ✅ Embed Links
- ✅ Read Message History
- ✅ View Channels

📖 **For complete setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)**

## 📊 Automated Weekly Reports

When configured, the bot automatically posts weekly team reports every Monday at midnight UTC containing:

- 📈 Total team hours worked
- 🏆 Top 5 contributors
- 📊 Team performance metrics

Set up with: `/setup_weekly_reports channel:#your-channel`

## 🎮 Roblox Integration Features

### Game Moderation
Ban or unban players directly from Discord using Roblox's official Open Cloud API:

```
/ban_player roblox_username:PlayerName duration_days:7 reason:Cheating
/unban_player roblox_username:PlayerName
```

**Requirements:**
1. Roblox Open Cloud API key with "User Restrictions" permission
2. Your game's Universe ID configured in the database

### Group Integration
Link your Roblox group and display member info:

```
/link_roblox_group group_id:12345678
/roblox_group_info
```

## 🐛 Troubleshooting

### "Private application cannot have a default authorization link" Error
**Solution:** Go to Discord Developer Portal → Installation tab → Set Authorization Methods to **"None"**. Then use the OAuth2 URL Generator to create your invite link.

### Bot can't assign roles
**Solution:** In Discord server settings, drag the bot's role **ABOVE** the shift role in Server Settings → Roles.

### Commands not appearing
**Solution:** 
1. Make sure you invited the bot with `applications.commands` scope
2. Wait 1-2 hours for global sync, or kick and re-invite the bot

### Database connection errors
**Solution:** Verify your `DATABASE_URL` secret is correct and your Neon database is active.

### Roblox ban commands not working
**Solution:**
1. Make sure `ROBLOX_API_KEY` secret is set
2. Ensure API key has "User Restrictions" permissions
3. Verify your Universe ID is configured

## 📁 Project Structure

```
├── main.py              # Main bot code with all commands
├── database.py          # PostgreSQL database operations
├── web_server.py        # Health check endpoint
├── pyproject.toml       # Python dependencies
├── .env.example         # Example environment variables
├── SETUP_GUIDE.md       # Complete setup instructions
└── README.md            # This file

Deployment files:
├── Dockerfile           # Docker configuration for Fly.io
├── fly.toml             # Fly.io deployment settings
├── .dockerignore        # Docker ignore file
└── .gitignore           # Git ignore file
```

## 🔐 Security

- Bot token stored as secret (never in code)
- Database URL stored as secret
- Roblox API key stored as secret
- Bot can be configured as private (owner-only invites)
- Admin commands require either Discord administrator permission OR configured admin roles

## 📝 Environment Variables

```bash
# Required
DISCORD_BOT_TOKEN=your_discord_bot_token
DATABASE_URL=postgresql://user:pass@host/db

# Optional (for Roblox features)
ROBLOX_API_KEY=your_roblox_api_key
```

## 🚀 Deployment to Fly.io

For 24/7 uptime, deploy to Fly.io:

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Edit fly.toml and change app name
nano fly.toml

# Create app
flyctl apps create your-discord-bot-name

# Set secrets
flyctl secrets set DISCORD_BOT_TOKEN="your-token"
flyctl secrets set DATABASE_URL="your-database-url"
flyctl secrets set ROBLOX_API_KEY="your-roblox-key"  # Optional

# Deploy
flyctl deploy

# Check logs
flyctl logs
```

## 📖 Documentation

- [SETUP_GUIDE.md](SETUP_GUIDE.md) - Complete setup instructions with Discord portal configuration
- [.env.example](.env.example) - Example environment variables

## 🎯 Use Cases

Perfect for:
- Roblox game development teams
- Indie game studios
- Discord communities tracking member activity
- Remote team hour tracking
- Project-based work logging

## 💡 Future Features

Ideas for enhancement (from FEATURE_SUGGESTIONS.md):
- Task assignment system
- Bug report tracking
- Sprint/milestone management
- Achievement system
- GitHub integration
- Build deployment tracker

## 📄 License

Free to use for your Roblox game development team!

---

**Need help?** Check [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed instructions or review the error messages in the console - they're designed to be helpful!
