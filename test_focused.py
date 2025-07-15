#!/usr/bin/env python3
"""
Focused test suite for existing PCRst functionality
"""

import os
import sys
import tempfile
import shutil
import unittest
import time
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import what we can from the main module
from PCRst import (
    sanitize_filename, is_path_safe, validate_file_security,
    calculate_file_hash, get_file_metadata, create_zip_from_directory,
    format_size, get_file_type_icon, filter_files, sort_files,
    format_file_listing, UploadConfig, DownloadConfig,
    validate_url, validate_destination_path
)

from security_manager import SecurityManager, SecurityConfig

class TestBasicFunctionality(unittest.TestCase):
    """Test basic file operations"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="test_basic_")
        self.test_file = os.path.join(self.test_dir, "test.txt")
        with open(self.test_file, 'w') as f:
            f.write("Test content for basic functionality testing.")
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        # Test basic cases
        self.assertEqual(sanitize_filename("normal.txt"), "normal.txt")
        self.assertEqual(sanitize_filename("file<>with|bad:chars.txt"), "file__with_bad_chars.txt")
        self.assertEqual(sanitize_filename("CON.txt"), "file_CON.txt")
        
        # Test empty filename
        result = sanitize_filename("")
        self.assertTrue(result.startswith("file_"))
        
        print("✅ Filename sanitization tests passed")
    
    def test_path_safety(self):
        """Test path safety validation"""
        # Test safe path (temp directory)
        self.assertTrue(is_path_safe(self.test_file))
        
        # Test unsafe paths
        unsafe_paths = ["/etc/passwd", "/root/secret.txt", "C:\\Windows\\System32\\file.txt"]
        for path in unsafe_paths:
            self.assertFalse(is_path_safe(path))
        
        print("✅ Path safety tests passed")
    
    def test_file_security_validation(self):
        """Test file security validation"""
        # Test valid file
        valid, msg = validate_file_security(self.test_file)
        self.assertTrue(valid)
        
        # Test non-existent file
        valid, msg = validate_file_security("/nonexistent/file.txt")
        self.assertFalse(valid)
        
        print("✅ File security validation tests passed")
    
    def test_file_hash_calculation(self):
        """Test file hash calculation"""
        hash_result = calculate_file_hash(self.test_file)
        self.assertIsNotNone(hash_result)
        self.assertEqual(len(hash_result), 64)  # SHA-256 length
        
        # Test non-existent file
        self.assertIsNone(calculate_file_hash("/nonexistent/file.txt"))
        
        print("✅ File hash calculation tests passed")
    
    def test_file_metadata_extraction(self):
        """Test file metadata extraction"""
        metadata = get_file_metadata(self.test_file)
        self.assertIsNotNone(metadata)
        
        # Check required fields
        required_fields = ['name', 'size', 'mime_type', 'hash']
        for field in required_fields:
            self.assertIn(field, metadata)
        
        print("✅ File metadata extraction tests passed")
    
    def test_format_size(self):
        """Test size formatting"""
        test_cases = [
            (0, "0 B"),
            (1024, "1.0 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB")
        ]
        
        for size, expected in test_cases:
            result = format_size(size)
            self.assertEqual(result, expected)
        
        print("✅ Size formatting tests passed")
    
    def test_file_type_icons(self):
        """Test file type icon assignment"""
        test_cases = [
            ("file.txt", "📄"),
            ("script.py", "🐍"),
            ("image.jpg", "🖼️"),
            ("unknown.xyz", "📄")
        ]
        
        for filename, expected_icon in test_cases:
            icon = get_file_type_icon(filename)
            self.assertEqual(icon, expected_icon)
        
        print("✅ File type icon tests passed")
    
    def test_url_validation(self):
        """Test URL validation"""
        # Valid URLs
        valid_urls = [
            "https://example.com/file.txt",
            "http://test.org/document.pdf"
        ]
        
        for url in valid_urls:
            valid, msg = validate_url(url)
            self.assertTrue(valid)
        
        # Invalid URLs
        invalid_urls = [
            "ftp://example.com/file.txt",
            "javascript:alert('xss')",
            "not-a-url"
        ]
        
        for url in invalid_urls:
            valid, msg = validate_url(url)
            self.assertFalse(valid)
        
        print("✅ URL validation tests passed")


class TestSecurityManager(unittest.TestCase):
    """Test security manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()
        self.security_manager = SecurityManager(self.test_db.name)
        
    def tearDown(self):
        """Clean up test environment"""
        try:
            self.security_manager.stop_cleanup_service()
        except:
            pass
        if os.path.exists(self.test_db.name):
            os.unlink(self.test_db.name)
    
    def test_user_authentication(self):
        """Test user authentication"""
        user = self.security_manager.authenticate_user(12345, "testuser")
        self.assertIsNotNone(user)
        self.assertEqual(user.telegram_id, 12345)
        self.assertTrue(user.is_authenticated)
        
        print("✅ User authentication tests passed")
    
    def test_file_quota_management(self):
        """Test file quota management"""
        user = self.security_manager.authenticate_user(12345, "testuser")
        
        # Test quota check
        valid, msg = self.security_manager.check_file_quota(user.user_id, 1024)
        self.assertTrue(valid)
        
        # Test oversized file
        valid, msg = self.security_manager.check_file_quota(user.user_id, 200 * 1024 * 1024)
        self.assertFalse(valid)
        
        print("✅ File quota management tests passed")


def run_focused_tests():
    """Run focused test suite"""
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [TestBasicFunctionality, TestSecurityManager]
    
    for test_class in test_classes:
        tests = test_loader.loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    print("🔧 Running focused PCRst functionality tests...")
    print("=" * 50)
    
    success = run_focused_tests()
    
    print("=" * 50)
    if success:
        print("✅ All focused tests passed successfully!")
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)
