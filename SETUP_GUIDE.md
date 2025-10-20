# Discord Bot Setup Guide

## Complete Setup Instructions

This guide will help you set up your Discord bot from scratch, including fixing the "Private application cannot have a default authorization link" error.

---

## Part 1: Discord Developer Portal Setup

### Step 1: Create Your Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** and give it a name
3. Go to the **"Bot"** section in the left sidebar
4. Click **"Add Bot"** and confirm

### Step 2: Enable Required Privileged Intents ⚠️ CRITICAL

In the **Bot** section, scroll down to **"Privileged Gateway Intents"**:

✅ **Enable These:**
- ☑ **Server Members Intent** (REQUIRED)
- ☑ **Message Content Intent** (REQUIRED)

**Why these are needed:**
- **Server Members Intent**: Required for role management (adding/removing shift role)
- **Message Content Intent**: Required for message handling and bot functionality

### Step 3: Make Your Bot Private

Still in the **Bot** section:

1. Find the **"Public Bot"** toggle
2. **UNCHECK/DISABLE** this option
3. Save changes

**Result:** Only you (the bot owner) can add the bot to servers.

### Step 4: Fix "Private application cannot have a default authorization link" Error

**THIS IS THE MOST IMPORTANT STEP!**

1. Go to **"Installation"** tab in the left sidebar
2. Under **"Authorization Methods"**, you'll see **"Discord Provided Link"**
3. **CHANGE THIS TO "NONE"**
4. Save changes

**This is the fix for the error you're getting!** Private bots cannot use Discord's provided authorization link. You must use "None" and create your own OAuth2 URL.

### Step 5: Bot Permissions Setup - OAuth2 URL Generator

1. Go to **"OAuth2"** → **"URL Generator"** in the left sidebar

2. Under **SCOPES**, select:
   - ☑ `bot`
   - ☑ `applications.commands`

3. Under **BOT PERMISSIONS**, select:
   - ☑ **Manage Roles** (Required for shift role management)
   - ☑ **Send Messages** (Required for bot responses)
   - ☑ **Embed Links** (Required for embedded messages)
   - ☑ **Read Message History** (Recommended)
   - ☑ **Use Slash Commands** (Required for commands)
   - ☑ **Manage Messages** (Optional, for cleanup)
   - ☑ **View Channels** (Required to see channels)

4. **Copy the generated URL** at the bottom
5. Use this URL to invite your bot to your server

**Important:** Make sure your bot's role in the server is positioned **ABOVE** the shift role you want it to manage in Server Settings → Roles!

### Step 6: Copy Your Bot Token

1. Go back to the **"Bot"** section
2. Under **"Token"**, click **"Reset Token"**
3. Click **"Copy"**
4. **IMPORTANT:** Store this securely - you'll need it for the next steps!

---

## Part 2: Replit Environment Setup

### Step 1: Set Up Secrets

1. In your Replit project, click on **"Secrets"** in the left sidebar (lock icon)
2. Add these secrets:

   **Required:**
   - Key: `DISCORD_BOT_TOKEN`
     Value: [Your bot token from Step 6 above]
   
   - Key: `DATABASE_URL`
     Value: [Your Neon PostgreSQL URL - see below for how to get it]

   **Optional (for Roblox game moderation):**
   - Key: `ROBLOX_API_KEY`
     Value: [Your Roblox Open Cloud API key]

### Step 2: Get Your Neon Database URL

