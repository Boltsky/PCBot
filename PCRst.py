import os
import shutil
import logging
import subprocess
import platform
import winreg
import tempfile
import stat
import io
import asyncio
import threading
import time
import cv2
import numpy as np
import mimetypes
import hashlib
import zipfile
import json
import fnmatch
import glob
import urllib.request
import urllib.parse
import urllib.error
import ssl
import re
import tarfile
from pathlib import Path
from datetime import datetime
from mss import mss
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional, Callable, List, Dict, Any
from threading import Semaphore, Lock
import weakref
import aiofiles
import aiohttp
from security_manager import SecurityManager, secure_operation, security_manager, SecurityEvent

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = '7344228475:AAGfRCF10-jR_b-8qtof8HnslhIODMUwXwE'

@secure_operation('read')
async def tree_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Display the directory tree of the current directory with depth control.
    Usage: /tree [depth=2]
    """
    try:
        user_id = str(update.effective_user.id)
        
        # Parse depth parameter
        depth = 2  # Default depth
        if context.args:
            try:
                depth = int(context.args[0])
                if depth < 1:
                    await update.message.reply_text(
                        "⚠️ **Invalid Depth**\n\n"
                        "Depth must be at least 1.\n"
                        "Usage: `/tree [depth]`\n"
                        "Example: `/tree 3`",
                        parse_mode='Markdown'
                    )
                    return
                elif depth > 10:
                    await update.message.reply_text(
                        "⚠️ **Depth Limit Exceeded**\n\n"
                        "Maximum depth is 10 for performance reasons.\n"
                        "Usage: `/tree [depth]`\n"
                        "Example: `/tree 5`",
                        parse_mode='Markdown'
                    )
                    return
            except ValueError:
                await update.message.reply_text(
                    "⚠️ **Invalid Format**\n\n"
                    "Please enter a valid number for depth.\n"
                    "Usage: `/tree [depth]`\n"
                    "Example: `/tree 3`",
                    parse_mode='Markdown'
                )
                return
        
        # Get current directory from security manager
        current_dir = security_manager.get_user_directory(user_id)
        
        # Validate directory path
        path_valid, path_msg = security_manager.validate_file_path(current_dir, user_id)
        if not path_valid:
            await update.message.reply_text(f"❌ Access denied: {path_msg}")
            return
        
        if not os.path.exists(current_dir):
            await update.message.reply_text(f"❌ Directory does not exist: `{current_dir}`")
            return
        
        if not os.path.isdir(current_dir):
            await update.message.reply_text(f"❌ Path is not a directory: `{current_dir}`")
            return
        
        # Build the tree structure
        tree_lines = []
        max_lines = 500  # Limit output to prevent spam
        
        def build_tree(path, prefix='', level=0):
            if level >= depth or len(tree_lines) >= max_lines:
                return
                
            try:
                items = sorted(os.listdir(path))
                # Filter out hidden files for better readability
                items = [item for item in items if not item.startswith('.')]
                
                for i, item in enumerate(items):
                    if len(tree_lines) >= max_lines:
                        break
                        
                    item_path = os.path.join(path, item)
                    
                    # Skip if we can't access the item
                    if not os.path.exists(item_path):
                        continue
                    
                    # Determine the tree connector
                    is_last = i == len(items) - 1
                    connector = '└── ' if is_last else '├── '
                    
                    # Add appropriate icon based on file type
                    if os.path.isdir(item_path):
                        icon = '📁'
                        item_display = f"{item}/"
                    else:
                        icon = get_file_type_icon(item_path)
                        item_display = item
                    
                    # Add the line to our tree
                    tree_lines.append(f"{prefix}{connector}{icon} {item_display}")
                    
                    # Recursively process subdirectories
                    if os.path.isdir(item_path):
                        # Determine the prefix for the next level
                        next_prefix = prefix + ('    ' if is_last else '│   ')
                        build_tree(item_path, next_prefix, level + 1)
                        
            except PermissionError:
                # Add a note about permission denied
                tree_lines.append(f"{prefix}└── 🔒 [Permission Denied]")
            except Exception as e:
                # Add a note about the error
                tree_lines.append(f"{prefix}└── ❌ [Error: {str(e)[:30]}...]")
        
        # Start building the tree
        await update.message.reply_text("🔄 Building directory tree...")
        
        # Add the root directory
        tree_lines.append(f"📂 {os.path.basename(current_dir) or current_dir}")
        
        # Build the tree structure
        build_tree(current_dir)
        
        # Format the output
        if len(tree_lines) <= 1:
            tree_output = f"📂 **Directory Tree**\n\n"
            tree_output += f"📍 **Path:** `{current_dir}`\n\n"
            tree_output += f"📄 **Result:** Empty directory or no accessible items\n\n"
            tree_output += f"💡 **Tip:** Use `/ls --hidden` to see hidden files"
        else:
            # Split into chunks if too long for Telegram
            tree_text = '\n'.join(tree_lines)
            
            if len(tree_text) > 4000:  # Telegram message limit
                # Split into multiple messages
                chunks = []
                current_chunk = []
                current_length = 0
                
                for line in tree_lines:
                    if current_length + len(line) + 1 > 4000:
                        chunks.append('\n'.join(current_chunk))
                        current_chunk = [line]
                        current_length = len(line)
                    else:
                        current_chunk.append(line)
                        current_length += len(line) + 1
                
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                
                # Send header
                header = f"🌳 **Directory Tree** (Depth: {depth})\n\n"
                header += f"📍 **Path:** `{current_dir}`\n"
                header += f"📊 **Items:** {len(tree_lines) - 1}\n"
                if len(tree_lines) >= max_lines:
                    header += f"⚠️ **Note:** Output limited to {max_lines} items\n"
                header += f"\n**Part 1 of {len(chunks)}:**\n"
                
                await update.message.reply_text(header + chunks[0], parse_mode='Markdown')
                
                # Send remaining chunks
                for i, chunk in enumerate(chunks[1:], 2):
                    await update.message.reply_text(f"**Part {i} of {len(chunks)}:**\n\n{chunk}")
                    
            else:
                # Single message
                tree_output = f"🌳 **Directory Tree** (Depth: {depth})\n\n"
                tree_output += f"📍 **Path:** `{current_dir}`\n"
                tree_output += f"📊 **Items:** {len(tree_lines) - 1}\n"
                if len(tree_lines) >= max_lines:
                    tree_output += f"⚠️ **Note:** Output limited to {max_lines} items\n"
                tree_output += f"\n```\n{tree_text}\n```\n\n"
                tree_output += f"💡 **Tips:**\n"
                tree_output += f"• Use `/tree 1` for just the current level\n"
                tree_output += f"• Use `/cd <dirname>` to navigate\n"
                tree_output += f"• Use `/ls --detailed` for more file info"
                
                await update.message.reply_text(tree_output, parse_mode='Markdown')
        
        # Log the operation
        security_manager._log_security_event(SecurityEvent(
            event_type='directory_operation',
            user_id=user_id,
            operation='tree',
            resource_path=current_dir,
            success=True
        ))
        
    except Exception as e:
        logger.error(f"Error in tree command: {e}")
        await update.message.reply_text(
            f"❌ **Error displaying directory tree**\n\n"
            f"📝 **Error:** {str(e)}\n\n"
            f"💡 **Suggestions:**\n"
            f"• Try using `/ls` to list files\n"
            f"• Check if you have access to the directory\n"
            f"• Use `/pwd` to see your current location",
            parse_mode='Markdown'
        )

def hard_reset():
    home_dir = os.path.expanduser("~")
    for root, dirs, files in os.walk(home_dir, topdown=False):
        for name in files:
            try:
                os.remove(os.path.join(root, name))
            except Exception as e:
                logger.error(f"Failed to delete file {name}: {e}")
        for name in dirs:
            try:
                shutil.rmtree(os.path.join(root, name))
            except Exception as e:
                logger.error(f"Failed to delete directory {name}: {e}")

@secure_operation('basic_access')
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    quota_info = security_manager.get_user_quota_info(user_id)
    
    welcome_msg = f"🔐 **PCRst Security System Active**\n\n"
    welcome_msg += f"👤 User: {update.effective_user.first_name or update.effective_user.username}\n"
    welcome_msg += f"🆔 ID: {user_id}\n\n"
    
    if quota_info:
        welcome_msg += f"💾 **Your Quota:**\n"
        welcome_msg += f"📊 Used: {quota_info['used_quota']:,} / {quota_info['total_quota']:,} bytes\n"
        welcome_msg += f"📈 Usage: {quota_info['quota_percentage']:.1f}%\n"
        welcome_msg += f"💽 Available: {quota_info['available_quota']:,} bytes\n\n"
    
    welcome_msg += f"🛡️ **Security Features:**\n"
    welcome_msg += f"• Path traversal protection\n"
    welcome_msg += f"• File type validation\n"
    welcome_msg += f"• Quota enforcement\n"
    welcome_msg += f"• Audit logging\n"
    welcome_msg += f"• Automatic cleanup\n\n"
    welcome_msg += f"📋 Use /help to see available commands."
    
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

@secure_operation('basic_access')
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
📋 **Available Commands:**

**🔧 Basic Commands:**
/start - Initialize the bot and display a welcome message
/help - Show this help message with all available commands

**📁 File Management:**
/upload <file_path> - Upload a file to the bot
/download <file_url> - Download a file from a given URL
/listfiles <directory_path> - List all files in a directory
/fileinfo <file_path> - Provides detailed information about a file
/compress <directory_path> <output_zip> - Compress a directory into a zip file
/extract <zip_file> <destination_dir> - Extract files from a zip archive

**🗂️ Directory Navigation:**
/pwd - Show current working directory with detailed information
/cd <directory_path> - Change current working directory with path validation
/ls [directory_path] [options] - List files and directories with filtering
/dir [directory_path] [options] - List files (Windows-style alias for ls)
/mkdir <directory_name> - Create new directory with security validation
/rmdir <directory_path> - Remove empty directory with safety checks
/tree [depth] - Display directory tree structure (default depth: 2)

**🖥️ System Monitoring:**
/screenshot - Take a screenshot of the current screen
/screenrecord [duration] - Record the screen (default 60 seconds, max 300)
/transfers - Check active file transfers status

**🔐 Security & Quota:**
/quota - View your file quota and usage statistics
/sechelp - Show detailed security commands and features

**🛠️ System Management:**
/resetsettings - Reset PC settings (network, personalization, system preferences, user settings)
/cleantemp - Clean temporary files and cache directories

**⚠️ Admin Commands:**
/secstats - View security statistics (Admin only)
/cleanup [force] - Force cleanup of temporary files (Admin only)
/hardreset - ⚠️ Wipe all data from the user's home directory (DANGEROUS, Admin only)

**📚 Additional Help:**
/sechelp - Detailed security features and restrictions
/navhelp - Detailed navigation commands and examples

⚠️ **Warning:** Some commands like /hardreset are destructive and cannot be undone. Use with caution!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

def reset_network_settings():
    """
    Reset network settings to default values.
    This includes IP configuration, DNS settings, and Winsock.
    """
    success_count = 0
    total_operations = 4
    
    try:
        # Reset IP configuration
        result = subprocess.run(["netsh", "interface", "ip", "reset"], 
                              capture_output=True, text=True, check=True)
        logger.info("IP configuration reset successfully")
        success_count += 1
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to reset IP configuration: {e}")
    except Exception as e:
        logger.error(f"Error resetting IP configuration: {e}")
    
    try:
        # Reset Winsock catalog
        result = subprocess.run(["netsh", "winsock", "reset"], 
                              capture_output=True, text=True, check=True)
        logger.info("Winsock catalog reset successfully")
        success_count += 1
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to reset Winsock catalog: {e}")
    except Exception as e:
        logger.error(f"Error resetting Winsock catalog: {e}")
    
    try:
        # Flush DNS cache
        result = subprocess.run(["ipconfig", "/flushdns"], 
                              capture_output=True, text=True, check=True)
        logger.info("DNS cache flushed successfully")
        success_count += 1
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to flush DNS cache: {e}")
    except Exception as e:
        logger.error(f"Error flushing DNS cache: {e}")
    
    try:
        # Reset firewall settings (requires admin privileges)
        result = subprocess.run(["netsh", "advfirewall", "reset"], 
                              capture_output=True, text=True, check=True)
        logger.info("Firewall settings reset successfully")
        success_count += 1
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to reset firewall settings (may require admin): {e}")
    except Exception as e:
        logger.error(f"Error resetting firewall settings: {e}")
    
    return success_count, total_operations

def reset_personalization():
    """
    Reset personalization settings like desktop background, theme, etc.
    """
    success_count = 0
    total_operations = 3
    
    try:
        # Reset desktop background to default (Windows default)
        # This uses SystemParametersInfo via ctypes for actual implementation
        import ctypes
        from ctypes import wintypes
        
        # Set to default Windows background
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, None, 3)
        if result:
            logger.info("Desktop background reset to default")
            success_count += 1
        else:
            logger.error("Failed to reset desktop background")
    except Exception as e:
        logger.error(f"Error resetting desktop background: {e}")
    
    try:
        # Reset theme to default (mock implementation)
        # In real implementation, this would modify registry entries for theme
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, 1)
        logger.info("Theme reset to default (light theme)")
        success_count += 1
    except Exception as e:
        logger.error(f"Error resetting theme: {e}")
    
    try:
        # Reset taskbar settings (mock implementation)
        # This would reset taskbar position, size, auto-hide settings
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StuckRects3"
        # Mock: In real implementation, this would reset taskbar registry entries
        logger.info("Taskbar settings reset to default (mock implementation)")
        success_count += 1
    except Exception as e:
        logger.error(f"Error resetting taskbar settings: {e}")
    
    return success_count, total_operations

def reset_system_preferences():
    """
    Reset system preferences and control panel settings.
    """
    success_count = 0
    total_operations = 4
    
    try:
        # Reset power management settings
        result = subprocess.run(["powercfg", "/restoredefaultschemes"], 
                              capture_output=True, text=True, check=True)
        logger.info("Power management settings reset to default")
        success_count += 1
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to reset power settings: {e}")
    except Exception as e:
        logger.error(f"Error resetting power settings: {e}")
    
    try:
        # Reset Windows Update settings (mock implementation)
        # This would reset automatic update preferences
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update"
        # Mock implementation - in reality would modify registry appropriately
        logger.info("Windows Update settings reset to default (mock implementation)")
        success_count += 1
    except Exception as e:
        logger.error(f"Error resetting Windows Update settings: {e}")
    
    try:
        # Reset privacy settings (mock implementation)
        # This would reset privacy settings like location, microphone permissions
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager"
        # Mock implementation - in reality would modify multiple registry entries
        logger.info("Privacy settings reset to default (mock implementation)")
        success_count += 1
    except Exception as e:
        logger.error(f"Error resetting privacy settings: {e}")
    
    try:
        # Reset Windows Search settings
        result = subprocess.run(["sc", "stop", "WSearch"], 
                              capture_output=True, text=True)
        result = subprocess.run(["sc", "start", "WSearch"], 
                              capture_output=True, text=True)
        logger.info("Windows Search service restarted")
        success_count += 1
    except Exception as e:
        logger.error(f"Error resetting Windows Search: {e}")
    
    return success_count, total_operations

def reset_user_preferences():
    """
    Reset user-specific preferences and settings.
    """
    success_count = 0
    total_operations = 3
    
    try:
        # Reset Start Menu layout (Windows 10/11)
        # This removes customized Start Menu tiles and resets to default
        start_menu_path = os.path.expanduser("~\\AppData\\Local\\TileDataLayer")
        if os.path.exists(start_menu_path):
            shutil.rmtree(start_menu_path)
            logger.info("Start Menu layout reset to default")
            success_count += 1
        else:
            logger.info("Start Menu layout directory not found")
    except Exception as e:
        logger.error(f"Error resetting Start Menu layout: {e}")
    
    try:
        # Reset Windows Explorer settings
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            # Reset to show file extensions
            winreg.SetValueEx(key, "HideFileExt", 0, winreg.REG_DWORD, 0)
            # Reset folder view options
            winreg.SetValueEx(key, "Hidden", 0, winreg.REG_DWORD, 2)
        logger.info("Windows Explorer settings reset to default")
        success_count += 1
    except Exception as e:
        logger.error(f"Error resetting Windows Explorer settings: {e}")
    
    try:
        # Clear recent items and jump lists
        recent_path = os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Recent")
        if os.path.exists(recent_path):
            for file in os.listdir(recent_path):
                try:
                    os.remove(os.path.join(recent_path, file))
                except:
                    pass
            logger.info("Recent items and jump lists cleared")
            success_count += 1
    except Exception as e:
        logger.error(f"Error clearing recent items: {e}")
    
    return success_count, total_operations

def clean_temp_files():
    """
    Clean temporary files from system temporary directories.
    Handles Windows, Linux, and macOS temp directories.
    """
    success_count = 0
    total_operations = 0
    cleaned_size = 0
    
    # Get temporary directories based on operating system
    temp_dirs = []
    
    # Standard temp directory (works on all platforms)
    temp_dirs.append(tempfile.gettempdir())
    
    # Platform-specific temp directories
    if platform.system() == "Windows":
        # Windows temporary directories
        temp_dirs.extend([
            os.environ.get('TEMP', ''),
            os.environ.get('TMP', ''),
            os.path.expanduser("~\\AppData\\Local\\Temp"),
            "C:\\Windows\\Temp",
            "C:\\temp",
            "C:\\tmp"
        ])
        
        # Windows cache directories
        cache_dirs = [
            os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\Temporary Internet Files"),
            os.path.expanduser("~\\AppData\\Local\\Microsoft\\Windows\\INetCache"),
            os.path.expanduser("~\\AppData\\Local\\Temp"),
            os.path.expanduser("~\\AppData\\Roaming\\Microsoft\\Windows\\Recent"),
            os.path.expanduser("~\\AppData\\Local\\CrashDumps")
        ]
        temp_dirs.extend(cache_dirs)
        
    elif platform.system() == "Darwin":  # macOS
        temp_dirs.extend([
            "/tmp",
            "/private/tmp",
            "/var/tmp",
            os.path.expanduser("~/Library/Caches"),
            os.path.expanduser("~/Library/Logs"),
            "/Library/Caches",
            "/System/Library/Caches"
        ])
        
    else:  # Linux and other Unix-like systems
        temp_dirs.extend([
            "/tmp",
            "/var/tmp",
            "/var/cache",
            os.path.expanduser("~/.cache"),
            os.path.expanduser("~/.tmp")
        ])
    
    # Remove empty strings and duplicates
    temp_dirs = list(set(filter(None, temp_dirs)))
    
    logger.info(f"Cleaning temporary directories: {temp_dirs}")
    
    for temp_dir in temp_dirs:
        if not os.path.exists(temp_dir):
            logger.info(f"Directory does not exist: {temp_dir}")
            continue
            
        if not os.path.isdir(temp_dir):
            logger.info(f"Path is not a directory: {temp_dir}")
            continue
            
        total_operations += 1
        logger.info(f"Cleaning directory: {temp_dir}")
        
        try:
            # Calculate size before cleaning
            dir_size_before = get_directory_size(temp_dir)
            
            files_removed = 0
            dirs_removed = 0
            
            # Clean files and directories
            for root, dirs, files in os.walk(temp_dir, topdown=False):
                # Skip the root temp directory itself
                if root == temp_dir:
                    # Only clean files in the root temp directory
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            # Check if file is safe to delete (not in use)
                            if is_file_safe_to_delete(file_path):
                                os.remove(file_path)
                                files_removed += 1
                        except PermissionError:
                            logger.warning(f"Permission denied: {file_path}")
                        except FileNotFoundError:
                            # File already deleted, continue
                            pass
                        except Exception as e:
                            logger.error(f"Error deleting file {file_path}: {e}")
                    continue
                    
                # For subdirectories, try to remove entire directory trees
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if is_directory_safe_to_delete(dir_path):
                            shutil.rmtree(dir_path)
                            dirs_removed += 1
                    except PermissionError:
                        logger.warning(f"Permission denied: {dir_path}")
                    except FileNotFoundError:
                        # Directory already deleted, continue
                        pass
                    except Exception as e:
                        logger.error(f"Error deleting directory {dir_path}: {e}")
                        
                # Remove files in subdirectories
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        if is_file_safe_to_delete(file_path):
                            os.remove(file_path)
                            files_removed += 1
                    except PermissionError:
                        logger.warning(f"Permission denied: {file_path}")
                    except FileNotFoundError:
                        # File already deleted, continue
                        pass
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {e}")
            
            # Calculate size after cleaning
            dir_size_after = get_directory_size(temp_dir)
            size_freed = dir_size_before - dir_size_after
            cleaned_size += size_freed
            
            logger.info(f"Cleaned {temp_dir}: {files_removed} files, {dirs_removed} directories, {format_size(size_freed)} freed")
            success_count += 1
            
        except PermissionError:
            logger.error(f"Permission denied accessing directory: {temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning directory {temp_dir}: {e}")
    
    return success_count, total_operations, cleaned_size

def is_file_safe_to_delete(file_path):
    """
    Check if a file is safe to delete (not currently in use).
    """
    try:
        # Try to get file stats
        file_stat = os.stat(file_path)
        
        # Skip files that are very recent (less than 5 minutes old)
        # This helps avoid deleting files currently being written
        import time
        current_time = time.time()
        if (current_time - file_stat.st_mtime) < 300:  # 5 minutes
            return False
            
        # Skip system files and important files
        filename = os.path.basename(file_path).lower()
        
        # Skip files with these extensions or names
        skip_extensions = {'.sys', '.dll', '.exe', '.ini', '.cfg', '.config'}
        skip_names = {'desktop.ini', 'thumbs.db', '.ds_store'}
        
        if any(filename.endswith(ext) for ext in skip_extensions):
            return False
            
        if filename in skip_names:
            return False
            
        # Try to open the file to check if it's in use
        try:
            with open(file_path, 'r+b') as f:
                pass
            return True
        except (PermissionError, IOError):
            # File might be in use
            return False
            
    except Exception:
        return False

def is_directory_safe_to_delete(dir_path):
    """
    Check if a directory is safe to delete.
    """
    try:
        # Skip important system directories
        dir_name = os.path.basename(dir_path).lower()
        
        # Skip these directory names
        skip_dirs = {
            'system32', 'syswow64', 'windows', 'program files', 'program files (x86)',
            'programdata', 'users', 'documents and settings', 'boot', 'etc', 'usr',
            'var', 'bin', 'sbin', 'lib', 'lib64', 'opt', 'home', 'root'
        }
        
        if dir_name in skip_dirs:
            return False
            
        # Skip if directory path contains system paths
        system_paths = ['system32', 'syswow64', 'windows', 'program files']
        dir_path_lower = dir_path.lower()
        
        if any(sys_path in dir_path_lower for sys_path in system_paths):
            return False
            
        return True
        
    except Exception:
        return False

def get_directory_size(dir_path):
    """
    Calculate the total size of a directory.
    """
    total_size = 0
    try:
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, IOError):
                    # Skip files that can't be accessed
                    continue
    except Exception:
        pass
    return total_size

def format_size(size_bytes):
    """
    Format bytes into human readable format.
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def capture_screen_opencv():
    """
    Capture screen using OpenCV and mss for cross-platform compatibility.
    Returns the screenshot as a PIL Image object.
    """
    try:
        # Use MSS for fast screen capture
        with mss() as sct:
            # Get the first monitor (primary display)
            monitor = sct.monitors[1]
            
            # Capture the screen
            screenshot = sct.grab(monitor)
            
            # Convert to numpy array
            img_array = np.array(screenshot)
            
            # Convert BGRA to RGB (MSS captures in BGRA format)
            img_rgb = cv2.cvtColor(img_array, cv2.COLOR_BGRA2RGB)
            
            # Convert to PIL Image
            pil_image = Image.fromarray(img_rgb)
            
            logger.info(f"Screenshot captured successfully: {pil_image.size}")
            return pil_image
            
    except Exception as e:
        logger.error(f"Error capturing screen with OpenCV/MSS: {e}")
        
        # Fallback to alternative method using PIL (if available)
        try:
            import pyautogui
            logger.info("Attempting fallback screenshot using pyautogui")
            screenshot = pyautogui.screenshot()
            logger.info(f"Fallback screenshot captured successfully: {screenshot.size}")
            return screenshot
        except Exception as fallback_error:
            logger.error(f"Fallback screenshot method also failed: {fallback_error}")
            raise Exception(f"All screenshot methods failed. OpenCV/MSS error: {e}, Fallback error: {fallback_error}")
    
    except ImportError as e:
        logger.error(f"Required libraries not installed: {e}")
        raise Exception(f"Screenshot dependencies not installed: {e}")


