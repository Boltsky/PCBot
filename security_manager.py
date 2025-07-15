#!/usr/bin/env python3
"""
Security Manager Module for PCRst
Implements comprehensive security features including:
- User authentication and authorization
- Path traversal and file type restrictions
- Detailed audit logging (GDPR compliant)
- File size/quota limits per user
- Automatic cleanup of temporary files
"""

import os
import sys
import json
import hashlib
import time
import logging
import threading
import tempfile
import shutil
import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from functools import wraps
import mimetypes

# Configure secure logging
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

# Create file handler for security logs
security_log_file = os.path.join(tempfile.gettempdir(), 'pcrst_security.log')
security_handler = logging.FileHandler(security_log_file)
security_handler.setLevel(logging.INFO)

# Create console handler for security warnings
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)

# Create formatters
security_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
console_formatter = logging.Formatter(
    '%(levelname)s - %(message)s'
)

security_handler.setFormatter(security_formatter)
console_handler.setFormatter(console_formatter)

security_logger.addHandler(security_handler)
security_logger.addHandler(console_handler)

@dataclass
class UserProfile:
    """User profile with authentication and quota information"""
    user_id: str
    username: str
    telegram_id: int
    is_authenticated: bool = False
    is_authorized: bool = False
    quota_bytes: int = 100 * 1024 * 1024  # 100MB default
    used_bytes: int = 0
    last_access: datetime = None
    permissions: List[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = ['read', 'write', 'upload', 'download']
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_access is None:
            self.last_access = datetime.now()

@dataclass
class SecurityEvent:
    """Security event for audit logging"""
    event_type: str
    user_id: str
    operation: str
    resource_path: str
    success: bool
    error_message: str = None
    timestamp: datetime = None
    ip_address: str = None
    user_agent: str = None
    file_size: int = None
    file_hash: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

@dataclass
class FileQuota:
    """File quota management"""
    user_id: str
    total_quota: int
    used_quota: int
    file_count: int
    max_file_size: int
    last_cleanup: datetime = None
    
    def __post_init__(self):
        if self.last_cleanup is None:
            self.last_cleanup = datetime.now()

class SecurityConfig:
    """Security configuration and policies"""
    
    # File size limits
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB per file
    DEFAULT_USER_QUOTA = 100 * 1024 * 1024  # 100MB per user
    MAX_USER_QUOTA = 500 * 1024 * 1024  # 500MB maximum
    
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
    
    # Blocked file extensions (additional security)
    BLOCKED_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js', '.jar',
        '.msi', '.dll', '.sys', '.scf', '.lnk', '.inf', '.reg', '.hta', '.ps1'
    }
    
    # Dangerous filename patterns
    DANGEROUS_PATTERNS = [
        r'\.\./',  # Path traversal
        r'\\\.\.\\',  # Windows path traversal
        r'[<>:"|?*]',  # Invalid filename characters
        r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$',  # Windows reserved names
        r'[\x00-\x1f]',  # Control characters
    ]
    
    # Safe directories (sandboxed)
    SAFE_DIRECTORIES = [
        os.path.expanduser('~/Desktop'),
        os.path.expanduser('~/Documents'),
        os.path.expanduser('~/Downloads'),
        os.path.expanduser('~/Pictures'),
        os.path.expanduser('~/Videos'),
        os.path.expanduser('~/Music'),
        tempfile.gettempdir(),
    ]
    
    # Cleanup policies
    TEMP_FILE_RETENTION_HOURS = 24
    MAX_TEMP_FILES_PER_USER = 100
    CLEANUP_INTERVAL_MINUTES = 60