1. Go to [Neon.tech](https://neon.tech)
2. Create a free account
3. Create a new project
4. Copy your connection string - it looks like:
   ```
   postgresql://username:password@ep-xyz-123.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
5. Add this as the `DATABASE_URL` secret in Replit

---

## Part 3: Discord Server Configuration

### After Inviting the Bot

1. **Position the Bot's Role:**
   - Go to Server Settings → Roles
   - Drag the bot's role **ABOVE** the role you want it to manage
   - This is critical for the shift role system to work!

2. **Run the Setup Command:**
   ```
   /setup_shift shift_role:@YourShiftRole logs_channel:#shift-logs
   ```

3. **Set Admin Roles (Recommended):**
   ```
   /set_admin role1:@Admin role2:@Moderator
   ```
   This allows users with these roles to use admin commands without needing Discord administrator permissions.

4. **Set Up Weekly Reports (Optional):**
   ```
   /setup_weekly_reports channel:#reports
   ```
   This will automatically post weekly team statistics every Monday at midnight UTC.

---

## Part 4: Roblox Integration (Optional)

### For Game Moderation (Ban/Kick Features)

1. **Create Roblox API Key:**
   - Go to https://create.roblox.com/credentials
   - Click "Create API Key"
   - Give it a name like "Discord Bot Moderation"
   - Under "Access Permissions", select:
     - **User Restrictions** → Read + Write
   - Select your experience/universe
   - Create the key and copy it
   - Add it as `ROBLOX_API_KEY` in Replit Secrets

2. **Get Your Universe ID:**
   - Go to your game's page on Roblox
   - Click "..." → "Configure"
   - Look for "Universe ID" in the settings
   - Save this ID - you'll use it with the `/ban_player` command

3. **Link Your Universe:**
   - In your database (you can use a tool or manual SQL), add:
     ```sql
     INSERT INTO config (key, value) VALUES ('roblox_universe_id', 'YOUR_UNIVERSE_ID');
     ```

### For Group Integration

1. **Find Your Group ID:**
   - Go to your Roblox group page
   - The URL will be: `https://www.roblox.com/groups/GROUP_ID/...`
   - Copy the GROUP_ID number

2. **Link Your Group:**
   ```
   /link_roblox_group group_id:YOUR_GROUP_ID
   ```

3. **View Group Info:**
   ```
   /roblox_group_info
   ```

---

## Part 5: UptimeRobot (Keep Bot Alive - Optional for Fly.io)

If you're deploying to Fly.io, this is handled automatically. If you're running on Replit or another platform:

1. Go to [UptimeRobot.com](https://uptimerobot.com)
2. Create a free account
3. Add a new monitor:
   - **Monitor Type**: HTTP(s)
   - **Friendly Name**: Discord Shift Bot
   - **URL**: Your bot's URL + `/health`
   - **Monitoring Interval**: 5 minutes

---

## Summary of What to Enable in OAuth2 URL Generator

### Scopes:
- ✅ `bot`
- ✅ `applications.commands`

### Bot Permissions (Minimum Required):
- ✅ Manage Roles
- ✅ Send Messages
- ✅ Embed Links
- ✅ Read Message History
- ✅ View Channels

### Recommended Additional Permissions:
- ✅ Manage Messages
- ✅ Read Message History

---

## Available Commands

### Everyone Can Use:
- `/mystats` - Check your personal shift statistics

### Admin Only:
- `/setup_shift` - Set up the shift tracking system
- `/set_admin` - Configure admin roles for the bot
- `/help` - Show all available bot commands
- `/leaderboard` - Show top workers
- `/team_status` - View current team status
- `/set_goal` - Set team work goals
- `/force_clockout` - Force clock out a user
- `/send_embed` - Send custom embedded messages
- `/setup_weekly_reports` - Configure automated weekly reports
- `/link_roblox_group` - Link a Roblox group
- `/roblox_group_info` - Display Roblox group information
- `/ban_player` - Ban a player from your Roblox game
- `/unban_player` - Unban a player

---

## Automated Weekly Reports - What They Look Like

When you set up weekly reports, the bot will automatically post a message every Monday at midnight UTC containing:

📊 **Weekly Team Report**
- 📈 Total team hours worked this week
- 🏆 Top 5 contributors with their hours
- 📊 Team statistics

This helps you track team productivity and recognize top performers without manual work!

---

## Troubleshooting

### "Privileged intents not enabled" error
- Go to Bot section → Enable Server Members Intent and Message Content Intent

### "Private application cannot have a default authorization link" error
- Go to Installation tab → Set Authorization Methods to "None"
- Use the OAuth2 URL Generator instead

### Bot can't assign roles
- In Discord server settings, drag the bot's role ABOVE the shift role

### Commands not appearing
- Wait 1-2 hours for global command sync, or kick and re-invite the bot
- Make sure you invited the bot with `applications.commands` scope

### Database connection errors
- Verify your DATABASE_URL is correct in Replit Secrets
- Check that your Neon database is active

---

## Files Needed for Fly.io Deployment

When deploying to Fly.io, these are the files you need:

- ✅ `main.py` - Main bot code
- ✅ `database.py` - Database operations
- ✅ `web_server.py` - Health check server
- ✅ `Dockerfile` - Docker configuration
- ✅ `fly.toml` - Fly.io deployment settings
- ✅ `.dockerignore` - Docker ignore file
- ✅ `pyproject.toml` - Python dependencies
- ✅ `.gitignore` - Git ignore file

**DO NOT include:**
- ❌ `.env` file (use Fly secrets instead)
- ❌ Database files
- ❌ `__pycache__/` directories

---

## Next Steps

1. ✅ Complete Discord Developer Portal setup
2. ✅ Add secrets to Replit
3. ✅ Run the bot on Replit
4. ✅ Invite bot to your Discord server
5. ✅ Run `/setup_shift` in Discord
6. ✅ (Optional) Set up Roblox integration
7. ✅ (Optional) Deploy to Fly.io for 24/7 uptime

Need help? Check the error messages in the console - they're designed to be helpful!
