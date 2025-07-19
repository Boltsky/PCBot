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
        print(f"\n✓ Configuration saved to {config_path.absolute()}")
        return True
    except Exception as e:
        print(f"\n✗ Error saving configuration: {e}")
        return False

def run_pcbot():
    """Launch the PCBot."""
    pcbot_path = Path("src/PCBot.py")
    
    if not pcbot_path.exists():
        print(f"\n✗ Error: PCBot.py not found in current directory")
        print(f"Current directory: {Path.cwd()}")
        return False
    
    print("\n=== Launching PCBot ===")
    print("Press Ctrl+C to stop the bot")
    print("🤖 Welcome to the bot! Please go to the bot and press /start to begin.\n")
    
    try:
        # Run PCBot.py
        subprocess.run([sys.executable, str(pcbot_path)], check=True)
        return True
    except KeyboardInterrupt:
        print("\n\n✓ Bot stopped by user")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Error running PCBot.py: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

def check_existing_config():
    """Check if config file already exists and ask user if they want to reconfigure."""
    config_path = Path("config.json")
    
    if config_path.exists():
        print("Found existing configuration file.")
        while True:
            choice = input("Do you want to reconfigure? (y/n): ").strip().lower()
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no.")
    
    return True

def main():
    """Main function to orchestrate the configuration and launch process."""
    print("PCBot Launcher")
    print("=" * 50)
    
    # Check if we need to configure
    if check_existing_config():
        # Get user input
        bot_token, user_ids = get_user_input()
        
        # Create configuration file
        if not create_config_file(bot_token, user_ids):
            print("\nFailed to create configuration. Exiting.")
            sys.exit(1)
    else:
        print("\nUsing existing configuration...")
    
    # Run the bot
    if not run_pcbot():
        print("\nFailed to launch PCBot.")
        sys.exit(1)

if __name__ == "__main__":
    main()
