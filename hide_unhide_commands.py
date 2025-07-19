"""
Command Interface Design for /hide and /unhide Commands

This module defines the interface specifications for the hide/unhide functionality
that integrates with the existing PCRst telegram bot command system.
"""

import os
import shutil
import logging
import json
from pathlib import Path
from typing import Optional, Tuple, List
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from security_manager import SecurityManager, secure_operation, security_manager, SecurityEvent
from path_utils import PathUtils
from windows_file_attributes import WindowsFileAttributes, AttributeMethod, set_hidden_attribute, clear_hidden_attribute, is_hidden_attribute

logger = logging.getLogger(__name__)

# Hidden files directory structure
HIDDEN_FILES_DIR = ".hidden_files"
HIDDEN_MAPPING_FILE = ".hidden_mapping.json"

@secure_operation('write')
async def hide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Hide a file or directory by moving it to a hidden location.
    
    Usage: /hide <path>
    
    Features:
    - Supports both files and directories
    - Handles paths with spaces (use quotes if needed)
    - Supports absolute and relative paths
    - Path validation and security checks
    - Preserves original file permissions
    - Maintains mapping for unhiding
    - Provides detailed feedback
    
    Args:
        update: Telegram update object
        context: Command context containing arguments
    
    Security:
        - Path traversal protection
        - Safe directory validation
        - User permission checks
        - Audit logging
    """
    try:
        # Validate command arguments
        if not context.args:
            await update.message.reply_text(
                "📁 **Hide File/Directory**\n\n"
                "**Usage:** `/hide <path>`\n\n"
                "**Examples:**\n"
                "• `/hide document.txt` - Hide file in current directory\n"
                "• `/hide ~/Documents/secret.pdf` - Hide file with full path\n"
                "• `/hide \"my folder\"` - Hide directory with spaces in name\n"
                "• `/hide ../project` - Hide directory using relative path\n"
                "• `/hide /path/to/file` - Hide file using absolute path\n\n"
                "**Features:**\n"
                "• Supports files and directories\n"
                "• Handles paths with spaces\n"
                "• Preserves file permissions\n"
                "• Secure path validation\n"
                "• Reversible with `/unhide`\n\n"
                "**Security:** Only files in safe directories can be hidden",
                parse_mode='Markdown'
            )
            return
        
        user_id = str(update.effective_user.id)
        target_path = ' '.join(context.args)  # Handle spaces in paths
        
        # Process and validate the path
        resolved_path = _resolve_path(target_path, user_id)
        if not resolved_path:
            await update.message.reply_text(
                "❌ **Invalid Path**\n\n"
                f"📍 **Path:** `{target_path}`\n\n"
                "🚫 **Error:** Path could not be resolved or is invalid\n\n"
                "💡 **Suggestions:**\n"
                "• Check the path spelling\n"
                "• Use `/pwd` to see current directory\n"
                "• Use `/ls` to see available files\n"
                "• Ensure the path exists and is accessible",
                parse_mode='Markdown'
            )
            return
        
        # Security validation
        path_valid, path_msg = security_manager.validate_file_path(resolved_path, user_id)
        if not path_valid:
            await update.message.reply_text(
                "❌ **Security Restriction**\n\n"
                f"📍 **Path:** `{resolved_path}`\n\n"
                f"🚫 **Error:** {path_msg}\n\n"
                "💡 **Tip:** Only files in safe directories can be hidden",
                parse_mode='Markdown'
            )
            return
        
        # Check if path exists
        if not os.path.exists(resolved_path):
            await update.message.reply_text(
                "❌ **Path Not Found**\n\n"
                f"📍 **Path:** `{resolved_path}`\n\n"
                "🚫 **Error:** The specified path does not exist\n\n"
                "💡 **Suggestions:**\n"
                "• Check the path spelling\n"
                "• Use `/ls` to see available files\n"
                "• Ensure you have access to the location",
                parse_mode='Markdown'
            )
            return
        
        # Check if already hidden
        if _is_already_hidden(resolved_path, user_id):
            await update.message.reply_text(
                "⚠️ **Already Hidden**\n\n"
                f"📍 **Path:** `{resolved_path}`\n\n"
                "🔒 **Status:** This file/directory is already hidden\n\n"
                "💡 **Tip:** Use `/unhide <path>` to make it visible again",
                parse_mode='Markdown'
            )
            return
        
        # Perform the hide operation
        await update.message.reply_text("🔄 Hiding file/directory...")
        
        success, message, hidden_info = await _hide_item(resolved_path, user_id)
        
        if success:
            item_type = "📁 Directory" if hidden_info['is_directory'] else "📄 File"
            await update.message.reply_text(
                f"✅ **Successfully Hidden!**\n\n"
                f"📍 **Original Path:** `{resolved_path}`\n"
                f"🎯 **Type:** {item_type}\n"
                f"📊 **Size:** {hidden_info['size_formatted']}\n"
                f"🔒 **Status:** Hidden from normal view\n\n"
                f"💡 **To unhide:** `/unhide {os.path.basename(resolved_path)}`\n"
                f"🛡️ **Security:** Operation logged for audit",
                parse_mode='Markdown'
            )
            
            # Log the operation
            security_manager._log_security_event(SecurityEvent(
                event_type='file_operation',
                user_id=user_id,
                operation='hide',
                resource_path=resolved_path,
                success=True
            ))
        else:
            await update.message.reply_text(
                f"❌ **Hide Operation Failed**\n\n"
                f"📍 **Path:** `{resolved_path}`\n\n"
                f"🚫 **Error:** {message}\n\n"
                "💡 **Suggestions:**\n"
                "• Check file permissions\n"
                "• Ensure sufficient disk space\n"
                "• Try again or contact support",
                parse_mode='Markdown'
            )
            
            # Log the error
            security_manager._log_security_event(SecurityEvent(
                event_type='file_operation',
                user_id=user_id,
                operation='hide',
                resource_path=resolved_path,
                success=False,
                error_message=message
            ))
    
    except Exception as e:
        logger.error(f"Error in hide command: {e}")
        await update.message.reply_text(
            f"❌ **Unexpected Error**\n\n"
            f"📝 **Error:** {str(e)}\n\n"
            "💡 **Suggestions:**\n"
            "• Try again in a few moments\n"
            "• Check if the file is in use\n"
            "• Contact support if issue persists",
            parse_mode='Markdown'
        )


@secure_operation('write')
async def unhide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Unhide a previously hidden file or directory.
    
    Usage: /unhide <path>
    
    Features:
    - Restores files and directories to original location
    - Handles paths with spaces (use quotes if needed)
    - Supports absolute and relative paths for target location
    - Path validation and security checks
    - Preserves original file permissions
    - Provides detailed feedback
    
    Args:
        update: Telegram update object
        context: Command context containing arguments
    
    Security:
        - Path traversal protection
        - Safe directory validation
        - User permission checks
        - Audit logging
    """
    try:
        # Validate command arguments
        if not context.args:
            await update.message.reply_text(
                "📁 **Unhide File/Directory**\n\n"
                "**Usage:** `/unhide <path>`\n\n"
                "**Examples:**\n"
                "• `/unhide document.txt` - Unhide file by original name\n"
                "• `/unhide \"my folder\"` - Unhide directory with spaces\n"
                "• `/unhide secret.pdf` - Unhide file to original location\n\n"
                "**Features:**\n"
                "• Restores to original location\n"
                "• Handles paths with spaces\n"
                "• Preserves file permissions\n"
                "• Secure path validation\n"
                "• Shows restoration details\n\n"
                "**Note:** You can only unhide files you previously hid\n"
                "**Tip:** Use `/hidden` to see list of hidden files",
                parse_mode='Markdown'
            )
            return
        
        user_id = str(update.effective_user.id)
        target_identifier = ' '.join(context.args)  # Handle spaces in paths
        
        # Check if user has any hidden files
        hidden_items = await _get_hidden_items(user_id)
        if not hidden_items:
            await update.message.reply_text(
                "ℹ️ **No Hidden Files**\n\n"
                "📂 **Status:** You don't have any hidden files or directories\n\n"
                "💡 **Tip:** Use `/hide <path>` to hide files first",
                parse_mode='Markdown'
            )
            return
        
        # Find the item to unhide
        item_to_unhide = _find_hidden_item(target_identifier, hidden_items)
        if not item_to_unhide:
            await update.message.reply_text(
                "❌ **Hidden Item Not Found**\n\n"
                f"📍 **Searched for:** `{target_identifier}`\n\n"
                "🚫 **Error:** No matching hidden file or directory found\n\n"
                "💡 **Suggestions:**\n"
                "• Check the spelling of the file/directory name\n"
                "• Use `/hidden` to see all hidden items\n"
                "• Try using the exact original name",
                parse_mode='Markdown'
            )
            return
        
        # Validate destination path
        original_path = item_to_unhide['original_path']
        path_valid, path_msg = security_manager.validate_file_path(original_path, user_id)
        if not path_valid:
            await update.message.reply_text(
                "❌ **Security Restriction**\n\n"
                f"📍 **Original Path:** `{original_path}`\n\n"
                f"🚫 **Error:** {path_msg}\n\n"
                "💡 **Note:** Cannot unhide to restricted location",
                parse_mode='Markdown'
            )
            return
        
        # Check if destination already exists
        if os.path.exists(original_path):
            await update.message.reply_text(
                "⚠️ **Destination Exists**\n\n"
                f"📍 **Path:** `{original_path}`\n\n"
                "🚫 **Error:** A file or directory already exists at the original location\n\n"
                "💡 **Options:**\n"
                "• Remove or rename the existing item first\n"
                "• The hidden item will remain hidden until resolved",
                parse_mode='Markdown'
            )
            return
        
        # Perform the unhide operation
        await update.message.reply_text("🔄 Restoring file/directory...")
        
        success, message, restored_info = await _unhide_item(item_to_unhide, user_id)
        
        if success:
            item_type = "📁 Directory" if restored_info['is_directory'] else "📄 File"
            await update.message.reply_text(
                f"✅ **Successfully Restored!**\n\n"
                f"📍 **Restored to:** `{original_path}`\n"
                f"🎯 **Type:** {item_type}\n"
                f"📊 **Size:** {restored_info['size_formatted']}\n"
                f"🔓 **Status:** Visible in normal view\n\n"
                f"💡 **Tip:** Use `/ls` to see the restored item\n"
                f"🛡️ **Security:** Operation logged for audit",
                parse_mode='Markdown'
            )
            
            # Log the operation
            security_manager._log_security_event(SecurityEvent(
                event_type='file_operation',
                user_id=user_id,
                operation='unhide',
                resource_path=original_path,
                success=True
            ))
        else:
            await update.message.reply_text(
                f"❌ **Unhide Operation Failed**\n\n"
                f"📍 **Item:** `{target_identifier}`\n\n"
                f"🚫 **Error:** {message}\n\n"
                "💡 **Suggestions:**\n"
                "• Check destination directory permissions\n"
                "• Ensure sufficient disk space\n"
                "• Try again or contact support",
                parse_mode='Markdown'
            )
            
            # Log the error
            security_manager._log_security_event(SecurityEvent(
                event_type='file_operation',
                user_id=user_id,
                operation='unhide',
                resource_path=original_path,
                success=False,
                error_message=message
            ))
    
    except Exception as e:
        logger.error(f"Error in unhide command: {e}")
        await update.message.reply_text(
            f"❌ **Unexpected Error**\n\n"
            f"📝 **Error:** {str(e)}\n\n"
            "💡 **Suggestions:**\n"
            "• Try again in a few moments\n"
            "• Check if the destination is accessible\n"
            "• Contact support if issue persists",
            parse_mode='Markdown'
        )


