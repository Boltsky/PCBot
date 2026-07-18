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
├── install_prerequisites.bat  # Fresh Windows setup script (run this FIRST)
├── deploy.bat                 # Windows quick-deploy script
├── deploy.sh                  # Linux quick-deploy script
├── run_pcbot.py               # Bot launcher script
└── README.md                  # This file
```

---

## Windows Installation (Fresh Machine)

> These steps are for a **brand new Windows PC** with nothing pre-installed (no Python, no Git, no package managers). Follow them in order.

### Step 1 — Download and Run the Prerequisites Installer

On a fresh Windows machine, you won't have Git to clone the repo yet. So the very first thing to do is:

1. Download **[install_prerequisites.bat](https://github.com/Boltsky/PCBot/blob/master/install_prerequisites.bat)** directly from the GitHub page (click **Raw**, then save the file)
2. Right-click the downloaded file and choose **"Run as administrator"
3. Wait for it to complete — this may take several minutes depending on your internet speed

The script will automatically install:
- **Chocolatey** — Windows package manager
- **Git** — required to clone the repository
- **Python 3** — required to run the bot

It checks for each tool before installing, so it is safe to re-run. At the end, it prints the installed versions to confirm everything is ready.

> **Note:** You must run this as Administrator or the script will exit with an error. Right-click the file and select "Run as administrator".

> **Note:** After the script finishes, **close and reopen any terminal/Command Prompt windows** to ensure the new PATH changes (Git, Python) take effect.

---

### Step 2 — Clone the Repository

Once Git is installed, open a new Command Prompt and run:

```bash
git clone https://github.com/Boltsky/PCBot.git
cd PCBot
```

---

### Step 3 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — First Run & Bot Setup

```bash
python run_pcbot.py
```

On first run, PCBot will prompt you for:
- Your **Telegram bot token** (get one from [@BotFather](https://t.me/BotFather))
- Your **authorized Telegram user ID(s)**

It will then create `config.json` automatically. Once setup is complete, stop the bot (`Ctrl+C`) and proceed to the deployment step.

> Manual editing of `config.json` is optional. The file is auto-generated on first run.

---

### Step 5 — Deploy Hidden with VBS Launcher

PCBot includes `hidden_pcbot.vbs` — a portable Windows launcher that starts the bot silently (no console window) from whatever folder it lives in.

**Double-click `hidden_pcbot.vbs`** to start PCBot with no visible window.

Or run it from command line:

```bat
wscript.exe hidden_pcbot.vbs
```

The launcher uses this portable pattern (no hardcoded paths):

```vbscript
Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

scriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

WshShell.Run "cmd /c ""py -3 run_pcbot.py""", 0, False

Set FSO = Nothing
Set WshShell = Nothing
```

- Window mode `0` = hidden (no black console window)
- `False` = non-blocking
- Works from any location — Desktop, USB drive, server share, etc.
- `hidden_pcbot.vbs` and `run_pcbot.py` must stay in the same folder

---

## Auto-Start After Reboot (Windows Persistence)

### Method A: Startup Folder (Simple)

1. Press `Win + R`, type `shell:startup`, press **Enter**
2. Right-click `hidden_pcbot.vbs` → **Create shortcut**
3. Move the **shortcut** (not the original file) into the Startup folder
4. PCBot will now launch automatically on every Windows login

> Place only the shortcut in the Startup folder, not the `.vbs` file itself.

### Method B: Task Scheduler (More Reliable)

1. Open **Task Scheduler** → **Create Task**
2. **General tab:** Name it `PCBot`; optionally check **Run with highest privileges**
3. **Triggers tab:** New → **At log on**
4. **Actions tab:** New →
   - Program/script: `wscript.exe`
   - Add arguments: `"C:\full\path\to\hidden_pcbot.vbs"`
5. Click **OK** to save

> Always use the full absolute path to the `.vbs` file in the arguments field.

---

## Linux Deployment

For Linux servers, use the included `deploy.sh`:

```bash
chmod +x deploy.sh
./deploy.sh
```

The script:
- Pulls the latest code (`git pull origin main`)
- Installs/updates dependencies (`pip install -r requirements.txt`)
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

`config.json` is created automatically on first run. To edit it manually:

```json
{
  "bot_token": "your_telegram_bot_token_here",
  "authorized_users": [123456789, 987654321]
}
```

- `bot_token`: Get from [@BotFather](https://t.me/BotFather) on Telegram
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

- Windows 10/11 (for VBS launcher) or Linux
- Python 3.8+
- Git
- Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Internet connection

> On a fresh Windows machine, run `install_prerequisites.bat` as Administrator first — it handles Git and Python installation automatically.

See `requirements.txt` for Python package dependencies.

---

## Disclaimer

This project is intended for research and education purposes only. Use responsibly and only on systems you own or have explicit permission to manage.
