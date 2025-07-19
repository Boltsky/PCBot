import os
import time
import tempfile
import logging
import asyncio
from typing import Optional, Callable, Dict, Any
from telegram import Update, File
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from security_manager import SecurityManager, SecurityEvent, secure_operation
import aiohttp
import aiofiles

# Configure logging
logger = logging.getLogger(__name__)

class DownloadProgress:
    """
    Class to track download progress and provide feedback to users.
    """
    
    def __init__(self, total_size: int, file_name: str, update_interval: int = 5):
        """
        Initialize progress tracker.
        
        Args:
            total_size: Total file size in bytes
            file_name: Name of the file being downloaded
            update_interval: Minimum seconds between progress updates
        """
        self.total_size = total_size
        self.file_name = file_name
        self.downloaded_size = 0
        self.start_time = time.time()
        self.last_update_time = 0
        self.update_interval = update_interval
        self.progress_callback = None
        
    def set_progress_callback(self, callback: Callable):
        """Set callback function for progress updates."""
        self.progress_callback = callback
        
    def update_progress(self, chunk_size: int):
        """
        Update download progress.
        
        Args:
            chunk_size: Size of the downloaded chunk in bytes
        """
        self.downloaded_size += chunk_size
        current_time = time.time()
        
        # Check if we should send an update
        if current_time - self.last_update_time >= self.update_interval:
            self.last_update_time = current_time
            
            if self.progress_callback:
                progress_info = self.get_progress_info()
                asyncio.create_task(self.progress_callback(progress_info))
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Get current progress information."""
        current_time = time.time()
        elapsed_time = current_time - self.start_time
        
        progress_percent = (self.downloaded_size / self.total_size) * 100 if self.total_size > 0 else 0
        download_speed = self.downloaded_size / elapsed_time if elapsed_time > 0 else 0
        
        # Estimate remaining time
        remaining_bytes = self.total_size - self.downloaded_size
        eta_seconds = remaining_bytes / download_speed if download_speed > 0 else 0
        
        return {
            'file_name': self.file_name,
            'downloaded_size': self.downloaded_size,
            'total_size': self.total_size,
            'progress_percent': progress_percent,
            'download_speed': download_speed,
            'eta_seconds': eta_seconds,
            'elapsed_time': elapsed_time
        }

def format_size(size_bytes: int) -> str:
    """Format bytes into human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def format_time(seconds: float) -> str:
    """Format seconds into human readable time format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

async def download_telegram_file_with_progress(
    file_obj: File,
    destination_path: str,
    progress_tracker: DownloadProgress,
    chunk_size: int = 8192
) -> bool:
    """
    Download a Telegram file with progress tracking.
    
    Args:
        file_obj: Telegram File object
        destination_path: Path where the file should be saved
        progress_tracker: Progress tracker instance
        chunk_size: Size of chunks to download (default 8KB)
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    temp_path = destination_path + '.tmp'
    
    try:
        # Get the download URL from the file object
        # The file_path property contains the relative path, we need to construct full URL
        if not hasattr(file_obj, 'file_path') or not file_obj.file_path:
            logger.error("File object does not have a valid file_path")
            return False
            
        # Construct the full download URL
        bot_token = file_obj.get_bot().token
        file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_obj.file_path}"
        
        logger.info(f"Attempting to download from URL: {file_url[:50]}...")
        
        # Create temporary file for safe download
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        # Download file with progress tracking
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    # Get actual file size from headers
                    content_length = response.headers.get('content-length')
                    if content_length:
                        actual_size = int(content_length)
                        if actual_size != progress_tracker.total_size:
                            progress_tracker.total_size = actual_size
                    
                    # Download in chunks with progress updates
                    async with aiofiles.open(temp_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(chunk_size):
                            await f.write(chunk)
                            progress_tracker.update_progress(len(chunk))
                    
                    # Move temporary file to final destination
                    os.rename(temp_path, destination_path)
                    return True
                else:
                    logger.error(f"Failed to download file: HTTP {response.status} - {response.reason}")
                    return False
                    
    except Exception as e:
        logger.error(f"Error downloading file with progress: {e}")
        # Clean up temporary file if it exists
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False

async def download_telegram_file_fallback(
    file_obj: File,
    destination_path: str,
    progress_tracker: DownloadProgress
) -> bool:
    """
    Fallback download method using Telegram's built-in download_to_drive.
    
    Args:
        file_obj: Telegram File object
        destination_path: Path where the file should be saved
        progress_tracker: Progress tracker instance
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    try:
        # Use Telegram's built-in download method
        await file_obj.download_to_drive(destination_path)
        
        # Since we can't track progress with the built-in method,
        # we'll simulate progress updates
        file_size = os.path.getsize(destination_path) if os.path.exists(destination_path) else 0
        
        # Update progress to completion
        progress_tracker.downloaded_size = file_size
        progress_tracker.total_size = file_size
        progress_info = progress_tracker.get_progress_info()
        
        if progress_tracker.progress_callback:
            await progress_tracker.progress_callback(progress_info)
            
        return os.path.exists(destination_path)
        
    except Exception as e:
        logger.error(f"Error in fallback download: {e}")
        return False

@secure_operation('upload')
async def download_telegram_file_with_feedback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    file_obj: File,
    file_name: str,
    file_size: int,
    destination_path: str
) -> bool:
    """
    Download a Telegram file with user progress feedback.
    
    Args:
        update: Telegram Update object
        context: Telegram context object
        file_obj: Telegram File object to download
        file_name: Name of the file being downloaded
        file_size: Size of the file in bytes
        destination_path: Path where the file should be saved
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    user_id = str(update.effective_user.id)
    
    # Create progress tracker
    progress_tracker = DownloadProgress(file_size, file_name, update_interval=3)
    
    # Send initial progress message
    progress_msg = await update.message.reply_text(
        f"📥 **Starting download**\n\n"
        f"📄 **File:** `{file_name}`\n"
        f"📁 **Size:** {format_size(file_size)}\n"
        f"🔄 **Progress:** 0%\n"
        f"⚡ **Speed:** Initializing...\n"
        f"⏱️ **ETA:** Calculating...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Define progress callback function
    async def progress_callback(progress_info: Dict[str, Any]):
        """Update progress message with current download status."""
        try:
            progress_percent = progress_info['progress_percent']
            download_speed = progress_info['download_speed']
            eta_seconds = progress_info['eta_seconds']
            
            # Create progress bar
            progress_bar_length = 20
            filled_length = int(progress_bar_length * progress_percent / 100)
            progress_bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
            
            # Format message
            progress_text = (
                f"📥 **Downloading from Telegram**\n\n"
                f"📄 **File:** `{file_name}`\n"
                f"📁 **Size:** {format_size(progress_info['downloaded_size'])} / {format_size(progress_info['total_size'])}\n"
                f"🔄 **Progress:** {progress_percent:.1f}%\n"
                f"📊 **Bar:** `{progress_bar}`\n"
                f"⚡ **Speed:** {format_size(download_speed)}/s\n"
                f"⏱️ **ETA:** {format_time(eta_seconds) if eta_seconds > 0 else 'Calculating...'}\n"
                f"⏰ **Elapsed:** {format_time(progress_info['elapsed_time'])}"
            )
            
            # Update progress message
            await progress_msg.edit_text(progress_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.warning(f"Failed to update progress message: {e}")
    
    # Set progress callback
    progress_tracker.set_progress_callback(progress_callback)
    
    # Try enhanced download with progress tracking
    download_success = False
    
    try:
        # Import security manager
        from security_manager import security_manager
        
        # Log download start
        security_manager._log_security_event(SecurityEvent(
            event_type='file_download',
            user_id=user_id,
            operation='telegram_download_start',
            resource_path=destination_path,
            success=True,
            metadata={
                'file_name': file_name,
                'file_size': file_size,
                'download_method': 'enhanced_with_progress'
            }
        ))
        
        # Use fallback method (more reliable)
        logger.info("Using Telegram's built-in download method for reliability...")
        
        await progress_msg.edit_text(
            f"📥 **Downloading from Telegram**\n\n"
            f"📄 **File:** `{file_name}`\n"
            f"📁 **Size:** {format_size(file_size)}\n"
            f"🔄 **Status:** Downloading using Telegram's API...\n"
            f"⚡ **Method:** Reliable download method",
            parse_mode=ParseMode.MARKDOWN
        )
        
        download_success = await download_telegram_file_fallback(
            file_obj, destination_path, progress_tracker
        )
        
        # Log download method used
        security_manager._log_security_event(SecurityEvent(
            event_type='file_download',
            user_id=user_id,
            operation='telegram_download_reliable',
            resource_path=destination_path,
            success=download_success,
            metadata={
                'file_name': file_name,
                'file_size': file_size,
                'download_method': 'telegram_builtin'
            }
        ))
        
        # Update final status
        if download_success:
            actual_size = os.path.getsize(destination_path) if os.path.exists(destination_path) else 0
            
            await progress_msg.edit_text(
                f"✅ **Download completed successfully!**\n\n"
                f"📄 **File:** `{file_name}`\n"
                f"📁 **Size:** {format_size(actual_size)}\n"
                f"🔄 **Progress:** 100%\n"
                f"📊 **Bar:** `{'█' * 20}`\n"
                f"⚡ **Avg Speed:** {format_size(actual_size / progress_tracker.get_progress_info()['elapsed_time'])}/s\n"
                f"⏱️ **Total Time:** {format_time(progress_tracker.get_progress_info()['elapsed_time'])}\n"
                f"📍 **Saved to:** `{destination_path}`",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log successful download
            security_manager._log_security_event(SecurityEvent(
                event_type='file_download',
                user_id=user_id,
                operation='telegram_download_complete',
                resource_path=destination_path,
                success=True,
                metadata={
                    'file_name': file_name,
                    'file_size': actual_size,
                    'download_time': progress_tracker.get_progress_info()['elapsed_time']
                }
            ))
            
        else:
            await progress_msg.edit_text(
                f"❌ **Download failed**\n\n"
                f"📄 **File:** `{file_name}`\n"
                f"📁 **Size:** {format_size(file_size)}\n"
                f"🔄 **Status:** Download unsuccessful\n"
                f"⚠️ **Error:** Unable to download file from Telegram servers\n\n"
                f"**Troubleshooting:**\n"
                f"• Check internet connection\n"
                f"• Try again in a few minutes\n"
                f"• Contact support if issue persists",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Log failed download
            security_manager._log_security_event(SecurityEvent(
                event_type='file_download',
                user_id=user_id,
                operation='telegram_download_complete',
                resource_path=destination_path,
                success=False,
                error_message="Download failed after trying both methods"
            ))
        
        return download_success
        
    except Exception as e:
        logger.error(f"Error in download_telegram_file_with_feedback: {e}")
        
        await progress_msg.edit_text(
            f"❌ **Download error**\n\n"
            f"📄 **File:** `{file_name}`\n"
            f"📁 **Size:** {format_size(file_size)}\n"
            f"🔄 **Status:** Error occurred\n"
            f"⚠️ **Error:** {str(e)}\n\n"
            f"**Please try again or contact support.**",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return False

# Example usage function that can be integrated into existing handlers
async def enhanced_file_download_example(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Example function showing how to use the enhanced download functionality.
    This can be integrated into existing file handlers.
    """
    # This would be called from your existing file_attachment_handler
    # when a file attachment is detected
    
    message = update.message
    
    # Detect file attachment (assuming document for this example)
    if message.document:
        file_obj = message.document
        file_name = file_obj.file_name or f"document_{int(time.time())}"
        file_size = file_obj.file_size or 0
        
        # Get temporary destination path
        temp_dir = tempfile.gettempdir()
        destination_path = os.path.join(temp_dir, file_name)
        
        # Download with progress feedback
        success = await download_telegram_file_with_feedback(
            update, context, file_obj, file_name, file_size, destination_path
        )
        
        if success:
            logger.info(f"File downloaded successfully: {destination_path}")
        else:
            logger.error(f"Failed to download file: {file_name}")
    else:
        await message.reply_text("Please send a document to test the download functionality.")

# Integration function to update existing file_attachment_handler
def integrate_with_existing_handler():
    """
    Instructions for integrating this enhanced download functionality
    with the existing file_attachment_handler.py
    """
    integration_guide = """
    INTEGRATION GUIDE:
    
    1. Replace the download section in file_attachment_handler.py (lines 226-237):
    
       # OLD CODE:
       try:
           telegram_file = await file_obj.get_file()
           await telegram_file.download_to_drive(destination_path)
       except Exception as download_error:
           # error handling...
    
       # NEW CODE:
       try:
           telegram_file = await file_obj.get_file()
           success = await download_telegram_file_with_feedback(
               update, context, telegram_file, unique_filename, file_size, destination_path
           )
           if not success:
               raise Exception("Download failed")
       except Exception as download_error:
           # error handling...
    
    2. Add import at the top of file_attachment_handler.py:
       from telegram_download_handler import download_telegram_file_with_feedback
    
    3. Remove the status update messages in the original handler since
       the new function handles progress updates automatically.
    """
    
    return integration_guide

# Export main functions
__all__ = [
    'download_telegram_file_with_feedback',
    'DownloadProgress',
    'enhanced_file_download_example',
    'integrate_with_existing_handler'
]