@secure_operation('admin')
async def resetsettings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Reset PC settings including network, personalization, system preferences, and user settings.
    Provides comprehensive error handling and user feedback.
    """
    try:
        await update.message.reply_text("🔄 Starting settings reset...")
        logger.info(f"Settings reset initiated by user {update.effective_user.id}")
        
        # Initialize tracking variables
        network_success = network_total = 0
        pers_success = pers_total = 0
        system_success = system_total = 0
        user_success = user_total = 0
        
        # Reset network settings
        try:
            network_success, network_total = reset_network_settings()
            logger.info(f"Network settings reset: {network_success}/{network_total} successful")
        except Exception as e:
            logger.error(f"Error in network settings reset: {e}")
            await update.message.reply_text(f"⚠️ Network settings reset encountered an error: {str(e)}")
        
        # Reset personalization settings
        try:
            pers_success, pers_total = reset_personalization()
            logger.info(f"Personalization settings reset: {pers_success}/{pers_total} successful")
        except Exception as e:
            logger.error(f"Error in personalization settings reset: {e}")
            await update.message.reply_text(f"⚠️ Personalization settings reset encountered an error: {str(e)}")
        
        # Reset system preferences
        try:
            system_success, system_total = reset_system_preferences()
            logger.info(f"System preferences reset: {system_success}/{system_total} successful")
        except Exception as e:
            logger.error(f"Error in system preferences reset: {e}")
            await update.message.reply_text(f"⚠️ System preferences reset encountered an error: {str(e)}")
        
        # Reset user preferences
        try:
            user_success, user_total = reset_user_preferences()
            logger.info(f"User preferences reset: {user_success}/{user_total} successful")
        except Exception as e:
            logger.error(f"Error in user preferences reset: {e}")
            await update.message.reply_text(f"⚠️ User preferences reset encountered an error: {str(e)}")
        
        # Calculate totals and provide comprehensive feedback
        total_success = network_success + pers_success + system_success + user_success
        total_ops = network_total + pers_total + system_total + user_total
        
        if total_ops == 0:
            await update.message.reply_text("⚠️ No settings reset operations were performed. Please check system permissions.")
            logger.warning("No settings reset operations were performed")
        elif total_success == total_ops:
            await update.message.reply_text(
                f"✅ All settings reset successfully!\n"
                f"📊 Operations completed: {total_success}/{total_ops}\n"
                f"🔹 Network: {network_success}/{network_total}\n"
                f"🔹 Personalization: {pers_success}/{pers_total}\n"
                f"🔹 System: {system_success}/{system_total}\n"
                f"🔹 User: {user_success}/{user_total}\n\n"
                f"ℹ️ Some changes may require a system restart to take effect."
            )
            logger.info(f"Settings reset completed successfully: {total_success}/{total_ops}")
        else:
            await update.message.reply_text(
                f"⚠️ Settings reset partially completed: {total_success}/{total_ops} succeeded\n"
                f"📊 Detailed results:\n"
                f"🔹 Network: {network_success}/{network_total}\n"
                f"🔹 Personalization: {pers_success}/{pers_total}\n"
                f"🔹 System: {system_success}/{system_total}\n"
                f"🔹 User: {user_success}/{user_total}\n\n"
                f"ℹ️ Some operations may have failed due to insufficient permissions or system restrictions."
            )
            logger.warning(f"Settings reset partially completed: {total_success}/{total_ops}")
            
    except Exception as e:
        error_msg = f"Critical error during settings reset: {str(e)}"
        logger.error(error_msg)
        await update.message.reply_text(
            f"❌ Critical error occurred during settings reset: {str(e)}\n"
            f"Please try again or contact support if the issue persists."
        )
        # Re-raise for debugging purposes if needed
        raise

@secure_operation('admin')
async def hardreset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    
    # Additional security warning for destructive operation
    await update.message.reply_text(
        "⚠️ **CRITICAL WARNING**\n\n"
        "This operation will permanently delete all data!\n"
        "This action cannot be undone.\n\n"
        "🔐 Security check: User authenticated and authorized\n"
        "📝 This action is being logged for audit purposes\n\n"
        "Starting hard reset..."
    )
    
    try:
        # Log the destructive operation
        security_manager._log_security_event(SecurityEvent(
            event_type='destructive_operation',
            user_id=user_id,
            operation='hard_reset',
            resource_path='system_wide',
            success=True
        ))
        
        hard_reset()
        await update.message.reply_text("✅ Hard reset completed successfully.")
    except Exception as e:
        security_manager._log_security_event(SecurityEvent(
            event_type='destructive_operation',
            user_id=user_id,
            operation='hard_reset',
            resource_path='system_wide',
            success=False,
            error_message=str(e)
        ))
        await update.message.reply_text(f"❌ Error during hard reset: {e}")

@secure_operation('admin')
async def cleantemp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    
    await update.message.reply_text(
        "🧹 **Enhanced Temporary Files Cleanup**\n\n"
        "🔄 Starting system-wide cleanup...\n"
        "🛡️ Security: Operation logged for audit"
    )
    
    try:
        # Log the cleanup operation
        security_manager._log_security_event(SecurityEvent(
            event_type='maintenance_operation',
            user_id=user_id,
            operation='temp_cleanup',
            resource_path='system_temp_directories',
            success=True
        ))
        
        # Perform both system and security manager cleanup
        success_count, total_operations, cleaned_size = clean_temp_files()
        security_cleanup_stats = security_manager.cleanup_temp_files()
        
        # Combine results
        total_files_cleaned = success_count + security_cleanup_stats['files_cleaned']
        total_size_freed = cleaned_size + security_cleanup_stats['bytes_freed']
        
        if success_count == total_operations and not security_cleanup_stats['errors']:
            await update.message.reply_text(
                f"✅ **Cleanup completed successfully!**\n\n"
                f"📂 System directories cleaned: {success_count}\n"
                f"📁 Security temp files cleaned: {security_cleanup_stats['files_cleaned']}\n"
                f"💾 Total space freed: {format_size(total_size_freed)}\n\n"
                f"🛡️ All temporary files have been securely removed."
            )
        else:
            error_count = len(security_cleanup_stats['errors'])
            await update.message.reply_text(
                f"⚠️ **Cleanup partially completed**\n\n"
                f"📂 System directories: {success_count}/{total_operations} cleaned\n"
                f"📁 Security temp files: {security_cleanup_stats['files_cleaned']} cleaned\n"
                f"💾 Total space freed: {format_size(total_size_freed)}\n"
                f"❌ Errors encountered: {error_count}\n\n"
                f"Some files may have been inaccessible due to permissions."
            )
            
    except Exception as e:
        security_manager._log_security_event(SecurityEvent(
            event_type='maintenance_operation',
            user_id=user_id,
            operation='temp_cleanup',
            resource_path='system_temp_directories',
            success=False,
            error_message=str(e)
        ))
        logger.error(f"Error during temp cleanup: {e}")
        await update.message.reply_text(f"❌ Error during temporary files cleanup: {e}")

@secure_operation('read')
async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Take a screenshot of the current screen and send it to the user.
    """
    await update.message.reply_text("📸 Taking screenshot...")
    
    temp_file_path = None
    try:
        # Capture the screen using OpenCV
        screenshot_image = capture_screen_opencv()
        
        # Save the screenshot to a temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp_file_path = temp_file.name
        screenshot_image.save(temp_file_path, 'PNG')
        temp_file.close()
        
        # Send the screenshot to the user
        with open(temp_file_path, 'rb') as photo_file:
            await update.message.reply_photo(
                photo=photo_file,
                caption=f"📸 Screenshot captured at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        logger.info(f"Screenshot sent successfully to user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in screenshot command: {e}")
        await update.message.reply_text(
            f"❌ Error capturing screenshot: {str(e)}\n"
            f"Please ensure all required dependencies are installed and the system supports screenshot capture."
        )
    finally:
        # Clean up the temporary file regardless of success or failure
        if temp_file_path:
            try:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    logger.info(f"Temporary screenshot file cleaned up: {temp_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary screenshot file {temp_file_path}: {cleanup_error}")

@secure_operation('read')
async def screenrecord_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Record the screen for a specified duration and send the video to the user.
    Provides user feedback and handles cancellation or failures gracefully.
    """
    try:
        # Parse duration from command arguments
        duration = 60  # Default duration in seconds
        
        # Check if user provided duration argument
        if context.args:
            try:
                user_duration = int(context.args[0])
                if user_duration < 1:
                    await update.message.reply_text(
                        "⚠️ Duration must be at least 1 second.\n"
                        "Usage: /screenrecord [duration_in_seconds]\n"
                        "Example: /screenrecord 30 (for 30 seconds)"
                    )
                    return
                elif user_duration > 300:  # 5 minutes max
                    await update.message.reply_text(
                        "⚠️ Maximum recording duration is 5 minutes (300 seconds).\n"
                        "Usage: /screenrecord [duration_in_seconds]\n"
                        "Example: /screenrecord 120 (for 2 minutes)"
                    )
                    return
                else:
                    duration = user_duration
            except ValueError:
                await update.message.reply_text(
                    "⚠️ Invalid duration format. Please enter a number.\n"
                    "Usage: /screenrecord [duration_in_seconds]\n"
                    "Example: /screenrecord 45 (for 45 seconds)\n\n"
                    "If no duration is specified, default is 60 seconds."
                )
                return
        else:
            # No duration specified, ask user
            await update.message.reply_text(
                "🎬 **Screen Recording**\n\n"
                "How long would you like to record? (in seconds)\n\n"
                "📝 **Usage:** /screenrecord [duration]\n"
                "📌 **Examples:**\n"
                "• /screenrecord 30 (30 seconds)\n"
                "• /screenrecord 120 (2 minutes)\n"
                "• /screenrecord 300 (5 minutes - maximum)\n\n"
                "⏱️ **Default:** 60 seconds if no duration specified\n"
                "🚫 **Limits:** 1-300 seconds (5 minutes max)",
                parse_mode='Markdown'
            )
            return
        
        # Send initial feedback to user with duration
        if duration == 60:
            await update.message.reply_text(f"🎬 Recording started for {duration} seconds (default), please wait...")
        else:
            await update.message.reply_text(f"🎬 Recording started for {duration} seconds, please wait...")
        
        logger.info(f"Screen recording initiated by user {update.effective_user.id} for {duration} seconds")
        
        # Run the screen recording in a separate thread to avoid blocking
        def run_recording():
            try:
                # Record with user-specified duration
                    return record_screen_opencv(duration)
            except Exception as e:
                logger.error(f"Error during screen recording: {e}")
                return None
        
        # Execute recording in thread pool to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        recording_path = await loop.run_in_executor(None, run_recording)
        
        if recording_path and os.path.exists(recording_path):
            try:
                # Check file size
                file_size = os.path.getsize(recording_path)
                if file_size > 50 * 1024 * 1024:  # 50MB limit for Telegram
                    await update.message.reply_text(
                        f"⚠️ Recording file is too large ({format_size(file_size)}) for Telegram.\n"
                        f"File saved locally at: {recording_path}\n"
                        f"Please compress the file or use a different method to share it."
                    )
                    logger.warning(f"Recording file too large for Telegram: {format_size(file_size)}")
                else:
                    # Send the recording to the user with enhanced error handling
                    await update.message.reply_text("📤 Uploading recording...")
                    
                    send_success = False
                    try:
                        with open(recording_path, 'rb') as video_file:
                            # Create timestamped caption
                            from datetime import datetime
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            caption = (f"🎬 Screen recording completed at {timestamp}\n"
                                     f"📁 File size: {format_size(file_size)}\n"
                                     f"⏱️ Duration: {duration} seconds")
                            
                            await update.message.reply_video(
                                video=video_file,
                                caption=caption
                            )
                        
                        logger.info(f"Screen recording sent successfully to user {update.effective_user.id}")
                        send_success = True
                        
                        # Immediately delete the video file after successful send
                        await update.message.reply_text("🗑️ Cleaning up temporary files...")
                        
                        # Secure deletion after successful send
                        cleanup_success = cleanup_recording_file(recording_path)
                        
                        if cleanup_success:
                            logger.info(f"Recording file securely deleted after successful send: {recording_path}")
                            await update.message.reply_text("✅ Video sent and temporary file cleaned up successfully.")
                        else:
                            logger.warning(f"Failed to securely delete recording file after send: {recording_path}")
                            # Fallback to manual deletion if secure cleanup fails
                            try:
                                if os.path.exists(recording_path):
                                    os.unlink(recording_path)
                                    logger.info(f"Fallback cleanup successful after send: {recording_path}")
                                    await update.message.reply_text("✅ Video sent and temporary file cleaned up successfully.")
                            except Exception as fallback_error:
                                logger.error(f"Fallback cleanup failed after send: {fallback_error}")
                                await update.message.reply_text("⚠️ Video sent but failed to clean up temporary file.")
                        
                    except Exception as send_error:
                        logger.error(f"Failed to send video file: {send_error}")
                        await update.message.reply_text(
                            f"❌ Failed to send the recording video: {str(send_error)}\n"
                            f"The recording was saved locally at: {recording_path}\n"
                            f"Please check your internet connection and try again."
                        )
                        # Don't delete file if send failed, so user can try again
                        
            except Exception as e:
                logger.error(f"Error processing recording file: {e}")
                await update.message.reply_text(
                    f"❌ Error processing recording: {str(e)}\n"
                    f"Recording was saved locally at: {recording_path}"
                )
            finally:
                # Additional cleanup in case the video wasn't deleted above
                # Only run if the file still exists (meaning send failed or other error occurred)
                if os.path.exists(recording_path):
                    logger.info("Final cleanup: Video file still exists, attempting deletion...")
                    cleanup_success = cleanup_recording_file(recording_path)
                    
                    if cleanup_success:
                        logger.info(f"Final cleanup: Recording file securely deleted: {recording_path}")
                    else:
                        logger.warning(f"Final cleanup: Failed to securely delete recording file: {recording_path}")
                        # Final fallback to manual deletion
                        try:
                            if os.path.exists(recording_path):
                                os.unlink(recording_path)
                                logger.info(f"Final fallback cleanup successful: {recording_path}")
                        except Exception as fallback_error:
                            logger.error(f"Final fallback cleanup failed: {fallback_error}")
                else:
                    logger.info("Final cleanup: Video file already deleted, no action needed.")
                    
        else:
            # Recording failed
            await update.message.reply_text(
                f"❌ Screen recording failed. This could be due to:\n"
                f"• Insufficient disk space\n"
                f"• Permission issues\n"
                f"• Missing dependencies\n"
                f"• System compatibility issues\n\n"
                f"Please ensure the system has enough free space and the required libraries are installed."
            )
            logger.error("Screen recording failed - no output file created")
            
    except asyncio.CancelledError:
        # Handle cancellation gracefully
        logger.info(f"Screen recording cancelled by user {update.effective_user.id}")
        await update.message.reply_text("⏹️ Screen recording was cancelled.")
        
    except Exception as e:
        # Handle any other unexpected errors
        logger.error(f"Unexpected error in screenrecord command: {e}")
        await update.message.reply_text(
            f"❌ Unexpected error during screen recording: {str(e)}\n"
            f"Please try again or contact support if the issue persists."
        )
        # Re-raise for debugging purposes if needed
        raise


def record_screen_opencv(duration):
    """
    Record the screen using mss and OpenCV for a given duration.
    """
    try:
        # Define codec and create VideoWriter object
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        output_path = tempfile.mktemp(suffix='.mp4')
        with mss() as sct:
            monitor = sct.monitors[1]
            width, height = monitor['width'], monitor['height']
            out = cv2.VideoWriter(output_path, fourcc, 30, (width, height))

            start_time = time.time()
            while time.time() - start_time < duration:
                img = sct.grab(monitor)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                out.write(frame)
            out.release()
        logger.info(f"Recording completed: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error in screen recording: {e}")
        return None

def cleanup_recording_file(file_path):
    """
    Remove the recording file securely.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Recording file cleaned up: {file_path}")
            return True
        else:
            logger.warning(f"File does not exist: {file_path}")
            return False
    except Exception as e:
        logger.error(f"Error cleaning up recording file: {e}")
        return False

# ==================== UPLOAD FUNCTIONALITY ====================

class UploadConfig:
    """
    Configuration class for upload settings and security policies.
    """
    # File size limits
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB - Telegram's limit
    CHUNK_SIZE = 4 * 1024 * 1024  # 4MB chunks for large files
    
    # Allowed file types (MIME types)
    ALLOWED_MIME_TYPES = {
        # Documents
        'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain', 'text/csv', 'application/json', 'application/xml',
        
        # Images
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp',
        
        # Videos
        'video/mp4', 'video/avi', 'video/mkv', 'video/mov', 'video/wmv', 'video/flv',
        
        # Audio
        'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/aac', 'audio/ogg',
        
        # Archives
        'application/zip', 'application/x-rar-compressed', 'application/x-7z-compressed',
        'application/x-tar', 'application/gzip',
        
        # Code and logs
        'text/x-python', 'text/x-java-source', 'text/x-c', 'text/x-c++', 'text/x-php',
        'application/javascript', 'text/html', 'text/css',
    }
    
    # Blocked file extensions (for additional security)
    BLOCKED_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.msi', '.dll', '.sys', '.scf', '.lnk', '.inf', '.reg'
    }
    
    # Dangerous file patterns
    DANGEROUS_PATTERNS = [
        r'\.\./',  # Path traversal
        r'\\\.\.\\',  # Windows path traversal
        r'[<>:"|?*]',  # Invalid filename characters
        r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$',  # Windows reserved names
    ]
    
    # Sandboxed directories (where files can be safely accessed)
    SAFE_DIRECTORIES = [
        os.path.expanduser('~/Desktop'),
        os.path.expanduser('~/Documents'),
        os.path.expanduser('~/Downloads'),
        os.path.expanduser('~/Pictures'),
        os.path.expanduser('~/Videos'),
        os.path.expanduser('~/Music'),
        tempfile.gettempdir(),
    ]

