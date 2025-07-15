#!/usr/bin/env python3
"""
Cross-platform Test Suite for PCRst Commands
Tests command behavior on Windows and Unix systems including:
- Path separators
- Root/home usage
- Permissions
- Large trees
- Invalid operations
"""

import os
import sys
import platform
import tempfile
import shutil
import stat
import time
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import logging

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules
from PCRst import (
    sanitize_filename, is_path_safe, validate_file_security,
    calculate_file_hash, get_file_metadata, format_size,
    get_file_type_icon, filter_files, sort_files
)
from path_utils import PathUtils
from security_manager import SecurityManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrossPlatformTestSuite(unittest.TestCase):
    """Test suite for cross-platform functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix='cross_platform_test_')
        self.current_platform = platform.system()
        self.path_sep = os.sep
        self.alt_path_sep = os.altsep
        
        # Create security manager
        self.security_manager = SecurityManager()
        self.path_utils = PathUtils(self.security_manager)
        
        # Create test user
        self.test_user_id = "test_user_12345"
        self.test_user = self.security_manager.authenticate_user(12345, "test_user")
        
        logger.info(f"Testing on {self.current_platform} platform")
        logger.info(f"Test directory: {self.test_dir}")
        
    def tearDown(self):
        """Clean up test environment"""
        try:
            if os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
        except:
            pass
        
        try:
            self.security_manager.stop_cleanup_service()
        except:
            pass
    
    def test_path_separator_handling(self):
        """Test path separator handling across platforms"""
        logger.info("Testing path separator handling...")
        
        # Test different path separator combinations
        test_cases = [
            ("folder/subfolder/file.txt", "Forward slashes"),
            ("folder\\subfolder\\file.txt", "Backslashes"),
            ("folder/subfolder\\file.txt", "Mixed separators"),
            ("./folder/file.txt", "Relative with dot"),
            ("../folder/file.txt", "Relative with parent"),
        ]
        
        for test_path, description in test_cases:
            with self.subTest(path=test_path, desc=description):
                # Normalize the path
                normalized = self.path_utils._normalize_path(test_path)
                
                # Check that path uses correct separator for platform
                if self.current_platform == "Windows":
                    # Windows should use backslashes
                    self.assertIn('\\', normalized.replace(':', ''), f"Windows path should use backslashes: {normalized}")
                    # Should not have forward slashes in normalized path
                    self.assertNotIn('/', normalized.replace(':', ''), f"Windows path should not have forward slashes: {normalized}")
                else:
                    # Unix should use forward slashes
                    self.assertIn('/', normalized, f"Unix path should use forward slashes: {normalized}")
                    # Should not have backslashes
                    self.assertNotIn('\\', normalized, f"Unix path should not have backslashes: {normalized}")
    
    def test_root_and_home_paths(self):
        """Test root and home path handling"""
        logger.info("Testing root and home path handling...")
        
        if self.current_platform == "Windows":
            # Windows root paths
            root_paths = ["C:\\", "C:\\Windows", "C:\\Users"]
            home_path = os.path.expanduser("~")
        else:
            # Unix root paths
            root_paths = ["/", "/home", "/usr", "/tmp"]
            home_path = os.path.expanduser("~")
        
        # Test root path detection
        for root_path in root_paths:
            with self.subTest(root_path=root_path):
                is_absolute = self.path_utils._is_absolute_path(root_path)
                self.assertTrue(is_absolute, f"Root path {root_path} should be detected as absolute")
        
        # Test home path expansion
        expanded_home = os.path.expanduser("~")
        self.assertTrue(os.path.exists(expanded_home), f"Home path {expanded_home} should exist")
        
        # Test path validation with home directory
        is_valid, message = self.path_utils.validate_path(self.test_user_id, home_path)
        logger.info(f"Home path validation: {is_valid}, {message}")
    
    def test_permission_handling(self):
        """Test permission handling across platforms"""
        logger.info("Testing permission handling...")
        
        # Create test files with different permissions
        test_file = os.path.join(self.test_dir, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Test readable file
        is_valid, message = validate_file_security(test_file)
        self.assertTrue(is_valid, f"Readable file should be valid: {message}")
        
        if self.current_platform != "Windows":
            # Unix permission tests
            try:
                # Make file unreadable
                os.chmod(test_file, 0o000)
                is_valid, message = validate_file_security(test_file)
                self.assertFalse(is_valid, f"Unreadable file should be invalid: {message}")
                
                # Restore permissions
                os.chmod(test_file, 0o644)
            except OSError as e:
                logger.warning(f"Permission test failed: {e}")
        
        # Test non-existent file
        non_existent = os.path.join(self.test_dir, "non_existent.txt")
        is_valid, message = validate_file_security(non_existent)
        self.assertFalse(is_valid, f"Non-existent file should be invalid: {message}")
    
    def test_large_directory_tree(self):
        """Test handling of large directory trees"""
        logger.info("Testing large directory tree handling...")
        
        # Create a deep directory structure
        max_depth = 10
        files_per_dir = 5
        
        def create_deep_structure(base_path, depth=0):
            if depth >= max_depth:
                return
            
            # Create files in current directory
            for i in range(files_per_dir):
                file_path = os.path.join(base_path, f"file_{depth}_{i}.txt")
                with open(file_path, 'w') as f:
                    f.write(f"Content for depth {depth}, file {i}")
            
            # Create subdirectories
            for i in range(2):  # 2 subdirectories per level
                subdir = os.path.join(base_path, f"subdir_{depth}_{i}")
                os.makedirs(subdir, exist_ok=True)
                create_deep_structure(subdir, depth + 1)
        
        # Create the structure
        create_deep_structure(self.test_dir)
        
        # Test directory traversal
        file_count = 0
        for root, dirs, files in os.walk(self.test_dir):
            file_count += len(files)
        
        logger.info(f"Created {file_count} files in deep structure")
        self.assertGreater(file_count, 0, "Should have created files")
        
        # Test path resolution on deep paths
        deep_path = os.path.join(self.test_dir, "subdir_0_0", "subdir_1_0", "file_2_0.txt")
        if os.path.exists(deep_path):
            is_valid, message = self.path_utils.validate_path(self.test_user_id, deep_path)
            logger.info(f"Deep path validation: {is_valid}, {message}")
    
    def test_invalid_operations(self):
        """Test handling of invalid operations"""
        logger.info("Testing invalid operations...")
        
        # Test invalid path characters
        invalid_chars = []
        if self.current_platform == "Windows":
            invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        else:
            invalid_chars = ['\x00']  # Null byte is invalid on Unix
        
        for char in invalid_chars:
            with self.subTest(char=char):
                invalid_filename = f"test{char}file.txt"
                sanitized = sanitize_filename(invalid_filename)
                self.assertNotIn(char, sanitized, f"Invalid character {char} should be removed")
        
        # Test path traversal attempts
        traversal_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\Windows\\System32\\config",
            "folder/../../../secret.txt",
            "folder\\..\\..\\..\\secret.txt"
        ]
        
        for path in traversal_paths:
            with self.subTest(path=path):
                is_valid, message = self.path_utils.validate_path(self.test_user_id, path)
                self.assertFalse(is_valid, f"Path traversal should be rejected: {path}")
        
        # Test extremely long paths
        long_path = "a" * 1000
        is_valid, message = self.path_utils._validate_path_length(long_path)
        self.assertFalse(is_valid, f"Extremely long path should be rejected")
    
    def test_filename_sanitization(self):
        """Test filename sanitization across platforms"""
        logger.info("Testing filename sanitization...")
        
        test_cases = [
            ("normal_file.txt", "normal_file.txt"),
            ("file with spaces.txt", "file with spaces.txt"),
            ("file\twith\ttabs.txt", "file_with_tabs.txt"),
            ("file\nwith\nnewlines.txt", "file_with_newlines.txt"),
        ]
        
        # Add platform-specific test cases
        if self.current_platform == "Windows":
            test_cases.extend([
                ("CON.txt", "_CON.txt"),
                ("PRN.txt", "_PRN.txt"),
                ("file<>:\"|?*.txt", "file________.txt"),
            ])
        
        for input_name, expected_pattern in test_cases:
            with self.subTest(input_name=input_name):
                sanitized = sanitize_filename(input_name)
                # Check that dangerous characters are removed
                if self.current_platform == "Windows":
                    dangerous_chars = '<>:"|?*'
                    for char in dangerous_chars:
                        self.assertNotIn(char, sanitized, f"Dangerous character {char} should be removed")
                
                # Check that result is not empty
                self.assertGreater(len(sanitized), 0, "Sanitized filename should not be empty")
    
    def test_file_metadata_extraction(self):
        """Test file metadata extraction"""
        logger.info("Testing file metadata extraction...")
        
        # Create test files of different types
        test_files = [
            ("test.txt", "text/plain", "Hello World"),
            ("test.py", "text/x-python", "print('Hello')"),
            ("test.json", "application/json", '{"key": "value"}'),
        ]
        
        for filename, expected_mime, content in test_files:
            with self.subTest(filename=filename):
                file_path = os.path.join(self.test_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(content)
                
                # Test metadata extraction
                metadata = get_file_metadata(file_path)
                self.assertIsNotNone(metadata, f"Should extract metadata for {filename}")
                
                # Check required fields
                required_fields = ['name', 'size', 'mime_type', 'hash']
                for field in required_fields:
                    self.assertIn(field, metadata, f"Metadata should contain {field}")
                
                # Check file size
                self.assertEqual(metadata['size'], len(content.encode('utf-8')))
                
                # Check hash
                file_hash = calculate_file_hash(file_path)
                self.assertEqual(metadata['hash'], file_hash)
    
    def test_path_conversion(self):
        """Test path conversion between platforms"""
        logger.info("Testing path conversion...")
        
        test_path = "folder/subfolder/file.txt"
        
        # Test conversion to Windows format
        windows_path = self.path_utils.convert_path_separators(test_path, 'windows')
        self.assertIn('\\', windows_path, "Windows path should contain backslashes")
        
        # Test conversion to POSIX format
        posix_path = self.path_utils.convert_path_separators(test_path, 'posix')
        self.assertIn('/', posix_path, "POSIX path should contain forward slashes")
        
        # Test round-trip conversion
        if self.current_platform == "Windows":
            original = "folder\\subfolder\\file.txt"
            converted = self.path_utils.convert_path_separators(original, 'posix')
            back_converted = self.path_utils.convert_path_separators(converted, 'windows')
            self.assertEqual(original, back_converted, "Round-trip conversion should work")
    
    def test_safe_path_detection(self):
        """Test safe path detection"""
        logger.info("Testing safe path detection...")
        
        # Test safe paths (within temp directory)
        safe_path = os.path.join(tempfile.gettempdir(), "safe_file.txt")
        is_safe = self.path_utils.is_safe_path(self.test_user_id, safe_path)
        self.assertTrue(is_safe, f"Temp directory path should be safe: {safe_path}")
        
        # Test unsafe paths
        if self.current_platform == "Windows":
            unsafe_paths = [
                "C:\\Windows\\System32\\config",
                "C:\\Windows\\System32\\drivers\\etc\\hosts",
            ]
        else:
            unsafe_paths = [
                "/etc/passwd",
                "/etc/shadow",
                "/root/.ssh/id_rsa",
            ]
        
        for unsafe_path in unsafe_paths:
            with self.subTest(path=unsafe_path):
                is_safe = self.path_utils.is_safe_path(self.test_user_id, unsafe_path)
                self.assertFalse(is_safe, f"System path should be unsafe: {unsafe_path}")
    
    def test_file_type_icons(self):
        """Test file type icon assignment"""
        logger.info("Testing file type icon assignment...")
        
        icon_tests = [
            ("document.txt", "📄"),
            ("script.py", "🐍"),
            ("image.jpg", "🖼️"),
            ("video.mp4", "🎬"),
            ("audio.mp3", "🎵"),
            ("archive.zip", "📦"),
            ("unknown.xyz", "📄"),
        ]
        
        for filename, expected_icon in icon_tests:
            with self.subTest(filename=filename):
                icon = get_file_type_icon(filename)
                self.assertEqual(icon, expected_icon, f"Icon for {filename} should be {expected_icon}")
    
    def test_size_formatting(self):
        """Test size formatting"""
        logger.info("Testing size formatting...")
        
        size_tests = [
            (0, "0 B"),
            (1024, "1.0 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB"),
            (1099511627776, "1.0 TB"),
        ]
        
        for size, expected in size_tests:
            with self.subTest(size=size):
                formatted = format_size(size)
                self.assertEqual(formatted, expected, f"Size {size} should format to {expected}")
    
    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        logger.info("Testing edge cases...")
        
        # Test with None values
        self.assertIsNone(calculate_file_hash(None))
        self.assertIsNone(get_file_metadata(None))
        
        # Test with empty strings
        sanitized = sanitize_filename("")
        self.assertGreater(len(sanitized), 0, "Empty filename should be replaced")
        
        # Test with very long filenames
        long_filename = "a" * 300 + ".txt"
        sanitized = sanitize_filename(long_filename)
        self.assertLessEqual(len(sanitized), 255, "Long filename should be truncated")
        
        # Test with special Unicode characters
        unicode_filename = "файл.txt"  # Russian
        sanitized = sanitize_filename(unicode_filename)
        self.assertGreater(len(sanitized), 0, "Unicode filename should be handled")


def create_performance_test():
    """Create a performance test for large directory structures"""
    logger.info("Creating performance test...")
    
    # Create a large directory structure
    base_dir = tempfile.mkdtemp(prefix='perf_test_')
    
    try:
        # Create 1000 files in 100 directories
        for i in range(100):
            subdir = os.path.join(base_dir, f"dir_{i:03d}")
            os.makedirs(subdir, exist_ok=True)
            
            for j in range(10):
                file_path = os.path.join(subdir, f"file_{j:03d}.txt")
                with open(file_path, 'w') as f:
                    f.write(f"Content for file {i}-{j}")
        
        # Measure time to traverse
        start_time = time.time()
        file_count = 0
        for root, dirs, files in os.walk(base_dir):
            file_count += len(files)
        end_time = time.time()
        
        logger.info(f"Performance test: {file_count} files traversed in {end_time - start_time:.2f} seconds")
        
    finally:
        # Clean up
        shutil.rmtree(base_dir)


def run_platform_specific_tests():
    """Run platform-specific tests"""
    current_platform = platform.system()
    logger.info(f"Running platform-specific tests for {current_platform}")
    
    if current_platform == "Windows":
        # Windows-specific tests
        logger.info("Running Windows-specific tests...")
        
        # Test Windows drive letters
        drives = ['C:', 'D:', 'E:']
        for drive in drives:
            if os.path.exists(drive + '\\'):
                logger.info(f"Drive {drive} exists")
        
        # Test Windows reserved names
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1']
        for name in reserved_names:
            sanitized = sanitize_filename(f"{name}.txt")
            logger.info(f"Reserved name {name} sanitized to {sanitized}")
        
        # Test Windows path length limits
        long_path = "\\\\?\\" + "a" * 300
        logger.info(f"Long path support test: {len(long_path)} characters")
    
    elif current_platform in ["Linux", "Darwin"]:
        # Unix-specific tests
        logger.info("Running Unix-specific tests...")
        
        # Test Unix hidden files
        hidden_files = ['.hidden', '.bashrc', '.profile']
        for hidden in hidden_files:
            logger.info(f"Hidden file pattern: {hidden}")
        
        # Test Unix permissions
        try:
            test_file = os.path.join(tempfile.gettempdir(), "perm_test.txt")
            with open(test_file, 'w') as f:
                f.write("test")
            
            # Test different permission modes
            for mode in [0o644, 0o755, 0o600]:
                os.chmod(test_file, mode)
                current_mode = oct(os.stat(test_file).st_mode)[-3:]
                logger.info(f"Permission mode {oct(mode)[-3:]} set, current: {current_mode}")
            
            os.remove(test_file)
        except OSError as e:
            logger.warning(f"Permission test failed: {e}")
    
    else:
        logger.info(f"Unknown platform: {current_platform}")


if __name__ == "__main__":
    print("=" * 60)
    print("PCRst Cross-Platform Test Suite")
    print("=" * 60)
    
    # Print system information
    print(f"Platform: {platform.system()}")
    print(f"Python Version: {platform.python_version()}")
    print(f"Architecture: {platform.architecture()}")
    print(f"Machine: {platform.machine()}")
    print(f"Current Directory: {os.getcwd()}")
    print(f"Path Separator: '{os.sep}'")
    print(f"Alt Path Separator: '{os.altsep}'")
    print("=" * 60)
    
    # Run platform-specific tests
    run_platform_specific_tests()
    
    # Run performance test
    create_performance_test()
    
    print("\nRunning cross-platform unit tests...")
    print("=" * 60)
    
    # Run the main test suite
    unittest.main(verbosity=2, exit=False)
    
    print("=" * 60)
    print("Cross-platform testing completed!")
