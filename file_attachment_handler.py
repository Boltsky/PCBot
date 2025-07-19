import os
import time
import logging
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from security_manager import SecurityManager, SecurityEvent, secure_operation, get_fresh_security_manager
from telegram_download_handler import download_telegram_file_with_feedback

# Configure logging
logger = logging.getLogger(__name__)

def sanitize_filename(filename: str) -> str:
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

def format_size(size_bytes: int) -> str:
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

def get_file_extension_for_type(file_type: str) -> str:
    """
    Get appropriate file extension for different file types.
    """
    extension_map = {
        'photo': '.jpg',
        'video': '.mp4',
        'audio': '.mp3',
        'voice': '.ogg',
        'video_note': '.mp4',
        'sticker': '.webp',
        'document': ''
    }
    return extension_map.get(file_type, '')

def detect_attachment_type(message) -> tuple[Optional[Any], Optional[str]]:
    """
    Detect the type of attachment and return the file object and type.
    
    Returns:
        tuple: (file_object, file_type) or (None, None) if no attachment found
    """
    if message.document:
        return message.document, "document"
    elif message.photo:
        return message.photo[-1], "photo"  # Get the highest resolution photo
    elif message.video:
        return message.video, "video"
    elif message.audio:
        return message.audio, "audio"
    elif message.voice:
        return message.voice, "voice"
    elif message.video_note:
        return message.video_note, "video_note"
    elif message.sticker:
        return message.sticker, "sticker"
    else:
        return None, None

def generate_unique_filename(destination_dir: str, filename: str) -> str:
    """
    Generate a unique filename if a file with the same name already exists.
    
    Args:
        destination_dir: Directory where the file will be saved
        filename: Original filename
        
    Returns:
        str: Unique filename
    """
    destination_path = os.path.join(destination_dir, filename)
    
    if not os.path.exists(destination_path):
        return filename
    
    # File exists, generate unique name
    counter = 1
    name, ext = os.path.splitext(filename)
    
    while os.path.exists(destination_path):
        new_filename = f"{name}_{counter}{ext}"
        destination_path = os.path.join(destination_dir, new_filename)
        counter += 1
    
    return os.path.basename(destination_path)

