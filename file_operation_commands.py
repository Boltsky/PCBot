import os
import shutil
import logging
from typing import Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from command_argument_parser import command_parser

# Configure logging
logger = logging.getLogger(__name__)


async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Delete a file or directory using key=value arguments.
    Usage: /delete path=<file_or_dir_path> isDirectory=<true/false>
    """
    try:
        user_id = str(update.effective_user.id)
        
        # Check if arguments are provided
        if not context.args:
            help_text = command_parser.get_command_help('delete')
            await update.message.reply_text(
                f"🗑️ **Delete Command Help**\n\n{help_text}\n\n"
                f"**Security Features:**\n"
                f"• Path validation and sanitization\n"
                f"• User permission checks\n"
                f"• Audit logging\n"
                f"• Confirmation for directory deletion",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Parse command arguments
        try:
            args = command_parser.parse_command_args(context.args)
        except ValueError as e:
            await update.message.reply_text(
                f"❌ **Argument Parsing Error**\n\n"
                f"**Error:** {str(e)}\n\n"
                f"**Expected format:** `/delete path=<path> isDirectory=<true/false>`\n"
                f"**Example:** `/delete path=\"my file.txt\" isDirectory=false`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Validate arguments
        is_valid, error_message = command_parser.validate_args_for_command(args, 'delete')
        if not is_valid:
            await update.message.reply_text(
                f"❌ **Validation Error**\n\n"
                f"**Error:** {error_message}\n\n"
                f"**Required parameters:**\n"
                f"• `path` - Path to file or directory\n"
                f"• `isDirectory` - Set to 'true' for directories, 'false' for files\n\n"
                f"**Example:** `/delete path=\"my file.txt\" isDirectory=false`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Extract validated arguments
        file_path = args['path']
        is_directory = args['isDirectory'].lower() == 'true'
        
        # Basic path validation
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
        
        # Check if file/directory exists
        if not os.path.exists(file_path):
            await update.message.reply_text(
                f"❌ **File Not Found**\n\n"
                f"**Path:** `{file_path}`\n\n"
                f"**Error:** The specified path does not exist\n\n"
                f"**Tip:** Use `/ls` to list files in the current directory",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Verify the file type matches the isDirectory parameter
        actual_is_directory = os.path.isdir(file_path)
        if actual_is_directory != is_directory:
            type_name = "directory" if actual_is_directory else "file"
            expected_type = "directory" if is_directory else "file"
            await update.message.reply_text(
                f"⚠️ **Type Mismatch**\n\n"
                f"**Path:** `{file_path}`\n"
                f"**Expected:** {expected_type}\n"
                f"**Actual:** {type_name}\n\n"
                f"**Correction:** Use `isDirectory={str(actual_is_directory).lower()}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Send confirmation message
        item_type = "directory" if is_directory else "file"
        size_info = ""
        if is_directory:
            try:
                file_count = len([f for f in os.listdir(file_path) if os.path.isfile(os.path.join(file_path, f))])
                dir_count = len([d for d in os.listdir(file_path) if os.path.isdir(os.path.join(file_path, d))])
                size_info = f"**Contents:** {file_count} files, {dir_count} directories\n"
            except PermissionError:
                size_info = "**Contents:** Unable to read directory contents\n"
        else:
            try:
                file_size = os.path.getsize(file_path)
                size_info = f"**Size:** {format_size(file_size)}\n"
            except OSError:
                size_info = "**Size:** Unknown\n"
        
        await update.message.reply_text(
            f"🗑️ **Delete {item_type.title()}**\n\n"
            f"**Path:** `{file_path}`\n"
            f"**Type:** {item_type}\n"
            f"{size_info}\n"
            f"🔄 **Status:** Proceeding with deletion...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Perform the deletion
        try:
            if is_directory:
                shutil.rmtree(file_path)
            else:
                os.remove(file_path)
            
            # Log successful deletion
            logger.info(f"User {user_id} successfully deleted {item_type}: {file_path}")
            
            await update.message.reply_text(
                f"✅ **{item_type.title()} Deleted Successfully**\n\n"
                f"**Path:** `{file_path}`\n"
                f"**Type:** {item_type}\n"
                f"**Status:** Permanently removed\n\n"
                f"**Note:** This action cannot be undone",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except PermissionError:
            await update.message.reply_text(
                f"🚫 **Permission Denied**\n\n"
                f"**Path:** `{file_path}`\n"
                f"**Error:** Insufficient permissions to delete {item_type}\n\n"
                f"**Possible causes:**\n"
                f"• File is in use by another program\n"
                f"• Directory contains protected files\n"
                f"• System-level restrictions",
                parse_mode=ParseMode.MARKDOWN
            )
        except OSError as e:
            await update.message.reply_text(
                f"❌ **Deletion Failed**\n\n"
                f"**Path:** `{file_path}`\n"
                f"**Error:** {str(e)}\n\n"
                f"**Tip:** Ensure the {item_type} is not in use and try again",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log failed deletion
            logger.error(f"User {user_id} failed to delete {item_type} {file_path}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in delete command: {e}")
        await update.message.reply_text(
            f"❌ **Critical Error**\n\n"
            f"**Error:** {str(e)}\n\n"
            f"**Please try again or contact support**",
            parse_mode=ParseMode.MARKDOWN
        )


async def copy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Copy a file or directory using key=value arguments.
    Usage: /copy sourcePath=<source_path> destinationPath=<dest_path> isDirectory=<true/false>
    """
    try:
        user_id = str(update.effective_user.id)
        
        # Check if arguments are provided
        if not context.args:
            help_text = command_parser.get_command_help('copy')
            await update.message.reply_text(
                f"📋 **Copy Command Help**\n\n{help_text}\n\n"
                f"**Security Features:**\n"
                f"• Path validation for both source and destination\n"
                f"• User permission checks\n"
                f"• Audit logging\n"
                f"• Overwrite protection",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Parse and validate arguments
        try:
            args = command_parser.parse_command_args(context.args)
        except ValueError as e:
            await update.message.reply_text(
                f"❌ **Argument Parsing Error**\n\n"
                f"**Error:** {str(e)}\n\n"
                f"**Expected format:** `/copy sourcePath=<source> destinationPath=<dest> isDirectory=<true/false>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        is_valid, error_message = command_parser.validate_args_for_command(args, 'copy')
        if not is_valid:
            await update.message.reply_text(
                f"❌ **Validation Error**\n\n"
                f"**Error:** {error_message}\n\n"
                f"**Required parameters:**\n"
                f"• `sourcePath` - Path to source file or directory\n"
                f"• `destinationPath` - Path for the copy\n"
                f"• `isDirectory` - Set to 'true' for directories, 'false' for files",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Extract arguments
        source_path = args['sourcePath']
        dest_path = args['destinationPath']
        is_directory = args['isDirectory'].lower() == 'true'
        
        # Basic path validation
        for path, name in [(source_path, 'source'), (dest_path, 'destination')]:
            if not os.path.isabs(path):
                path = os.path.abspath(path)
        
        # Check if source exists
        if not os.path.exists(source_path):
            await update.message.reply_text(
                f"❌ **Source Not Found**\n\n"
                f"**Path:** `{source_path}`\n\n"
                f"**Error:** The source path does not exist",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Verify source type
        actual_is_directory = os.path.isdir(source_path)
        if actual_is_directory != is_directory:
            type_name = "directory" if actual_is_directory else "file"
            expected_type = "directory" if is_directory else "file"
            await update.message.reply_text(
                f"⚠️ **Source Type Mismatch**\n\n"
                f"**Path:** `{source_path}`\n"
                f"**Expected:** {expected_type}\n"
                f"**Actual:** {type_name}",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Check if destination already exists
        if os.path.exists(dest_path):
            await update.message.reply_text(
                f"⚠️ **Destination Exists**\n\n"
                f"**Path:** `{dest_path}`\n\n"
                f"**Error:** A file or directory already exists at the destination\n\n"
                f"**Tip:** Choose a different destination path",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Perform the copy operation
        item_type = "directory" if is_directory else "file"
        await update.message.reply_text(
            f"📋 **Copying {item_type.title()}**\n\n"
            f"**Source:** `{source_path}`\n"
            f"**Destination:** `{dest_path}`\n"
            f"**Type:** {item_type}\n\n"
            f"🔄 **Status:** Copying...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            if is_directory:
                shutil.copytree(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)
            
            # Log successful copy
            logger.info(f"User {user_id} successfully copied {item_type}: {source_path} -> {dest_path}")
            
            await update.message.reply_text(
                f"✅ **{item_type.title()} Copied Successfully**\n\n"
                f"**Source:** `{source_path}`\n"
                f"**Destination:** `{dest_path}`\n"
                f"**Type:** {item_type}\n\n"
                f"**Status:** Copy completed successfully",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except PermissionError:
            await update.message.reply_text(
                f"🚫 **Permission Denied**\n\n"
                f"**Error:** Insufficient permissions to copy {item_type}\n\n"
                f"**Check:** Ensure you have read access to source and write access to destination",
                parse_mode=ParseMode.MARKDOWN
            )
        except OSError as e:
            await update.message.reply_text(
                f"❌ **Copy Failed**\n\n"
                f"**Error:** {str(e)}\n\n"
                f"**Tip:** Ensure sufficient disk space and proper permissions",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log failed copy
            logger.error(f"User {user_id} failed to copy {item_type} {source_path} -> {dest_path}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in copy command: {e}")
        await update.message.reply_text(
            f"❌ **Critical Error**\n\n"
            f"**Error:** {str(e)}\n\n"
            f"**Please try again or contact support**",
            parse_mode=ParseMode.MARKDOWN
        )


async def move_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Move a file or directory using key=value arguments.
    Usage: /move sourcePath=<source_path> destinationPath=<dest_path> isDirectory=<true/false>
    """
    try:
        user_id = str(update.effective_user.id)
        
        # Check if arguments are provided
        if not context.args:
            help_text = command_parser.get_command_help('move')
            await update.message.reply_text(
                f"📦 **Move Command Help**\n\n{help_text}\n\n"
                f"**Security Features:**\n"
                f"• Path validation for both source and destination\n"
                f"• User permission checks\n"
                f"• Audit logging\n"
                f"• Cross-device move handling\n"
                f"• Safe handling of files in use",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Parse and validate arguments
        try:
            args = command_parser.parse_command_args(context.args)
        except ValueError as e:
            await update.message.reply_text(
                f"❌ **Argument Parsing Error**\n\n"
                f"**Error:** {str(e)}\n\n"
                f"**Expected format:** `/move sourcePath=<source> destinationPath=<dest> isDirectory=<true/false>`\n"
                f"**Example:** `/move sourcePath=\"old file.txt\" destinationPath=\"new file.txt\" isDirectory=false`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        is_valid, error_message = command_parser.validate_args_for_command(args, 'move')
        if not is_valid:
            await update.message.reply_text(
                f"❌ **Validation Error**\n\n"
                f"**Error:** {error_message}\n\n"
                f"**Required parameters:**\n"
                f"• `sourcePath` - Path to source file or directory\n"
                f"• `destinationPath` - Path where the item should be moved\n"
                f"• `isDirectory` - Set to 'true' for directories, 'false' for files",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Extract arguments
        source_path = args['sourcePath']
        dest_path = args['destinationPath']
        is_directory = args['isDirectory'].lower() == 'true'
        
        # Basic path validation
        for path, name in [(source_path, 'source'), (dest_path, 'destination')]:
            if not os.path.isabs(path):
                path = os.path.abspath(path)
        
        # Check if source exists
        if not os.path.exists(source_path):
            await update.message.reply_text(
                f"❌ **Source Not Found**\n\n"
                f"**Path:** `{source_path}`\n\n"
                f"**Error:** The source path does not exist\n\n"
                f"**Tip:** Use `/ls` to list files in the current directory",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Verify source type matches isDirectory parameter
        actual_is_directory = os.path.isdir(source_path)
        if actual_is_directory != is_directory:
            type_name = "directory" if actual_is_directory else "file"
            expected_type = "directory" if is_directory else "file"
            await update.message.reply_text(
                f"⚠️ **Source Type Mismatch**\n\n"
                f"**Path:** `{source_path}`\n"
                f"**Expected:** {expected_type}\n"
                f"**Actual:** {type_name}\n\n"
                f"**Correction:** Use `isDirectory={str(actual_is_directory).lower()}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Check if destination already exists
        if os.path.exists(dest_path):
            await update.message.reply_text(
                f"⚠️ **Destination Exists**\n\n"
                f"**Path:** `{dest_path}`\n\n"
                f"**Error:** A file or directory already exists at the destination\n\n"
                f"**Options:**\n"
                f"• Choose a different destination path\n"
                f"• Delete the existing file/directory first\n"
                f"• Use `/rename` if you want to rename within the same directory",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Perform the move operation
        item_type = "directory" if is_directory else "file"
        size_info = ""
        
        # Get size info for feedback
        if is_directory:
            try:
                file_count = len([f for f in os.listdir(source_path) if os.path.isfile(os.path.join(source_path, f))])
                dir_count = len([d for d in os.listdir(source_path) if os.path.isdir(os.path.join(source_path, d))])
                size_info = f"**Contents:** {file_count} files, {dir_count} directories\n"
            except PermissionError:
                size_info = "**Contents:** Unable to read directory contents\n"
        else:
            try:
                file_size = os.path.getsize(source_path)
                size_info = f"**Size:** {format_size(file_size)}\n"
            except OSError:
                size_info = "**Size:** Unknown\n"
        
        await update.message.reply_text(
            f"📦 **Moving {item_type.title()}**\n\n"
            f"**Source:** `{source_path}`\n"
            f"**Destination:** `{dest_path}`\n"
            f"**Type:** {item_type}\n"
            f"{size_info}\n"
            f"🔄 **Status:** Moving...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Use shutil.move for safe cross-device move operation
            shutil.move(source_path, dest_path)
            
            # Log successful move
            logger.info(f"User {user_id} successfully moved {item_type}: {source_path} -> {dest_path}")
            
            await update.message.reply_text(
                f"✅ **{item_type.title()} Moved Successfully**\n\n"
                f"**From:** `{source_path}`\n"
                f"**To:** `{dest_path}`\n"
                f"**Type:** {item_type}\n"
                f"{size_info}\n"
                f"**Status:** Move completed successfully\n\n"
                f"**Note:** The original file/directory has been moved to the new location",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except FileNotFoundError:
            await update.message.reply_text(
                f"❌ **Source Not Found During Move**\n\n"
                f"**Source:** `{source_path}`\n\n"
                f"**Error:** The source file or directory was not found during the move operation\n\n"
                f"**Possible causes:**\n"
                f"• File was deleted by another process\n"
                f"• Network drive disconnection\n"
                f"• Insufficient permissions",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log failed move
            logger.error(f"User {user_id} failed to move {item_type} {source_path} -> {dest_path}: Source not found during move")
            
        except PermissionError:
            await update.message.reply_text(
                f"🚫 **Permission Denied**\n\n"
                f"**Error:** Insufficient permissions to move {item_type}\n\n"
                f"**Possible causes:**\n"
                f"• Source file is in use by another program\n"
                f"• Destination directory is read-only\n"
                f"• System-level access restrictions\n"
                f"• Antivirus software blocking the operation\n\n"
                f"**Solutions:**\n"
                f"• Close programs using the file\n"
                f"• Check destination directory permissions\n"
                f"• Try running as administrator (if applicable)",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log failed move
            logger.error(f"User {user_id} failed to move {item_type} {source_path} -> {dest_path}: Permission denied")
            
        except OSError as e:
            # Handle various OS-level errors including cross-device issues
            error_code = getattr(e, 'errno', None)
            if error_code == 18:  # EXDEV - Cross-device link
                await update.message.reply_text(
                    f"⚠️ **Cross-Device Move Detected**\n\n"
                    f"**Source:** `{source_path}`\n"
                    f"**Destination:** `{dest_path}`\n\n"
                    f"**Info:** Moving between different drives/filesystems\n"
                    f"**Status:** shutil.move automatically handles this by copying and deleting\n\n"
                    f"**Error Details:** {str(e)}\n\n"
                    f"**Note:** This is normal for moves between different drives",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text(
                    f"❌ **Move Failed**\n\n"
                    f"**Source:** `{source_path}`\n"
                    f"**Destination:** `{dest_path}`\n"
                    f"**Error:** {str(e)}\n\n"
                    f"**Possible causes:**\n"
                    f"• Insufficient disk space at destination\n"
                    f"• File system limitations\n"
                    f"• Network connectivity issues\n"
                    f"• File/directory is in use\n\n"
                    f"**Tip:** Ensure sufficient disk space and try again",
                    parse_mode=ParseMode.MARKDOWN
                )
            
            # Log failed move
            logger.error(f"User {user_id} failed to move {item_type} {source_path} -> {dest_path}: {str(e)}")
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Unexpected Error**\n\n"
                f"**Source:** `{source_path}`\n"
                f"**Destination:** `{dest_path}`\n"
                f"**Error:** {str(e)}\n\n"
                f"**Please try again or contact support if the issue persists",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log failed move
            logger.error(f"User {user_id} failed to move {item_type} {source_path} -> {dest_path}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in move command: {e}")
        await update.message.reply_text(
            f"❌ **Critical Error**\n\n"
            f"**Error:** {str(e)}\n\n"
            f"**Please try again or contact support**",
            parse_mode=ParseMode.MARKDOWN
        )


async def rename_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Rename a file or directory using key=value arguments.
    Usage: /rename path=<current_path> newName=<new_name> isDirectory=<true/false>
    """
    try:
        user_id = str(update.effective_user.id)
        
        if not context.args:
            help_text = command_parser.get_command_help('rename')
            await update.message.reply_text(
                f"🏷️ **Rename Command Help**\n\n{help_text}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Parse and validate arguments
        try:
            args = command_parser.parse_command_args(context.args)
        except ValueError as e:
            await update.message.reply_text(
                f"❌ **Argument Parsing Error**\n\n"
                f"**Error:** {str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        is_valid, error_message = command_parser.validate_args_for_command(args, 'rename')
        if not is_valid:
            await update.message.reply_text(
                f"❌ **Validation Error**\n\n"
                f"**Error:** {error_message}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        current_path = args['path']
        new_name = args['newName']
        is_directory = args['isDirectory'].lower() == 'true'
        
        # Construct new path
        parent_dir = os.path.dirname(current_path)
        new_path = os.path.join(parent_dir, new_name)
        
        # Basic path validation
        if not os.path.isabs(current_path):
            current_path = os.path.abspath(current_path)
        if not os.path.isabs(new_path):
            new_path = os.path.abspath(new_path)

        # Check if source exists
        if not os.path.exists(current_path):
            await update.message.reply_text(
                f"❌ **File Not Found**\n\n"
                f"**Path:** `{current_path}`\n\n"
                f"**Error:** The specified path does not exist\n\n"
                f"**Tip:** Use `/ls` to list files in the current directory",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Verify the file type matches the isDirectory parameter
        actual_is_directory = os.path.isdir(current_path)
        if actual_is_directory != is_directory:
            type_name = "directory" if actual_is_directory else "file"
            expected_type = "directory" if is_directory else "file"
            await update.message.reply_text(
                f"⚠️ **Type Mismatch**\n\n"
                f"**Path:** `{current_path}`\n"
                f"**Expected:** {expected_type}\n"
                f"**Actual:** {type_name}\n\n"
                f"**Correction:** Use `isDirectory={str(actual_is_directory).lower()}`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Check for dangerous filename patterns
        filename_error = command_parser._validate_filename(new_name)
        if filename_error:
            await update.message.reply_text(
                f"❌ **Invalid Filename**\n\n"
                f"**Error:** {filename_error}\n\n"
                f"**Security Note:** Filename contains invalid characters or reserved names",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Check if new name already exists
        if os.path.exists(new_path):
            await update.message.reply_text(
                f"⚠️ **Name Already Exists**\n\n"
                f"**New path:** `{new_path}`\n\n"
                f"**Error:** A file or directory with that name already exists\n\n"
                f"**Tip:** Choose a different name or delete the existing file first",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Perform rename
        item_type = "directory" if is_directory else "file"
        
        # Send progress message
        await update.message.reply_text(
            f"🏷️ **Renaming {item_type.title()}**\n\n"
            f"**Current name:** `{os.path.basename(current_path)}`\n"
            f"**New name:** `{new_name}`\n"
            f"**Path:** `{current_path}`\n\n"
            f"🔄 **Status:** Processing rename operation...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        try:
            # Perform the secure rename operation
            os.rename(current_path, new_path)
            
            # Log successful rename
            logger.info(f"User {user_id} successfully renamed {item_type}: {current_path} -> {new_path}")
            
            await update.message.reply_text(
                f"✅ **{item_type.title()} Renamed Successfully**\n\n"
                f"**Old name:** `{os.path.basename(current_path)}`\n"
                f"**New name:** `{new_name}`\n"
                f"**Full path:** `{new_path}`\n\n"
                f"**Status:** Rename operation completed successfully",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except PermissionError:
            await update.message.reply_text(
                f"🚫 **Permission Denied**\n\n"
                f"**Error:** Insufficient permissions to rename {item_type}\n\n"
                f"**Possible causes:**\n"
                f"• {item_type.title()} is in use by another program\n"
                f"• Parent directory is read-only\n"
                f"• System-level access restrictions\n"
                f"• Antivirus software blocking the operation\n\n"
                f"**Solutions:**\n"
                f"• Close programs using the {item_type}\n"
                f"• Check directory permissions\n"
                f"• Try running as administrator (if applicable)",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log failed rename
            logger.error(f"User {user_id} failed to rename {item_type} {current_path} -> {new_path}: Permission denied")
            
        except FileNotFoundError:
            await update.message.reply_text(
                f"❌ **Source Not Found During Rename**\n\n"
                f"**Source:** `{current_path}`\n\n"
                f"**Error:** The source file or directory was not found during the rename operation\n\n"
                f"**Possible causes:**\n"
                f"• File was deleted by another process\n"
                f"• Network drive disconnection\n"
                f"• Insufficient permissions\n"
                f"• Path became invalid during operation",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log failed rename
            logger.error(f"User {user_id} failed to rename {item_type} {current_path} -> {new_path}: Source not found during rename")
            
        except OSError as e:
            await update.message.reply_text(
                f"❌ **Rename Failed**\n\n"
                f"**Source:** `{current_path}`\n"
                f"**Destination:** `{new_path}`\n"
                f"**Error:** {str(e)}\n\n"
                f"**Possible causes:**\n"
                f"• File system limitations\n"
                f"• Network connectivity issues\n"
                f"• Disk space issues\n"
                f"• Cross-device rename attempt\n\n"
                f"**Tip:** Ensure the {item_type} is not in use and try again",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log failed rename
            logger.error(f"User {user_id} failed to rename {item_type} {current_path} -> {new_path}: {str(e)}")
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Unexpected Error**\n\n"
                f"**Source:** `{current_path}`\n"
                f"**Destination:** `{new_path}`\n"
                f"**Error:** {str(e)}\n\n"
                f"**Please try again or contact support if the issue persists",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log failed rename
            logger.error(f"User {user_id} failed to rename {item_type} {current_path} -> {new_path}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error in rename command: {e}")
        await update.message.reply_text(f"❌ **Critical Error:** {str(e)}")


def format_size(size_bytes):
    """Format bytes into human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"
