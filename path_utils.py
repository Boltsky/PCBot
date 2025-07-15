#!/usr/bin/env python3
"""
Path Resolution and Validation Utilities Module for PCRst
Implements cross-platform path resolution, normalization, and validation
with strict adherence to security policies via security_manager.
"""

import os
import re
import sys
import platform
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Tuple, Union, Optional, List
import logging
from urllib.parse import unquote

# Configure logging
path_logger = logging.getLogger('path_utils')
path_logger.setLevel(logging.INFO)

class PathUtils:
    """
    Cross-platform path resolution and validation utilities.
    Ensures secure path handling with strict adherence to permitted directories.
    """
    
    # Platform-specific dangerous patterns
    DANGEROUS_PATTERNS = {
        'posix': [
            r'\.\./',  # Path traversal (Unix/Linux)
            r'[\x00-\x1f]',  # Control characters
            r'\$\{.*\}',  # Variable expansion attempts
            r'`.*`',  # Command substitution
            r'\|',  # Pipe characters
            r';',  # Command separator
            r'&',  # Background process
        ],
        'windows': [
            r'\.\.\\',  # Path traversal (Windows only backslash)
            r'[\x00-\x1f]',  # Control characters
            r'\$\{.*\}',  # Variable expansion attempts
            r'%[A-Za-z_][A-Za-z0-9_]*%',  # Environment variable expansion
            r'\\\\[.\\]',  # UNC path attempts
        ],
        'common': [
            r'\x00',  # Null bytes
            r'\\x[0-9a-fA-F]{2}',  # Hex encoded characters
            r'%[0-9a-fA-F]{2}',  # URL encoded characters
        ]
    }
    
    # Maximum path lengths by platform
    MAX_PATH_LENGTH = {
        'posix': 4096,
        'windows': 260,  # Traditional limit, can be 32767 with long path support
        'default': 255
    }
    
    # Reserved names (case-insensitive for Windows)
    RESERVED_NAMES = {
        'windows': {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        },
        'posix': set()  # No reserved names in POSIX
    }
    
    def __init__(self, security_manager):
        """
        Initialize PathUtils with security manager integration.
        
        Args:
            security_manager: Instance of SecurityManager for validation
        """
        self.security_manager = security_manager
        self.platform = self._detect_platform()
        self.path_class = PureWindowsPath if self.platform == 'windows' else PurePosixPath
        self.max_path_length = self.MAX_PATH_LENGTH.get(self.platform, self.MAX_PATH_LENGTH['default'])
        
        path_logger.info(f"PathUtils initialized for platform: {self.platform}")
    
    def _detect_platform(self) -> str:
        """
        Detect the current platform for path handling.
        
        Returns:
            str: Platform identifier ('windows', 'posix', or 'other')
        """
        if os.name == 'nt' or platform.system() == 'Windows':
            return 'windows'
        elif os.name == 'posix' or platform.system() in ['Linux', 'Darwin']:
            return 'posix'
        else:
            return 'other'
    
    def resolve_path(self, user_id: str, path: str) -> Tuple[bool, str]:
        """
        Resolve a path relative to the user's base directory.
        
        Args:
            user_id: User identifier
            path: Path to resolve (can be relative or absolute)
            
        Returns:
            Tuple[bool, str]: (success, resolved_path_or_error_message)
        """
        try:
            # Get user's base directory
            base_dir = self.security_manager.get_user_directory(user_id)
            
            # Handle different path types
            if self._is_absolute_path(path):
                # For absolute paths, validate they're within allowed directories
                resolved_path = self._normalize_path(path)
            else:
                # For relative paths, resolve against user's base directory
                resolved_path = self._normalize_path(os.path.join(base_dir, path))
            
            # Validate the resolved path
            is_valid, validation_message = self.validate_path(user_id, resolved_path)
            if not is_valid:
                return False, validation_message
            
            path_logger.debug(f"Path resolved for user {user_id}: {path} -> {resolved_path}")
            return True, resolved_path
            
        except Exception as e:
            path_logger.error(f"Error resolving path '{path}' for user {user_id}: {e}")
            return False, f"Error resolving path: {e}"
    
    def _is_absolute_path(self, path: str) -> bool:
        """
        Check if a path is absolute in a cross-platform manner.
        
        Args:
            path: Path to check
            
        Returns:
            bool: True if path is absolute
        """
        try:
            return os.path.isabs(path) or self.path_class(path).is_absolute()
        except (ValueError, TypeError):
            return False
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize a path for the current platform.
        
        Args:
            path: Path to normalize
            
        Returns:
            str: Normalized path
        """
        # Handle URL encoded paths
        if '%' in path:
            try:
                path = unquote(path)
            except Exception:
                pass  # Continue with original path if decoding fails
        
        # Normalize path separators and resolve . and .. components
        normalized = os.path.normpath(os.path.abspath(path))
        
        # Additional platform-specific normalization
        if self.platform == 'windows':
            # Convert forward slashes to backslashes on Windows
            normalized = normalized.replace('/', '\\')
            # Handle long path prefix if needed
            if len(normalized) > 260 and not normalized.startswith('\\\\?\\'):
                normalized = '\\\\?\\' + normalized
        
        return normalized
    
    def validate_path(self, user_id: str, path: str) -> Tuple[bool, str]:
        """
        Comprehensive path validation with security checks.
        
        Args:
            user_id: User identifier
            path: Path to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message_or_success)
        """
        try:
            # Basic path validation
            validation_result = self._validate_path_format(path)
            if not validation_result[0]:
                return validation_result
            
            # Security pattern validation
            security_result = self._validate_security_patterns(path)
            if not security_result[0]:
                return security_result
            
            # Path length validation
            length_result = self._validate_path_length(path)
            if not length_result[0]:
                return length_result
            
            # Reserved name validation
            reserved_result = self._validate_reserved_names(path)
            if not reserved_result[0]:
                return reserved_result
            
            # Use security manager for directory validation
            is_safe, message = self.security_manager.validate_file_path(path, user_id)
            if not is_safe:
                return False, message
            
            return True, "Path validation successful"
            
        except Exception as e:
            path_logger.error(f"Error validating path '{path}' for user {user_id}: {e}")
            return False, f"Error validating path: {e}"
    
    def _validate_path_format(self, path: str) -> Tuple[bool, str]:
        """
        Validate basic path format.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message_or_success)
        """
        if not path or not isinstance(path, str):
            return False, "Path must be a non-empty string"
        
        # Check for null bytes
        if '\x00' in path:
            return False, "Path contains null bytes"
        
        # Try to create a Path object to validate format
        try:
            Path(path)
        except (TypeError, ValueError) as e:
            return False, f"Invalid path format: {e}"
        
        return True, "Path format valid"
    
    def _validate_security_patterns(self, path: str) -> Tuple[bool, str]:
        """
        Validate path against dangerous patterns.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message_or_success)
        """
        # Get platform-specific patterns
        patterns = self.DANGEROUS_PATTERNS.get(self.platform, [])
        patterns.extend(self.DANGEROUS_PATTERNS['common'])
        
        # Check each pattern
        for pattern in patterns:
            if re.search(pattern, path, re.IGNORECASE):
                path_logger.warning(f"Dangerous pattern detected in path: {pattern}")
                return False, f"Path contains dangerous pattern: {pattern}"
        
        return True, "Security patterns check passed"
    
    def _validate_path_length(self, path: str) -> Tuple[bool, str]:
        """
        Validate path length against platform limits.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message_or_success)
        """
        if len(path) > self.max_path_length:
            return False, f"Path too long ({len(path)} > {self.max_path_length})"
        
        return True, "Path length valid"
    
    def _validate_reserved_names(self, path: str) -> Tuple[bool, str]:
        """
        Validate path against reserved names.
        
        Args:
            path: Path to validate
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message_or_success)
        """
        reserved_names = self.RESERVED_NAMES.get(self.platform, set())
        if not reserved_names:
            return True, "No reserved names for this platform"
        
        # Check filename components
        filename = os.path.basename(path)
        name_without_ext = os.path.splitext(filename)[0]
        
        if name_without_ext.upper() in reserved_names:
            return False, f"Filename '{filename}' uses reserved name"
        
        return True, "Reserved names check passed"
    
    def is_safe_path(self, user_id: str, path: str) -> bool:
        """
        Check if a path is safe for the user.
        
        Args:
            user_id: User identifier
            path: Path to check
            
        Returns:
            bool: True if path is safe
        """
        is_valid, _ = self.validate_path(user_id, path)
        return is_valid
    
    def get_user_directory(self, user_id: str) -> str:
        """
        Get the user's base directory.
        
        Args:
            user_id: User identifier
            
        Returns:
            str: User's base directory path
        """
        return self.security_manager.get_user_directory(user_id)
    
    def convert_path_separators(self, path: str, target_platform: Optional[str] = None) -> str:
        """
        Convert path separators for the target platform.
        
        Args:
            path: Path to convert
            target_platform: Target platform ('windows', 'posix', or None for current)
            
        Returns:
            str: Path with converted separators
        """
        if target_platform is None:
            target_platform = self.platform
        
        if target_platform == 'windows':
            return path.replace('/', '\\')
        else:
            return path.replace('\\', '/')
    
    def get_relative_path(self, user_id: str, path: str) -> Tuple[bool, str]:
        """
        Get relative path from user's base directory.
        
        Args:
            user_id: User identifier
            path: Absolute path
            
        Returns:
            Tuple[bool, str]: (success, relative_path_or_error_message)
        """
        try:
            base_dir = self.security_manager.get_user_directory(user_id)
            
            # Normalize both paths
            normalized_path = self._normalize_path(path)
            normalized_base = self._normalize_path(base_dir)
            
            # Calculate relative path
            try:
                relative_path = os.path.relpath(normalized_path, normalized_base)
                
                # Validate that the relative path doesn't go outside base directory
                if relative_path.startswith('..' + os.sep) or relative_path == '..':
                    return False, "Path is outside user's base directory"
                
                return True, relative_path
                
            except ValueError:
                # Paths are on different drives (Windows)
                return False, "Path is on different drive than user's base directory"
            
        except Exception as e:
            path_logger.error(f"Error getting relative path for user {user_id}: {e}")
            return False, f"Error calculating relative path: {e}"
    
    def join_paths(self, *paths: str) -> str:
        """
        Join multiple path components safely.
        
        Args:
            *paths: Path components to join
            
        Returns:
            str: Joined path
        """
        if not paths:
            return ''
        
        # Filter out empty components
        valid_paths = [p for p in paths if p]
        
        if not valid_paths:
            return ''
        
        # Join paths and normalize
        joined = os.path.join(*valid_paths)
        return self._normalize_path(joined)
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for the current platform.
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            str: Sanitized filename
        """
        if not filename:
            return 'unnamed'
        
        # Remove or replace invalid characters
        if self.platform == 'windows':
            # Windows invalid characters
            invalid_chars = '<>:"|?*'
            for char in invalid_chars:
                filename = filename.replace(char, '_')
        
        # Remove control characters
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # Remove leading/trailing whitespace and dots
        filename = filename.strip('. ')
        
        # Check reserved names
        reserved_names = self.RESERVED_NAMES.get(self.platform, set())
        name_without_ext = os.path.splitext(filename)[0]
        if name_without_ext.upper() in reserved_names:
            filename = f"_{filename}"
        
        # Ensure filename is not empty
        if not filename:
            filename = 'unnamed'
        
        return filename
    
    def get_path_info(self, path: str) -> dict:
        """
        Get comprehensive path information.
        
        Args:
            path: Path to analyze
            
        Returns:
            dict: Path information
        """
        try:
            normalized = self._normalize_path(path)
            path_obj = Path(normalized)
            
            return {
                'original': path,
                'normalized': normalized,
                'absolute': path_obj.is_absolute(),
                'exists': path_obj.exists(),
                'is_file': path_obj.is_file() if path_obj.exists() else None,
                'is_dir': path_obj.is_dir() if path_obj.exists() else None,
                'parent': str(path_obj.parent),
                'name': path_obj.name,
                'stem': path_obj.stem,
                'suffix': path_obj.suffix,
                'parts': path_obj.parts,
                'platform': self.platform
            }
        except Exception as e:
            return {
                'original': path,
                'error': str(e),
                'platform': self.platform
            }

