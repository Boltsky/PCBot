#!/usr/bin/env python3
"""
Run PCBot - Configuration and Launcher Script

On first run: automatically prompts the user for their Telegram bot token
and authorized user ID(s), creates config.json, then launches the bot.

On subsequent runs: detects existing config.json and launches directly.
"""

import json
import os
import sys
import subprocess
from pathlib import Path

CONFIG_PATH = Path("config.json")


def first_run_setup():
    """
    Called only on first run (no config.json found).
    Walks the user through entering their bot token and user ID(s),
    then writes config.json automatically.
    """
    print()
    print("=" * 55)
    print(" Welcome to PCBot - First-Time Setup")
    print("=" * 55)
    print()
    print(" No configuration file was found.")
    print(" Let's create one now. You will need:")
    print(" 1. A Telegram Bot Token (from @BotFather)")
    print(" 2. Your Telegram User ID (from @userinfobot)")
    print()
    print("=" * 55)
    print()

    while True:
        bot_token = input(" Enter your Telegram bot token: ").strip()
        if not bot_token:
            print(" [!] Token cannot be empty. Please try again.\n")
            continue

        if ":" not in bot_token:
            print(" [!] That doesn't look like a valid token (expected format: 123456:ABC...).")
            confirm = input(" Use it anyway? (y/n): ").strip().lower()
            if confirm not in ("y", "yes"):
                continue
        break

    print()

    print(" Enter the Telegram user ID(s) that are allowed to control this bot.")
    print(" For multiple users, separate with commas: 123456789,987654321")
    print()
    while True:
        user_input = input(" Enter authorized user ID(s): ").strip()
        if not user_input:
            print(" [!] User ID cannot be empty. Please try again.\n")
            continue
        try:
            user_ids = [int(uid.strip()) for uid in user_input.split(",") if uid.strip()]
            if not user_ids:
                raise ValueError
            break
        except ValueError:
            print(" [!] Invalid format. Please enter numeric IDs only (e.g. 123456789).\n")

    config = {
        "bot_token": bot_token,
        "authorized_users": user_ids
    }

    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print()
        print(f" [OK] Configuration saved to {CONFIG_PATH}")
        print()
    except Exception as e:
        print(f"\n [ERROR] Could not write {CONFIG_PATH}: {e}")
        sys.exit(1)

    return config


def load_existing_config():
    """
    Load and validate an existing config.json.
    Returns the config dict, or exits with an error if the file is broken.
    """
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        if not config.get("bot_token"):
            raise ValueError("'bot_token' is missing or empty in config.json")
        if not config.get("authorized_users"):
            raise ValueError("'authorized_users' is missing or empty in config.json")

        print(f" [OK] Loaded configuration from {CONFIG_PATH}")
        return config

    except json.JSONDecodeError as e:
        print(f"\n [ERROR] config.json is corrupted or invalid JSON: {e}")
        print(" Delete config.json and run again to reconfigure.")
        sys.exit(1)
    except ValueError as e:
        print(f"\n [ERROR] {e}")
        print(" Delete config.json and run again to reconfigure.")
        sys.exit(1)
    except Exception as e:
        print(f"\n [ERROR] Could not read config.json: {e}")
        sys.exit(1)


def run_pcbot():
    """Launch src/PCBot.py as a subprocess."""
    bot_script = Path("src/PCBot.py")

    if not bot_script.exists():
        print(f"\n [ERROR] Cannot find {bot_script}")
        print(f" Current directory: {os.getcwd()}")
        print(" Make sure you are running this from the PCBot root folder.")
        sys.exit(1)

    print()
    print("=" * 55)
    print(" PCBot Launcher")
    print("=" * 55)
    print(" Starting bot... Go to Telegram and send /start")
    print(" Press Ctrl+C at any time to stop the bot.")
    print("=" * 55)
    print()

    try:
        subprocess.run([sys.executable, str(bot_script)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n [ERROR] PCBot exited with error code: {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\n\n PCBot stopped by user. Goodbye!")
    except Exception as e:
        print(f"\n [ERROR] Unexpected error: {e}")
        sys.exit(1)


def main():
    """Main entry point - handles first-run setup automatically."""
    if not CONFIG_PATH.exists():
        first_run_setup()
    else:
        load_existing_config()

    run_pcbot()


if __name__ == "__main__":
    main()
