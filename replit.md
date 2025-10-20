# Discord Shift Tracking Bot for Roblox Game Development

## Overview
A comprehensive Discord bot designed specifically for Roblox game development teams. Features shift tracking, work hour management, team dashboards, Roblox game moderation, Discord moderation, automated reports, and more. Built with discord.py, PostgreSQL (Neon), and designed for 24/7 operation.

## Recent Changes
- **October 20, 2025**: Complete bot setup and new features
  - **Discord Moderation Commands**: Added `/kick_member`, `/timeout_member`, `/warn_member`, `/warnings`, and `/clear_warnings`
  - **Warning System**: Full warning tracking with database storage and warning history
  - **Roblox Integration**: Instant group linking with `/link_roblox_group` 
  - **Game Moderation**: Ban/unban players via Roblox Open Cloud API
  - **Enhanced Permissions**: Role-based moderation with hierarchy checks
  - **Bot Token Management**: Added proper token validation and error handling
  - **Database Ready**: Neon PostgreSQL with DATABASE_URL from environment
  - **Deployment Ready**: Configured for fly.io deployment with UptimeRobot monitoring

## Project Architecture

### Core Components
- **main.py**: Discord bot with slash commands, button interactions, and automated tasks (1282 lines)
- **database.py**: PostgreSQL database operations with connection pooling and warnings system (315 lines)
- **web_server.py**: Aiohttp web server for health checks on port 8080 (22 lines)
- **README.md**: Complete project documentation for end users
- **SETUP_GUIDE.md**: Step-by-step Discord Developer Portal and deployment setup guide

### Features

#### 1. Shift System
   - Interactive clock in/out buttons with instant updates
   - Real-time embedded message showing active workers
   - Automatic role assignment/removal
   - All shift actions logged with durations
   - Personal statistics and leaderboards

#### 2. Permission System
   - Discord administrators always have access
   - Custom admin roles via `/set_admin` command (supports up to 5 roles)
   - Only `/mystats` available to non-admins
   - All other commands require admin permissions