@secure_operation('read')
async def hidden_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    List all hidden files and directories for the user.
    
    Usage: /hidden
    
    Features:
    - Shows all hidden items with details
    - Displays original paths and sizes
    - Provides unhide instructions
    - Secure listing with validation
    """
    try:
        user_id = str(update.effective_user.id)
        
        # Get all hidden items for the user
        hidden_items = await _get_hidden_items(user_id)
        
        if not hidden_items:
            await update.message.reply_text(
                "ℹ️ **No Hidden Files**\n\n"
                "📂 **Status:** You don't have any hidden files or directories\n\n"
                "💡 **Tip:** Use `/hide <path>` to hide files or directories",
                parse_mode='Markdown'
            )
            return
        
        # Format the hidden items list
        hidden_text = f"🔒 **Hidden Files & Directories** ({len(hidden_items)} items)\n\n"
        
        total_size = 0
        for item in hidden_items:
            item_type = "📁" if item['is_directory'] else "📄"
            item_name = os.path.basename(item['original_path'])
            
            hidden_text += f"{item_type} `{item_name}`\n"
            hidden_text += f"   📍 Original: `{item['original_path']}`\n"
            hidden_text += f"   📊 Size: {item['size_formatted']}\n"
            hidden_text += f"   📅 Hidden: {item['hidden_date']}\n\n"
            
            total_size += item['size']
        
        hidden_text += f"📊 **Total Size:** {format_size(total_size)}\n\n"
        hidden_text += f"💡 **To unhide:** `/unhide <filename>`\n"
        hidden_text += f"🛡️ **Security:** Hidden items are secure and private"
        
        await update.message.reply_text(hidden_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in hidden command: {e}")
        await update.message.reply_text(
            f"❌ **Error listing hidden items**\n\n"
            f"📝 **Error:** {str(e)}\n\n"
            "💡 **Tip:** Try again or contact support",
            parse_mode='Markdown'
        )


# Helper functions (implementation details)
def _resolve_path(path: str, user_id: str) -> Optional[str]:
    """
    Securely resolve a path to its absolute form with comprehensive validation.
    
    Handles:
    - Relative paths
    - Absolute paths
    - User home directory expansion (~)
    - Path normalization
    - Security validation
    """
    try:
        from path_utils import PathUtils
        path_utils = PathUtils(security_manager)
        
        # Use PathUtils for secure path resolution
        success, resolved_path = path_utils.resolve_path(user_id, path)
        if not success:
            logger.warning(f"Path resolution failed for user {user_id}: {resolved_path}")
            return None
        
        return resolved_path
    except Exception as e:
        logger.error(f"Error resolving path for user {user_id}: {e}")
        # Fallback to basic path resolution
        try:
            user_dir = security_manager.get_user_directory(user_id)
            if os.path.isabs(path):
                return os.path.normpath(path)
            else:
                return os.path.normpath(os.path.join(user_dir, path))
        except Exception as fallback_error:
            logger.error(f"Fallback path resolution failed: {fallback_error}")
            return None


@secure_operation('read')
def _is_already_hidden(path: str, user_id: str) -> bool:
    """
    Securely check if a path is already hidden.
    """
    try:
        if not os.path.exists(HIDDEN_MAPPING_FILE):
            return False
        
        with open(HIDDEN_MAPPING_FILE, 'r') as f:
            hidden_map = json.load(f)
        
        return path in hidden_map
    except Exception as e:
        logger.error(f"Error checking hidden status for {path}: {e}")
        return False


@secure_operation('write')
async def _hide_item(path: str, user_id: str) -> Tuple[bool, str, dict]:
    """
    Securely hide an item by setting its hidden attribute.
    
    Returns:
        (success, message, item_info)
    """
    try:
        path_utils = PathUtils(security_manager)
        
        # Validate path exists and is accessible
        if not os.path.exists(path):
            return False, "Path does not exist", {}
        
        # Validate path is within allowed directories
        is_valid, validation_msg = path_utils.validate_path(user_id, path)
        if not is_valid:
            return False, f"Path validation failed: {validation_msg}", {}
        
        # Check if file matches safe patterns
        path_info = path_utils.get_path_info(path)
        if 'error' in path_info:
            return False, f"Path analysis failed: {path_info['error']}", {}
        
        # Set hidden attribute using Windows file attributes
        success, msg = set_hidden_attribute(path)
        if not success:
            return False, f"Failed to set hidden attribute: {msg}", {}
        
        # Create item info
        hidden_info = {
            'original_path': path,
            'is_directory': path_info['is_dir'] if path_info['is_dir'] is not None else os.path.isdir(path),
            'size': os.path.getsize(path) if os.path.isfile(path) else 0,
            'size_formatted': format_size(os.path.getsize(path) if os.path.isfile(path) else 0),
            'hidden_date': datetime.now().isoformat(),
            'user_id': user_id
        }
        
        # Update hidden mapping file
        mapping_file = os.path.join(security_manager.get_user_directory(user_id), HIDDEN_MAPPING_FILE)
        hidden_map = {}
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r') as f:
                    hidden_map = json.load(f)
            except (json.JSONDecodeError, IOError):
                hidden_map = {}
        
        hidden_map[path] = hidden_info
        try:
            with open(mapping_file, 'w') as f:
                json.dump(hidden_map, f, indent=2)
        except IOError as e:
            # Revert hidden attribute if mapping fails
            clear_hidden_attribute(path)
            return False, f"Failed to update mapping file: {e}", {}
        
        return True, "Item successfully hidden", hidden_info
        
    except Exception as e:
        logger.error(f"Error hiding item {path}: {e}")
        return False, f"Unexpected error: {e}", {}


@secure_operation('write')
async def _unhide_item(item_info: dict, user_id: str) -> Tuple[bool, str, dict]:
    """
    Securely unhide an item by clearing its hidden attribute.
    
    Returns:
        (success, message, item_info)
    """
    try:
        path = item_info['original_path']
        
        # Validate path exists and is accessible
        if not os.path.exists(path):
            return False, "Path does not exist", {}
        
        # Validate path is within allowed directories
        path_utils = PathUtils(security_manager)
        is_valid, validation_msg = path_utils.validate_path(user_id, path)
        if not is_valid:
            return False, f"Path validation failed: {validation_msg}", {}
        
        # Clear hidden attribute using Windows file attributes
        success, msg = clear_hidden_attribute(path)
        if not success:
            return False, f"Failed to clear hidden attribute: {msg}", {}
        
        # Update mapping file (remove entry)
        mapping_file = os.path.join(security_manager.get_user_directory(user_id), HIDDEN_MAPPING_FILE)
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, 'r') as f:
                    hidden_map = json.load(f)
                
                if path in hidden_map:
                    del hidden_map[path]
                    
                with open(mapping_file, 'w') as f:
                    json.dump(hidden_map, f, indent=2)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to update mapping file after unhiding: {e}")
                # Continue anyway since the main operation succeeded
        
        # Update item info for response
        restored_info = item_info.copy()
        restored_info['unhidden_date'] = datetime.now().isoformat()
        
        return True, "Item successfully unhidden", restored_info
        
    except Exception as e:
        logger.error(f"Error unhiding item {item_info.get('original_path', 'unknown')}: {e}")
        return False, f"Unexpected error: {e}", {}


@secure_operation('read')
async def _get_hidden_items(user_id: str) -> List[dict]:
    """
    Get all hidden items for a user.
    """
    try:
        mapping_file = os.path.join(security_manager.get_user_directory(user_id), HIDDEN_MAPPING_FILE)
        if not os.path.exists(mapping_file):
            return []
        
        with open(mapping_file, 'r') as f:
            hidden_map = json.load(f)
        
        # Filter out items that no longer exist or are not actually hidden
        valid_items = []
        updated_map = {}
        
        for path, item_info in hidden_map.items():
            if os.path.exists(path):
                # Verify the item is actually hidden (has hidden attribute)
                if is_hidden_attribute(path):
                    valid_items.append(item_info)
                    updated_map[path] = item_info
                else:
                    # Item exists but is not hidden, remove from mapping
                    logger.info(f"Removing non-hidden item from mapping: {path}")
            else:
                # Item no longer exists, remove from mapping
                logger.info(f"Removing non-existent item from mapping: {path}")
        
        # Update mapping file if there were changes
        if len(updated_map) != len(hidden_map):
            try:
                with open(mapping_file, 'w') as f:
                    json.dump(updated_map, f, indent=2)
            except IOError as e:
                logger.warning(f"Failed to update mapping file: {e}")
        
        return valid_items
        
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error reading hidden items for user {user_id}: {e}")
        return []


@secure_operation('read')
def _find_hidden_item(identifier: str, hidden_items: List[dict]) -> Optional[dict]:
    """
    Find a hidden item by name or path.
    """
    if not hidden_items:
        return None
    
    # Try exact path match first
    for item in hidden_items:
        if item['original_path'] == identifier:
            return item
    
    # Try exact filename match
    for item in hidden_items:
        if os.path.basename(item['original_path']) == identifier:
            return item
    
    # Try case-insensitive filename match
    identifier_lower = identifier.lower()
    for item in hidden_items:
        if os.path.basename(item['original_path']).lower() == identifier_lower:
            return item
    
    # Try partial filename match
    for item in hidden_items:
        filename = os.path.basename(item['original_path'])
        if identifier_lower in filename.lower():
            return item
    
    return None


def format_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


# Command Registration Information
COMMAND_HANDLERS = [
    {
        'command': 'hide',
        'handler': hide_command,
        'description': 'Hide a file or directory from normal view'
    },
    {
        'command': 'unhide', 
        'handler': unhide_command,
        'description': 'Restore a hidden file or directory to its original location'
    },
    {
        'command': 'hidden',
        'handler': hidden_command,
        'description': 'List all hidden files and directories'
    }
]

# Usage Examples for Help System
USAGE_EXAMPLES = {
    'hide': [
        '/hide document.txt',
        '/hide ~/Documents/secret.pdf',
        '/hide "my folder"',
        '/hide ../project',
        '/hide /path/to/file'
    ],
    'unhide': [
        '/unhide document.txt',
        '/unhide "my folder"',
        '/unhide secret.pdf'
    ],
    'hidden': [
        '/hidden'
    ]
}
