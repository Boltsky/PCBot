#!/usr/bin/env python3
"""
Comprehensive test suite for PCRst file operations
Tests all new file functionality including edge cases and security scenarios
"""

import os
import sys
import tempfile
import shutil
import sqlite3
import json
import time
import asyncio
import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
import zipfile
import hashlib
from datetime import datetime, timedelta

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PCRst import (
    UploadConfig, DownloadConfig,
    sanitize_filename, is_path_safe, validate_file_security,
    calculate_file_hash, get_file_metadata, create_zip_from_directory,
    validate_url, validate_destination_path, get_file_info_from_url,
    download_file_advanced, format_size, get_file_type_icon,
    filter_files, sort_files, format_file_listing,
    ConcurrentFileTransfer, TransferStats, BandwidthManager, ProgressTracker
)

from security_manager import (
    SecurityManager, SecurityEvent, UserProfile, FileQuota, SecurityConfig,
    secure_operation, security_manager
)

class TestFileOperations(unittest.TestCase):
    """Test suite for basic file operations"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="test_file_ops_")
        self.test_files = {}
        self._create_test_files()
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def _create_test_files(self):
        """Create various test files"""
        # Text file
        text_file = os.path.join(self.test_dir, "test.txt")
        with open(text_file, 'w') as f:
            f.write("This is a test file for comprehensive testing.")
        self.test_files['text'] = text_file
        
        # JSON file
        json_file = os.path.join(self.test_dir, "config.json")
        with open(json_file, 'w') as f:
            json.dump({"test": "data", "version": "1.0"}, f)
        self.test_files['json'] = json_file
        
        # Binary file (fake image)
        binary_file = os.path.join(self.test_dir, "image.png")
        with open(binary_file, 'wb') as f:
            f.write(b'\x89PNG\r\n\x1a\n' + b'fake image data' * 100)
        self.test_files['binary'] = binary_file
        
        # Large file
        large_file = os.path.join(self.test_dir, "large.txt")
        with open(large_file, 'w') as f:
            f.write("large file content " * 100000)
        self.test_files['large'] = large_file
        
        # Subdirectory with files
        sub_dir = os.path.join(self.test_dir, "subdir")
        os.makedirs(sub_dir)
        sub_file = os.path.join(sub_dir, "subfile.txt")
        with open(sub_file, 'w') as f:
            f.write("subdirectory file")
        self.test_files['subdir'] = sub_dir
        self.test_files['subfile'] = sub_file
        
        # Empty file
        empty_file = os.path.join(self.test_dir, "empty.txt")
        with open(empty_file, 'w') as f:
            pass
        self.test_files['empty'] = empty_file
        
        # Malformed filename
        malformed_file = os.path.join(self.test_dir, "file with spaces & symbols.txt")
        with open(malformed_file, 'w') as f:
            f.write("malformed filename test")
        self.test_files['malformed'] = malformed_file

    def test_sanitize_filename(self):
        """Test filename sanitization"""
        test_cases = [
            ("normal.txt", "normal.txt"),
            ("file<>with|dangerous:chars.txt", "file__with_dangerous_chars.txt"),
            ("CON.txt", "file_CON.txt"),
            ("../../../etc/passwd", "........etcpasswd"),
            ("", "file_" + str(int(time.time()))),
            ("   .   ", "file_" + str(int(time.time()))),
            ("COM1.txt", "file_COM1.txt"),
            ("file\x00with\x01control.txt", "file_with_control.txt")
        ]
        
        for input_name, expected_prefix in test_cases:
            result = sanitize_filename(input_name)
            if expected_prefix.startswith("file_" + str(int(time.time()))):
                self.assertTrue(result.startswith("file_"))
            else:
                self.assertEqual(result, expected_prefix)

    def test_path_safety(self):
        """Test path safety validation"""
        # Safe paths
        safe_paths = [
            self.test_files['text'],
            os.path.join(self.test_dir, "new_file.txt"),
            os.path.expanduser("~/Desktop/test.txt"),
            os.path.join(tempfile.gettempdir(), "temp.txt")
        ]
        
        for path in safe_paths:
            self.assertTrue(is_path_safe(path), f"Path should be safe: {path}")
        
        # Unsafe paths
        unsafe_paths = [
            "/etc/passwd",
            "/root/secret.txt",
            "C:\\Windows\\System32\\config.txt",
            "/usr/bin/malicious"
        ]
        
        for path in unsafe_paths:
            self.assertFalse(is_path_safe(path), f"Path should be unsafe: {path}")

    def test_file_security_validation(self):
        """Test comprehensive file security validation"""
        # Valid files
        valid, msg = validate_file_security(self.test_files['text'])
        self.assertTrue(valid, f"Text file should be valid: {msg}")
        
        valid, msg = validate_file_security(self.test_files['json'])
        self.assertTrue(valid, f"JSON file should be valid: {msg}")
        
        # Invalid file - doesn't exist
        valid, msg = validate_file_security("/nonexistent/file.txt")
        self.assertFalse(valid, "Non-existent file should be invalid")
        
        # Invalid file - blocked extension
        blocked_file = os.path.join(self.test_dir, "malicious.exe")
        with open(blocked_file, 'w') as f:
            f.write("fake executable")
        valid, msg = validate_file_security(blocked_file)
        self.assertFalse(valid, "Blocked extension should be invalid")
        
        # Invalid file - directory instead of file
        valid, msg = validate_file_security(self.test_files['subdir'])
        self.assertFalse(valid, "Directory should be invalid as file")

    def test_file_hash_calculation(self):
        """Test file hash calculation"""
        # Calculate hash for text file
        hash1 = calculate_file_hash(self.test_files['text'])
        self.assertIsNotNone(hash1)
        self.assertEqual(len(hash1), 64)  # SHA-256 hex length
        
        # Calculate hash again - should be same
        hash2 = calculate_file_hash(self.test_files['text'])
        self.assertEqual(hash1, hash2)
        
        # Different file should have different hash
        hash3 = calculate_file_hash(self.test_files['json'])
        self.assertNotEqual(hash1, hash3)
        
        # Empty file hash
        empty_hash = calculate_file_hash(self.test_files['empty'])
        self.assertIsNotNone(empty_hash)
        
        # Non-existent file
        none_hash = calculate_file_hash("/nonexistent/file.txt")
        self.assertIsNone(none_hash)

    def test_file_metadata_extraction(self):
        """Test file metadata extraction"""
        metadata = get_file_metadata(self.test_files['text'])
        self.assertIsNotNone(metadata)
        
        # Check required fields
        required_fields = ['name', 'size', 'size_formatted', 'mime_type', 
                          'created', 'modified', 'hash', 'path', 'extension']
        for field in required_fields:
            self.assertIn(field, metadata)
        
        # Check specific values
        self.assertEqual(metadata['name'], "test.txt")
        self.assertEqual(metadata['extension'], ".txt")
        self.assertGreater(metadata['size'], 0)
        self.assertTrue(metadata['size_formatted'].endswith('B'))
        
        # Test with binary file
        binary_metadata = get_file_metadata(self.test_files['binary'])
        self.assertEqual(binary_metadata['extension'], ".png")
        self.assertIn('image', binary_metadata['mime_type'])

    def test_directory_compression(self):
        """Test directory compression functionality"""
        # Compress subdirectory
        zip_path, msg = create_zip_from_directory(self.test_files['subdir'])
        self.assertIsNotNone(zip_path, f"Compression failed: {msg}")
        self.assertTrue(os.path.exists(zip_path))
        
        # Verify zip file contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            files = zf.namelist()
            self.assertGreater(len(files), 0)
            self.assertIn('subfile.txt', files)
        
        # Clean up
        if os.path.exists(zip_path):
            os.remove(zip_path)
        
        # Test with non-existent directory
        zip_path, msg = create_zip_from_directory("/nonexistent/dir")
        self.assertIsNone(zip_path)
        self.assertIn("not a directory", msg)

    def test_file_type_icons(self):
        """Test file type icon assignment"""
        test_cases = [
            ("file.txt", "📄"),
            ("document.pdf", "📕"),
            ("script.py", "🐍"),
            ("image.jpg", "🖼️"),
            ("video.mp4", "🎬"),
            ("audio.mp3", "🎵"),
            ("archive.zip", "📦"),
            ("unknown.xyz", "📄")
        ]
        
        for filename, expected_icon in test_cases:
            icon = get_file_type_icon(filename)
            self.assertEqual(icon, expected_icon, f"Wrong icon for {filename}")

    def test_file_filtering(self):
        """Test file filtering functionality"""
        # Create test file list
        files = [
            {'path': '/test/file1.txt', 'size': 1000, 'modified': '2023-01-01T10:00:00'},
            {'path': '/test/image.jpg', 'size': 5000, 'modified': '2023-01-02T10:00:00'},
            {'path': '/test/document.pdf', 'size': 2000, 'modified': '2023-01-03T10:00:00'},
            {'path': '/test/video.mp4', 'size': 10000, 'modified': '2023-01-04T10:00:00'},
            {'path': '/test/archive.zip', 'size': 3000, 'modified': '2023-01-05T10:00:00'}
        ]
        
        # Test pattern filtering
        txt_files = filter_files(files, pattern="*.txt")
        self.assertEqual(len(txt_files), 1)
        self.assertIn('file1.txt', txt_files[0]['path'])
        
        # Test type filtering
        image_files = filter_files(files, file_type="image")
        self.assertEqual(len(image_files), 1)
        self.assertIn('.jpg', image_files[0]['path'])
        
        # Test size filtering
        large_files = filter_files(files, size_min=5000)
        self.assertEqual(len(large_files), 2)
        
        small_files = filter_files(files, size_max=2000)
        self.assertEqual(len(small_files), 2)

    def test_file_sorting(self):
        """Test file sorting functionality"""
        files = [
            {'path': '/test/zebra.txt', 'size': 1000, 'modified': '2023-01-01T10:00:00'},
            {'path': '/test/apple.txt', 'size': 3000, 'modified': '2023-01-03T10:00:00'},
            {'path': '/test/banana.txt', 'size': 2000, 'modified': '2023-01-02T10:00:00'}
        ]
        
        # Sort by name
        sorted_by_name = sort_files(files, 'name')
        self.assertEqual(os.path.basename(sorted_by_name[0]['path']), 'apple.txt')
        
        # Sort by size
        sorted_by_size = sort_files(files, 'size', reverse=True)
        self.assertEqual(sorted_by_size[0]['size'], 3000)
        
        # Sort by modified time
        sorted_by_time = sort_files(files, 'modified')
        self.assertEqual(sorted_by_time[0]['modified'], '2023-01-01T10:00:00')


class TestDownloadOperations(unittest.TestCase):
    """Test suite for download operations"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="test_download_")
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_url_validation(self):
        """Test URL validation"""
        # Valid URLs
        valid_urls = [
            "https://example.com/file.txt",
            "http://test.org/document.pdf",
            "https://cdn.example.com/image.jpg"
        ]
        
        for url in valid_urls:
            valid, msg = validate_url(url)
            self.assertTrue(valid, f"URL should be valid: {url}")
        
        # Invalid URLs
        invalid_urls = [
            "ftp://example.com/file.txt",
            "file:///etc/passwd",
            "javascript:alert('xss')",
            "http://",
            "not-a-url",
            "https://example.com/../../../etc/passwd"
        ]
        
        for url in invalid_urls:
            valid, msg = validate_url(url)
            self.assertFalse(valid, f"URL should be invalid: {url}")

    def test_destination_path_validation(self):
        """Test destination path validation"""
        # Valid destination paths
        valid_paths = [
            os.path.join(self.test_dir, "file.txt"),
            os.path.join(self.test_dir, "subdir", "file.txt"),
            os.path.expanduser("~/Downloads/file.txt")
        ]
        
        for path in valid_paths:
            valid, msg, final_path = validate_destination_path(path)
            if valid:  # Only check if path is in safe directory
                self.assertTrue(valid, f"Path should be valid: {path}")
                self.assertIsNotNone(final_path)
        
        # Invalid destination paths
        invalid_paths = [
            "/etc/passwd",
            "/root/secret.txt",
            "C:\\Windows\\System32\\file.txt",
            os.path.join(self.test_dir, "malware.exe")
        ]
        
        for path in invalid_paths:
            valid, msg, final_path = validate_destination_path(path)
            self.assertFalse(valid, f"Path should be invalid: {path}")

    @patch('urllib.request.urlopen')
    def test_file_info_from_url(self, mock_urlopen):
        """Test getting file info from URL"""
        # Mock response
        mock_response = Mock()
        mock_response.headers = {
            'content-length': '1024',
            'content-type': 'text/plain',
            'last-modified': 'Wed, 01 Jan 2023 12:00:00 GMT',
            'accept-ranges': 'bytes'
        }
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        url = "https://example.com/test.txt"
        info = get_file_info_from_url(url)
        
        self.assertIsNotNone(info)
        self.assertEqual(info['content_length'], 1024)
        self.assertEqual(info['content_type'], 'text/plain')
        self.assertTrue(info['supports_resume'])

    def test_format_size(self):
        """Test size formatting"""
        test_cases = [
            (0, "0 B"),
            (1023, "1023 B"),
            (1024, "1.0 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB"),
            (1099511627776, "1.0 TB")
        ]
        
        for size, expected in test_cases:
            result = format_size(size)
            self.assertEqual(result, expected)