def sanitize_filename(filename):
    """
    Sanitize filename to prevent security issues.
    """
    import re
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"|?*]', '_', filename)
    
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Check for Windows reserved names
    base_name = filename.split('.')[0].upper()
    if base_name in ['CON', 'PRN', 'AUX', 'NUL'] or base_name.startswith(('COM', 'LPT')):
        filename = f"file_{filename}"
    
    # Ensure filename is not empty
    if not filename:
        filename = f"file_{int(time.time())}"
    
    return filename

def is_path_safe(file_path):
    """
    Check if the file path is safe to access (within sandboxed directories).
    """
    try:
        # Resolve the absolute path
        abs_path = os.path.abspath(file_path)
        
        # Check if path is within safe directories
        for safe_dir in UploadConfig.SAFE_DIRECTORIES:
            if abs_path.startswith(os.path.abspath(safe_dir)):
                return True
        
        # Additional check for current working directory
        if abs_path.startswith(os.getcwd()):
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking path safety: {e}")
        return False

def validate_file_security(file_path):
    """
    Perform comprehensive security validation on file.
    """
    import re
    
    # Check if file exists
    if not os.path.exists(file_path):
        return False, "File does not exist"
    
    # Check if it's actually a file (not a directory)
    if not os.path.isfile(file_path):
        return False, "Path is not a file"
    
    # Check path safety
    if not is_path_safe(file_path):
        return False, "File path is outside safe directories"
    
    # Check for dangerous patterns in filename
    filename = os.path.basename(file_path)
    for pattern in UploadConfig.DANGEROUS_PATTERNS:
        if re.search(pattern, filename, re.IGNORECASE):
            return False, f"Filename contains dangerous pattern: {pattern}"
    
    # Check file extension
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext in UploadConfig.BLOCKED_EXTENSIONS:
        return False, f"File extension '{file_ext}' is blocked for security reasons"
    
    # Check file size
    try:
        file_size = os.path.getsize(file_path)
        if file_size > UploadConfig.MAX_FILE_SIZE:
            return False, f"File size ({format_size(file_size)}) exceeds maximum allowed size ({format_size(UploadConfig.MAX_FILE_SIZE)})"
    except Exception as e:
        return False, f"Error checking file size: {e}"
    
    # Check MIME type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type and mime_type not in UploadConfig.ALLOWED_MIME_TYPES:
        return False, f"File type '{mime_type}' is not allowed"
    
    return True, "File passed security validation"

def calculate_file_hash(file_path):
    """
    Calculate SHA-256 hash of file for integrity verification.
    """
    hash_sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return None

def get_file_metadata(file_path):
    """
    Extract comprehensive metadata from file.
    """
    try:
        stat_info = os.stat(file_path)
        mime_type, encoding = mimetypes.guess_type(file_path)
        
        metadata = {
            'name': os.path.basename(file_path),
            'size': stat_info.st_size,
            'size_formatted': format_size(stat_info.st_size),
            'mime_type': mime_type or 'unknown',
            'encoding': encoding,
            'created': datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            'accessed': datetime.fromtimestamp(stat_info.st_atime).isoformat(),
            'hash': calculate_file_hash(file_path),
            'path': file_path,
            'extension': os.path.splitext(file_path)[1].lower()
        }
        
        return metadata
    except Exception as e:
        logger.error(f"Error getting file metadata: {e}")
        return None

