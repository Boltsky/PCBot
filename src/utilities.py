import os
import re
import logging
import sys
import platform
import subprocess
import ctypes
from ctypes import wintypes
from pathlib import Path, PureWindowsPath, PurePosixPath
from typing import Tuple, Union, Optional, List
from enum import Enum
from urllib.parse import unquote
from security_manager import SecurityManager

# Configure logging
logger = logging.getLogger(__name__)

class AttributeMethod(Enum):
    CTYPES_API = "ctypes_api"
    OS_MODULE = "os_module"
    ATTRIB_COMMAND = "attrib_command"

class PathUtils:
    DANGEROUS_PATTERNS = {
        'posix': [r'\.\./', r'[\x00-\x1f]', r'\$\{.*\}', r'`.*`', r'\|', r';', r'&'],
        'windows': [r'\.\.\\', r'[\x00-\x1f]', r'\$\{.*\}', r'%[A-Za-z_][A-Za-z0-9_]*%', r'\\\\[.\\]'],
        'common': [r'\x00', r'\\x[0-9a-fA-F]{2}', r'%[0-9a-fA-F]{2}']
    }
    MAX_PATH_LENGTH = {'posix': 4096, 'windows': 260, 'default': 255}
    RESERVED_NAMES = { 'windows': {'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'},
        'posix': set()}

    def __init__(self, security_manager):
        self.security_manager = security_manager
        self.platform = self._detect_platform()
        self.path_class = PureWindowsPath if self.platform == 'windows' else PurePosixPath
        self.max_path_length = self.MAX_PATH_LENGTH.get(self.platform, self.MAX_PATH_LENGTH['default'])
        logger.info(f"PathUtils initialized for platform: {self.platform}")

    def _detect_platform(self) -> str:
        if os.name == 'nt' or platform.system() == 'Windows':
            return 'windows'
        elif os.name == 'posix' or platform.system() in ['Linux', 'Darwin']:
            return 'posix'
        return 'other'

class WindowsFileAttributes:
    FILE_ATTRIBUTE_HIDDEN = 0x02
    FILE_ATTRIBUTE_NORMAL = 0x80

    def __init__(self, preferred_method: AttributeMethod = AttributeMethod.CTYPES_API):
        self.preferred_method = preferred_method
        self._validate_platform()
        self._setup_ctypes_api()

    def _validate_platform(self):
        if sys.platform != "win32":
            raise RuntimeError("Windows file attributes can only be modified on Windows platform")

class SavePathResolver:
    def __init__(self, security_manager: SecurityManager = None, path_utils: PathUtils = None):
        self.security_manager = security_manager or SecurityManager()
        self.path_utils = path_utils or PathUtils(self.security_manager)
        logger.info("SavePathResolver initialized")

    def resolve_save_path(self, user_id: str, filename: str) -> Tuple[bool, str]:
        try:
            return self.security_manager.resolve_save_path(user_id, filename, self.path_utils)
            
        except Exception as e:
            error_message = f"Error in save path resolution: {e}"
            logger.error(error_message)
            return False, error_message
    
    def sanitize_filename(self, filename: str) -> str:
        return self.path_utils.sanitize_filename(filename)


