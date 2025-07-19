#!/usr/bin/env python3
"""
Save Path Resolver Utility for PCRst

This module provides a comprehensive solution for resolving save paths with security validation,
including filename sanitization, path traversal prevention, and extension validation.
"""

import os
import logging
from typing import Tuple, Optional
from security_manager import SecurityManager
from path_utils import PathUtils

# Configure logging
resolver_logger = logging.getLogger('save_path_resolver')
resolver_logger.setLevel(logging.INFO)

class SavePathResolver:
    """
    Resolves and validates save paths with comprehensive security checks.
    
    This class integrates the SecurityManager and PathUtils to provide:
    - User directory resolution
    - Filename sanitization
    - Security validation
    - Path traversal prevention
    - Extension validation
    """
    
    def __init__(self, security_manager: SecurityManager = None, path_utils: PathUtils = None):
        """
        Initialize the SavePathResolver.
        
        Args:
            security_manager: Instance of SecurityManager for validation
            path_utils: Instance of PathUtils for filename sanitization
        """
        self.security_manager = security_manager or SecurityManager()
        self.path_utils = path_utils or PathUtils(self.security_manager)
        
        resolver_logger.info("SavePathResolver initialized")
    
    def resolve_save_path(self, user_id: str, filename: str) -> Tuple[bool, str]:
        """
        Resolve and validate save path with comprehensive security checks.
        
        This method performs the following security validations:
        1. Gets the user's current directory using security_manager.get_user_directory()
        2. Sanitizes the filename using path_utils.sanitize_filename()
        3. Validates the file extension against blocked extensions
        4. Prevents path traversal attacks
        5. Ensures the final path is within the user's allowed directory
        
        Args:
            user_id: User identifier
            filename: Filename to save (will be sanitized)
            
        Returns:
            Tuple[bool, str]: (success, resolved_path_or_error_message)
        """
        try:
            # Use the security manager's comprehensive resolve_save_path method
            return self.security_manager.resolve_save_path(user_id, filename, self.path_utils)
            
        except Exception as e:
            error_message = f"Error in save path resolution: {e}"
            resolver_logger.error(error_message)
            return False, error_message
    
    def validate_save_operation(self, user_id: str, filename: str, file_size: int = 0) -> Tuple[bool, str]:
        """
        Comprehensive validation for save operations.
        
        Args:
            user_id: User identifier
            filename: Filename to save
            file_size: Size of the file to save (for quota checking)
            
        Returns:
            Tuple[bool, str]: (success, path_or_error_message)
        """
        try:
            # First, resolve the save path
            success, path_or_error = self.resolve_save_path(user_id, filename)
            if not success:
                return False, path_or_error
            
            resolved_path = path_or_error
            
            # Check file quota (if enabled)
            quota_success, quota_message = self.security_manager.check_file_quota(user_id, file_size)
            if not quota_success:
                return False, quota_message
            
            # Validate file type (optional, based on MIME type)
            if os.path.splitext(filename)[1]:  # Only check if file has extension
                type_success, type_message = self.security_manager.validate_file_type(resolved_path, user_id)
                if not type_success:
                    return False, type_message
            
            resolver_logger.info(f"Save operation validated successfully for user {user_id}: {resolved_path}")
            return True, resolved_path
            
        except Exception as e:
            error_message = f"Error validating save operation: {e}"
            resolver_logger.error(error_message)
            return False, error_message
    
    def get_user_directory(self, user_id: str) -> str:
        """
        Get the user's current directory.
        
        Args:
            user_id: User identifier
            
        Returns:
            str: User's current directory path
        """
        return self.security_manager.get_user_directory(user_id)
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe usage.
        
        Args:
            filename: Filename to sanitize
            
        Returns:
            str: Sanitized filename
        """
        return self.path_utils.sanitize_filename(filename)


# Example usage and demonstration
def demonstrate_save_path_resolution():
    """
    Demonstrate the save path resolution functionality.
    """
    print("=== Save Path Resolution Demonstration ===")
    
    # Initialize resolver
    resolver = SavePathResolver()
    
    # Test cases
    test_cases = [
        ("user123", "document.txt"),
        ("user123", "my file with spaces.pdf"),
        ("user123", "CON.txt"),  # Windows reserved name
        ("user123", "file<>with|invalid*chars.doc"),
        ("user123", "../../../etc/passwd"),  # Path traversal attempt
        ("user123", "normal_file.jpg"),
        ("user123", "executable.exe"),  # Blocked extension
        ("user123", ""),  # Empty filename
        ("user123", "file.with.multiple.dots.txt"),
    ]
    
    for user_id, filename in test_cases:
        print(f"\nTesting: user_id='{user_id}', filename='{filename}'")
        
        # Test basic path resolution
        success, result = resolver.resolve_save_path(user_id, filename)
        print(f"  Resolution: {'SUCCESS' if success else 'FAILED'}")
        print(f"  Result: {result}")
        
        # Test comprehensive validation
        success, result = resolver.validate_save_operation(user_id, filename, 1024)
        print(f"  Validation: {'SUCCESS' if success else 'FAILED'}")
        print(f"  Final: {result}")


if __name__ == "__main__":
    # Run demonstration
    demonstrate_save_path_resolution()