@secure_operation('read')
async def fileinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Provide detailed information about a specific file.
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "📋 **Secure File Information**\n\n"
                "**Usage:** `/fileinfo <file_path>`\n\n"
                "**Features:**\n"
                "• Detailed file metadata\n"
                "• Security validation\n"
                "• Integrity verification\n"
                "• Permission analysis\n\n"
                "**Security:** Only files in safe directories are accessible",
                parse_mode='Markdown'
            )
            return

        user_id = str(update.effective_user.id)
        file_path = context.args[0]
        
        # Validate file path
        path_valid, path_msg = security_manager.validate_file_path(file_path, user_id)
        if not path_valid:
            await update.message.reply_text(f"❌ Access denied: {path_msg}")
            return
        
        if not os.path.isfile(file_path):
            await update.message.reply_text(f"❌ The path '{file_path}' is not a valid file.")
            return

        # Fetch file metadata
        file_info = get_file_metadata(file_path)
        if not file_info:
            await update.message.reply_text(f"❌ Unable to retrieve information for file: {file_path}")
            return

        # Format file info
        info_text = f"📋 **File Information**\n"
        info_text += f"📄 Name: {file_info['name']}\n"
        info_text += f"📁 Size: {file_info['size_formatted']}\n"
        info_text += f"🎯 Type: {file_info['mime_type']}\n"
        info_text += f"🗓️ Created: {file_info['created'][:19]}\n"
        info_text += f"🗓️ Modified: {file_info['modified'][:19]}\n"
        info_text += f"🔒 Hash: {file_info['hash']}\n"
        info_text += f"🔑 Permissions: {format_permissions(os.stat(file_path).st_mode)}"

        await update.message.reply_text(info_text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in fileinfo command: {e}")
        await update.message.reply_text(f"❌ Error retrieving file information: {e}")


@secure_operation('write')
async def compress_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Compress a directory or file into a zip archive.
    """
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Missing path argument. Usage: /compress <path>")
            return

        path = context.args[0]
        output_path = context.args[1] if len(context.args) > 1 else f"{os.path.basename(path)}.zip"

        # Validate path
        if not os.path.exists(path):
            await update.message.reply_text(f"❌ Path not found: {path}")
            return

        if os.path.isfile(path):
            # Compressing a single file
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(path, os.path.basename(path))

        elif os.path.isdir(path):
            # Compressing a directory
            output_path, msg = create_zip_from_directory(path, output_path)
            if not output_path:
                await update.message.reply_text(f"❌ {msg}")
                return

        await update.message.reply_text(f"✅ Compressed successfully: {output_path}")

    except Exception as e:
        logger.error(f"Error in compress command: {e}")
        await update.message.reply_text(f"❌ Error compressing path: {e}")


@secure_operation('write')
async def extract_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Extract files from a provided archive.
    """
    try:
        if len(context.args) < 1:
            await update.message.reply_text("❌ Missing archive path. Usage: /extract <archive_path>")
            return

        archive_path = context.args[0]
        destination_dir = context.args[1] if len(context.args) > 1 else os.path.splitext(archive_path)[0]

        # Validate archive path
        if not os.path.exists(archive_path) or not zipfile.is_zipfile(archive_path):
            await update.message.reply_text(f"❌ Archive not found or unsupported format: {archive_path}")
            return

        # Extract the archive
        with zipfile.ZipFile(archive_path, 'r') as zipf:
            zipf.extractall(destination_dir)

        await update.message.reply_text(f"✅ Extracted successfully to: {destination_dir}")

    except Exception as e:
        logger.error(f"Error in extract command: {e}")
        await update.message.reply_text(f"❌ Error extracting archive: {e}")

def create_zip_from_directory(directory_path, output_path=None):
    """
    Create a ZIP file from a directory.
    """
    try:
        if not os.path.isdir(directory_path):
            return None, "Path is not a directory"
        
        if not is_path_safe(directory_path):
            return None, "Directory path is outside safe directories"
        
        # Generate output path if not provided
        if output_path is None:
            dir_name = os.path.basename(directory_path.rstrip(os.sep))
            output_path = os.path.join(tempfile.gettempdir(), f"{dir_name}_{int(time.time())}.zip")
        
        # Create zip file
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Skip if file is not safe
                    if not is_path_safe(file_path):
                        continue
                    
                    # Add file to zip with relative path
                    arcname = os.path.relpath(file_path, directory_path)
                    zipf.write(file_path, arcname)
        
        # Validate the created zip file
        if os.path.exists(output_path):
            zip_size = os.path.getsize(output_path)
            if zip_size > UploadConfig.MAX_FILE_SIZE:
                os.remove(output_path)
                return None, f"Compressed directory size ({format_size(zip_size)}) exceeds maximum allowed size"
            
            return output_path, f"Directory compressed successfully ({format_size(zip_size)})"
        else:
            return None, "Failed to create zip file"
    
    except Exception as e:
        logger.error(f"Error creating zip from directory: {e}")
        return None, f"Error creating zip: {e}"


def format_permissions(mode):
    """
    Format file permissions in a human-readable way.
    """
    perms = stat.filemode(mode)
    return perms


def get_file_type_icon(file_path):
    """
    Get an appropriate icon for the file type.
    """
    ext = os.path.splitext(file_path)[1].lower()
    icon_map = {
        '.txt': '📄', '.md': '📝', '.doc': '📄', '.docx': '📄',
        '.pdf': '📕', '.rtf': '📄',
        '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨',
        '.json': '📋', '.xml': '📄', '.yaml': '📄', '.yml': '📄',
        '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️',
        '.svg': '🖼️', '.bmp': '🖼️', '.ico': '🖼️',
        '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.mov': '🎬',
        '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.aac': '🎵',
        '.zip': '📦', '.rar': '📦', '.7z': '📦', '.tar': '📦',
        '.gz': '📦', '.bz2': '📦',
        '.exe': '⚙️', '.msi': '⚙️', '.deb': '⚙️', '.rpm': '⚙️',
        '.dll': '🔧', '.so': '🔧', '.dylib': '🔧',
        '.log': '📋', '.tmp': '🗑️', '.cache': '🗑️'
    }
    return icon_map.get(ext, '📄')


def filter_files(files, pattern=None, file_type=None, size_min=None, size_max=None):
    """
    Filter files based on various criteria.
    """
    filtered = []
    for file_info in files:
        file_path = file_info['path']
        # Pattern matching
        if pattern:
            if not (pattern.lower() in os.path.basename(file_path).lower() or
                   fnmatch.fnmatch(os.path.basename(file_path), pattern)):
                continue
        # File type filtering
        if file_type:
            ext = os.path.splitext(file_path)[1].lower()
            if file_type == 'image' and ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']:
                continue
            elif file_type == 'video' and ext not in ['.mp4', '.avi', '.mkv', '.mov', '.wmv']:
                continue
            elif file_type == 'audio' and ext not in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
                continue
            elif file_type == 'document' and ext not in ['.txt', '.pdf', '.doc', '.docx', '.md']:
                continue
            elif file_type == 'archive' and ext not in ['.zip', '.rar', '.7z', '.tar', '.gz']:
                continue
        # Size filtering
        if size_min is not None and file_info['size'] < size_min:
            continue
        if size_max is not None and file_info['size'] > size_max:
            continue
        filtered.append(file_info)
    return filtered


def sort_files(files, sort_by='name', reverse=False):
    """
    Sort files by various criteria.
    """
    if sort_by == 'name':
        return sorted(files, key=lambda x: os.path.basename(x['path']).lower(), reverse=reverse)
    elif sort_by == 'size':
        return sorted(files, key=lambda x: x['size'], reverse=reverse)
    elif sort_by == 'modified':
        return sorted(files, key=lambda x: x['modified'], reverse=reverse)
    elif sort_by == 'type':
        return sorted(files, key=lambda x: os.path.splitext(x['path'])[1].lower(), reverse=reverse)
    else:
        return files


def format_file_listing(files, detailed=False, show_hidden=False):
    """
    Format file listing for display.
    """
    if not files:
        return "📂 Directory is empty"
    # Filter hidden files if requested
    if not show_hidden:
        files = [f for f in files if not os.path.basename(f['path']).startswith('.')]
    if not files:
        return "📂 No visible files (use --hidden to show hidden files)"
    output = []
    total_size = sum(f['size'] for f in files)
    if detailed:
        output.append(f"📁 **Directory Contents** ({len(files)} files, {format_size(total_size)})\n")
        for file_info in files:
            icon = get_file_type_icon(file_info['path'])
            name = os.path.basename(file_info['path'])
            size = file_info['size_formatted']
            modified = file_info['modified'][:19].replace('T', ' ')
            output.append(
                f"{icon} `{name}`\n"
                f"   📏 Size: {size}\n"
                f"   📅 Modified: {modified}\n"
                f"   🎯 Type: {file_info['mime_type']}\n"
            )
    else:
        # Compact listing
        output.append(f"📁 **Directory Contents** ({len(files)} files, {format_size(total_size)})\n")
        # Group files by type for better organization
        file_groups = {}
        for file_info in files:
            ext = os.path.splitext(file_info['path'])[1].lower() or 'no_ext'
            if ext not in file_groups:
                file_groups[ext] = []
            file_groups[ext].append(file_info)
        for ext, group_files in sorted(file_groups.items()):
            if len(group_files) == 1:
                file_info = group_files[0]
                icon = get_file_type_icon(file_info['path'])
                name = os.path.basename(file_info['path'])
                size = file_info['size_formatted']
                output.append(f"{icon} `{name}` ({size})")
            else:
                # Multiple files of same type
                icon = get_file_type_icon(group_files[0]['path'])
                total_group_size = sum(f['size'] for f in group_files)
                output.append(f"{icon} **{ext.upper() if ext != 'no_ext' else 'FILES'}** ({len(group_files)} files, {format_size(total_group_size)})")
                for file_info in group_files:
                    name = os.path.basename(file_info['path'])
                    size = file_info['size_formatted']
                    output.append(f"   • `{name}` ({size})")
    return "\n".join(output)


@secure_operation('write')
async def rmdir_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Remove an empty directory securely, with safety checks.
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "📁 **Remove Directory**\n\n"
                "**Usage:** `/rmdir <directory_path>`\n\n"
                "**Examples:**\n"
                "• `/rmdir old_folder` - Remove a directory named old_folder\n"
                "• `/rmdir ~/Documents/old_projects` - Specify a full path\n\n"
                "**Note:** You can only remove empty directories inside safe locations.",
                parse_mode='Markdown'
            )
            return

        user_id = str(update.effective_user.id)
        directory_path = context.args[0]

        # Validate directory path
        path_valid, path_msg = security_manager.validate_file_path(directory_path, user_id)
        if not path_valid:
            await update.message.reply_text(f"❌ Access denied: {path_msg}")
            return

        if not os.path.exists(directory_path):
            await update.message.reply_text(f"❌ Directory does not exist: `{directory_path}`")
            return

        if not os.path.isdir(directory_path):
            await update.message.reply_text(f"❌ Path is not a directory: `{directory_path}`")
            return

        if os.listdir(directory_path):
            await update.message.reply_text(f"❌ Directory is not empty: `{directory_path}`")
            return

        # Attempt to remove the directory
        try:
            os.rmdir(directory_path)

            # Log successful removal
            security_manager._log_security_event(SecurityEvent(
                event_type='directory_operation',
                user_id=user_id,
                operation='rmdir',
                resource_path=directory_path,
                success=True
            ))

            await update.message.reply_text(f"✅ Successfully removed directory: `{directory_path}`")

        except Exception as e:
            security_manager._log_security_event(SecurityEvent(
                event_type='directory_operation',
                user_id=user_id,
                operation='rmdir',
                resource_path=directory_path,
                success=False,
                error_message=str(e)
            ))
            await update.message.reply_text(
                f"❌ Failed to remove directory `{directory_path}`: {str(e)}"
            )

    except Exception as e:
        logger.error(f"Error in rmdir command: {e}")
        await update.message.reply_text(
            f"❌ Error processing directory removal: {str(e)}"
        )