#### 3. Discord Moderation Commands (NEW)
   - `/kick_member` - Kick members from server with reason
   - `/timeout_member` - Timeout members for X minutes
   - `/warn_member` - Warn members and track warnings in database
   - `/warnings` - View warning history for any member
   - `/clear_warnings` - Clear all warnings for a member
   - Role hierarchy protection (can't moderate higher roles)
   - DM notifications to warned users

#### 4. Logging & Analytics
   - All shift actions logged to dedicated channel
   - Shows shift duration and total time worked
   - Real-time leaderboards (admin-only)
   - Personal statistics tracking
   - Warning history with timestamps and moderator info

#### 5. Team Management Commands (Admin Only)
   - `/setup_shift` - Configure the shift system
   - `/set_admin` - Set admin roles (supports up to 5 roles)
   - `/help` - Show all available commands
   - `/send_embed` - Send custom embedded messages
   - `/leaderboard` - Show top workers
   - `/team_status` - Team dashboard with active users
   - `/set_goal` - Set work hour goals
   - `/force_clockout` - Admin override for clock out
   - `/setup_weekly_reports` - Configure automated reports

#### 6. Public Commands
   - `/mystats` - Personal statistics (everyone - ONLY non-admin command)

#### 7. Roblox Integration
   - `/link_roblox_group` - Instantly link Roblox group (admin-only)
   - `/roblox_group_info` - Display group information with member count (admin-only)
   - `/ban_player` - Ban players from game using Open Cloud API (admin-only)
   - `/unban_player` - Unban players (admin-only)
   - Real-time group data fetching via Roblox API

#### 8. Automated Features
   - Weekly team reports posted every Monday at midnight UTC
   - Reports include total hours, top contributors, and statistics
   - Configured via `/setup_weekly_reports` command
   - Auto-restart on deployment

#### 9. Deployment
   - Fly.io ready with Dockerfile and fly.toml
   - PostgreSQL (Neon) database with connection pooling
   - Health check endpoint at /health for UptimeRobot
   - Environment-based secrets management
   - Graceful error handling for missing secrets

### Database Schema (PostgreSQL)

#### shifts table
   - Tracks clock in/out times (TIMESTAMP)
   - Duration in seconds
   - Active status (BOOLEAN)
   - Indexed on user_id and is_active

#### config table
   - Bot configuration persistence
   - Stores admin_role_ids, roblox_group_id, reports_channel_id, etc.
   - Survives restarts and deployments

#### warnings table (NEW)
   - Track member warnings with full history
   - Stores user_id, username, moderator info, reason, timestamp
   - Indexed on user_id for fast lookups
   - Supports warning counts and history retrieval

## Dependencies
- discord.py - Discord bot framework
- aiohttp - Async HTTP for web server and Roblox API calls
- python-dotenv - Environment variable management
- psycopg2-binary - PostgreSQL database driver

## Environment Variables (Secrets)
- `DISCORD_BOT_TOKEN` - Discord bot authentication token (REQUIRED)
- `DATABASE_URL` - Neon PostgreSQL connection string (REQUIRED)
- `ROBLOX_API_KEY` - Roblox Open Cloud API key (OPTIONAL - for game moderation)

**Note:** DATABASE_URL is used in database.py line 10 to create the connection pool. Bot will exit gracefully if DISCORD_BOT_TOKEN is missing.

## Discord Developer Portal Setup
- **Required Intents**: Server Members Intent, Message Content Intent
- **Bot Privacy**: Can be private (owner-only invites)
- **IMPORTANT**: For private bots, set Authorization Methods to "NONE" in Installation tab
- **OAuth2 Scopes**: bot, applications.commands
- **Permissions**: Manage Roles, Send Messages, Embed Links, Kick Members, Moderate Members, Use Slash Commands
- See SETUP_GUIDE.md for complete configuration guide

## Deployment Files for Fly.io

### Required Files for GitHub:
1. **main.py** - Main bot code (1282 lines)
2. **database.py** - Database operations (315 lines)
3. **web_server.py** - Health check server (22 lines)
4. **Dockerfile** - Docker build configuration
5. **fly.toml** - Fly.io app configuration
6. **pyproject.toml** - Python dependencies (uv)
7. **uv.lock** - Dependency lock file
8. **.dockerignore** - Docker ignore rules
9. **.gitignore** - Git ignore rules
10. **README.md** - Project documentation
11. **SETUP_GUIDE.md** - Setup instructions
12. **.env.example** - Example environment variables

### DO NOT Deploy:
- `.env` file (use Fly secrets instead)
- Database files (*.db, *.sqlite)
- `__pycache__/` directories
- `.pythonlibs/` virtual environment
- `attached_assets/` folder

## UptimeRobot Integration
- Health endpoint: `https://your-app.fly.dev/health`
- Runs on port 8080
- Implemented in web_server.py
- Started automatically when bot runs (main.py)

## Fly.io Deployment Steps

1. **Set up Neon database** and get DATABASE_URL
2. **Configure Discord bot** in Developer Portal
3. **Create Fly.io app**: 
   ```bash
   flyctl apps create your-bot-name
   ```
4. **Set secrets**:
   ```bash
   flyctl secrets set DISCORD_BOT_TOKEN="your-token"
   flyctl secrets set DATABASE_URL="your-database-url"
   flyctl secrets set ROBLOX_API_KEY="your-key"  # Optional
   ```
5. **Deploy**: 
   ```bash
   flyctl deploy
   ```
6. **Check logs**: 
   ```bash
   flyctl logs
   ```
7. **Set up UptimeRobot** monitoring on /health endpoint

## User Preferences
- **ONLY `/mystats` is usable by non-admin users** - all other commands require admin permissions
- Admin roles can be configured via `/set_admin` command (supports up to 5 roles)
- Discord administrators always have access to admin commands
- Weekly reports are automated (posted every Monday at midnight UTC)
- Bot supports Roblox game moderation via Open Cloud API
- Discord moderation with full warning system
- Private bot configuration supported
- Uses external PostgreSQL database (Neon.com)
- Designed for Roblox game development workflow

## Roblox Open Cloud API Setup

### For Ban/Unban Features:
1. Go to https://create.roblox.com/credentials
2. Create API Key
3. Name it "Discord Bot Moderation"
4. Select "User Restrictions" with Read + Write permissions
5. Select your experience/universe
6. Copy the key and add as `ROBLOX_API_KEY` secret
7. Add your Universe ID to config table:
   ```sql
   INSERT INTO config (key, value) VALUES ('roblox_universe_id', 'YOUR_UNIVERSE_ID');
   ```

### Where to Find APIs:
- **Ban/Unban API**: https://create.roblox.com/docs/cloud/reference/UserRestriction
- **Group API**: https://groups.roblox.com/v1/groups/{groupId}
- **User API**: https://users.roblox.com/v1/usernames/users

## New Command Summary

### Discord Moderation (NEW):
- `/kick_member <member> [reason]` - Kick a member from the server
- `/timeout_member <member> <duration> [reason]` - Timeout a member for X minutes
- `/warn_member <member> <reason>` - Warn a member and log to database
- `/warnings <member>` - View warning history for a member
- `/clear_warnings <member>` - Clear all warnings for a member

### All Commands Require Admin Except:
- `/mystats` - Everyone can use this

## Bot Permissions Needed (Discord)
- Manage Roles (for shift role)
- Send Messages
- Embed Links
- Read Message History
- View Channels
- Kick Members (for `/kick_member`)
- Moderate Members (for `/timeout_member`)
- Use Slash Commands

## Troubleshooting Common Issues

1. **Bot won't start**: Check that DISCORD_BOT_TOKEN is set in secrets
2. **Database errors**: Verify DATABASE_URL is correct
3. **Can't assign roles**: Move bot's role ABOVE shift role in server settings
4. **Commands not showing**: Wait 1-2 hours or re-invite with applications.commands scope
5. **Can't kick/timeout**: Verify bot has Kick Members and Moderate Members permissions
6. **Roblox bans fail**: Check ROBLOX_API_KEY is set and has User Restrictions permissions

## Project Stats
- Total Lines of Code: ~1,620
- Commands: 23 total (22 admin-only, 1 public)
- Database Tables: 3 (shifts, config, warnings)
- API Integrations: 2 (Discord, Roblox)
- Deployment Platforms: Fly.io, Replit
- Database: Neon PostgreSQL
