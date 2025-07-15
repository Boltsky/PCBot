#!/usr/bin/env python3
"""
Example usage of Path Resolution and Validation Utilities
Demonstrates how to use the PathUtils class with SecurityManager
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from path_utils import PathUtils
from security_manager import SecurityManager

def main():
    """Main demonstration function"""
    print("=== Path Resolution and Validation Utilities Demo ===\n")
    
    # Initialize SecurityManager and PathUtils
    print("1. Initializing SecurityManager and PathUtils...")
    security_manager = SecurityManager()
    path_utils = PathUtils(security_manager)
    
    # Create test user
    user_id = "demo_user_123"
    user = security_manager.authenticate_user(12345, "demo_user")
    
    print(f"   Platform detected: {path_utils.platform}")
    print(f"   Max path length: {path_utils.max_path_length}")
    print(f"   User directory: {path_utils.get_user_directory(user_id)}")
    print()
    
    # Test path resolution
    print("2. Testing path resolution...")
    test_paths = [
        "documents/test.txt",
        "subfolder/file.pdf",
        os.path.join(tempfile.gettempdir(), "temp_file.txt"),
        "../../dangerous_path.txt"
    ]
    
    for path in test_paths:
        success, result = path_utils.resolve_path(user_id, path)
        status = "✓" if success else "✗"
        print(f"   {status} {path}")
        if success:
            print(f"     → {result}")
        else:
            print(f"     → Error: {result}")
    print()
    
    # Test path validation
    print("3. Testing path validation...")
    validation_tests = [
        "normal_file.txt",
        "folder/subfolder/file.txt",
        "../outside_directory.txt",
        "file\x00with_null.txt",
        "CON.txt" if path_utils.platform == 'windows' else "normal.txt"
    ]
    
    for path in validation_tests:
        is_valid, message = path_utils.validate_path(user_id, path)
        status = "✓" if is_valid else "✗"
        print(f"   {status} {path}")
        print(f"     → {message}")
    print()
    
    # Test filename sanitization
    print("4. Testing filename sanitization...")
    dirty_filenames = [
        "normal_file.txt",
        "file<>:\"|?*.txt",
        "  .hidden_file.txt  ",
        "file\x01\x02\x03.txt",
        "CON.txt",
        ""
    ]
    
    for filename in dirty_filenames:
        sanitized = path_utils.sanitize_filename(filename)
        print(f"   '{filename}' → '{sanitized}'")
    print()
    
    # Test path information
    print("5. Testing path information retrieval...")
    info_path = __file__  # Use this script file as example
    path_info = path_utils.get_path_info(info_path)
    
    print(f"   File: {info_path}")
    for key, value in path_info.items():
        print(f"     {key}: {value}")
    print()
    
    # Test cross-platform path conversion
    print("6. Testing cross-platform path conversion...")
    test_path = "folder/subfolder/file.txt"
    
    windows_path = path_utils.convert_path_separators(test_path, 'windows')
    posix_path = path_utils.convert_path_separators(test_path, 'posix')
    
    print(f"   Original: {test_path}")
    print(f"   Windows:  {windows_path}")
    print(f"   POSIX:    {posix_path}")
    print()
    
    # Test relative path calculation
    print("7. Testing relative path calculation...")
    user_dir = path_utils.get_user_directory(user_id)
    test_abs_path = os.path.join(user_dir, "documents", "test.txt")
    
    success, relative = path_utils.get_relative_path(user_id, test_abs_path)
    if success:
        print(f"   Absolute: {test_abs_path}")
        print(f"   Relative: {relative}")
    else:
        print(f"   Error: {relative}")
    print()
    
    # Test path joining
    print("8. Testing safe path joining...")
    components = ["folder", "subfolder", "file.txt"]
    joined = path_utils.join_paths(*components)
    print(f"   Components: {components}")
    print(f"   Joined: {joined}")
    print()
    
    # Test security integration
    print("9. Testing security integration...")
    security_tests = [
        tempfile.gettempdir() + "/safe_file.txt",
        "/etc/passwd" if path_utils.platform == 'posix' else "C:\\Windows\\System32\\config",
        "../../../sensitive_file.txt"
    ]
    
    for path in security_tests:
        is_safe = path_utils.is_safe_path(user_id, path)
        status = "✓ SAFE" if is_safe else "✗ UNSAFE"
        print(f"   {status}: {path}")
    print()
    
    # Cleanup
    print("10. Cleaning up...")
    security_manager.stop_cleanup_service()
    print("    ✓ Cleanup service stopped")
    print()
    
    print("=== Demo completed successfully! ===")

if __name__ == "__main__":
    main()