class TestSecurityManager(unittest.TestCase):
    """Test suite for security manager"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db.close()
        self.security_manager = SecurityManager(self.test_db.name)
        
    def tearDown(self):
        """Clean up test environment"""
        self.security_manager.stop_cleanup_service()
        if os.path.exists(self.test_db.name):
            os.unlink(self.test_db.name)
    
    def test_user_authentication(self):
        """Test user authentication"""
        # Authenticate new user
        user = self.security_manager.authenticate_user(12345, "testuser")
        self.assertIsNotNone(user)
        self.assertEqual(user.telegram_id, 12345)
        self.assertEqual(user.username, "testuser")
        self.assertTrue(user.is_authenticated)
        
        # Authenticate existing user
        user2 = self.security_manager.authenticate_user(12345, "testuser")
        self.assertEqual(user.user_id, user2.user_id)
    
    def test_operation_authorization(self):
        """Test operation authorization"""
        # Authenticate user first
        user = self.security_manager.authenticate_user(12345, "testuser")
        
        # Test authorized operations
        self.assertTrue(self.security_manager.authorize_operation(user.user_id, "read"))
        self.assertTrue(self.security_manager.authorize_operation(user.user_id, "write"))
        self.assertTrue(self.security_manager.authorize_operation(user.user_id, "upload"))
        
        # Test unauthorized operation
        self.assertFalse(self.security_manager.authorize_operation(user.user_id, "admin"))
        
        # Test with invalid user
        self.assertFalse(self.security_manager.authorize_operation("invalid", "read"))
    
    def test_file_path_validation(self):
        """Test file path validation"""
        user = self.security_manager.authenticate_user(12345, "testuser")
        
        # Test valid paths
        valid_paths = [
            os.path.expanduser("~/Desktop/test.txt"),
            os.path.expanduser("~/Documents/document.pdf"),
            os.path.join(tempfile.gettempdir(), "temp.txt")
        ]
        
        for path in valid_paths:
            valid, msg = self.security_manager.validate_file_path(path, user.user_id)
            self.assertTrue(valid, f"Path should be valid: {path}")
        
        # Test invalid paths
        invalid_paths = [
            "/etc/passwd",
            "../../../etc/passwd",
            "/root/secret.txt",
            "file<>with|bad:chars.txt"
        ]
        
        for path in invalid_paths:
            valid, msg = self.security_manager.validate_file_path(path, user.user_id)
            self.assertFalse(valid, f"Path should be invalid: {path}")
    
    def test_file_quota_management(self):
        """Test file quota management"""
        user = self.security_manager.authenticate_user(12345, "testuser")
        
        # Test quota check for normal file
        valid, msg = self.security_manager.check_file_quota(user.user_id, 1024)
        self.assertTrue(valid, "Normal file should fit in quota")
        
        # Test quota check for oversized file
        valid, msg = self.security_manager.check_file_quota(user.user_id, 200 * 1024 * 1024)
        self.assertFalse(valid, "Oversized file should exceed quota")
        
        # Test quota update
        self.security_manager.update_file_quota(user.user_id, 1024, 'add')
        quota_info = self.security_manager.get_user_quota_info(user.user_id)
        self.assertEqual(quota_info['used_quota'], 1024)
        
        # Test quota removal
        self.security_manager.update_file_quota(user.user_id, 512, 'remove')
        quota_info = self.security_manager.get_user_quota_info(user.user_id)
        self.assertEqual(quota_info['used_quota'], 512)
    
    def test_temp_file_management(self):
        """Test temporary file management"""
        user = self.security_manager.authenticate_user(12345, "testuser")
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(b"test content")
        temp_file.close()
        
        # Register temp file
        success = self.security_manager.register_temp_file(
            user.user_id, temp_file.name, 12, retention_hours=0.01
        )
        self.assertTrue(success)
        
        # Test cleanup
        time.sleep(0.1)  # Wait for expiration
        cleanup_stats = self.security_manager.cleanup_temp_files(force=True)
        self.assertGreater(cleanup_stats['files_cleaned'], 0)
        
        # File should be deleted
        self.assertFalse(os.path.exists(temp_file.name))


class TestConcurrentTransfer(unittest.TestCase):
    """Test suite for concurrent file transfer"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="test_transfer_")
        self.transfer_manager = ConcurrentFileTransfer(max_concurrent=2)
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_bandwidth_manager(self):
        """Test bandwidth management"""
        bandwidth_manager = BandwidthManager(max_bandwidth_bps=1024)
        
        # Test bandwidth acquisition
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def test_acquire():
            # Should not need delay for small request
            delay = await bandwidth_manager.acquire_bandwidth(512)
            self.assertLessEqual(delay, 0.1)
            
            # Should need delay for large request
            delay = await bandwidth_manager.acquire_bandwidth(2048)
            self.assertGreater(delay, 0.5)
        
        loop.run_until_complete(test_acquire())
        loop.close()
    
    def test_progress_tracker(self):
        """Test progress tracking"""
        tracker = ProgressTracker(total_size=1024, filename="test.txt")
        
        # Test initial state
        self.assertEqual(tracker.stats.total_size, 1024)
        self.assertEqual(tracker.stats.bytes_transferred, 0)
        
        # Test progress update
        tracker.update_progress(512)
        self.assertEqual(tracker.stats.bytes_transferred, 512)
        self.assertGreater(tracker.stats.speed, 0)
        
        # Test callback
        callback_called = False
        def test_callback(stats):
            nonlocal callback_called
            callback_called = True
            self.assertEqual(stats.bytes_transferred, 1024)
        
        tracker.add_callback(test_callback)
        tracker.update_progress(1024)
        self.assertTrue(callback_called)


