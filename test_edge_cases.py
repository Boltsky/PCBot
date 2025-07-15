#!/usr/bin/env python3
"""
Edge Case Tests for Cross-Platform Functionality
Tests specific edge cases and error conditions for PCRst commands
"""

import os
import sys
import platform
import tempfile
import shutil
import unittest
import logging

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PCRst import (
    sanitize_filename, is_path_safe, validate_file_security,
    calculate_file_hash, get_file_metadata, format_size,
    get_file_type_icon
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

class EdgeCaseTests(unittest.TestCase):
    """Test edge cases for cross-platform functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix='edge_case_test_')
        self.current_platform = platform.system()
        
    def tearDown(self):
        """Clean up test environment"""
        try:
            if os.path.exists(self.test_dir):
                shutil.rmtree(self.test_dir)
        except:
            pass
    
    def test_windows_path_separators(self):
        """Test Windows path separator handling"""
        print(f"\n=== Testing Windows Path Separators ===")
        
        test_cases = [
            "folder\\file.txt",
            "folder/file.txt",
            "folder\\subfolder/file.txt",
            "C:\\Users\\test\\file.txt",
            "C:/Users/test/file.txt",
        ]
        
        for test_path in test_cases:
            normalized = os.path.normpath(test_path)
            print(f"Input: {test_path}")
            print(f"Normalized: {normalized}")
            print(f"Uses correct separator: {os.sep in normalized}")
            print()
    
    def test_unix_path_separators(self):
        """Test Unix path separator handling"""
        print(f"\n=== Testing Unix Path Separators ===")
        
        test_cases = [
            "folder/file.txt",
            "folder\\file.txt",
            "/home/user/file.txt",
            "/tmp/test/file.txt",
            "../relative/path.txt",
        ]
        
        for test_path in test_cases:
            normalized = os.path.normpath(test_path)
            print(f"Input: {test_path}")
            print(f"Normalized: {normalized}")
            print(f"Is absolute: {os.path.isabs(normalized)}")
            print()
    
    def test_path_traversal_detection(self):
        """Test path traversal attack detection"""
        print(f"\n=== Testing Path Traversal Detection ===")
        
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\Windows\\System32\\config",
            "folder/../../../secret.txt",
            "folder\\..\\..\\secret.txt",
            "normal_file.txt",  # This should be safe
        ]
        
        for path in dangerous_paths:
            try:
                normalized = os.path.normpath(os.path.abspath(path))
                is_safe = is_path_safe(path)
                print(f"Path: {path}")
                print(f"Normalized: {normalized}")
                print(f"Is safe: {is_safe}")
                print(f"Contains '..': {'/..' in path or '\\..' in path}")
                print()
            except Exception as e:
                print(f"Error testing path {path}: {e}")
                print()
    
    def test_reserved_names_windows(self):
        """Test Windows reserved names"""
        print(f"\n=== Testing Windows Reserved Names ===")
        
        if self.current_platform == "Windows":
            reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'LPT1', 'LPT2']
            
            for name in reserved_names:
                test_filename = f"{name}.txt"
                sanitized = sanitize_filename(test_filename)
                print(f"Original: {test_filename}")
                print(f"Sanitized: {sanitized}")
                print(f"Is different: {test_filename != sanitized}")
                print()
        else:
            print("Not on Windows - skipping reserved names test")
    
    def test_invalid_filename_characters(self):
        """Test invalid filename characters"""
        print(f"\n=== Testing Invalid Filename Characters ===")
        
        if self.current_platform == "Windows":
            invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
            base_name = "test_file"
            
            for char in invalid_chars:
                test_filename = f"{base_name}{char}.txt"
                sanitized = sanitize_filename(test_filename)
                print(f"Char: '{char}' -> Original: {test_filename}")
                print(f"Sanitized: {sanitized}")
                print(f"Contains invalid char: {char in sanitized}")
                print()
        else:
            # Unix systems mainly care about null bytes and slashes
            invalid_chars = ['\x00', '/']
            base_name = "test_file"
            
            for char in invalid_chars:
                if char == '\x00':
                    test_filename = f"{base_name}\x00.txt"
                else:
                    test_filename = f"{base_name}{char}.txt"
                sanitized = sanitize_filename(test_filename)
                print(f"Char: '{repr(char)}' -> Original: {repr(test_filename)}")
                print(f"Sanitized: {sanitized}")
                print()
    
    def test_long_paths(self):
        """Test long path handling"""
        print(f"\n=== Testing Long Path Handling ===")
        
        # Test various long path scenarios
        long_filename = "a" * 255 + ".txt"
        very_long_filename = "a" * 1000 + ".txt"
        
        test_cases = [
            ("Normal length", "normal_file.txt"),
            ("255 char filename", long_filename),
            ("1000 char filename", very_long_filename),
        ]
        
        for description, filename in test_cases:
            sanitized = sanitize_filename(filename)
            print(f"{description}:")
            print(f"  Original length: {len(filename)}")
            print(f"  Sanitized length: {len(sanitized)}")
            print(f"  Sanitized: {sanitized[:50]}{'...' if len(sanitized) > 50 else ''}")
            print()
    
    def test_unicode_filenames(self):
        """Test Unicode filename handling"""
        print(f"\n=== Testing Unicode Filename Handling ===")
        
        unicode_names = [
            "файл.txt",  # Russian
            "文件.txt",   # Chinese
            "ファイル.txt",  # Japanese
            "파일.txt",    # Korean
            "αρχείο.txt", # Greek
            "📄file.txt",  # Emoji
        ]
        
        for name in unicode_names:
            try:
                sanitized = sanitize_filename(name)
                print(f"Original: {name}")
                print(f"Sanitized: {sanitized}")
                print(f"Length: {len(sanitized)}")
                print()
            except Exception as e:
                print(f"Error with {name}: {e}")
                print()
    
    def test_file_metadata_edge_cases(self):
        """Test file metadata extraction edge cases"""
        print(f"\n=== Testing File Metadata Edge Cases ===")
        
        # Test with None
        try:
            metadata = get_file_metadata(None)
            print(f"get_file_metadata(None): {metadata}")
        except Exception as e:
            print(f"get_file_metadata(None) error: {e}")
        
        # Test with empty string
        try:
            metadata = get_file_metadata("")
            print(f"get_file_metadata(''): {metadata}")
        except Exception as e:
            print(f"get_file_metadata('') error: {e}")
        
        # Test with non-existent file
        try:
            metadata = get_file_metadata("/nonexistent/file.txt")
            print(f"get_file_metadata(nonexistent): {metadata}")
        except Exception as e:
            print(f"get_file_metadata(nonexistent) error: {e}")
        
        # Test with empty file
        empty_file = os.path.join(self.test_dir, "empty.txt")
        with open(empty_file, 'w') as f:
            pass  # Create empty file
        
        try:
            metadata = get_file_metadata(empty_file)
            print(f"Empty file metadata: {metadata}")
        except Exception as e:
            print(f"Empty file metadata error: {e}")
    
    def test_file_hash_edge_cases(self):
        """Test file hash calculation edge cases"""
        print(f"\n=== Testing File Hash Edge Cases ===")
        
        # Test with None
        try:
            hash_result = calculate_file_hash(None)
            print(f"calculate_file_hash(None): {hash_result}")
        except Exception as e:
            print(f"calculate_file_hash(None) error: {e}")
        
        # Test with empty string
        try:
            hash_result = calculate_file_hash("")
            print(f"calculate_file_hash(''): {hash_result}")
        except Exception as e:
            print(f"calculate_file_hash('') error: {e}")
        
        # Test with non-existent file
        try:
            hash_result = calculate_file_hash("/nonexistent/file.txt")
            print(f"calculate_file_hash(nonexistent): {hash_result}")
        except Exception as e:
            print(f"calculate_file_hash(nonexistent) error: {e}")
    
    def test_size_formatting_edge_cases(self):
        """Test size formatting edge cases"""
        print(f"\n=== Testing Size Formatting Edge Cases ===")
        
        test_sizes = [
            -1,
            0,
            1,
            1023,
            1024,
            1024 * 1024 - 1,
            1024 * 1024,
            1024 * 1024 * 1024,
            1024 * 1024 * 1024 * 1024,
            1024 * 1024 * 1024 * 1024 * 1024,
        ]
        
        for size in test_sizes:
            try:
                formatted = format_size(size)
                print(f"Size: {size:>15} -> {formatted}")
            except Exception as e:
                print(f"Size: {size:>15} -> Error: {e}")
    
    def test_file_type_icon_edge_cases(self):
        """Test file type icon assignment edge cases"""
        print(f"\n=== Testing File Type Icon Edge Cases ===")
        
        test_files = [
            "",
            "file_without_extension",
            ".hidden_file",
            "file.unknown_extension",
            "file.TXT",  # uppercase
            "file.txt.backup",
            "very.long.file.name.with.many.dots.txt",
            "file with spaces.txt",
            "файл.txt",  # Unicode
        ]
        
        for filename in test_files:
            try:
                icon = get_file_type_icon(filename)
                print(f"File: '{filename}' -> Icon: {icon}")
            except Exception as e:
                print(f"File: '{filename}' -> Error: {e}")
    
    def test_permission_scenarios(self):
        """Test various permission scenarios"""
        print(f"\n=== Testing Permission Scenarios ===")
        
        # Create test files
        test_file = os.path.join(self.test_dir, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("Test content")
        
        # Test readable file
        try:
            is_valid, message = validate_file_security(test_file)
            print(f"Readable file: {is_valid} - {message}")
        except Exception as e:
            print(f"Readable file error: {e}")
        
        # Test non-existent file
        try:
            is_valid, message = validate_file_security("/nonexistent/file.txt")
            print(f"Non-existent file: {is_valid} - {message}")
        except Exception as e:
            print(f"Non-existent file error: {e}")
        
        # Test directory instead of file
        try:
            is_valid, message = validate_file_security(self.test_dir)
            print(f"Directory: {is_valid} - {message}")
        except Exception as e:
            print(f"Directory error: {e}")
        
        # Unix permission tests
        if self.current_platform != "Windows":
            try:
                # Make file unreadable
                os.chmod(test_file, 0o000)
                is_valid, message = validate_file_security(test_file)
                print(f"Unreadable file: {is_valid} - {message}")
                
                # Restore permissions
                os.chmod(test_file, 0o644)
            except Exception as e:
                print(f"Permission change error: {e}")
    
    def test_platform_specific_behavior(self):
        """Test platform-specific behavior"""
        print(f"\n=== Testing Platform-Specific Behavior ===")
        
        print(f"Current platform: {self.current_platform}")
        print(f"OS name: {os.name}")
        print(f"Path separator: '{os.sep}'")
        print(f"Alt path separator: '{os.altsep}'")
        print(f"Current directory: {os.getcwd()}")
        
        # Test home directory
        home = os.path.expanduser("~")
        print(f"Home directory: {home}")
        print(f"Home exists: {os.path.exists(home)}")
        
        # Test temp directory
        temp = tempfile.gettempdir()
        print(f"Temp directory: {temp}")
        print(f"Temp exists: {os.path.exists(temp)}")
        
        # Test root/system paths
        if self.current_platform == "Windows":
            system_paths = ["C:\\", "C:\\Windows", "C:\\Users"]
        else:
            system_paths = ["/", "/home", "/tmp", "/usr"]
        
        for path in system_paths:
            exists = os.path.exists(path)
            is_abs = os.path.isabs(path)
            print(f"System path {path}: exists={exists}, absolute={is_abs}")


def run_all_edge_case_tests():
    """Run all edge case tests"""
    print("=" * 60)
    print("PCRst Edge Case Tests")
    print("=" * 60)
    
    test_instance = EdgeCaseTests()
    test_instance.setUp()
    
    try:
        # Run all test methods
        test_methods = [
            'test_windows_path_separators',
            'test_unix_path_separators',
            'test_path_traversal_detection',
            'test_reserved_names_windows',
            'test_invalid_filename_characters',
            'test_long_paths',
            'test_unicode_filenames',
            'test_file_metadata_edge_cases',
            'test_file_hash_edge_cases',
            'test_size_formatting_edge_cases',
            'test_file_type_icon_edge_cases',
            'test_permission_scenarios',
            'test_platform_specific_behavior',
        ]
        
        for method_name in test_methods:
            print(f"\nRunning {method_name}...")
            try:
                method = getattr(test_instance, method_name)
                method()
            except Exception as e:
                print(f"Error in {method_name}: {e}")
    
    finally:
        test_instance.tearDown()
    
    print("\n" + "=" * 60)
    print("Edge case testing completed!")


if __name__ == "__main__":
    run_all_edge_case_tests()
