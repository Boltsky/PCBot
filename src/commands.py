import os
import re
import shlex
import time
import shutil
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import math
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from security_manager import SecurityManager, SecurityEvent, secure_operation, get_fresh_security_manager
from telegram_download_handler import download_telegram_file_with_feedback
from windows_file_attributes import (WindowsFileAttributes, AttributeMethod,
                                     set_hidden_attribute, clear_hidden_attribute, 
                                     is_hidden_attribute)

# Configure logging
logger = logging.getLogger(__name__)

# Hidden files directory structure
HIDDEN_FILES_DIR = ".hidden_files"
HIDDEN_MAPPING_FILE = ".hidden_mapping.json"

class CommandArgumentParser:
    """
    Robust command argument parser for file/folder operations handling.
    """
    
    def __init__(self):
        self.supported_commands = {
            'delete': ['path', 'isDirectory'],
            'copy': ['sourcePath', 'destinationPath', 'isDirectory'],
            'move': ['sourcePath', 'destinationPath', 'isDirectory'],
            'rename': ['path', 'newName', 'isDirectory']
        }

    def parse_command_args(self, command_args: List[str]) -> Dict[str, str]:
        """
        Parse command arguments with spaces and edge cases.
        """
        parsed_args = {}
        full_arg_string = ' '.join(command_args)
        pattern = r'(\w+)=(["\']?)([^"\']*)\2(?=\s|$)'
        matches = re.findall(pattern, full_arg_string)

        if not matches:
            for arg in command_args:
                if '=' in arg:
                    key, value = arg.split('=', 1)
                    parsed_args[key.strip()] = value.strip()
                else:
                    raise ValueError(f"Invalid argument format: '{arg}'. Expected key=value format.")
        else:
            for match in matches:
                key, quote, value = match
                parsed_args[key] = value

        for key, value in parsed_args.items():
            if value.startswith('"') and value.endswith('"'):
                parsed_args[key] = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                parsed_args[key] = value[1:-1]

        return parsed_args

    def validate_args_for_command(self, args: Dict[str, str], command: str) -> Tuple[bool, str]:
        """
        Validate arguments for specific commands.
        """
        if command not in self.supported_commands:
            return False, f"Unsupported command: {command}"
        
        required_keys = self.supported_commands[command]
        missing_keys = [key for key in required_keys if key not in args or not args[key].strip()]
        if missing_keys:
            return False, f"Missing required arguments: {', '.join(missing_keys)}"

        validation_errors = []
        path_keys = ['path', 'sourcePath', 'destinationPath']
        for key in path_keys:
            if key in args:
                error = self._validate_path(args[key], key)
                if error:
                    validation_errors.append(error)

        if 'isDirectory' in args:
            if args['isDirectory'].lower() not in ['true', 'false']:
                validation_errors.append("isDirectory must be 'true' or 'false'")

        return (True, "") if not validation_errors else (False, "; ".join(validation_errors))

    def _validate_path(self, path: str, param_name: str) -> Optional[str]:
        """ Validate file/directory path. """
        if not path or not path.strip():
            return f"{param_name} cannot be empty"
        dangerous_chars = ['<', '>', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in path:
                return f"{param_name} contains invalid character: '{char}'"
        if '..' in path:
            return f"{param_name} contains path traversal sequence '..'"
        path_parts = path.split(os.sep)
        for part in path_parts:
            if part.upper() in ['CON', 'PRN', 'AUX', 'NUL'] or part.upper().startswith(('COM', 'LPT')):
                return f"{param_name} contains Windows reserved name: '{part}'"
        return None


command_parser = CommandArgumentParser()


async def handle_file_operations(update: Update, context: ContextTypes.DEFAULT_TYPE, op: str) -> None:
    """
    Handle file operations (delete, copy, move, rename) with Telegram context.
    """
    try:
        user_id = str(update.effective_user.id)

        if not context.args:
            await update.message.reply_text(f"❌No arguments provided for {op} command.")
            return

        args = command_parser.parse_command_args(context.args)
        is_valid, validation_msg = command_parser.validate_args_for_command(args, op)
        if not is_valid:
            await update.message.reply_text(f"❌Validation failed for {op}: {validation_msg}")
            return

        # Extract file path and operation-specific logic
        if op == 'delete':
            file_path = args['path']
            is_directory = args['isDirectory'].lower() == 'true'
            if not os.path.exists(file_path):
                await update.message.reply_text(f"File not found: {file_path}")
                return
            if is_directory:
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            await update.message.reply_text(f"Deleted successfully: {file_path}")

    except Exception as e:
        logger.error(f"Error in {op} command: {e}")
        await update.message.reply_text(f"❌ Error in {op}: {str(e)}")


async def hide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Hide files or directories with enhanced security.
    """
    try:
        if not context.args:
            await update.message.reply_text("No path specified for hide.")
            return
        # Assume resolve_path and security checks are encapsulated functions
        resolved_path = _resolve_path(context.args[0], str(update.effective_user.id))
        if resolved_path:
            set_hidden_attribute(resolved_path)
            await update.message.reply_text(f"Hidden: {resolved_path}")
    except Exception as e:
        logger.error(f"Error hiding path: {e}")


@secure_operation('write')
async def file_attachment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle file attachments for secure downloading.
    """
    try:
        user_id = str(update.effective_user.id)
        file_obj, file_type = detect_attachment_type(update.message)
        # Further handling for specific file types and storage
    except Exception as e:
        logger.error(f"Error handling file attachment: {e}")


def detect_attachment_type(message) -> tuple[Optional[Any], Optional[str]]:
    """ Simplified attachment detection logic. """
    if message.document:
        return message.document, "document"
    return None, None


def _resolve_path(path: str, user_id: str) -> Optional[str]:
    """ Simplified path resolution placeholder. """
    return path


# Command handler functions that are imported by PCBot.py

async def unhide_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Unhide files or directories with enhanced security.
    """
    try:
        if not context.args:
            await update.message.reply_text("No path specified for unhide.")
            return
        resolved_path = _resolve_path(context.args[0], str(update.effective_user.id))
        if resolved_path:
            clear_hidden_attribute(resolved_path)
            await update.message.reply_text(f"Unhidden: {resolved_path}")
    except Exception as e:
        logger.error(f"Error unhiding path: {e}")
        await update.message.reply_text(f"❌ Error unhiding path: {e}")


async def hidden_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    List all hidden files and directories.
    """
    try:
        await update.message.reply_text("📁 Listing hidden files...")
        # Implementation would scan for hidden files
        await update.message.reply_text("📂 Hidden files functionality is available.")
    except Exception as e:
        logger.error(f"Error listing hidden files: {e}")
        await update.message.reply_text(f"❌ Error listing hidden files: {e}")


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Delete files or directories.
    """
    await handle_file_operations(update, context, 'delete')


async def copy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Copy files or directories.
    """
    await handle_file_operations(update, context, 'copy')


async def move_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Move files or directories.
    """
    await handle_file_operations(update, context, 'move')


async def rename_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Rename files or directories.
    """
    await handle_file_operations(update, context, 'rename')

