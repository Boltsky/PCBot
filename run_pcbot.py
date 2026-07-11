#!/usr/bin/env python3
"""
Run PCBot - Configuration and Launcher Script

This script prompts the user for their Telegram bot token and user ID,
creates a configuration file, and then launches the PCBot.
"""

import json
import os
import sys
import subprocess
from pathlib import Path

def get_user_input():
    """Get bot token and user ID from user input."""
    print("=== PCBot Configuration ===\n")

    print("Please provide your Telegram bot credentials:")
    print("(You can get a bot token from @BotFather on Telegram)\n")

    # Get bot token
    while True:
        bot_token = input("Enter your Telegram bot token: ").strip()
        if bot_token:
            break
        print("Bot token cannot be empty. Please try again.\n")

    # Get user ID(s)
    print("\nEnter your Telegram user ID(s):")
    print("(You can get your user ID from @userinfobot on Telegram)")
    print("(For multiple users, separate with commas: 123456789,987654321)")

    while True:
        user_input = input("Enter authorized user ID(s): ").strip()
        if user_input:
            try:
                # Parse user IDs and convert to integers
                user_ids = [int(uid.strip()) for uid in user_input.split(',')]
                break
            except ValueError:
                print("Invalid user ID format. Please enter numeric IDs only.\n")
        else:
            print("User ID cannot be empty. Please try again.\n")

    return bot_token, user_ids

def create_config_file(bot_token, user_ids):
    """Create the configuration file with the provided credentials."""
    config = {
        "bot_token": bot_token,
        "authorized_users": user_ids
    }

    config_path = Path("config.json")

    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        print(f"\nConfiguration saved to {config_path}")
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False

def check_existing_config():
    """Check if config file already exists and use it automatically."""
    config_path = Path("config.json")
    if config_path.exists():
        print("Found existing configuration file.")
        print("Using existing configuration...")  # Auto-no
        return False  # Changed: Always False (skip reconfigure)
    return True

def run_pcbot():
    """Launch the PCBot."""
    bot_script = Path("src/PCBot.py")

    if not bot_script.exists():
        print(f"Error: Could not find {bot_script}")
        print(f"Current directory: {os.getcwd()}")
        sys.exit(1)

    print("\n" + "="*50)
    print("PCBot Launcher")
    print("="*50)
    print("Starting PCBot...")
    print("Go to your bot on Telegram and press /start")
    print("="*50 + "\n")

    try:
        subprocess.run([sys.executable, str(bot_script)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nPCBot exited with error code: {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print("\nPCBot stopped by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    needs_config = check_existing_config()

    if needs_config:
        bot_token, user_ids = get_user_input()
        if not create_config_file(bot_token, user_ids):
            sys.exit(1)
    else:
        print("Using existing configuration...")

    run_pcbot()

if __name__ == "__main__":
    main()