@secure_operation('upload')
async def file_attachment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle file attachments sent to the bot.
    This function manages file retrieval and saving when attachments are detected.
    
    Features:
    - Supports multiple file types (documents, photos, videos, audio, etc.)
    - Comprehensive security validation
    - Quota management
    - Progress tracking for large files
    - Error handling and logging
    - Automatic filename sanitization
    - Duplicate filename handling
    
    Args:
        update: Telegram Update object containing the message
        context: Telegram context object
    """
    user_id = str(update.effective_user.id)
    message = update.message
    
    # Use fresh security manager to avoid cached data
    security_manager = get_fresh_security_manager()
    
    try:
        # Step 1: Detect attachment type
        file_obj, file_type = detect_attachment_type(message)
        
        if not file_obj:
            await message.reply_text(
                "❌ **No supported file attachment found**\\n\\n"
                "**Supported file types:**\\n"
                "• Documents (PDF, DOC, TXT, etc.)\\n"
                "• Images (JPG, PNG, GIF, etc.)\\n"
                "• Videos (MP4, AVI, MOV, etc.)\\n"
                "• Audio files (MP3, WAV, etc.)\\n"
                "• Voice messages\\n"
                "• Video notes\\n"
                "• Stickers",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Step 2: Extract file information
        file_size = getattr(file_obj, 'file_size', 0)
        file_name = getattr(file_obj, 'file_name', None)
        file_id = getattr(file_obj, 'file_id', None)
        
        # Generate filename if not provided
        if not file_name:
            file_extension = get_file_extension_for_type(file_type)
            file_name = f"{file_type}_{int(time.time())}{file_extension}"
        
        # Step 3: Sanitize filename for security
        file_name = sanitize_filename(file_name)
        
        # Step 4: Pre-validate upload security (before downloading)
        # We'll do a preliminary check, then final validation after download
        preliminary_valid, preliminary_msg = security_manager.validate_upload_security(
            user_id, os.path.join(security_manager.get_user_directory(user_id), file_name), file_size
        )
        if not preliminary_valid:
            await message.reply_text(
                f"❌ **Upload security validation failed**\\n\\n"
                f"**Error:** {preliminary_msg}\\n\\n"
                f"**Security Check Failed**\\n"
                f"• File size, type, or quota validation failed\\n"
                f"• Use `/quota` to check your usage\\n"
                f"• Ensure file type is supported",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Step 5: Send initial processing message
        status_msg = await message.reply_text(
            f"📥 **Processing {file_type} attachment**\\n\\n"
            f"📄 **Filename:** `{file_name}`\\n"
            f"📁 **Size:** {format_size(file_size)}\\n"
            f"🔄 **Status:** Initializing download...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Step 6: Get destination directory
        current_dir = security_manager.get_user_directory(user_id)
        
        # Step 7: Generate unique filename to avoid conflicts
        unique_filename = generate_unique_filename(current_dir, file_name)
        destination_path = os.path.join(current_dir, unique_filename)
        
        # Step 8: Validate destination path
        path_valid, path_msg = security_manager.validate_file_path(destination_path, user_id)
        if not path_valid:
            await status_msg.edit_text(
                f"❌ **Security validation failed**\\n\\n"
                f"**Error:** {path_msg}\\n\\n"
                f"**This file cannot be saved to the requested location.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Step 9: Download file from Telegram using reliable method
        try:
            telegram_file = await file_obj.get_file()
            
            # Delete the initial status message since download handler will create its own
            await status_msg.delete()
            
            # Use advanced download method with feedback
            download_success = await download_telegram_file_with_feedback(
                update, context, telegram_file, unique_filename, file_size, destination_path
            )
            
            if not download_success:
                raise Exception("Download failed")
                
        except Exception as download_error:
            await update.message.reply_text(
                f"❌ **Download failed**\\n\\n"
                f"**Error:** {str(download_error)}\\n\\n"
                f"**Please try again or contact support if the issue persists.**",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Step 11: Verify file was saved
        if not os.path.exists(destination_path):
            await status_msg.edit_text(
                f"❌ **File save failed**\\n\\n"
                f"**Error:** File could not be saved to disk\\n\\n"
                f"**Possible causes:**\\n"
                f"• Insufficient disk space\\n"
                f"• Permission issues\\n"
                f"• Storage device error",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Step 12: Get actual file size and validate
        actual_size = os.path.getsize(destination_path)
        
        # Step 13: Final comprehensive security validation and quota update
        validation_msg = await update.message.reply_text(
            f"📥 **Processing {file_type} attachment**\\n\\n"
            f"📄 **Filename:** `{unique_filename}`\n"
            f"📁 **Size:** {format_size(actual_size)}\\n"
            f"🔄 **Status:** Validating file security and updating quota...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Use comprehensive security validation and quota management
        upload_success, upload_msg = security_manager.process_file_upload(user_id, destination_path, actual_size)
        if not upload_success:
            # Remove the file if validation fails
            try:
                os.remove(destination_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup invalid file {destination_path}: {cleanup_error}")
            
            await validation_msg.edit_text(
                f"❌ **Upload processing failed**\\n\\n"
                f"**Error:** {upload_msg}\\n\\n"
                f"**Security Check:** Comprehensive validation failed\\n"
                f"**Action:** File has been removed for security",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Step 15: Log successful operation
        security_manager._log_security_event(SecurityEvent(
            event_type='file_upload',
            user_id=user_id,
            operation='attachment_upload',
            resource_path=destination_path,
            success=True,
            metadata={
                'file_type': file_type,
                'file_size': actual_size,
                'original_filename': file_name,
                'saved_filename': unique_filename,
                'file_id': file_id
            }
        ))
        
        # Step 16: Send success message
        await validation_msg.edit_text(
            f"✅ **File saved successfully!**\\n\\n"
            f"📄 **Filename:** `{unique_filename}`\n"
            f"📁 **Size:** {format_size(actual_size)}\\n"
            f"📍 **Location:** `{destination_path}`\\n"
            f"🎯 **Type:** {file_type}\\n"
            f"🔒 **Security:** Validated and safe\\n\\n"
            f"**💡 Next steps:**\\n"
            f"• Use `/fileinfo {destination_path}` for detailed information\\n"
            f"• Use `/ls` to see all files in current directory\\n"
            f"• Use `/quota` to check remaining storage space",
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"File attachment successfully processed: {destination_path} (user: {user_id})")
        
    except Exception as e:
        logger.error(f"Error in file_attachment_handler: {e}")
        
        # Log the error
        security_manager._log_security_event(SecurityEvent(
            event_type='file_upload',
            user_id=user_id,
            operation='attachment_upload',
            resource_path=file_name if 'file_name' in locals() else 'unknown',
            success=False,
            error_message=str(e)
        ))
        
        # Send error message to user
        await message.reply_text(
            f"❌ **Error processing file attachment**\\n\\n"
            f"**Error:** {str(e)}\\n\\n"
            f"**Troubleshooting:**\\n"
            f"• Check if file is not corrupted\\n"
            f"• Verify file size is within limits\\n"
            f"• Ensure file type is supported\\n"
            f"• Try using `/upload` command instead\\n\\n"
            f"**Contact support if the issue persists.**",
            parse_mode=ParseMode.MARKDOWN
        )

# Additional utility functions for the handler

def get_file_info_summary(file_path: str) -> Dict[str, Any]:
    """
    Get a summary of file information.
    
    Args:
        file_path: Path to the file
        
    Returns:
        dict: File information summary
    """
    try:
        stat_info = os.stat(file_path)
        import mimetypes
        mime_type, _ = mimetypes.guess_type(file_path)
        
        return {
            'name': os.path.basename(file_path),
            'size': stat_info.st_size,
            'size_formatted': format_size(stat_info.st_size),
            'mime_type': mime_type or 'unknown',
            'extension': os.path.splitext(file_path)[1].lower(),
            'created': stat_info.st_ctime,
            'modified': stat_info.st_mtime
        }
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        return {}

def cleanup_failed_upload(file_path: str) -> bool:
    """
    Clean up a failed upload file.
    
    Args:
        file_path: Path to the file to clean up
        
    Returns:
        bool: True if cleanup was successful
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up failed upload: {file_path}")
            return True
        return True  # File doesn't exist, consider it cleaned
    except Exception as e:
        logger.error(f"Failed to cleanup file {file_path}: {e}")
        return False

# Export the main handler function
__all__ = ['file_attachment_handler']
