# PCBot - Telegram Bot with File Management and Security Features

## Overview

PCBot is a secure Telegram bot designed for remote PC management with advanced file operations, system monitoring, and security features. The bot provides secure file hiding/unhiding capabilities, system screenshots, and comprehensive audit logging.

## Project Structure

```
PCBot/
|
├── src/
|   ├── PCBot.py               # Main bot entry point
|   ├── commands.py            # Consolidated command handlers
|   ├── security_manager.py    # Security and authorization
|   ├── utilities.py           # Consolidated utility functions
|   ├── monitor.py             # System monitoring functions
|   └── secure_delete.py       # Secure file deletion
├── docs/
|   └── TESTING_REPORT.md      # Comprehensive testing report
├── backup/
|   └── [archived files]       # Backup of original modular files
├── config.json                # Bot configuration (auto-created on first run)
├── requirements.txt           # Python dependencies
├── hidden_pcbot.vbs           # Windows hidden launcher (primary)
├── install_prerequisites.bat  # One-time Windows setup script
├── deploy.bat                 # Windows quick-deploy script
├── deploy.sh                  # Linux quick-deploy script
├── run_pcbot.py               # Bot launcher script
└── README.md                  # This file
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Boltsky/PCBot.git
cd PCBot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the Bot

On first run, PCBot will automatically prompt you to enter your Telegram bot token and authorized user IDs, then create `config.json` for you. Manual editing is optional:

```json
{
  "bot_token": "your_telegram_bot_token_here",
  "authorized_users": [123456789, 987654321]
}
```

### 4. First Run

```bash
python run_pcbot.py
```

Complete the interactive setup when prompted. After `config.json` is created, stop the bot and use the Windows VBS launcher for persistent deployment.

---

## Windows Deployment (Recommended)

PCBot ships with `hidden_pcbot.vbs` — a portable Windows launcher that starts the bot silently (no console window) from whatever folder it is stored in.

### Prerequisites (one time per PC)

Run as **Administrator**:

```bat
install_prerequisites.bat
```

This installs Chocolatey, Git, and Python 3 automatically.

### Required Folder Layout

Keep all these files in the same folder:

```
PCBot/
├── hidden_pcbot.vbs     <- launcher
├── run_pcbot.py
├── requirements.txt
├── config.json
├── src/
└── logs/
```

### The VBS Launcher

`hidden_pcbot.vbs` uses a portable pattern that detects its own folder at runtime — no hardcoded paths:

```vbscript
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

WshShell.Run "cmd /c ""py -3 run_pcbot.py""", 0, False

Set FSO = Nothing
Set WshShell = Nothing
```

- Runs `run_pcbot.py` from the folder where the `.vbs` is saved
- Window mode `0` = hidden (no black console window)
- `False` = non-blocking (does not wait for script to finish)
- Works from any path — USB drive, Desktop, server share, etc.

### Launch Hidden

Double-click `hidden_pcbot.vbs` to start PCBot with no visible window.

Alternatively via command line:

```bat
wscript.exe hidden_pcbot.vbs
```

---

## Auto-Start After Reboot (Windows Persistence)

### Method A: Startup Folder (Simple)

1. Press `Win + R`, type `shell:startup`, press **Enter**
2. Create a **shortcut** to `hidden_pcbot.vbs` (right-click → Create shortcut)
3. Move the **shortcut** (not the original file) into the Startup folder
4. PCBot will now start automatically on every Windows login

> **Note:** Place the shortcut in the Startup folder, not the original `.vbs` file itself.

### Method B: Task Scheduler (More Reliable / Elevated)

Use this method for higher reliability or if you need the bot to run with elevated privileges:

1. Open **Task Scheduler** (search in Start menu)
2. Click **Create Task** (not "Create Basic Task")
3. **General tab:**
   - Name: `PCBot`
   - (Optional) Check **Run with highest privileges**
4. **Triggers tab:**
   - Click **New** → Begin the task: **At log on**
5. **Actions tab:**
   - Click **New**
   - Program/script: `wscript.exe`
   - Add arguments: `"C:\full\path\to\hidden_pcbot.vbs"`
6. Click **OK** to save

After every reboot or logon, Task Scheduler will silently launch `hidden_pcbot.vbs`, which starts PCBot.

> **Important:** Use the full absolute path to the `.vbs` file in Task Scheduler arguments.

---

## Linux Deployment

For Linux servers, use the included `deploy.sh`:

```bash
chmod +x deploy.sh
./deploy.sh
```

The script performs:
- `git pull origin main` — pulls latest code
- `pip install -r requirements.txt` — updates dependencies
- Runs tests via `python3 test_focused.py`
- Starts `python3 run_pcbot.py`
- Tails `/var/log/pcbot/pcbot.log` for live output

> Adjust the log path in `deploy.sh` to match your server environment.

---

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize bot and verify authorization |
| `/help` | Display all available commands |
| `/screenshot` | Capture current screen |
| `/files [path]` | List files in directory |
| `/download [file]` | Download a file from the PC |
| `/upload` | Upload a file to the PC |
| `/hide [file]` | Securely hide a file |
| `/unhide [file]` | Restore a hidden file |
| `/sysinfo` | Display system information |
| `/processes` | List running processes |
| `/kill [pid]` | Kill a process by PID |
| `/cmd [command]` | Execute a shell command |

---

## Configuration

```json
{
  "bot_token": "your_telegram_bot_token_here",
  "authorized_users": [123456789, 987654321]
}
```

- `bot_token`: Get this from [@BotFather](https://t.me/BotFather) on Telegram
- `authorized_users`: List of Telegram user IDs allowed to control the bot

---

## Security Features

- **Authorization**: Only whitelisted Telegram user IDs can interact with the bot
- **Audit Logging**: All commands and actions are logged with timestamps
- **Secure File Operations**: Files are hidden using system-level attributes
- **Secure Delete**: Files can be permanently deleted without recovery
- **No Open Ports**: Bot communicates via Telegram polling — no inbound firewall rules needed

---

## Requirements

- Python 3.8+
- Windows 10/11 (for VBS launcher) or Linux
- Telegram bot token (from @BotFather)
- Internet connection

See `requirements.txt` for Python package dependencies.

---

## Disclaimer

This project is intended for research and education purposes only. Use responsibly and only on systems you own or have explicit permission to manage.
