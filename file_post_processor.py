#!/usr/bin/env python3
"""
File Post-Processor Module for PCRst
Handles moving downloaded files from temporary locations to user directories
and performs post-processing for media files (images, videos, audio)
"""

import os
import shutil
import tempfile
import logging
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None
import subprocess
import mimetypes
from security_manager import SecurityManager, SecurityEvent, security_manager

# Configure logging
logger = logging.getLogger(__name__)

class FilePostProcessor:
    """
    Handles post-processing of downloaded files including:
    - Moving files from temporary locations to final destinations
    - Creating thumbnails for images
    - Generating preview metadata for videos and audio
    - Registering files with security manager for cleanup
    """
    
    def __init__(self, security_mgr: SecurityManager = None):
        self.security_manager = security_mgr or security_manager
        self.temp_dir = tempfile.gettempdir()
        
    def move_downloaded_file(self, temp_path: str, final_filename: str, user_id: str) -> Tuple[bool, str]:
        """
        Move a downloaded file from temporary location to user's current directory
        
        Args:
            temp_path: Path to the temporary file
            final_filename: Desired filename in the destination
            user_id: User ID for directory resolution
            
        Returns:
            Tuple[bool, str]: (success, final_path_or_error_message)
        """
        try:
            # Check if temporary file exists
            if not os.path.exists(temp_path):
                return False, f"Temporary file not found: {temp_path}"
            
            # Get user's current directory
            user_directory = self.security_manager.get_user_directory(user_id)
            
            # Resolve final path with security validation
            path_valid, final_path_or_error = self.security_manager.resolve_save_path(
                user_id, final_filename
            )
            
            if not path_valid:
                return False, final_path_or_error
            
            final_path = final_path_or_error
            
            # Create destination directory if it doesn't exist
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            
            # Move file from temporary location to final destination
            shutil.move(temp_path, final_path)
            
            # Log successful move
            self.security_manager._log_security_event(SecurityEvent(
                event_type='file_move',
                user_id=user_id,
                operation='temp_to_final',
                resource_path=final_path,
                success=True,
                metadata={
                    'temp_path': temp_path,
                    'final_path': final_path,
                    'file_size': os.path.getsize(final_path)
                }
            ))
            
            logger.info(f"Successfully moved file from {temp_path} to {final_path}")
            return True, final_path
            
        except Exception as e:
            error_msg = f"Error moving file: {e}"
            
            # Log error
            self.security_manager._log_security_event(SecurityEvent(
                event_type='file_move',
                user_id=user_id,
                operation='temp_to_final',
                resource_path=temp_path,
                success=False,
                error_message=str(e)
            ))
            
            logger.error(error_msg)
            return False, error_msg
    
    def post_process_file(self, file_path: str, user_id: str) -> Dict[str, Any]:
        """
        Perform post-processing on a file based on its type
        
        Args:
            file_path: Path to the file to process
            user_id: User ID for security logging
            
        Returns:
            Dict containing post-processing results
        """
        try:
            # Get file information
            file_info = self._get_file_info(file_path)
            mime_type = file_info['mime_type']
            
            results = {
                'file_path': file_path,
                'file_info': file_info,
                'post_processing': {}
            }
            
            # Process based on file type
            if mime_type.startswith('image/'):
                results['post_processing'] = self._process_image(file_path, user_id)
            elif mime_type.startswith('video/'):
                results['post_processing'] = self._process_video(file_path, user_id)
            elif mime_type.startswith('audio/'):
                results['post_processing'] = self._process_audio(file_path, user_id)
            else:
                results['post_processing'] = {'type': 'document', 'processed': False}
            
            # Register with security manager for cleanup tracking
            self._register_for_cleanup(file_path, user_id)
            
            return results
            
        except Exception as e:
            logger.error(f"Error post-processing file {file_path}: {e}")
            return {
                'file_path': file_path,
                'error': str(e),
                'post_processing': {'type': 'error', 'processed': False}
            }
    
    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic file information"""
        try:
            stat_info = os.stat(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            
            return {
                'name': os.path.basename(file_path),
                'size': stat_info.st_size,
                'mime_type': mime_type or 'application/octet-stream',
                'extension': os.path.splitext(file_path)[1].lower(),
                'modified': stat_info.st_mtime
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return {
                'name': os.path.basename(file_path),
                'size': 0,
                'mime_type': 'application/octet-stream',
                'extension': '',
                'modified': 0
            }
    
    def _process_image(self, file_path: str, user_id: str) -> Dict[str, Any]:
        """Process image files - create thumbnails and extract metadata"""
        try:
            results = {'type': 'image', 'processed': False}
            
            # Create thumbnail
            thumbnail_path = self._create_thumbnail(file_path)
            if thumbnail_path:
                results['thumbnail'] = thumbnail_path
                results['processed'] = True
            
            # Extract image metadata
            try:
                if Image is not None:
                    with Image.open(file_path) as img:
                        results['metadata'] = {
                            'dimensions': img.size,
                            'format': img.format,
                            'mode': img.mode,
                            'has_transparency': img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                        }
                else:
                    logger.warning(f"PIL not available for extracting metadata from {file_path}")
                    results['metadata'] = {}
            except Exception as e:
                logger.warning(f"Could not extract image metadata from {file_path}: {e}")
                results['metadata'] = {}
            
            # Log processing
            self.security_manager._log_security_event(SecurityEvent(
                event_type='file_processing',
                user_id=user_id,
                operation='image_processing',
                resource_path=file_path,
                success=results['processed'],
                metadata=results
            ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing image {file_path}: {e}")
            return {'type': 'image', 'processed': False, 'error': str(e)}
    
    def _process_video(self, file_path: str, user_id: str) -> Dict[str, Any]:
        """Process video files - extract metadata and create preview"""
        try:
            results = {'type': 'video', 'processed': False}
            
            # Extract video metadata using ffprobe if available
            metadata = self._extract_video_metadata(file_path)
            if metadata:
                results['metadata'] = metadata
                results['processed'] = True
            
            # Create video thumbnail if possible
            thumbnail_path = self._create_video_thumbnail(file_path)
            if thumbnail_path:
                results['thumbnail'] = thumbnail_path
                results['processed'] = True
            
            # Log processing
            self.security_manager._log_security_event(SecurityEvent(
                event_type='file_processing',
                user_id=user_id,
                operation='video_processing',
                resource_path=file_path,
                success=results['processed'],
                metadata=results
            ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing video {file_path}: {e}")
            return {'type': 'video', 'processed': False, 'error': str(e)}
    
    def _process_audio(self, file_path: str, user_id: str) -> Dict[str, Any]:
        """Process audio files - extract metadata"""
        try:
            results = {'type': 'audio', 'processed': False}
            
            # Extract audio metadata using ffprobe if available
            metadata = self._extract_audio_metadata(file_path)
            if metadata:
                results['metadata'] = metadata
                results['processed'] = True
            
            # Log processing
            self.security_manager._log_security_event(SecurityEvent(
                event_type='file_processing',
                user_id=user_id,
                operation='audio_processing',
                resource_path=file_path,
                success=results['processed'],
                metadata=results
            ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error processing audio {file_path}: {e}")
            return {'type': 'audio', 'processed': False, 'error': str(e)}
    
    def _create_thumbnail(self, image_path: str, size: Tuple[int, int] = (200, 200)) -> Optional[str]:
        """Create a thumbnail for an image"""
        try:
            if Image is None:
                logger.warning(f"PIL not available - cannot create thumbnail for {image_path}")
                return None
                
            thumbnail_path = os.path.splitext(image_path)[0] + '_thumbnail.jpg'
            
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, 'JPEG', quality=85)
            
            return thumbnail_path
            
        except Exception as e:
            logger.warning(f"Could not create thumbnail for {image_path}: {e}")
            return None
    
    def _create_video_thumbnail(self, video_path: str) -> Optional[str]:
        """Create a thumbnail from a video file"""
        try:
            thumbnail_path = os.path.splitext(video_path)[0] + '_thumbnail.jpg'
            
            # Use ffmpeg to extract a frame at 1 second
            cmd = [
                'ffmpeg', '-i', video_path, '-ss', '00:00:01.000',
                '-vframes', '1', '-q:v', '2', thumbnail_path, '-y'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(thumbnail_path):
                return thumbnail_path
            else:
                logger.warning(f"ffmpeg failed for {video_path}: {result.stderr}")
                return None
                
        except Exception as e:
            logger.warning(f"Could not create video thumbnail for {video_path}: {e}")
            return None
    
    def _extract_video_metadata(self, video_path: str) -> Optional[Dict[str, Any]]:
        """Extract video metadata using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # Extract relevant metadata
                format_info = data.get('format', {})
                video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), {})
                
                return {
                    'duration': float(format_info.get('duration', 0)),
                    'bitrate': int(format_info.get('bit_rate', 0)),
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'fps': eval(video_stream.get('r_frame_rate', '0/1')),
                    'codec': video_stream.get('codec_name', 'unknown')
                }
            else:
                logger.warning(f"ffprobe failed for {video_path}: {result.stderr}")
                return None
                
        except Exception as e:
            logger.warning(f"Could not extract video metadata for {video_path}: {e}")
            return None
    
    def _extract_audio_metadata(self, audio_path: str) -> Optional[Dict[str, Any]]:
        """Extract audio metadata using ffprobe"""
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # Extract relevant metadata
                format_info = data.get('format', {})
                audio_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), {})
                
                return {
                    'duration': float(format_info.get('duration', 0)),
                    'bitrate': int(format_info.get('bit_rate', 0)),
                    'sample_rate': int(audio_stream.get('sample_rate', 0)),
                    'channels': int(audio_stream.get('channels', 0)),
                    'codec': audio_stream.get('codec_name', 'unknown')
                }
            else:
                logger.warning(f"ffprobe failed for {audio_path}: {result.stderr}")
                return None
                
        except Exception as e:
            logger.warning(f"Could not extract audio metadata for {audio_path}: {e}")
            return None
    
    def _register_for_cleanup(self, file_path: str, user_id: str):
        """Register file with security manager for future cleanup"""
        try:
            # Log file registration
            self.security_manager._log_security_event(SecurityEvent(
                event_type='file_registration',
                user_id=user_id,
                operation='register_cleanup',
                resource_path=file_path,
                success=True,
                metadata={
                    'file_size': os.path.getsize(file_path),
                    'registered_for_cleanup': True
                }
            ))
            
            logger.info(f"File registered for cleanup: {file_path}")
            
        except Exception as e:
            logger.error(f"Error registering file for cleanup {file_path}: {e}")