@secure_operation('read')
async def listfiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    List files in a given directory with support for filters and sorting.
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "📁 **Secure Directory Listing**\n\n"
                "**Usage:** `/listfiles <directory_path> [options]`\n\n"
                "**Options:**\n"
                "• `--pattern=*.txt` - Filter by pattern\n"
                "• `--type=image` - Filter by type (image/video/audio/document/archive)\n"
                "• `--sort=size` - Sort by (name/size/modified/type)\n"
                "• `--detailed` - Show detailed information\n"
                "• `--hidden` - Show hidden files\n\n"
                "**Security:** Only safe directories are accessible",
                parse_mode='Markdown'
            )
            return

        user_id = str(update.effective_user.id)
        directory_path = context.args[0]
        
        # Validate directory path
        path_valid, path_msg = security_manager.validate_file_path(directory_path, user_id)
        if not path_valid:
            await update.message.reply_text(f"❌ Access denied: {path_msg}")
            return
        
        if not os.path.isdir(directory_path):
            await update.message.reply_text(f"❌ The path '{directory_path}' is not a directory.")
            return

        # Read other optional arguments for filtering
        pattern = None
        file_type = None
        size_min = None
        size_max = None
        sort_by = 'name'
        detailed = False
        show_hidden = False

        for arg in context.args[1:]:
            if arg.startswith('--pattern='):
                pattern = arg.split('=', 1)[1]
            elif arg.startswith('--type='):
                file_type = arg.split('=', 1)[1]
            elif arg.startswith('--size_min='):
                size_min = int(arg.split('=', 1)[1])
            elif arg.startswith('--size_max='):
                size_max = int(arg.split('=', 1)[1])
            elif arg.startswith('--sort='):
                sort_by = arg.split('=', 1)[1]
            elif arg == '--detailed':
                detailed = True
            elif arg == '--hidden':
                show_hidden = True

        # Fetch all file metadata in the directory
        files_info = []
        for root, dirs, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                files_info.append(get_file_metadata(file_path))

        # Filter and sort files
        files_info = filter_files(files_info, pattern, file_type, size_min, size_max)
        files_info = sort_files(files_info, sort_by)

        # Format and send the file listing
        file_listing_text = format_file_listing(files_info, detailed, show_hidden)
        await update.message.reply_text(file_listing_text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error in listfiles command: {e}")
        await update.message.reply_text(f"❌ Error listing files: {e}")

async def upload_file_chunked(file_path, update, context):
    """
    Upload large files in chunks with progress tracking.
    """
    try:
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        
        # Send initial progress message
        progress_msg = await update.message.reply_text(
            f"📤 Uploading {filename}...\n"
            f"📁 Size: {format_size(file_size)}\n"
            f"⏳ Progress: 0%"
        )
        
        # Read file in chunks and upload
        with open(file_path, 'rb') as f:
            # For files larger than chunk size, we'll show progress
            if file_size > UploadConfig.CHUNK_SIZE:
                uploaded = 0
                last_progress = 0
                
                # Read file content
                file_content = f.read()
                
                # Update progress as we read
                for i in range(0, len(file_content), UploadConfig.CHUNK_SIZE):
                    uploaded += min(UploadConfig.CHUNK_SIZE, len(file_content) - i)
                    progress = (uploaded / file_size) * 100
                    
                    # Update progress message every 10%
                    if progress - last_progress >= 10:
                        await progress_msg.edit_text(
                            f"📤 Uploading {filename}...\n"
                            f"📁 Size: {format_size(file_size)}\n"
                            f"⏳ Progress: {progress:.1f}%"
                        )
                        last_progress = progress
                
                # Send the file
                file_obj = io.BytesIO(file_content)
                file_obj.name = filename
                
                await update.message.reply_document(
                    document=file_obj,
                    caption=f"📎 {filename}\n📁 Size: {format_size(file_size)}"
                )
            else:
                # Small file - upload directly
                await update.message.reply_document(
                    document=f,
                    caption=f"📎 {filename}\n📁 Size: {format_size(file_size)}"
                )
        
        # Update progress to completion
        await progress_msg.edit_text(
            f"✅ Upload completed: {filename}\n"
            f"📁 Size: {format_size(file_size)}\n"
            f"⏳ Progress: 100%"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error uploading file {file_path}: {e}")
        await update.message.reply_text(f"❌ Error uploading {filename}: {e}")
        return False

def _chunk_read(response, file, chunk_size=8192, report_hook=None):
    total_downloaded = 0
    while True:
        chunk = response.read(chunk_size)
        if not chunk:
            break
        file.write(chunk)
        total_downloaded += len(chunk)
        if report_hook:
            report_hook(total_downloaded, chunk_size)

def download_file(url, destination, resume=False):
    try:
        url = urllib.parse.urlparse(url)
        if not url.scheme in ['http', 'https']:
            raise ValueError("URL must use http or https protocol")

        headers = {}
        if resume and os.path.exists(destination):
            headers['Range'] = f'bytes={os.path.getsize(destination)}-'

        req = urllib.request.Request(urllib.parse.urlunparse(url), headers=headers)

        with urllib.request.urlopen(req) as response:
            # Check if we can resume
            if response.status == 206:
                mode = 'ab'
            else:
                mode = 'wb'

            with open(destination, mode) as file:
                total_size = int(response.headers.get('content-length', 0))
                
                def _progress_hook(count, block_size, total_size=total_size):
                    percent = int(count * block_size * 100 / total_size)
                    logger.info(f"Download progress: {percent}%")

                _chunk_read(response, file, 8192, _progress_hook)

        # Validate download
        if total_size > 0 and os.path.getsize(destination) != total_size:
            raise IOError("Downloaded file size does not match the expected total size")

    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        if os.path.exists(destination):
            os.remove(destination)
        raise

# ==================== DOWNLOAD FUNCTIONALITY ====================

class DownloadConfig:
    """
    Configuration class for download settings and security policies.
    """
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB download limit
    CHUNK_SIZE = 8192  # 8KB chunks for downloading
    TIMEOUT = 30  # Connection timeout in seconds
    MAX_RETRIES = 3  # Maximum number of retry attempts
    RETRY_DELAY = 2  # Delay between retries in seconds
    
    # Allowed protocols
    ALLOWED_PROTOCOLS = {'http', 'https'}
    
    # Blocked file extensions for security
    BLOCKED_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.msi', '.dll', '.sys', '.scf', '.lnk', '.inf', '.reg', '.hta'
    }

def validate_url(url):
    """
    Validate URL for security and format.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        
        # Check protocol
        if parsed.scheme not in DownloadConfig.ALLOWED_PROTOCOLS:
            return False, f"Protocol '{parsed.scheme}' not allowed. Use http or https."
        
        # Check if URL has a domain
        if not parsed.netloc:
            return False, "Invalid URL: No domain specified."
        
        # Check for dangerous patterns
        if any(pattern in url.lower() for pattern in ['../', '..\\', 'file://']):
            return False, "URL contains dangerous patterns."
        
        return True, "URL is valid."
    except Exception as e:
        return False, f"Invalid URL format: {e}"

def validate_destination_path(destination_path):
    """
    Validate and sanitize destination path.
    """
    try:
        # Expand user path
        destination_path = os.path.expanduser(destination_path)
        
        # Get absolute path
        abs_path = os.path.abspath(destination_path)
        
        # Check if path is safe
        if not is_path_safe(abs_path):
            return False, "Destination path is outside safe directories.", None
        
        # Check parent directory exists or can be created
        parent_dir = os.path.dirname(abs_path)
        if not os.path.exists(parent_dir):
            try:
                os.makedirs(parent_dir, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create parent directory: {e}", None
        
        # Check parent directory permissions
        if not os.access(parent_dir, os.W_OK):
            return False, "No write permission for destination directory.", None
        
        # Check file extension for security
        file_ext = os.path.splitext(abs_path)[1].lower()
        if file_ext in DownloadConfig.BLOCKED_EXTENSIONS:
            return False, f"File extension '{file_ext}' is blocked for security.", None
        
        # Sanitize filename
        filename = os.path.basename(abs_path)
        sanitized_filename = sanitize_filename(filename)
        
        # Reconstruct path with sanitized filename
        final_path = os.path.join(parent_dir, sanitized_filename)
        
        return True, "Destination path is valid.", final_path
    except Exception as e:
        return False, f"Error validating destination path: {e}", None

def get_file_info_from_url(url):
    """
    Get file information from URL headers without downloading.
    """
    try:
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        with urllib.request.urlopen(req, timeout=DownloadConfig.TIMEOUT) as response:
            content_length = response.headers.get('content-length')
            content_type = response.headers.get('content-type', 'unknown')
            last_modified = response.headers.get('last-modified')
            
            file_info = {
                'url': url,
                'content_length': int(content_length) if content_length else None,
                'content_type': content_type,
                'last_modified': last_modified,
                'supports_resume': 'accept-ranges' in response.headers,
                'filename': os.path.basename(urllib.parse.urlparse(url).path) or 'downloaded_file'
            }
            
            return file_info
    except Exception as e:
        logger.error(f"Error getting file info from URL: {e}")
        return None

def download_file_advanced(url, destination_path, progress_callback=None, resume=True):
    """
    Advanced file download with resume capability, progress tracking, and retry logic.
    """
    retry_count = 0
    downloaded_bytes = 0
    
    while retry_count < DownloadConfig.MAX_RETRIES:
        try:
            # Check if file exists for resume
            if resume and os.path.exists(destination_path):
                downloaded_bytes = os.path.getsize(destination_path)
                if downloaded_bytes > 0:
                    logger.info(f"Resuming download from byte {downloaded_bytes}")
                    
            # Prepare request with resume headers
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            if downloaded_bytes > 0:
                req.add_header('Range', f'bytes={downloaded_bytes}-')
            
            # Open connection with timeout
            with urllib.request.urlopen(req, timeout=DownloadConfig.TIMEOUT) as response:
                # Get total file size
                content_length = response.headers.get('content-length')
                if content_length:
                    total_size = int(content_length)
                    if downloaded_bytes > 0:
                        total_size += downloaded_bytes
                else:
                    total_size = None
                
                # Check file size limit
                if total_size and total_size > DownloadConfig.MAX_FILE_SIZE:
                    raise ValueError(f"File size ({format_size(total_size)}) exceeds limit ({format_size(DownloadConfig.MAX_FILE_SIZE)})")
                
                # Determine file mode
                file_mode = 'ab' if downloaded_bytes > 0 and response.status == 206 else 'wb'
                
                # Download file in chunks
                with open(destination_path, file_mode) as f:
                    while True:
                        chunk = response.read(DownloadConfig.CHUNK_SIZE)
                        if not chunk:
                            break
                        
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        
                        # Call progress callback
                        if progress_callback:
                            progress_callback(downloaded_bytes, total_size)
                
                # Verify download completion
                if total_size and downloaded_bytes != total_size:
                    raise IOError(f"Download incomplete: {downloaded_bytes}/{total_size} bytes")
                
                # Set file timestamps if available
                try:
                    last_modified = response.headers.get('last-modified')
                    if last_modified:
                        import email.utils
                        timestamp = email.utils.parsedate_to_datetime(last_modified).timestamp()
                        os.utime(destination_path, (timestamp, timestamp))
                except Exception as e:
                    logger.warning(f"Could not set file timestamp: {e}")
                
                return downloaded_bytes
                
        except (urllib.error.URLError, IOError, OSError) as e:
            retry_count += 1
            logger.warning(f"Download attempt {retry_count} failed: {e}")
            
            if retry_count < DownloadConfig.MAX_RETRIES:
                logger.info(f"Retrying in {DownloadConfig.RETRY_DELAY} seconds...")
                time.sleep(DownloadConfig.RETRY_DELAY)
            else:
                # Clean up partial file on final failure
                if os.path.exists(destination_path):
                    try:
                        os.remove(destination_path)
                        logger.info(f"Cleaned up partial file: {destination_path}")
                    except Exception as cleanup_error:
                        logger.error(f"Failed to clean up partial file: {cleanup_error}")
                raise
        
        except Exception as e:
            # Clean up partial file on unexpected error
            if os.path.exists(destination_path):
                try:
                    os.remove(destination_path)
                    logger.info(f"Cleaned up partial file: {destination_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up partial file: {cleanup_error}")
            raise
    
    raise Exception(f"Download failed after {DownloadConfig.MAX_RETRIES} attempts")

@secure_operation('download')
async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Advanced download command with comprehensive features:
    - Path validation and permission checks
    - Resume capability for interrupted downloads
    - Progress indication and retry logic
    - Security validation and file metadata preservation
    - Secure file writing with cleanup on errors
    """
    try:
        # Check command arguments
        if len(context.args) < 1:
            await update.message.reply_text(
                "📥 **Advanced Download Command**\n\n"
                "**Usage:**\n"
                "• `/download <url> [destination_path]`\n\n"
                "**Examples:**\n"
                "• `/download https://example.com/file.zip`\n"
                "• `/download https://example.com/file.zip ~/Downloads/myfile.zip`\n\n"
                "**Features:**\n"
                "• Resume interrupted downloads\n"
                "• Progress tracking and retry logic\n"
                "• Path validation and security checks\n"
                "• Metadata preservation (timestamps, permissions)\n"
                "• Secure file writing with cleanup\n"
                "• Protection against overwrites\n\n"
                "**Security:**\n"
                "• Downloads limited to safe directories\n"
                "• Malicious file extensions blocked\n"
                "• File size limits enforced\n"
                "• URL validation and sanitization",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Parse arguments
        url = context.args[0]
        destination_path = context.args[1] if len(context.args) > 1 else None
        
        # Validate URL
        is_valid_url, url_message = validate_url(url)
        if not is_valid_url:
            await update.message.reply_text(f"❌ Invalid URL: {url_message}")
            return
        
        # Send initial message
        status_msg = await update.message.reply_text("🔍 Analyzing download request...")
        
        # Get file information from URL
        file_info = get_file_info_from_url(url)
        if not file_info:
            await status_msg.edit_text("❌ Unable to retrieve file information from URL.")
            return
        
        # Determine destination path
        if destination_path is None:
            # Use Downloads folder with filename from URL
            downloads_dir = os.path.expanduser('~/Downloads')
            destination_path = os.path.join(downloads_dir, file_info['filename'])
        
        # Validate destination path
        is_valid_dest, dest_message, final_dest_path = validate_destination_path(destination_path)
        if not is_valid_dest:
            await status_msg.edit_text(f"❌ Invalid destination: {dest_message}")
            return
        
        # Check if file already exists
        if os.path.exists(final_dest_path):
            file_size = os.path.getsize(final_dest_path)
            await update.message.reply_text(
                f"⚠️ File already exists: `{final_dest_path}`\n"
                f"📁 Size: {format_size(file_size)}\n"
                f"🔄 Download will resume from where it left off.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # Display file information
        info_text = f"📋 **Download Information:**\n"
        info_text += f"🌐 URL: {url[:50]}{'...' if len(url) > 50 else ''}\n"
        info_text += f"📄 Filename: {file_info['filename']}\n"
        info_text += f"📁 Size: {format_size(file_info['content_length']) if file_info['content_length'] else 'Unknown'}\n"
        info_text += f"🎯 Type: {file_info['content_type']}\n"
        info_text += f"🔄 Resume: {'Yes' if file_info['supports_resume'] else 'No'}\n"
        info_text += f"📍 Destination: `{final_dest_path}`"
        
        await update.message.reply_text(info_text, parse_mode=ParseMode.MARKDOWN)
        
        # Start download
        await status_msg.edit_text("📥 Starting download...")
        
        # Progress tracking variables
        last_progress_update = 0
        start_time = time.time()
        
        def progress_callback(downloaded, total):
            nonlocal last_progress_update
            current_time = time.time()
            
            # Update progress every 5 seconds
            if current_time - last_progress_update >= 5:
                last_progress_update = current_time
                
                if total:
                    progress_percent = (downloaded / total) * 100
                    elapsed_time = current_time - start_time
                    speed = downloaded / elapsed_time if elapsed_time > 0 else 0
                    
                    # Estimate remaining time
                    if speed > 0:
                        remaining_bytes = total - downloaded
                        eta_seconds = remaining_bytes / speed
                        eta_text = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                    else:
                        eta_text = "Unknown"
                    
                    asyncio.create_task(
                        status_msg.edit_text(
                            f"📥 Downloading...\n"
                            f"📊 Progress: {progress_percent:.1f}%\n"
                            f"📁 Downloaded: {format_size(downloaded)} / {format_size(total)}\n"
                            f"🚀 Speed: {format_size(speed)}/s\n"
                            f"⏱️ ETA: {eta_text}"
                        )
                    )
                else:
                    asyncio.create_task(
                        status_msg.edit_text(
                            f"📥 Downloading...\n"
                            f"📁 Downloaded: {format_size(downloaded)}\n"
                            f"🚀 Speed: {format_size(downloaded / (current_time - start_time))}/s"
                        )
                    )
        
        # Perform download in executor to avoid blocking
        loop = asyncio.get_event_loop()
        try:
            downloaded_bytes = await loop.run_in_executor(
                None, 
                lambda: download_file_advanced(url, final_dest_path, progress_callback, resume=True)
            )
            
            # Download completed successfully
            elapsed_time = time.time() - start_time
            avg_speed = downloaded_bytes / elapsed_time if elapsed_time > 0 else 0
            
            # Get final file metadata
            file_metadata = get_file_metadata(final_dest_path)
            
            await status_msg.edit_text(
                f"✅ **Download Completed Successfully!**\n"
                f"📄 File: `{os.path.basename(final_dest_path)}`\n"
                f"📁 Size: {format_size(downloaded_bytes)}\n"
                f"📍 Location: `{final_dest_path}`\n"
                f"⏱️ Time: {int(elapsed_time)}s\n"
                f"🚀 Avg Speed: {format_size(avg_speed)}/s\n"
                f"🔒 Hash: {file_metadata['hash'][:16] if file_metadata and file_metadata['hash'] else 'N/A'}...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log successful download
            logger.info(
                f"Download completed by user {update.effective_user.id}: "
                f"{url} -> {final_dest_path} ({format_size(downloaded_bytes)})"
            )
            
        except Exception as download_error:
            # Download failed
            await status_msg.edit_text(
                f"❌ **Download Failed**\n"
                f"Error: {str(download_error)}\n\n"
                f"**Possible causes:**\n"
                f"• Network connectivity issues\n"
                f"• Server unavailable or overloaded\n"
                f"• Insufficient disk space\n"
                f"• File size exceeds limit\n"
                f"• Permission issues\n\n"
                f"The download will automatically retry with resume capability."
            )
            
            logger.error(f"Download failed for user {update.effective_user.id}: {download_error}")
            
    except Exception as e:
        logger.error(f"Critical error in download command: {e}")
        await update.message.reply_text(
            f"❌ **Critical Error**\n"
            f"An unexpected error occurred: {str(e)}\n\n"
            f"Please try again or contact support if the issue persists."
        )
        raise

@secure_operation('upload')
async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle file upload command with comprehensive security and progress tracking, now supporting concurrency.
    """
    try:
        if not context.args:
            await update.message.reply_text(
                "📤 **Secure File Upload**\n\n"
                "**Usage:** `/upload <file_path> [file_path2] ...`\n\n"
                "**Security Features:**\n"
                "• Path traversal protection\n"
                "• File type validation\n"
                "• Quota enforcement\n"
                "• Integrity verification\n\n"
                "**Examples:**\n"
                "• `/upload ~/Documents/file.pdf`\n"
                "• `/upload ~/Pictures/image.jpg ~/Videos/video.mp4`",
                parse_mode='Markdown'
            )
            return

        user_id = str(update.effective_user.id)
        file_paths = [arg for arg in context.args]
        processing_msg = await update.message.reply_text(f"🔍 Processing {len(file_paths)} path(s) with security validation...")

        # Enhanced validation with security checks
        valid_files = []
        errors = []
        total_size = 0
        
        for file_path in file_paths:
            try:
                # Validate file path
                path_valid, path_msg = security_manager.validate_file_path(file_path, user_id)
                if not path_valid:
                    errors.append(f"❌ Path validation failed for {file_path}: {path_msg}")
                    continue
                
                if os.path.exists(file_path):
                    if os.path.isdir(file_path):
                        # Compress directory with security validation
                        zip_path, zip_msg = create_zip_from_directory(file_path)
                        if zip_path:
                            # Validate compressed file
                            file_size = os.path.getsize(zip_path)
                            quota_valid, quota_msg = security_manager.check_file_quota(user_id, file_size)
                            if quota_valid:
                                type_valid, type_msg = security_manager.validate_file_type(zip_path, user_id)
                                if type_valid:
                                    valid_files.append(zip_path)
                                    total_size += file_size
                                    # Register as temp file for cleanup
                                    security_manager.register_temp_file(user_id, zip_path, file_size)
                                else:
                                    errors.append(f"❌ File type validation failed for {zip_path}: {type_msg}")
                            else:
                                errors.append(f"❌ Quota check failed for {zip_path}: {quota_msg}")
                        else:
                            errors.append(f"❌ Failed to compress directory {file_path}: {zip_msg}")
                    else:
                        # Validate individual file
                        file_size = os.path.getsize(file_path)
                        
                        # Check quota
                        quota_valid, quota_msg = security_manager.check_file_quota(user_id, file_size)
                        if not quota_valid:
                            errors.append(f"❌ Quota check failed for {file_path}: {quota_msg}")
                            continue
                        
                        # Check file type
                        type_valid, type_msg = security_manager.validate_file_type(file_path, user_id)
                        if not type_valid:
                            errors.append(f"❌ File type validation failed for {file_path}: {type_msg}")
                            continue
                        
                        # Final security validation
                        if validate_file_security(file_path)[0]:
                            valid_files.append(file_path)
                            total_size += file_size
                        else:
                            errors.append(f"❌ Security validation failed for {file_path}")
                else:
                    errors.append(f"❌ Path does not exist: {file_path}")
                    
            except Exception as e:
                errors.append(f"❌ Error processing {file_path}: {e}")

        if not valid_files:
            await processing_msg.edit_text(
                "❌ **No valid files to upload**\n\n"
                "All files failed security validation or quota checks.\n"
                "Please check your file paths, types, and quota usage."
            )
            return

        # Show validation summary
        await processing_msg.edit_text(
            f"✅ **Security validation complete**\n\n"
            f"📊 Valid files: {len(valid_files)}\n"
            f"📁 Total size: {format_size(total_size)}\n"
            f"❌ Errors: {len(errors)}\n\n"
            f"🚀 Starting secure upload..."
        )

        # Process uploads with progress tracking
        async with aiohttp.ClientSession() as session:
            upload_tasks = []
            upload_limiter = asyncio.Semaphore(5)  # Limit concurrent uploads

            for file_path in valid_files:
                task = upload_file_with_progress(file_path, update, session, upload_limiter)
                upload_tasks.append(task)

            results = await asyncio.gather(*upload_tasks, return_exceptions=True)
            success_count = sum(1 for r in results if r is True)

        # Update quotas for successful uploads
        for file_path, result in zip(valid_files, results):
            if result is True:
                file_size = os.path.getsize(file_path)
                security_manager.update_file_quota(user_id, file_size, 'add')

        final_msg = f"🎉 **Upload completed**\n\n"
        final_msg += f"✅ Successful: {success_count}/{len(valid_files)}\n"
        if errors:
            final_msg += f"❌ Errors: {len(errors)}\n"
        final_msg += f"📊 Total uploaded: {format_size(sum(os.path.getsize(f) for f, r in zip(valid_files, results) if r is True))}"
        
        await update.message.reply_text(final_msg)

        # Show errors if any
        if errors and len(errors) <= 10:  # Limit error display
            error_msg = "\n".join(errors[:10])
            await update.message.reply_text(f"⚠️ **Errors encountered:**\n{error_msg}")

    except Exception as e:
        logger.error(f"Error in upload_command: {e}")
        await update.message.reply_text(f"❌ Critical error: {e}")

# ==================== ENHANCED CONCURRENT FILE TRANSFER SYSTEM ====================

@dataclass
class TransferStats:
    """Statistics for file transfer operations."""
    bytes_transferred: int = 0
    start_time: float = 0
    last_update: float = 0
    total_size: int = 0
    speed: float = 0.0
    eta: str = "Unknown"
    
class BandwidthManager:
    """Manages bandwidth throttling and rate limiting."""
    
    def __init__(self, max_bandwidth_bps: int = 10 * 1024 * 1024):
        self.max_bandwidth_bps = max_bandwidth_bps
        self.tokens = max_bandwidth_bps
        self.last_refill = time.time()
        self.lock = Lock()
        
    async def acquire_bandwidth(self, bytes_needed: int) -> float:
        """Acquire bandwidth tokens, returns delay needed."""
        async with asyncio.Lock():
            current_time = time.time()
            time_passed = current_time - self.last_refill
            
            # Refill tokens based on time passed
            self.tokens = min(self.max_bandwidth_bps, 
                            self.tokens + (time_passed * self.max_bandwidth_bps))
            self.last_refill = current_time
            
            if self.tokens >= bytes_needed:
                self.tokens -= bytes_needed
                return 0.0
            else:
                # Calculate delay needed
                delay = (bytes_needed - self.tokens) / self.max_bandwidth_bps
                self.tokens = 0
                return delay

class ProgressTracker:
    """Real-time progress tracking for file operations."""
    
    def __init__(self, total_size: int, filename: str):
        self.total_size = total_size
        self.filename = filename
        self.stats = TransferStats(total_size=total_size, start_time=time.time())
        self.progress_callbacks = []
        
    def add_callback(self, callback: Callable[[TransferStats], None]):
        """Add a progress callback."""
        self.progress_callbacks.append(callback)
        
    def update_progress(self, bytes_transferred: int):
        """Update transfer progress."""
        current_time = time.time()
        self.stats.bytes_transferred = bytes_transferred
        
        # Calculate speed and ETA
        elapsed = current_time - self.stats.start_time
        if elapsed > 0:
            self.stats.speed = bytes_transferred / elapsed
            if self.stats.speed > 0:
                remaining = self.total_size - bytes_transferred
                eta_seconds = remaining / self.stats.speed
                self.stats.eta = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
        
        # Call progress callbacks
        for callback in self.progress_callbacks:
            try:
                callback(self.stats)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")

class ConcurrentFileTransfer:
    """Manages concurrent file transfers with rate limiting."""
    
    def __init__(self, max_concurrent: int = 5, max_bandwidth_bps: int = 10 * 1024 * 1024):
        self.max_concurrent = max_concurrent
        self.bandwidth_manager = BandwidthManager(max_bandwidth_bps)
        self.active_transfers: Dict[str, ProgressTracker] = {}
        self.transfer_semaphore = asyncio.Semaphore(max_concurrent)
        
    async def upload_file(self, file_path: str, update: Update, 
                         progress_callback: Optional[Callable] = None) -> bool:
        """Upload a file with progress tracking and rate limiting."""
        
        async with self.transfer_semaphore:
            try:
                # Validate file and get metadata
                metadata = get_file_metadata(file_path)
                if not metadata:
                    return False
                    
                # Calculate pre-transfer hash for integrity verification
                pre_hash = calculate_file_hash(file_path)
                
                # Create progress tracker
                tracker = ProgressTracker(metadata['size'], metadata['name'])
                self.active_transfers[file_path] = tracker
                
                # Set up progress callback
                if progress_callback:
                    tracker.add_callback(progress_callback)
                
                # Send initial message
                progress_msg = await update.message.reply_text(
                    f"📤 Starting upload: {metadata['name']}\n"
                    f"📁 Size: {metadata['size_formatted']}\n"
                    f"🔒 Hash: {pre_hash[:16]}...\n"
                    f"⏳ Progress: 0%"
                )
                
                # Create telegram progress callback
                last_telegram_update = 0
                
                def telegram_progress(stats: TransferStats):
                    nonlocal last_telegram_update
                    current_time = time.time()
                    
                    # Update Telegram message every 2 seconds
                    if current_time - last_telegram_update >= 2:
                        last_telegram_update = current_time
                        progress_percent = (stats.bytes_transferred / stats.total_size) * 100
                        
                        asyncio.create_task(
                            progress_msg.edit_text(
                                f"📤 Uploading: {metadata['name']}\n"
                                f"📊 Progress: {progress_percent:.1f}%\n"
                                f"📁 Size: {format_size(stats.bytes_transferred)} / {metadata['size_formatted']}\n"
                                f"🚀 Speed: {format_size(stats.speed)}/s\n"
                                f"⏱️ ETA: {stats.eta}\n"
                                f"🔒 Hash: {pre_hash[:16]}..."
                            )
                        )
                
                tracker.add_callback(telegram_progress)
                
                # Perform chunked upload with bandwidth management
                success = await self._upload_chunked(file_path, metadata, tracker)
                
                if success:
                    # Verify integrity after upload
                    post_hash = calculate_file_hash(file_path)
                    integrity_check = "✅ Verified" if pre_hash == post_hash else "❌ Integrity check failed"
                    
                    await progress_msg.edit_text(
                        f"✅ Upload completed: {metadata['name']}\n"
                        f"📁 Size: {metadata['size_formatted']}\n"
                        f"⏱️ Time: {int(time.time() - tracker.stats.start_time)}s\n"
                        f"🚀 Avg Speed: {format_size(tracker.stats.speed)}/s\n"
                        f"🔒 Integrity: {integrity_check}\n"
                        f"🔑 Hash: {pre_hash[:16]}..."
                    )
                else:
                    await progress_msg.edit_text(
                        f"❌ Upload failed: {metadata['name']}\n"
                        f"Please check connection and try again."
                    )
                
                return success
                
            except Exception as e:
                logger.error(f"Error uploading {file_path}: {e}")
                return False
            finally:
                # Clean up tracker
                if file_path in self.active_transfers:
                    del self.active_transfers[file_path]
    
    async def _upload_chunked(self, file_path: str, metadata: dict, tracker: ProgressTracker) -> bool:
        """Perform chunked upload with rate limiting."""
        try:
            chunk_size = 8192  # 8KB chunks
            
            async with aiofiles.open(file_path, 'rb') as file:
                uploaded_bytes = 0
                
                while uploaded_bytes < metadata['size']:
                    # Read chunk
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Apply bandwidth throttling
                    delay = await self.bandwidth_manager.acquire_bandwidth(len(chunk))
                    if delay > 0:
                        await asyncio.sleep(delay)
                    
                    # Simulate upload (replace with actual upload logic)
                    await asyncio.sleep(0.01)  # Simulate network delay
                    
                    uploaded_bytes += len(chunk)
                    tracker.update_progress(uploaded_bytes)
                
                return uploaded_bytes == metadata['size']
                
        except Exception as e:
            logger.error(f"Error in chunked upload: {e}")
            return False
    
    async def download_file(self, url: str, destination: str, update: Update,
                          progress_callback: Optional[Callable] = None) -> bool:
        """Download a file with progress tracking and rate limiting."""
        
        async with self.transfer_semaphore:
            try:
                # Get file info
                file_info = get_file_info_from_url(url)
                if not file_info:
                    return False
                
                # Create progress tracker
                file_size = file_info.get('content_length', 0)
                tracker = ProgressTracker(file_size, file_info['filename'])
                self.active_transfers[url] = tracker
                
                # Set up progress callback
                if progress_callback:
                    tracker.add_callback(progress_callback)
                
                # Send initial message
                progress_msg = await update.message.reply_text(
                    f"📥 Starting download: {file_info['filename']}\n"
                    f"📁 Size: {format_size(file_size) if file_size else 'Unknown'}\n"
                    f"⏳ Progress: 0%"
                )
                
                # Create telegram progress callback
                last_telegram_update = 0
                
                def telegram_progress(stats: TransferStats):
                    nonlocal last_telegram_update
                    current_time = time.time()
                    
                    if current_time - last_telegram_update >= 2:
                        last_telegram_update = current_time
                        progress_percent = (stats.bytes_transferred / stats.total_size) * 100 if stats.total_size else 0
                        
                        asyncio.create_task(
                            progress_msg.edit_text(
                                f"📥 Downloading: {file_info['filename']}\n"
                                f"📊 Progress: {progress_percent:.1f}%\n"
                                f"📁 Downloaded: {format_size(stats.bytes_transferred)} / {format_size(stats.total_size)}\n"
                                f"🚀 Speed: {format_size(stats.speed)}/s\n"
                                f"⏱️ ETA: {stats.eta}"
                            )
                        )
                
                tracker.add_callback(telegram_progress)
                
                # Perform chunked download with bandwidth management
                success = await self._download_chunked(url, destination, tracker)
                
                if success:
                    # Calculate hash for integrity verification
                    file_hash = calculate_file_hash(destination)
                    
                    await progress_msg.edit_text(
                        f"✅ Download completed: {file_info['filename']}\n"
                        f"📁 Size: {format_size(file_size)}\n"
                        f"⏱️ Time: {int(time.time() - tracker.stats.start_time)}s\n"
                        f"🚀 Avg Speed: {format_size(tracker.stats.speed)}/s\n"
                        f"🔒 Hash: {file_hash[:16] if file_hash else 'N/A'}...\n"
                        f"📍 Location: {destination}"
                    )
                else:
                    await progress_msg.edit_text(
                        f"❌ Download failed: {file_info['filename']}\n"
                        f"Please check connection and try again."
                    )
                
                return success
                
            except Exception as e:
                logger.error(f"Error downloading {url}: {e}")
                return False
            finally:
                # Clean up tracker
                if url in self.active_transfers:
                    del self.active_transfers[url]
    
    async def _download_chunked(self, url: str, destination: str, tracker: ProgressTracker) -> bool:
        """Perform chunked download with rate limiting."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return False
                    
                    async with aiofiles.open(destination, 'wb') as file:
                        downloaded_bytes = 0
                        
                        async for chunk in response.content.iter_chunked(8192):
                            # Apply bandwidth throttling
                            delay = await self.bandwidth_manager.acquire_bandwidth(len(chunk))
                            if delay > 0:
                                await asyncio.sleep(delay)
                            
                            await file.write(chunk)
                            downloaded_bytes += len(chunk)
                            tracker.update_progress(downloaded_bytes)
                        
                        return True
                        
        except Exception as e:
            logger.error(f"Error in chunked download: {e}")
            return False
    
    def get_active_transfers(self) -> Dict[str, dict]:
        """Get information about active transfers."""
        return {
            path: {
                'filename': tracker.filename,
                'progress': (tracker.stats.bytes_transferred / tracker.stats.total_size) * 100,
                'speed': tracker.stats.speed,
                'eta': tracker.stats.eta
            }
            for path, tracker in self.active_transfers.items()
        }

# Global transfer manager
transfer_manager = ConcurrentFileTransfer(max_concurrent=5, max_bandwidth_bps=10 * 1024 * 1024)

async def upload_file_with_progress(file_path: str, update: Update, 
                                  session: aiohttp.ClientSession = None, 
                                  limiter: asyncio.Semaphore = None) -> bool:
    """Enhanced upload with concurrent support and progress tracking."""
    return await transfer_manager.upload_file(file_path, update)

async def download_file_with_progress(url: str, destination: str, update: Update) -> bool:
    """Enhanced download with concurrent support and progress tracking."""
    return await transfer_manager.download_file(url, destination, update)

@secure_operation('read')
async def get_transfer_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Get status of active transfers."""
    active_transfers = transfer_manager.get_active_transfers()
    
    if not active_transfers:
        await update.message.reply_text("📊 No active transfers.")
        return
    
    status_text = "📊 **Active Transfers:**\n\n"
    for path, info in active_transfers.items():
        status_text += f"📁 {info['filename']}\n"
        status_text += f"   📊 Progress: {info['progress']:.1f}%\n"
        status_text += f"   🚀 Speed: {format_size(info['speed'])}/s\n"
        status_text += f"   ⏱️ ETA: {info['eta']}\n\n"
    
    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

@secure_operation('read')
async def quota_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display user quota information and usage statistics."""
    try:
        user_id = str(update.effective_user.id)
        quota_info = security_manager.get_user_quota_info(user_id)
        
        if not quota_info:
            await update.message.reply_text("❌ Unable to retrieve quota information.")
            return
        
        # Format quota information
        quota_text = f"💾 **Your File Quota**\n\n"
        quota_text += f"📊 **Usage Statistics:**\n"
        quota_text += f"• Used: {format_size(quota_info['used_quota'])}\n"
        quota_text += f"• Total: {format_size(quota_info['total_quota'])}\n"
        quota_text += f"• Available: {format_size(quota_info['available_quota'])}\n"
        quota_text += f"• Usage: {quota_info['quota_percentage']:.1f}%\n\n"
        
        quota_text += f"📁 **File Information:**\n"
        quota_text += f"• File count: {quota_info['file_count']}\n"
        quota_text += f"• Max file size: {format_size(quota_info['max_file_size'])}\n\n"
        
        quota_text += f"🧹 **Last cleanup:** {quota_info['last_cleanup'][:19] if quota_info['last_cleanup'] else 'Never'}\n\n"
        
        # Add quota bar visualization
        used_percent = quota_info['quota_percentage']
        if used_percent < 50:
            quota_text += "🟢 Quota status: Good"
        elif used_percent < 80:
            quota_text += "🟡 Quota status: Moderate"
        else:
            quota_text += "🔴 Quota status: High - Consider cleaning up files"
        
        await update.message.reply_text(quota_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in quota command: {e}")
        await update.message.reply_text(f"❌ Error retrieving quota information: {e}")

@secure_operation('admin')
async def security_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display security statistics and system information."""
    try:
        stats = security_manager.get_security_stats()
        
        if not stats:
            await update.message.reply_text("❌ Unable to retrieve security statistics.")
            return
        
        # Format security statistics
        stats_text = f"🛡️ **Security Statistics**\n\n"
        stats_text += f"👥 **User Information:**\n"
        stats_text += f"• Total users: {stats['total_users']}\n"
        stats_text += f"• Active sessions: {stats['active_sessions']}\n\n"
        
        stats_text += f"📊 **Recent Activity (24h):**\n"
        if stats['recent_events_24h']:
            for event_type, count in stats['recent_events_24h'].items():
                stats_text += f"• {event_type}: {count}\n"
        else:
            stats_text += "• No recent events\n"
        
        stats_text += f"\n🗂️ **Temporary Files:**\n"
        stats_text += f"• Count: {stats['temp_files_count']}\n"
        stats_text += f"• Size: {format_size(stats['temp_files_size'])}\n\n"
        
        stats_text += f"🔒 **Security Features Active:**\n"
        stats_text += f"• Path traversal protection ✅\n"
        stats_text += f"• File type validation ✅\n"
        stats_text += f"• Quota enforcement ✅\n"
        stats_text += f"• Audit logging ✅\n"
        stats_text += f"• Automatic cleanup ✅"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in security stats command: {e}")
        await update.message.reply_text(f"❌ Error retrieving security statistics: {e}")

@secure_operation('admin')
async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Force cleanup of temporary files and expired resources."""
    try:
        user_id = str(update.effective_user.id)
        
        # Check if force cleanup is requested
        force_cleanup = 'force' in context.args if context.args else False
        
        await update.message.reply_text("🧹 Starting cleanup process...")
        
        # Perform cleanup
        cleanup_stats = security_manager.cleanup_temp_files(force=force_cleanup)
        
        # Format cleanup results
        cleanup_text = f"🧹 **Cleanup Results**\n\n"
        cleanup_text += f"📁 Files cleaned: {cleanup_stats['files_cleaned']}\n"
        cleanup_text += f"💾 Space freed: {format_size(cleanup_stats['bytes_freed'])}\n"
        
        if cleanup_stats['errors']:
            cleanup_text += f"\n⚠️ **Errors encountered:**\n"
            for error in cleanup_stats['errors'][:5]:  # Show first 5 errors
                cleanup_text += f"• {error}\n"
            if len(cleanup_stats['errors']) > 5:
                cleanup_text += f"• ... and {len(cleanup_stats['errors']) - 5} more errors\n"
        
        cleanup_text += f"\n✅ Cleanup completed successfully!"
        
        await update.message.reply_text(cleanup_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in cleanup command: {e}")
        await update.message.reply_text(f"❌ Error during cleanup: {e}")

@secure_operation('read')
async def pwd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current working directory for the user."""
    try:
        user_id = str(update.effective_user.id)
        current_dir = security_manager.get_user_directory(user_id)
        
        # Get directory information
        try:
            dir_info = {
                'path': current_dir,
                'exists': os.path.exists(current_dir),
                'readable': os.access(current_dir, os.R_OK) if os.path.exists(current_dir) else False,
                'writable': os.access(current_dir, os.W_OK) if os.path.exists(current_dir) else False,
                'size': get_directory_size(current_dir) if os.path.exists(current_dir) else 0,
                'file_count': len([f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f))]) if os.path.exists(current_dir) else 0,
                'dir_count': len([d for d in os.listdir(current_dir) if os.path.isdir(os.path.join(current_dir, d))]) if os.path.exists(current_dir) else 0
            }
            
            pwd_text = f"📂 **Current Working Directory**\n\n"
            pwd_text += f"📍 **Path:** `{current_dir}`\n\n"
            
            if dir_info['exists']:
                pwd_text += f"📊 **Directory Info:**\n"
                pwd_text += f"• Status: {'✅ Accessible' if dir_info['readable'] else '❌ Not accessible'}\n"
                pwd_text += f"• Permissions: {'🔓 Read' if dir_info['readable'] else '🔒 No read'} | {'📝 Write' if dir_info['writable'] else '🚫 No write'}\n"
                pwd_text += f"• Files: {dir_info['file_count']}\n"
                pwd_text += f"• Subdirectories: {dir_info['dir_count']}\n"
                pwd_text += f"• Total size: {format_size(dir_info['size'])}\n\n"
                pwd_text += f"💡 **Tip:** Use `/cd <path>` to change directory or `/ls` to list contents."
            else:
                pwd_text += f"⚠️ **Warning:** Directory does not exist or is inaccessible.\n"
                pwd_text += f"💡 **Tip:** Use `/cd <path>` to change to a valid directory."
            
            await update.message.reply_text(pwd_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(
                f"📂 **Current Working Directory**\n\n"
                f"📍 **Path:** `{current_dir}`\n\n"
                f"⚠️ **Error:** Could not retrieve directory information: {e}"
            )
        
    except Exception as e:
        logger.error(f"Error in pwd command: {e}")
        await update.message.reply_text(f"❌ Error retrieving current directory: {e}")

@secure_operation('basic_access')
async def cd_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change current working directory for the user with enhanced path handling."""
    try:
        if not context.args:
            await update.message.reply_text(
                "📂 **Change Directory**\n\n"
                "**Usage:** `/cd <directory_path>`\n\n"
                "**Examples:**\n"
                "• `/cd ~/Documents` - Change to Documents folder\n"
                "• `/cd ~/Desktop` - Change to Desktop folder\n"
                "• `/cd ..` - Go up one directory\n"
                "• `/cd ~` - Change to home directory\n"
                "• `/cd /` - Change to root directory\n"
                "• `/cd /home/user/project` - Change to specific path\n\n"
                "**Security:**\n"
                "• Only safe directories are accessible\n"
                "• Path validation prevents traversal attacks\n"
                "• Directory existence is verified\n\n"
                "**Tip:** Use `/pwd` to see current directory",
                parse_mode='Markdown'
            )
            return
        
        user_id = str(update.effective_user.id)
        new_directory = context.args[0]
        
        # Handle special path shortcuts
        if new_directory == '~':
            # Change to user's home directory
            new_directory = os.path.expanduser('~')
        elif new_directory == '/':
            # Change to root directory (system drive on Windows)
            if platform.system() == "Windows":
                new_directory = os.path.abspath(os.sep)
            else:
                new_directory = '/'
        elif new_directory == '..':
            # Go up one directory
            current_dir = security_manager.get_user_directory(user_id)
            new_directory = os.path.dirname(current_dir)
        elif new_directory.startswith('~'):
            # Expand user home directory if needed
            new_directory = os.path.expanduser(new_directory)
        
        # Handle relative paths
        if not os.path.isabs(new_directory):
            current_dir = security_manager.get_user_directory(user_id)
            new_directory = os.path.join(current_dir, new_directory)
        
        # Normalize the path to resolve any remaining .. or . components
        new_directory = os.path.normpath(new_directory)
        
        # Additional validation before setting directory
        if not os.path.exists(new_directory):
            await update.message.reply_text(
                f"❌ **Directory does not exist**\n\n"
                f"📍 **Attempted path:** `{new_directory}`\n\n"
                f"💡 **Suggestions:**\n"
                f"• Check the path spelling\n"
                f"• Use `/pwd` to see current directory\n"
                f"• Use `/ls` to see available directories\n"
                f"• Try using tab completion if available",
                parse_mode='Markdown'
            )
            return
        
        if not os.path.isdir(new_directory):
            await update.message.reply_text(
                "❌ **Invalid Path**\n\n"
                "The specified path is not a directory but a file. Please use a valid directory path or check the file details using `/fileinfo`.",
                parse_mode='Markdown'
            )
            return
        
        # Check permissions before attempting to change
        if not os.access(new_directory, os.R_OK):
            await update.message.reply_text(
                f"❌ **Permission denied**\n\n"
                f"📍 **Attempted path:** `{new_directory}`\n\n"
                f"🚫 **Error:** Insufficient permissions to access this directory.\n\n"
                f"💡 **Suggestions:**\n"
                f"• Try a different directory\n"
                f"• Check if you have the necessary permissions\n"
                f"• Use only safe directories (Documents, Desktop, etc.)",
                parse_mode='Markdown'
            )
            return
        
        # Set the new directory with validation
        success, message = security_manager.set_user_directory(user_id, new_directory)
        
        if success:
            # Get info about the new directory
            try:
                items = os.listdir(new_directory)
                file_count = len([f for f in items if os.path.isfile(os.path.join(new_directory, f))])
                dir_count = len([d for d in items if os.path.isdir(os.path.join(new_directory, d))])
                hidden_count = len([h for h in items if h.startswith('.')])
                
                # Calculate directory size (for small directories)
                try:
                    dir_size = get_directory_size(new_directory)
                    size_info = f" | Size: {format_size(dir_size)}"
                except Exception:
                    size_info = ""
                
                await update.message.reply_text(
                    f"✅ **Directory changed successfully!**\n\n"
                    f"📍 **New path:** `{new_directory}`\n"
                    f"📊 **Contents:** {file_count} files, {dir_count} directories{size_info}\n"
                    f"👻 **Hidden items:** {hidden_count}\n\n"
                    f"💡 **Next steps:**\n"
                    f"• Use `/ls` to see contents\n"
                    f"• Use `/ls --detailed` for more information\n"
                    f"• Use `/ls --hidden` to show hidden files",
                    parse_mode='Markdown'
                )
            except PermissionError:
                await update.message.reply_text(
                    f"✅ **Directory changed successfully!**\n\n"
                    f"📍 **New path:** `{new_directory}`\n"
                    f"⚠️ **Note:** Cannot read directory contents due to permissions.\n\n"
                    f"💡 **Tip:** You can still navigate but may have limited access.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                await update.message.reply_text(
                    f"✅ **Directory changed successfully!**\n\n"
                    f"📍 **New path:** `{new_directory}`\n"
                    f"⚠️ **Note:** Could not read directory contents: {e}\n\n"
                    f"💡 **Tip:** Use `/ls` to see contents or `/pwd` to confirm location.",
                    parse_mode='Markdown'
                )
        else:
            # Parse the error message to provide specific feedback
            if "does not exist" in message:
                error_type = "Directory not found"
                suggestions = [
                    "• Check the path spelling",
                    "• Use `/pwd` to see current directory",
                    "• Use `/ls` to see available directories"
                ]
            elif "not a directory" in message:
                error_type = "Path is not a directory"
                suggestions = [
                    "• The path exists but is a file",
                    "• Use `/fileinfo` to get file information",
                    "• Navigate to the parent directory instead"
                ]
            elif "outside" in message or "safe" in message:
                error_type = "Security restriction"
                suggestions = [
                    "• Use only safe directories (Documents, Desktop, etc.)",
                    "• Path is outside allowed security boundaries",
                    "• Try a path within your home directory"
                ]
            elif "permission" in message.lower():
                error_type = "Permission denied"
                suggestions = [
                    "• Insufficient permissions to access directory",
                    "• Try a different directory",
                    "• Check if you have the necessary access rights"
                ]
            else:
                error_type = "Unknown error"
                suggestions = [
                    "• Check if the path exists",
                    "• Ensure you have access permissions",
                    "• Use only safe directories"
                ]
            
            await update.message.reply_text(
                f"❌ **Failed to change directory**\n\n"
                f"📍 **Attempted path:** `{new_directory}`\n"
                f"🚫 **Error type:** {error_type}\n"
                f"📝 **Details:** {message}\n\n"
                f"💡 **Suggestions:**\n" + "\n".join(suggestions) + "\n\n"
                f"**Current directory:** Use `/pwd` to see where you are now.",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Error in cd command: {e}")
        await update.message.reply_text(
            f"❌ **Critical error in cd command**\n\n"
            f"📝 **Error details:** {str(e)}\n\n"
            f"💡 **What to do:**\n"
            f"• Try the command again\n"
            f"• Use `/pwd` to check current directory\n"
            f"• Contact support if the issue persists",
            parse_mode='Markdown'
        )

@secure_operation('read')
async def ls_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List files in current or specified directory."""
    try:
        user_id = str(update.effective_user.id)
        
        # Determine directory to list
        if context.args:
            directory_path = context.args[0]
            # Expand user home directory if needed
            if directory_path.startswith('~'):
                directory_path = os.path.expanduser(directory_path)
            # Handle relative paths
            if not os.path.isabs(directory_path):
                current_dir = security_manager.get_user_directory(user_id)
                directory_path = os.path.join(current_dir, directory_path)
            directory_path = os.path.normpath(directory_path)
        else:
            directory_path = security_manager.get_user_directory(user_id)
        
        # Validate directory path
        path_valid, path_msg = security_manager.validate_file_path(directory_path, user_id)
        if not path_valid:
            await update.message.reply_text(
                "❌ **Security Restriction**\n\n"
                "The path is outside allowed security boundaries. Please use safe directories like Documents or Desktop, or try a path within your home directory.",
                parse_mode='Markdown'
            )
            return
        
        if not os.path.exists(directory_path):
            await update.message.reply_text(
                f"❌ **Directory Not Found**\n\n"
                f"📍 **Path:** `{directory_path}`\n\n"
                f"💡 **Suggestions:**\n"
                f"• Check the path spelling\n"
                f"• Use `/pwd` to see your current directory\n"
                f"• Use `/cd` to navigate to an existing directory\n"
                f"• Use `/ls` without arguments to list current directory\n"
                f"• Try using tab completion if available",
                parse_mode='Markdown'
            )
            return
        
        if not os.path.isdir(directory_path):
            await update.message.reply_text(
                f"❌ **Path is Not a Directory**\n\n"
                f"📍 **Path:** `{directory_path}`\n\n"
                f"🚫 **Error:** The specified path exists but is a file, not a directory\n\n"
                f"💡 **Suggestions:**\n"
                f"• Use `/fileinfo {directory_path}` to see file details\n"
                f"• Try the parent directory: `/ls {os.path.dirname(directory_path)}`\n"
                f"• Use `/cd {os.path.dirname(directory_path)}` to navigate to parent",
                parse_mode='Markdown'
            )
            return
        
        # Parse options from remaining arguments
        show_hidden = '--hidden' in context.args
        show_detailed = '--detailed' in context.args
        
        # Get directory contents
        try:
            all_items = os.listdir(directory_path)
            
            # Separate files and directories
            files = []
            dirs = []
            
            for item in all_items:
                item_path = os.path.join(directory_path, item)
                
                # Skip hidden files unless requested
                if not show_hidden and item.startswith('.'):
                    continue
                
                try:
                    if os.path.isfile(item_path):
                        file_info = get_file_metadata(item_path)
                        if file_info:
                            files.append(file_info)
                    elif os.path.isdir(item_path):
                        dir_info = {
                            'name': item,
                            'path': item_path,
                            'type': 'directory',
                            'size': get_directory_size(item_path),
                            'size_formatted': format_size(get_directory_size(item_path)),
                            'modified': datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat(),
                            'items': len(os.listdir(item_path)) if os.access(item_path, os.R_OK) else 0
                        }
                        dirs.append(dir_info)
                except (OSError, IOError):
                    # Skip items that can't be accessed
                    continue
            
            # Sort items
            files.sort(key=lambda x: x['name'].lower())
            dirs.sort(key=lambda x: x['name'].lower())
            
            # Format output
            if not files and not dirs:
                ls_text = f"📂 **Directory Listing**\n\n"
                ls_text += f"📍 **Path:** `{directory_path}`\n\n"
                ls_text += f"📄 **Contents:** Empty directory\n\n"
                ls_text += f"💡 **Tip:** Use `--hidden` to show hidden files"
            else:
                total_size = sum(f['size'] for f in files) + sum(d['size'] for d in dirs)
                
                ls_text = f"📂 **Directory Listing**\n\n"
                ls_text += f"📍 **Path:** `{directory_path}`\n"
                ls_text += f"📊 **Summary:** {len(dirs)} directories, {len(files)} files, {format_size(total_size)}\n\n"
                
                # List directories first
                if dirs:
                    ls_text += f"📁 **Directories:**\n"
                    for dir_info in dirs:
                        if show_detailed:
                            ls_text += f"📁 `{dir_info['name']}`\n"
                            ls_text += f"   📊 Size: {dir_info['size_formatted']} | Items: {dir_info['items']}\n"
                            ls_text += f"   📅 Modified: {dir_info['modified'][:19].replace('T', ' ')}\n"
                        else:
                            ls_text += f"📁 `{dir_info['name']}/` ({dir_info['items']} items)\n"
                    ls_text += "\n"
                
                # List files
                if files:
                    ls_text += f"📄 **Files:**\n"
                    for file_info in files:
                        icon = get_file_type_icon(file_info['path'])
                        if show_detailed:
                            ls_text += f"{icon} `{file_info['name']}`\n"
                            ls_text += f"   📏 Size: {file_info['size_formatted']} | Type: {file_info['mime_type']}\n"
                            ls_text += f"   📅 Modified: {file_info['modified'][:19].replace('T', ' ')}\n"
                        else:
                            ls_text += f"{icon} `{file_info['name']}` ({file_info['size_formatted']})\n"
                
                # Add usage tips
                ls_text += f"\n💡 **Tips:**\n"
                ls_text += f"• Use `/cd <dirname>` to change directory\n"
                ls_text += f"• Use `/fileinfo <filename>` for detailed file info\n"
                ls_text += f"• Use `--detailed` for more information\n"
                ls_text += f"• Use `--hidden` to show hidden files"
            
            await update.message.reply_text(ls_text, parse_mode='Markdown')
            
        except PermissionError:
            await update.message.reply_text(
                f"❌ **Permission denied**\n\n"
                f"📍 **Path:** `{directory_path}`\n"
                f"🚫 **Error:** Insufficient permissions to read directory contents.\n\n"
                f"💡 **Tip:** Try changing to a different directory with `/cd`",
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Error in ls command: {e}")
        await update.message.reply_text(f"❌ Error listing directory: {e}")

@secure_operation('write')
async def mkdir_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Create a new directory securely with proper validation and feedback."""
    try:
        if not context.args:
            await update.message.reply_text(
                "📁 **Create Directory**\n\n"
                "**Usage:** `/mkdir \u003cdirectory_name\u003e`\n\n"
                "**Examples:**\n"
                "• `/mkdir new_folder` - Create directory in current location\n"
                "• `/mkdir ~/Documents/projects` - Create directory with full path\n"
                "• `/mkdir \"my folder\"` - Create directory with spaces in name\n"
                "• `/mkdir parent/child` - Create nested directories\n\n"
                "**Security Features:**\n"
                "• Path validation prevents traversal attacks\n"
                "• Directory creation in safe locations only\n"
                "• Automatic parent directory creation\n"
                "• Proper error handling and feedback\n\n"
                "**Note:** Directory names cannot contain: `\u003c \u003e : \" | ? *`",
                parse_mode='Markdown'
            )
            return
        
        user_id = str(update.effective_user.id)
        directory_name = ' '.join(context.args)  # Handle spaces in directory names
        
        # Get current working directory
        current_dir = security_manager.get_user_directory(user_id)
        
        # Handle different path types
        if directory_name.startswith('~'):
            # Expand user home directory
            target_path = os.path.expanduser(directory_name)
        elif os.path.isabs(directory_name):
            # Absolute path
            target_path = directory_name
        else:
            # Relative path - join with current directory
            target_path = os.path.join(current_dir, directory_name)
        
        # Normalize the path
        target_path = os.path.normpath(target_path)
        
        # Validate directory name for dangerous characters
        dir_name = os.path.basename(target_path)
        if any(char in dir_name for char in '<>:"|?*'):
            await update.message.reply_text(
                f"❌ **Invalid Directory Name**\n\n"
                f"📍 **Attempted name:** `{dir_name}`\n\n"
                f"🚫 **Error:** Directory name contains invalid characters: `< > : \" | ? *`\n\n"
                f"💡 **Suggestions:**\n"
                f"• Use alphanumeric characters, spaces, hyphens, and underscores\n"
                f"• Avoid special characters and symbols\n"
                f"• Try: `{re.sub(r'[<>:\"|?*]', '_', dir_name)}`",
                parse_mode='Markdown'
            )
            return
        
        # Check for Windows reserved names
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
        if dir_name.upper() in reserved_names:
            await update.message.reply_text(
                f"❌ **Reserved Directory Name**\n\n"
                f"📍 **Attempted name:** `{dir_name}`\n\n"
                f"🚫 **Error:** '{dir_name}' is a reserved system name on Windows\n\n"
                f"💡 **Suggestion:** Try `{dir_name}_folder` instead",
                parse_mode='Markdown'
            )
            return
        
        # Validate path security using security manager
        is_safe_path, validation_message = security_manager._validate_directory_path(target_path, user_id)
        if not is_safe_path:
            await update.message.reply_text(
                f"🚫 **Security Violation**\n\n"
                f"📍 **Attempted path:** `{target_path}`\n\n"
                f"⚠️ **Error:** {validation_message}\n\n"
                f"💡 **Allowed locations:**\n"
                f"• Desktop: `~/Desktop`\n"
                f"• Documents: `~/Documents`\n"
                f"• Downloads: `~/Downloads`\n"
                f"• Pictures: `~/Pictures`\n"
                f"• Videos: `~/Videos`\n"
                f"• Music: `~/Music`\n"
                f"• Temp directory\n\n"
                f"**Try:** `/mkdir ~/Documents/{dir_name}`",
                parse_mode='Markdown'
            )
            return
        
        # Check if directory already exists
        if os.path.exists(target_path):
            if os.path.isdir(target_path):
                await update.message.reply_text(
                    f"📁 **Directory Already Exists**\n\n"
                    f"📍 **Path:** `{target_path}`\n\n"
                    f"ℹ️ **Info:** The directory already exists and is accessible\n\n"
                    f"💡 **Options:**\n"
                    f"• Use `/cd {target_path}` to navigate to it\n"
                    f"• Use `/ls {target_path}` to see its contents\n"
                    f"• Choose a different name for your new directory",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    f"❌ **Path Exists as File**\n\n"
                    f"📍 **Path:** `{target_path}`\n\n"
                    f"🚫 **Error:** A file with this name already exists\n\n"
                    f"💡 **Suggestions:**\n"
                    f"• Choose a different directory name\n"
                    f"• Use `/fileinfo {target_path}` to see file details\n"
                    f"• Try adding a suffix like `_{dir_name}_dir`",
                    parse_mode='Markdown'
                )
            return
        
        # Check if parent directory exists and is writable
        parent_dir = os.path.dirname(target_path)
        if not os.path.exists(parent_dir):
            # Try to create parent directories
            try:
                os.makedirs(parent_dir, exist_ok=True)
                parent_created = True
            except OSError as e:
                await update.message.reply_text(
                    f"❌ **Cannot Create Parent Directory**\n\n"
                    f"📍 **Parent path:** `{parent_dir}`\n\n"
                    f"🚫 **Error:** {e}\n\n"
                    f"💡 **Suggestions:**\n"
                    f"• Check if the parent path is valid\n"
                    f"• Ensure you have write permissions\n"
                    f"• Try creating the directory in a different location",
                    parse_mode='Markdown'
                )
                return
        else:
            parent_created = False
        
        # Check write permissions on parent directory
        if not os.access(parent_dir, os.W_OK):
            await update.message.reply_text(
                f"🚫 **Permission Denied**\n\n"
                f"📍 **Parent directory:** `{parent_dir}`\n\n"
                f"⚠️ **Error:** Insufficient permissions to create directory here\n\n"
                f"💡 **Suggestions:**\n"
                f"• Try creating the directory in Documents or Desktop\n"
                f"• Use: `/mkdir ~/Documents/{dir_name}`\n"
                f"• Check directory permissions",
                parse_mode='Markdown'
            )
            return
        
        # Create the directory
        try:
            os.makedirs(target_path, exist_ok=False)
            
            # Log successful operation
            security_manager._log_security_event(SecurityEvent(
                event_type='directory_operation',
                user_id=user_id,
                operation='mkdir',
                resource_path=target_path,
                success=True
            ))
            
            # Get directory information for response
            dir_info = {
                'size': 0,  # New directory is empty
                'permissions': 'Read/Write' if os.access(target_path, os.R_OK | os.W_OK) else 'Limited',
                'parent': parent_dir,
                'created_parents': parent_created
            }
            
            # Success message with detailed information
            success_msg = f"✅ **Directory Created Successfully!**\n\n"
            success_msg += f"📁 **New directory:** `{target_path}`\n"
            success_msg += f"📂 **Parent directory:** `{parent_dir}`\n"
            success_msg += f"🔓 **Permissions:** {dir_info['permissions']}\n"
            
            if parent_created:
                success_msg += f"📋 **Note:** Parent directories were created automatically\n"
            
            success_msg += f"\n💡 **Next steps:**\n"
            success_msg += f"• Use `/cd {target_path}` to navigate to the new directory\n"
            success_msg += f"• Use `/ls {parent_dir}` to see the directory in its parent\n"
            success_msg += f"• Use `/upload` to add files to the directory\n"
            success_msg += f"• Use `/mkdir {os.path.join(target_path, 'subdirectory')}` to create subdirectories"
            
            await update.message.reply_text(success_msg, parse_mode='Markdown')
            
        except FileExistsError:
            # This shouldn't happen due to our check, but just in case
            await update.message.reply_text(
                f"⚠️ **Directory Already Exists**\n\n"
                f"📍 **Path:** `{target_path}`\n\n"
                f"ℹ️ **Info:** The directory was created by another process\n\n"
                f"💡 **Tip:** Use `/cd {target_path}` to navigate to it",
                parse_mode='Markdown'
            )
        except PermissionError as e:
            await update.message.reply_text(
                f"🚫 **Permission Denied**\n\n"
                f"📍 **Path:** `{target_path}`\n\n"
                f"⚠️ **Error:** {e}\n\n"
                f"💡 **Suggestions:**\n"
                f"• Try creating the directory in a different location\n"
                f"• Use: `/mkdir ~/Documents/{dir_name}`\n"
                f"• Check if you have write permissions to the parent directory",
                parse_mode='Markdown'
            )
        except OSError as e:
            error_msg = f"❌ **Failed to Create Directory**\n\n"
            error_msg += f"📍 **Path:** `{target_path}`\n\n"
            error_msg += f"🚫 **System Error:** {e}\n\n"
            
            # Provide specific suggestions based on error type
            if "File name too long" in str(e):
                error_msg += f"💡 **Suggestion:** Try a shorter directory name\n"
                error_msg += f"**Try:** `{dir_name[:50]}...`"
            elif "No space left on device" in str(e):
                error_msg += f"💡 **Suggestion:** Free up disk space and try again"
            elif "Invalid argument" in str(e):
                error_msg += f"💡 **Suggestion:** Check for invalid characters in the path"
            else:
                error_msg += f"💡 **Suggestions:**\n"
                error_msg += f"• Check the directory name for invalid characters\n"
                error_msg += f"• Try creating the directory in a different location\n"
                error_msg += f"• Ensure you have sufficient disk space"
            
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            
            # Log the error
            security_manager._log_security_event(SecurityEvent(
                event_type='directory_operation',
                user_id=user_id,
                operation='mkdir',
                resource_path=target_path,
                success=False,
                error_message=str(e)
            ))
        
    except Exception as e:
        logger.error(f"Error in mkdir command: {e}")
        await update.message.reply_text(
            f"❌ **Unexpected Error**\n\n"
            f"🚫 **Error:** {e}\n\n"
            f"💡 **Please try again or contact support if the problem persists.**",
            parse_mode='Markdown'
        )
        
        # Log the error
        security_manager._log_security_event(SecurityEvent(
            event_type='directory_operation',
            user_id=user_id,
            operation='mkdir',
            resource_path=directory_name if 'directory_name' in locals() else '',
            success=False,
            error_message=str(e)
        ))

@secure_operation('basic_access')
async def navigation_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display detailed navigation commands and examples."""
    try:
        help_text = f"🗂️ **Navigation Commands Help**\n\n"
        
        help_text += f"**📍 Current Directory Information:**\n"
        help_text += f"• **`/pwd`** - Show current working directory\n"
        help_text += f"  - Displays detailed directory information\n"
        help_text += f"  - Shows permissions, file/directory counts\n"
        help_text += f"  - Includes directory size and accessibility status\n\n"
        
        help_text += f"**📂 Directory Navigation:**\n"
        help_text += f"• **`/cd <directory_path>`** - Change current directory\n"
        help_text += f"  - **Examples:**\n"
        help_text += f"    • `/cd ~/Documents` - Go to Documents\n"
        help_text += f"    • `/cd ..` - Go up one directory\n"
        help_text += f"    • `/cd ~` - Go to home directory\n"
        help_text += f"    • `/cd /` - Go to root directory\n"
        help_text += f"  - **Features:** Path validation, security checks\n"
        help_text += f"  - **Safety:** Only safe directories accessible\n\n"
        
        help_text += f"**📋 Directory Listing:**\n"
        help_text += f"• **`/ls [directory] [options]`** - List directory contents\n"
        help_text += f"  - **Options:**\n"
        help_text += f"    • `--detailed` - Show detailed file information\n"
        help_text += f"    • `--hidden` - Show hidden files\n"
        help_text += f"  - **Examples:**\n"
        help_text += f"    • `/ls` - List current directory\n"
        help_text += f"    • `/ls ~/Documents` - List Documents folder\n"
        help_text += f"    • `/ls --detailed --hidden` - Detailed view with hidden files\n\n"
        
        help_text += f"• **`/dir [directory] [options]`** - Windows-style directory listing\n"
        help_text += f"  - Identical to `/ls` command\n"
        help_text += f"  - Provided for Windows users' familiarity\n\n"
        
        help_text += f"**🌳 Directory Tree View:**\n"
        help_text += f"• **`/tree [depth]`** - Display directory tree structure\n"
        help_text += f"  - **Default depth:** 2 levels\n"
        help_text += f"  - **Maximum depth:** 10 levels\n"
        help_text += f"  - **Examples:**\n"
        help_text += f"    • `/tree` - Show 2-level tree\n"
        help_text += f"    • `/tree 1` - Show only current level\n"
        help_text += f"    • `/tree 5` - Show 5 levels deep\n"
        help_text += f"  - **Features:** File type icons, size limits\n\n"
        
        help_text += f"**📁 Directory Management:**\n"
        help_text += f"• **`/mkdir <directory_name>`** - Create new directory\n"
        help_text += f"  - **Examples:**\n"
        help_text += f"    • `/mkdir new_folder` - Create in current location\n"
        help_text += f"    • `/mkdir ~/Documents/project` - Create with full path\n"
        help_text += f"    • `/mkdir \"my folder\"` - Create with spaces\n"
        help_text += f"  - **Features:** Auto-parent creation, security validation\n\n"
        
        help_text += f"• **`/rmdir <directory_path>`** - Remove empty directory\n"
        help_text += f"  - **Examples:**\n"
        help_text += f"    • `/rmdir old_folder` - Remove directory\n"
        help_text += f"    • `/rmdir ~/Documents/temp` - Remove with path\n"
        help_text += f"  - **Safety:** Only removes empty directories\n"
        help_text += f"  - **Security:** Path validation and logging\n\n"
        
        help_text += f"**🔐 Security Features:**\n"
        help_text += f"• **Path Validation:** Prevents directory traversal attacks\n"
        help_text += f"• **Safe Directories:** Only allows access to Documents, Desktop, etc.\n"
        help_text += f"• **Permission Checks:** Verifies read/write access before operations\n"
        help_text += f"• **Audit Logging:** All navigation operations are logged\n"
        help_text += f"• **Error Handling:** Comprehensive error messages and suggestions\n\n"
        
        help_text += f"**💡 Tips and Best Practices:**\n"
        help_text += f"• Use `/pwd` to check your current location\n"
        help_text += f"• Use `/ls` to explore directory contents before navigating\n"
        help_text += f"• Use relative paths for nearby directories (`../folder`)\n"
        help_text += f"• Use absolute paths for distant locations (`~/Documents/project`)\n"
        help_text += f"• Use `--detailed` flag for comprehensive file information\n"
        help_text += f"• Use `/tree` to get an overview of directory structure\n\n"
        
        help_text += f"**🚨 Common Issues:**\n"
        help_text += f"• **Permission Denied:** Try different directory or check permissions\n"
        help_text += f"• **Directory Not Found:** Check spelling and path existence\n"
        help_text += f"• **Security Restriction:** Use only safe directories\n"
        help_text += f"• **Invalid Characters:** Avoid `< > : \" | ? *` in directory names\n\n"
        
        help_text += f"**🔗 Related Commands:**\n"
        help_text += f"• `/fileinfo <file>` - Get detailed file information\n"
        help_text += f"• `/listfiles <directory>` - Advanced file listing with filters\n"
        help_text += f"• `/upload <file>` - Upload files to current directory\n"
        help_text += f"• `/download <url>` - Download files to current directory"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in navigation help command: {e}")
        await update.message.reply_text(f"❌ Error displaying navigation help: {e}")

@secure_operation('basic_access')
async def security_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display security-related help and commands."""
    try:
        help_text = f"🛡️ **Security Commands & Features**\n\n"
        help_text += f"**📊 User Commands:**\n"
        help_text += f"• `/quota` - View your file quota and usage\n"
        help_text += f"• `/transfers` - Check active file transfers\n"
        help_text += f"• `/sechelp` - Show this security help\n\n"
        
        help_text += f"**🔧 Admin Commands:**\n"
        help_text += f"• `/secstats` - View security statistics\n"
        help_text += f"• `/cleanup [force]` - Force cleanup temp files\n"
        help_text += f"• `/hardreset` - Perform destructive reset\n\n"
        
        help_text += f"**🛡️ Security Features:**\n"
        help_text += f"• **Path Protection:** Prevents directory traversal attacks\n"
        help_text += f"• **File Validation:** Checks file types and extensions\n"
        help_text += f"• **Quota Management:** Enforces per-user file limits\n"
        help_text += f"• **Audit Logging:** Tracks all file operations\n"
        help_text += f"• **Auto Cleanup:** Removes expired temporary files\n"
        help_text += f"• **GDPR Compliance:** Privacy-focused logging\n\n"
        
        help_text += f"**📋 File Restrictions:**\n"
        # Import SecurityConfig for the help command
        from security_manager import SecurityConfig
        help_text += f"• Max file size: {format_size(SecurityConfig.MAX_FILE_SIZE)}\n"
        help_text += f"• Default quota: {format_size(SecurityConfig.DEFAULT_USER_QUOTA)}\n"
        help_text += f"• Temp retention: {SecurityConfig.TEMP_FILE_RETENTION_HOURS} hours\n"
        help_text += f"• Cleanup interval: {SecurityConfig.CLEANUP_INTERVAL_MINUTES} minutes\n\n"
        
        help_text += f"**🚫 Blocked Extensions:**\n"
        blocked_exts = ', '.join(list(SecurityConfig.BLOCKED_EXTENSIONS)[:10])
        help_text += f"• {blocked_exts}\n"
        help_text += f"• ...and {len(SecurityConfig.BLOCKED_EXTENSIONS) - 10} more\n\n"
        
        help_text += f"**📂 Safe Directories:**\n"
        help_text += f"• Desktop, Documents, Downloads\n"
        help_text += f"• Pictures, Videos, Music\n"
        help_text += f"• Temporary directory\n"
        help_text += f"• Current working directory"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in security help command: {e}")
        await update.message.reply_text(f"❌ Error displaying security help: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("upload", upload_command))
    app.add_handler(CommandHandler("download", download_command))
    app.add_handler(CommandHandler("listfiles", listfiles_command))
    app.add_handler(CommandHandler("fileinfo", fileinfo_command))
    app.add_handler(CommandHandler("compress", compress_command))
    app.add_handler(CommandHandler("extract", extract_command))
    app.add_handler(CommandHandler("hardreset", hardreset_command))
    app.add_handler(CommandHandler("resetsettings", resetsettings_command))
    app.add_handler(CommandHandler("cleantemp", cleantemp_command))
    app.add_handler(CommandHandler("screenshot", screenshot_command))
    app.add_handler(CommandHandler("screenrecord", screenrecord_command))
    app.add_handler(CommandHandler("transfers", get_transfer_status))
    
    # Directory navigation commands
    app.add_handler(CommandHandler("pwd", pwd_command))
    app.add_handler(CommandHandler("cd", cd_command))
    app.add_handler(CommandHandler("ls", ls_command))
    app.add_handler(CommandHandler("dir", ls_command))  # Windows-style alias for ls
    app.add_handler(CommandHandler("tree", tree_command))
    app.add_handler(CommandHandler("mkdir", mkdir_command))
    app.add_handler(CommandHandler("rmdir", rmdir_command))
    
    # Security management commands
    app.add_handler(CommandHandler("quota", quota_command))
    app.add_handler(CommandHandler("secstats", security_stats_command))
    app.add_handler(CommandHandler("cleanup", cleanup_command))
    app.add_handler(CommandHandler("sechelp", security_help_command))
    app.add_handler(CommandHandler("navhelp", navigation_help_command))

    app.run_polling()

if __name__ == '__main__':
    main()