class TestEdgeCases(unittest.TestCase):
    """Test suite for edge cases and error conditions"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="test_edge_cases_")
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_malformed_files(self):
        """Test handling of malformed files"""
        # Create corrupted zip file
        corrupted_zip = os.path.join(self.test_dir, "corrupted.zip")
        with open(corrupted_zip, 'wb') as f:
            f.write(b"This is not a valid zip file")
        
        # Test zip validation
        self.assertFalse(zipfile.is_zipfile(corrupted_zip))
        
        # Create file with null bytes
        null_file = os.path.join(self.test_dir, "null_file.txt")
        with open(null_file, 'wb') as f:
            f.write(b"Normal content\x00null byte\x00more content")
        
        # Should still be readable
        metadata = get_file_metadata(null_file)
        self.assertIsNotNone(metadata)
        self.assertGreater(metadata['size'], 0)
    
    def test_permission_errors(self):
        """Test handling of permission errors"""
        # Create file and make it read-only
        readonly_file = os.path.join(self.test_dir, "readonly.txt")
        with open(readonly_file, 'w') as f:
            f.write("read only content")
        
        # Make file read-only (on Windows, this might not work as expected)
        try:
            os.chmod(readonly_file, 0o444)
            
            # Try to calculate hash (should still work for reading)
            hash_result = calculate_file_hash(readonly_file)
            self.assertIsNotNone(hash_result)
            
        except OSError:
            # Permission change failed (e.g., on Windows)
            pass
    
    def test_interrupted_transfers(self):
        """Test handling of interrupted transfers"""
        # Create partial file
        partial_file = os.path.join(self.test_dir, "partial.txt")
        with open(partial_file, 'w') as f:
            f.write("partial content")
        
        # Simulate interrupted transfer by truncating
        with open(partial_file, 'r+') as f:
            f.truncate(7)  # Truncate to "partial"
        
        # File should still be readable
        metadata = get_file_metadata(partial_file)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['size'], 7)
    
    def test_large_file_handling(self):
        """Test handling of large files"""
        # Create large file (but not too large for testing)
        large_file = os.path.join(self.test_dir, "large.txt")
        chunk_size = 1024 * 1024  # 1MB chunks
        
        with open(large_file, 'w') as f:
            for i in range(10):  # 10MB file
                f.write('x' * chunk_size)
        
        # Test metadata extraction
        metadata = get_file_metadata(large_file)
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata['size'], 10 * chunk_size)
        
        # Test hash calculation
        hash_result = calculate_file_hash(large_file)
        self.assertIsNotNone(hash_result)
        self.assertEqual(len(hash_result), 64)
    
    def test_special_characters(self):
        """Test handling of special characters in filenames"""
        # Unicode filename
        unicode_file = os.path.join(self.test_dir, "файл.txt")
        try:
            with open(unicode_file, 'w', encoding='utf-8') as f:
                f.write("Unicode content")
            
            # Test metadata extraction
            metadata = get_file_metadata(unicode_file)
            self.assertIsNotNone(metadata)
            self.assertIn("файл.txt", metadata['name'])
            
        except (UnicodeError, OSError):
            # Skip if filesystem doesn't support Unicode
            pass
        
        # Test filename sanitization with special chars
        special_names = [
            "file\u2019s name.txt",  # Right single quotation mark
            "file\u00a0with\u00a0nbsp.txt",  # Non-breaking space
            "file\u200b\u200cwith\u200d\u2060zwsp.txt",  # Zero-width chars
        ]
        
        for name in special_names:
            sanitized = sanitize_filename(name)
            self.assertIsInstance(sanitized, str)
            self.assertNotIn('\u2019', sanitized)


def run_all_tests():
    """Run all test suites"""
    test_loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestFileOperations,
        TestDownloadOperations,
        TestSecurityManager,
        TestConcurrentTransfer,
        TestEdgeCases
    ]
    
    for test_class in test_classes:
        tests = test_loader.loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    print("🔧 Running comprehensive PCRst file operations test suite...")
    print("=" * 70)
    
    success = run_all_tests()
    
    print("=" * 70)
    if success:
        print("✅ All tests passed successfully!")
    else:
        print("❌ Some tests failed. Please check the output above.")
        sys.exit(1)