# Utility functions for external use
def move_and_process_file(temp_path: str, final_filename: str, user_id: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Move a file from temporary location and perform post-processing
    
    Returns:
        Tuple[bool, str, Dict]: (success, final_path_or_error, post_processing_results)
    """
    processor = FilePostProcessor()
    
    # Move file
    success, result = processor.move_downloaded_file(temp_path, final_filename, user_id)
    
    if not success:
        return False, result, {}
    
    final_path = result
    
    # Post-process file
    post_processing_results = processor.post_process_file(final_path, user_id)
    
    return True, final_path, post_processing_results

def find_and_process_recent_downloads(user_id: str, minutes_back: int = 30) -> List[Dict[str, Any]]:
    """
    Find recent downloads in temporary directory and process them
    
    Args:
        user_id: User ID for processing
        minutes_back: How many minutes back to search
        
    Returns:
        List of processing results
    """
    processor = FilePostProcessor()
    temp_dir = tempfile.gettempdir()
    cutoff_time = time.time() - (minutes_back * 60)
    
    results = []
    
    try:
        for file_path in Path(temp_dir).glob('*'):
            if file_path.is_file() and file_path.stat().st_mtime > cutoff_time:
                # Check if it looks like a download (not a system temp file)
                if not file_path.name.endswith('.tmp') and file_path.stat().st_size > 0:
                    final_filename = file_path.name
                    success, final_path, post_proc = move_and_process_file(
                        str(file_path), final_filename, user_id
                    )
                    
                    results.append({
                        'temp_path': str(file_path),
                        'final_path': final_path if success else None,
                        'success': success,
                        'error': final_path if not success else None,
                        'post_processing': post_proc
                    })
    
    except Exception as e:
        logger.error(f"Error finding recent downloads: {e}")
    
    return results

# Export main functions
__all__ = [
    'FilePostProcessor',
    'move_and_process_file',
    'find_and_process_recent_downloads'
]