class SecurityManager:
    """Main security manager class"""
    
    def set_user_directory(self, user_id: str, directory: str) -> Tuple[bool, str]:
        """Set the current working directory for a user with validation"""
        try:
            # Validate the directory path
            normalized_path = os.path.normpath(os.path.abspath(directory))
            
            # Check if directory exists
            if not os.path.exists(normalized_path):
                return False, f"Directory does not exist: {normalized_path}"
            
            # Check if it's actually a directory
            if not os.path.isdir(normalized_path):
                return False, f"Path is not a directory: {normalized_path}"
            
            # Validate against safe directories
            is_safe_path, validation_message = self._validate_directory_path(normalized_path, user_id)
            if not is_safe_path:
                return False, validation_message
            
            # Update database
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO user_directories (user_id, current_directory)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET current_directory=excluded.current_directory
                ''', (user_id, normalized_path))
                conn.commit()
            
            # Log directory change
            self._log_security_event(SecurityEvent(
                event_type='directory_change',
                user_id=user_id,
                operation='set_directory',
                resource_path=normalized_path,
                success=True
            ))
            
            return True, f"Directory set to: {normalized_path}"
            
        except Exception as e:
            self._log_security_event(SecurityEvent(
                event_type='directory_change',
                user_id=user_id,
                operation='set_directory',
                resource_path=directory,
                success=False,
                error_message=str(e)
            ))
            return False, f"Error setting directory: {e}"

    def get_user_directory(self, user_id: str) -> str:
        """Get the current working directory for a user"""
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT current_directory FROM user_directories WHERE user_id = ?
                ''', (user_id,))
                row = cursor.fetchone()
                
                if row:
                    # Verify directory still exists and is accessible
                    directory = row[0]
                    if os.path.exists(directory) and os.path.isdir(directory):
                        return directory
                    else:
                        # Directory no longer exists, fall back to safe default
                        self._log_security_event(SecurityEvent(
                            event_type='directory_fallback',
                            user_id=user_id,
                            operation='get_directory',
                            resource_path=directory,
                            success=True,
                            error_message='Directory no longer exists, using fallback'
                        ))
                
                # Get safe default directory
                default_dir = self._get_safe_default_directory(user_id)
                
                # Initialize user directory in database
                cursor.execute('''
                    INSERT INTO user_directories (user_id, current_directory)
                    VALUES (?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET current_directory=excluded.current_directory
                ''', (user_id, default_dir))
                conn.commit()
                
                return default_dir
                
        except Exception as e:
            security_logger.error(f"Error getting directory for user {user_id}: {e}")
            return self._get_safe_default_directory(user_id)
    
    def _get_safe_default_directory(self, user_id: str) -> str:
        """Get a safe default directory for the user"""
        safe_defaults = [
            os.path.expanduser('~/Documents'),
            os.path.expanduser('~/Desktop'),
            os.path.expanduser('~/Downloads'),
            os.path.expanduser('~'),
            tempfile.gettempdir(),
        ]
        
        for directory in safe_defaults:
            try:
                if os.path.exists(directory) and os.path.isdir(directory):
                    # Check if directory is accessible
                    test_path = os.path.join(directory, f'.pcrst_test_{user_id}')
                    try:
                        with open(test_path, 'w') as f:
                            f.write('test')
                        os.remove(test_path)
                        return directory
                    except (OSError, IOError):
                        continue
            except Exception:
                continue
        
        # Last resort - use temp directory
        return tempfile.gettempdir()
    
    def _validate_directory_path(self, directory: str, user_id: str) -> Tuple[bool, str]:
        """Validate if directory path is safe for user access"""
        try:
            # Check against safe directories
            is_safe = False
            for safe_dir in SecurityConfig.SAFE_DIRECTORIES:
                try:
                    safe_dir_abs = os.path.abspath(safe_dir)
                    if directory.startswith(safe_dir_abs):
                        is_safe = True
                        break
                except Exception:
                    continue
            
            if not is_safe:
                self._log_security_event(SecurityEvent(
                    event_type='security_violation',
                    user_id=user_id,
                    operation='directory_validation',
                    resource_path=directory,
                    success=False,
                    error_message='Directory outside safe paths'
                ))
                return False, f"Directory '{directory}' is outside allowed safe directories"
            
            # Check for dangerous path patterns
            for pattern in SecurityConfig.DANGEROUS_PATTERNS:
                if re.search(pattern, directory, re.IGNORECASE):
                    self._log_security_event(SecurityEvent(
                        event_type='security_violation',
                        user_id=user_id,
                        operation='directory_validation',
                        resource_path=directory,
                        success=False,
                        error_message=f'Dangerous pattern detected: {pattern}'
                    ))
                    return False, f"Directory path contains dangerous pattern: {pattern}"
            
            return True, "Directory validation successful"
            
        except Exception as e:
            return False, f"Error validating directory: {e}"
    
    def is_safe_path(self, user_id: str, path: str) -> bool:
        """Check if a path is safe for the user"""
        is_safe, _ = self.validate_file_path(path, user_id)
        return is_safe
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(tempfile.gettempdir(), 'pcrst_security.db')
        self.users: Dict[str, UserProfile] = {}
        self.active_sessions: Dict[str, datetime] = {}
        self.cleanup_thread = None
        self.running = False
        self._lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        # Start cleanup thread
        self.start_cleanup_service()
    
    def _init_database(self):
        """Initialize SQLite database for security data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        telegram_id INTEGER UNIQUE,
                        is_authenticated BOOLEAN DEFAULT 0,
                        is_authorized BOOLEAN DEFAULT 0,
                        quota_bytes INTEGER DEFAULT 104857600,
                        used_bytes INTEGER DEFAULT 0,
                        last_access TEXT,
                        permissions TEXT,
                        created_at TEXT
                    )
                ''')
                
                # User directories table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_directories (
                        user_id TEXT PRIMARY KEY,
                        current_directory TEXT NOT NULL
                    )
                ''')

                # Security events table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS security_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_type TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        resource_path TEXT,
                        success BOOLEAN NOT NULL,
                        error_message TEXT,
                        timestamp TEXT NOT NULL,
                        ip_address TEXT,
                        user_agent TEXT,
                        file_size INTEGER,
                        file_hash TEXT
                    )
                ''')
                
                # File quotas table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS file_quotas (
                        user_id TEXT PRIMARY KEY,
                        total_quota INTEGER NOT NULL,
                        used_quota INTEGER DEFAULT 0,
                        file_count INTEGER DEFAULT 0,
                        max_file_size INTEGER NOT NULL,
                        last_cleanup TEXT
                    )
                ''')
                
                # Temporary files table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS temp_files (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        file_path TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        file_hash TEXT
                    )
                ''')
                
                conn.commit()
                security_logger.info("Security database initialized successfully")
                
        except Exception as e:
            security_logger.error(f"Error initializing security database: {e}")
            raise
    
    def authenticate_user(self, telegram_id: int, username: str = None) -> UserProfile:
        """Authenticate user and return profile"""
        with self._lock:
            try:
                user_id = str(telegram_id)
                
                # Check if user exists in database
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT user_id, username, telegram_id, is_authenticated, is_authorized,
                               quota_bytes, used_bytes, last_access, permissions, created_at
                        FROM users WHERE telegram_id = ?
                    ''', (telegram_id,))
                    
                    row = cursor.fetchone()
                    
                    if row:
                        # Existing user
                        user = UserProfile(
                            user_id=row[0],
                            username=row[1],
                            telegram_id=row[2],
                            is_authenticated=bool(row[3]),
                            is_authorized=bool(row[4]),
                            quota_bytes=row[5],
                            used_bytes=row[6],
                            last_access=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                            permissions=json.loads(row[8]) if row[8] else ['read', 'write', 'upload', 'download'],
                            created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now()
                        )
                        
                        # Update last access
                        user.last_access = datetime.now()
                        cursor.execute('''
                            UPDATE users SET last_access = ?, is_authenticated = 1 
                            WHERE telegram_id = ?
                        ''', (user.last_access.isoformat(), telegram_id))
                        
                    else:
                        # New user
                        user = UserProfile(
                            user_id=user_id,
                            username=username or f"user_{telegram_id}",
                            telegram_id=telegram_id,
                            is_authenticated=True,
                            is_authorized=True,  # Default authorization for new users
                            quota_bytes=SecurityConfig.DEFAULT_USER_QUOTA,
                            used_bytes=0
                        )
                        
                        # Insert new user
                        cursor.execute('''
                            INSERT INTO users (user_id, username, telegram_id, is_authenticated, 
                                             is_authorized, quota_bytes, used_bytes, last_access, 
                                             permissions, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            user.user_id, user.username, user.telegram_id,
                            user.is_authenticated, user.is_authorized,
                            user.quota_bytes, user.used_bytes,
                            user.last_access.isoformat(),
                            json.dumps(user.permissions),
                            user.created_at.isoformat()
                        ))
                        
                        # Create quota entry
                        cursor.execute('''
                            INSERT INTO file_quotas (user_id, total_quota, used_quota, 
                                                    file_count, max_file_size, last_cleanup)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            user.user_id, user.quota_bytes, user.used_bytes,
                            0, SecurityConfig.MAX_FILE_SIZE,
                            datetime.now().isoformat()
                        ))
                    
                    conn.commit()
                
                # Cache user in memory
                self.users[user_id] = user
                self.active_sessions[user_id] = datetime.now()
                
                # Log authentication event
                self._log_security_event(SecurityEvent(
                    event_type='authentication',
                    user_id=user_id,
                    operation='user_login',
                    resource_path='',
                    success=True
                ))
                
                security_logger.info(f"User authenticated successfully: {user_id}")
                return user
                
            except Exception as e:
                security_logger.error(f"Authentication error for user {telegram_id}: {e}")
                raise
    
    def authorize_operation(self, user_id: str, operation: str, resource_path: str = None) -> bool:
        """Authorize user operation"""
        try:
            user = self.users.get(user_id)
            if not user:
                # Try to load from database
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT user_id, username, telegram_id, is_authenticated, is_authorized,
                               quota_bytes, used_bytes, last_access, permissions, created_at
                        FROM users WHERE user_id = ?
                    ''', (user_id,))
                    
                    row = cursor.fetchone()
                    if not row:
                        self._log_security_event(SecurityEvent(
                            event_type='authorization',
                            user_id=user_id,
                            operation=operation,
                            resource_path=resource_path or '',
                            success=False,
                            error_message='User not found'
                        ))
                        return False
                    
                    user = UserProfile(
                        user_id=row[0],
                        username=row[1],
                        telegram_id=row[2],
                        is_authenticated=bool(row[3]),
                        is_authorized=bool(row[4]),
                        quota_bytes=row[5],
                        used_bytes=row[6],
                        last_access=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                        permissions=json.loads(row[8]) if row[8] else ['read', 'write', 'upload', 'download'],
                        created_at=datetime.fromisoformat(row[9]) if row[9] else datetime.now()
                    )
                    self.users[user_id] = user
            
            # Check if user is authenticated and authorized
            if not user.is_authenticated or not user.is_authorized:
                self._log_security_event(SecurityEvent(
                    event_type='authorization',
                    user_id=user_id,
                    operation=operation,
                    resource_path=resource_path or '',
                    success=False,
                    error_message='User not authenticated or authorized'
                ))
                return False
            
            # Check if user has permission for this operation
            if operation not in user.permissions:
                self._log_security_event(SecurityEvent(
                    event_type='authorization',
                    user_id=user_id,
                    operation=operation,
                    resource_path=resource_path or '',
                    success=False,
                    error_message=f'Operation {operation} not permitted'
                ))
                return False
            
            # Check session validity (1 hour timeout)
            last_activity = self.active_sessions.get(user_id)
            if last_activity and datetime.now() - last_activity > timedelta(hours=1):
                self._log_security_event(SecurityEvent(
                    event_type='authorization',
                    user_id=user_id,
                    operation=operation,
                    resource_path=resource_path or '',
                    success=False,
                    error_message='Session expired'
                ))
                return False
            
            # Update session activity
            self.active_sessions[user_id] = datetime.now()
            
            # Log successful authorization
            self._log_security_event(SecurityEvent(
                event_type='authorization',
                user_id=user_id,
                operation=operation,
                resource_path=resource_path or '',
                success=True
            ))
            
            return True
            
        except Exception as e:
            security_logger.error(f"Authorization error for user {user_id}: {e}")
            self._log_security_event(SecurityEvent(
                event_type='authorization',
                user_id=user_id,
                operation=operation,
                resource_path=resource_path or '',
                success=False,
                error_message=str(e)
            ))
            return False
    
    def validate_file_path(self, file_path: str, user_id: str) -> Tuple[bool, str]:
        """Validate file path for security"""
        try:
            # Normalize path
            normalized_path = os.path.normpath(os.path.abspath(file_path))
            
            # Check for path traversal attempts
            for pattern in SecurityConfig.DANGEROUS_PATTERNS:
                if re.search(pattern, file_path, re.IGNORECASE):
                    self._log_security_event(SecurityEvent(
                        event_type='security_violation',
                        user_id=user_id,
                        operation='path_validation',
                        resource_path=file_path,
                        success=False,
                        error_message=f'Dangerous pattern detected: {pattern}'
                    ))
                    return False, f"Dangerous pattern detected in path: {pattern}"
            
            # Check if path is within safe directories
            is_safe = False
            for safe_dir in SecurityConfig.SAFE_DIRECTORIES:
                safe_dir_abs = os.path.abspath(safe_dir)
                if normalized_path.startswith(safe_dir_abs):
                    is_safe = True
                    break
            
            if not is_safe:
                self._log_security_event(SecurityEvent(
                    event_type='security_violation',
                    user_id=user_id,
                    operation='path_validation',
                    resource_path=file_path,
                    success=False,
                    error_message='Path outside safe directories'
                ))
                return False, "File path is outside allowed directories"
            
            # Check filename for dangerous characters
            filename = os.path.basename(file_path)
            if any(char in filename for char in '<>:"|?*'):
                return False, "Filename contains dangerous characters"
            
            # Check file extension
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in SecurityConfig.BLOCKED_EXTENSIONS:
                self._log_security_event(SecurityEvent(
                    event_type='security_violation',
                    user_id=user_id,
                    operation='path_validation',
                    resource_path=file_path,
                    success=False,
                    error_message=f'Blocked file extension: {file_ext}'
                ))
                return False, f"File extension '{file_ext}' is blocked for security"
            
            return True, "Path validation successful"
            
        except Exception as e:
            security_logger.error(f"Error validating file path {file_path}: {e}")
            return False, f"Error validating path: {e}"
    
    def validate_file_type(self, file_path: str, user_id: str) -> Tuple[bool, str]:
        """Validate file type based on MIME type"""
        try:
            mime_type, _ = mimetypes.guess_type(file_path)
            
            if mime_type is None:
                return False, "Cannot determine file type"
            
            if mime_type not in SecurityConfig.ALLOWED_MIME_TYPES:
                self._log_security_event(SecurityEvent(
                    event_type='security_violation',
                    user_id=user_id,
                    operation='file_type_validation',
                    resource_path=file_path,
                    success=False,
                    error_message=f'Disallowed MIME type: {mime_type}'
                ))
                return False, f"File type '{mime_type}' is not allowed"
            
            return True, "File type validation successful"
            
        except Exception as e:
            security_logger.error(f"Error validating file type {file_path}: {e}")
            return False, f"Error validating file type: {e}"
    
    def check_file_quota(self, user_id: str, file_size: int) -> Tuple[bool, str]:
        """Check if file fits within user quota"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT total_quota, used_quota, file_count, max_file_size
                    FROM file_quotas WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if not row:
                    # Create default quota for user
                    cursor.execute('''
                        INSERT INTO file_quotas (user_id, total_quota, used_quota, 
                                                file_count, max_file_size, last_cleanup)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id, SecurityConfig.DEFAULT_USER_QUOTA, 0,
                        0, SecurityConfig.MAX_FILE_SIZE,
                        datetime.now().isoformat()
                    ))
                    conn.commit()
                    total_quota = SecurityConfig.DEFAULT_USER_QUOTA
                    used_quota = 0
                    file_count = 0
                    max_file_size = SecurityConfig.MAX_FILE_SIZE
                else:
                    total_quota, used_quota, file_count, max_file_size = row
                
                # Check individual file size limit
                if file_size > max_file_size:
                    self._log_security_event(SecurityEvent(
                        event_type='quota_violation',
                        user_id=user_id,
                        operation='file_size_check',
                        resource_path='',
                        success=False,
                        error_message=f'File size {file_size} exceeds limit {max_file_size}',
                        file_size=file_size
                    ))
                    return False, f"File size ({file_size:,} bytes) exceeds maximum allowed ({max_file_size:,} bytes)"
                
                # Check total quota
                if used_quota + file_size > total_quota:
                    self._log_security_event(SecurityEvent(
                        event_type='quota_violation',
                        user_id=user_id,
                        operation='quota_check',
                        resource_path='',
                        success=False,
                        error_message=f'Quota exceeded: {used_quota + file_size} > {total_quota}',
                        file_size=file_size
                    ))
                    return False, f"File would exceed quota limit ({used_quota + file_size:,} > {total_quota:,} bytes)"
                
                return True, "Quota check successful"
                
        except Exception as e:
            security_logger.error(f"Error checking quota for user {user_id}: {e}")
            return False, f"Error checking quota: {e}"
    
    def update_file_quota(self, user_id: str, file_size: int, operation: str = 'add'):
        """Update user's file quota usage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if operation == 'add':
                    cursor.execute('''
                        UPDATE file_quotas 
                        SET used_quota = used_quota + ?, file_count = file_count + 1
                        WHERE user_id = ?
                    ''', (file_size, user_id))
                elif operation == 'remove':
                    cursor.execute('''
                        UPDATE file_quotas 
                        SET used_quota = used_quota - ?, file_count = file_count - 1
                        WHERE user_id = ?
                    ''', (file_size, user_id))
                
                conn.commit()
                
        except Exception as e:
            security_logger.error(f"Error updating quota for user {user_id}: {e}")
    
    def register_temp_file(self, user_id: str, file_path: str, file_size: int, 
                          retention_hours: int = None) -> bool:
        """Register a temporary file for cleanup"""
        try:
            retention_hours = retention_hours or SecurityConfig.TEMP_FILE_RETENTION_HOURS
            expires_at = datetime.now() + timedelta(hours=retention_hours)
            
            # Calculate file hash
            file_hash = None
            if os.path.exists(file_path):
                file_hash = self._calculate_file_hash(file_path)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO temp_files (user_id, file_path, file_size, 
                                          created_at, expires_at, file_hash)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, file_path, file_size,
                    datetime.now().isoformat(),
                    expires_at.isoformat(),
                    file_hash
                ))
                conn.commit()
            
            self._log_security_event(SecurityEvent(
                event_type='temp_file_registered',
                user_id=user_id,
                operation='temp_file_registration',
                resource_path=file_path,
                success=True,
                file_size=file_size,
                file_hash=file_hash
            ))
            
            return True
            
        except Exception as e:
            security_logger.error(f"Error registering temp file {file_path}: {e}")
            return False
    
    def cleanup_temp_files(self, force: bool = False) -> Dict[str, Any]:
        """Clean up expired temporary files"""
        try:
            cleanup_stats = {
                'files_cleaned': 0,
                'bytes_freed': 0,
                'errors': []
            }
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get expired files
                current_time = datetime.now().isoformat()
                if force:
                    cursor.execute('''
                        SELECT id, user_id, file_path, file_size, file_hash 
                        FROM temp_files
                    ''')
                else:
                    cursor.execute('''
                        SELECT id, user_id, file_path, file_size, file_hash 
                        FROM temp_files WHERE expires_at < ?
                    ''', (current_time,))
                
                expired_files = cursor.fetchall()
                
                for file_id, user_id, file_path, file_size, file_hash in expired_files:
                    try:
                        if os.path.exists(file_path):
                            # Verify file integrity before deletion
                            if file_hash:
                                current_hash = self._calculate_file_hash(file_path)
                                if current_hash != file_hash:
                                    security_logger.warning(f"File hash mismatch for {file_path}")
                            
                            # Remove file
                            os.remove(file_path)
                            cleanup_stats['files_cleaned'] += 1
                            cleanup_stats['bytes_freed'] += file_size
                            
                            # Update quota
                            self.update_file_quota(user_id, file_size, 'remove')
                            
                            # Log cleanup event
                            self._log_security_event(SecurityEvent(
                                event_type='temp_file_cleanup',
                                user_id=user_id,
                                operation='file_cleanup',
                                resource_path=file_path,
                                success=True,
                                file_size=file_size
                            ))
                        
                        # Remove from database
                        cursor.execute('DELETE FROM temp_files WHERE id = ?', (file_id,))
                        
                    except Exception as e:
                        error_msg = f"Error cleaning up {file_path}: {e}"
                        cleanup_stats['errors'].append(error_msg)
                        security_logger.error(error_msg)
                
                conn.commit()
                
            # Update cleanup timestamp
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE file_quotas SET last_cleanup = ? WHERE user_id IN (
                        SELECT DISTINCT user_id FROM temp_files
                    )
                ''', (datetime.now().isoformat(),))
                conn.commit()
            
            security_logger.info(f"Cleanup completed: {cleanup_stats}")
            return cleanup_stats
            
        except Exception as e:
            security_logger.error(f"Error during cleanup: {e}")
            return {'files_cleaned': 0, 'bytes_freed': 0, 'errors': [str(e)]}
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            security_logger.error(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def _log_security_event(self, event: SecurityEvent):
        """Log security event to database and file"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO security_events (event_type, user_id, operation, resource_path,
                                               success, error_message, timestamp, ip_address,
                                               user_agent, file_size, file_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.event_type, event.user_id, event.operation, event.resource_path,
                    event.success, event.error_message, event.timestamp.isoformat(),
                    event.ip_address, event.user_agent, event.file_size, event.file_hash
                ))
                conn.commit()
            
            # Log to file (GDPR compliant - no sensitive data)
            log_message = f"Event: {event.event_type} | User: {event.user_id} | " \
                         f"Operation: {event.operation} | Success: {event.success}"
            
            if event.error_message:
                log_message += f" | Error: {event.error_message}"
            
            if event.success:
                security_logger.info(log_message)
            else:
                security_logger.warning(log_message)
                
        except Exception as e:
            security_logger.error(f"Error logging security event: {e}")
    
    def start_cleanup_service(self):
        """Start background cleanup service"""
        def cleanup_worker():
            while self.running:
                try:
                    self.cleanup_temp_files()
                    time.sleep(SecurityConfig.CLEANUP_INTERVAL_MINUTES * 60)
                except Exception as e:
                    security_logger.error(f"Error in cleanup worker: {e}")
                    time.sleep(60)  # Wait 1 minute before retry
        
        self.running = True
        self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        security_logger.info("Cleanup service started")
    
    def stop_cleanup_service(self):
        """Stop background cleanup service"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        security_logger.info("Cleanup service stopped")
    
    def get_user_quota_info(self, user_id: str) -> Dict[str, Any]:
        """Get user quota information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT total_quota, used_quota, file_count, max_file_size, last_cleanup
                    FROM file_quotas WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'total_quota': row[0],
                        'used_quota': row[1],
                        'file_count': row[2],
                        'max_file_size': row[3],
                        'available_quota': row[0] - row[1],
                        'quota_percentage': (row[1] / row[0]) * 100 if row[0] > 0 else 0,
                        'last_cleanup': row[4]
                    }
                else:
                    return None
                    
        except Exception as e:
            security_logger.error(f"Error getting quota info for user {user_id}: {e}")
            return None
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get user count
                cursor.execute('SELECT COUNT(*) FROM users')
                user_count = cursor.fetchone()[0]
                
                # Get active sessions
                active_sessions = len([s for s in self.active_sessions.values() 
                                     if datetime.now() - s < timedelta(hours=1)])
                
                # Get recent security events
                cursor.execute('''
                    SELECT event_type, COUNT(*) FROM security_events 
                    WHERE timestamp > ? GROUP BY event_type
                ''', ((datetime.now() - timedelta(hours=24)).isoformat(),))
                
                recent_events = dict(cursor.fetchall())
                
                # Get temp files count
                cursor.execute('SELECT COUNT(*), SUM(file_size) FROM temp_files')
                temp_files_row = cursor.fetchone()
                temp_files_count = temp_files_row[0] or 0
                temp_files_size = temp_files_row[1] or 0
                
                return {
                    'total_users': user_count,
                    'active_sessions': active_sessions,
                    'recent_events_24h': recent_events,
                    'temp_files_count': temp_files_count,
                    'temp_files_size': temp_files_size
                }
                
        except Exception as e:
            security_logger.error(f"Error getting security stats: {e}")
            return {}

# Decorator for securing operations
def secure_operation(operation: str):
    """Decorator to secure operations with authentication, authorization, and logging"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract update context (assumes Telegram bot context)
            update = None
            context = None
            
            for arg in args:
                if hasattr(arg, 'effective_user'):
                    update = arg
                elif hasattr(arg, 'user_data'):
                    context = arg
            
            if not update:
                raise ValueError("Update context not found in arguments")
            
            # Initialize security manager if not exists
            if not hasattr(wrapper, '_security_manager'):
                wrapper._security_manager = SecurityManager()
            
            security_manager = wrapper._security_manager
            
            try:
                # Authenticate user
                user = security_manager.authenticate_user(
                    update.effective_user.id,
                    update.effective_user.username
                )
                
                # Authorize operation
                if not security_manager.authorize_operation(user.user_id, operation):
                    await update.message.reply_text(
                        "❌ Access denied. You don't have permission for this operation."
                    )
                    return
                
                # Execute original function
                result = await func(*args, **kwargs)
                
                # Log successful operation
                security_manager._log_security_event(SecurityEvent(
                    event_type='operation_success',
                    user_id=user.user_id,
                    operation=operation,
                    resource_path='',
                    success=True
                ))
                
                return result
                
            except Exception as e:
                # Log failed operation
                if hasattr(wrapper, '_security_manager'):
                    user_id = str(update.effective_user.id) if update else 'unknown'
                    security_manager._log_security_event(SecurityEvent(
                        event_type='operation_failure',
                        user_id=user_id,
                        operation=operation,
                        resource_path='',
                        success=False,
                        error_message=str(e)
                    ))
                
                raise
        
        return wrapper
    return decorator

# Global security manager instance
security_manager = SecurityManager()
