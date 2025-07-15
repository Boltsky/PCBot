#!/usr/bin/env python3
"""
Test suite for Path Resolution and Validation Utilities
Tests cross-platform path resolution, normalization, and validation
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
import shutil

# Add the current directory to path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from path_utils import PathUtils
from security_manager import SecurityManager, SecurityConfig

class TestPathUtils(unittest.TestCase):
    """Test cases for PathUtils class"""

    def setUp(self):
        """Set up test environment"""
        # Create a mock security manager
        self.security_manager = Mock(spec=SecurityManager)
        self.security_manager.get_user_directory.return_value = tempfile.gettempdir()
        self.security_manager.validate_file_path.return_value = (True, "Valid path")
        
        # Create PathUtils instance
        self.path_utils = PathUtils(self.security_manager)
        
        # Create test directories
        self.test_dir = tempfile.mkdtemp(prefix='path_utils_test_')
        self.user_id = "test_user_123"
        
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_platform_detection(self):
        """Test platform detection"""
        platform = self.path_utils._detect_platform()
        self.assertIn(platform, ['windows', 'posix', 'other'])
        
    def test_path_normalization(self):
        """Test path normalization"""
        # Test basic normalization
        test_path = os.path.join("folder", "subfolder", "file.txt")
        normalized = self.path_utils._normalize_path(test_path)
        self.assertTrue(os.path.isabs(normalized))
        
        # Test with URL encoding
        encoded_path = "folder%2Fsubfolder%2Ffile.txt"
        normalized = self.path_utils._normalize_path(encoded_path)
        self.assertNotIn('%2F', normalized)
        
    def test_absolute_path_detection(self):
        """Test absolute path detection"""
        # Test absolute path
        abs_path = os.path.abspath("test")
        self.assertTrue(self.path_utils._is_absolute_path(abs_path))
        
        # Test relative path
        rel_path = "relative/path"
        self.assertFalse(self.path_utils._is_absolute_path(rel_path))
        
    def test_path_format_validation(self):
        """Test basic path format validation"""
        # Valid path
        valid_path = "valid/path/file.txt"
        is_valid, message = self.path_utils._validate_path_format(valid_path)
        self.assertTrue(is_valid)
        
        # Invalid path (null bytes)
        invalid_path = "invalid\x00path"
        is_valid, message = self.path_utils._validate_path_format(invalid_path)
        self.assertFalse(is_valid)
        self.assertIn("null bytes", message)
        
        # Empty path
        is_valid, message = self.path_utils._validate_path_format("")
        self.assertFalse(is_valid)
        self.assertIn("non-empty string", message)
        
    def test_security_pattern_validation(self):
        """Test security pattern validation"""
        # Safe path
        safe_path = "documents/file.txt"
        is_valid, message = self.path_utils._validate_security_patterns(safe_path)
        self.assertTrue(is_valid)
        
        # Path traversal attempt
        dangerous_path = "../../../etc/passwd"
        is_valid, message = self.path_utils._validate_security_patterns(dangerous_path)
        self.assertFalse(is_valid)
        self.assertIn("dangerous pattern", message)
        
    def test_path_length_validation(self):
        """Test path length validation"""
        # Normal length path
        normal_path = "a" * 100
        is_valid, message = self.path_utils._validate_path_length(normal_path)
        self.assertTrue(is_valid)
        
        # Extremely long path
        long_path = "a" * 5000
        is_valid, message = self.path_utils._validate_path_length(long_path)
        self.assertFalse(is_valid)
        self.assertIn("Path too long", message)
        
    def test_reserved_names_validation(self):
        """Test reserved names validation"""
        # Test Windows reserved names if on Windows
        if self.path_utils.platform == 'windows':
            reserved_path = "CON.txt"
            is_valid, message = self.path_utils._validate_reserved_names(reserved_path)
            self.assertFalse(is_valid)
            self.assertIn("reserved name", message)
            
        # Test normal filename
        normal_path = "normal_file.txt"
        is_valid, message = self.path_utils._validate_reserved_names(normal_path)
        self.assertTrue(is_valid)
        
    def test_path_resolution(self):
        """Test path resolution"""
        # Test relative path resolution
        relative_path = "subfolder/file.txt"
        success, resolved_path = self.path_utils.resolve_path(self.user_id, relative_path)
        self.assertTrue(success)
        self.assertTrue(os.path.isabs(resolved_path))
        
        # Test absolute path resolution
        abs_path = os.path.join(tempfile.gettempdir(), "file.txt")
        success, resolved_path = self.path_utils.resolve_path(self.user_id, abs_path)
        self.assertTrue(success)
        
    def test_path_validation_comprehensive(self):
        """Test comprehensive path validation"""
        # Test valid path
        valid_path = os.path.join(tempfile.gettempdir(), "valid_file.txt")
        is_valid, message = self.path_utils.validate_path(self.user_id, valid_path)
        self.assertTrue(is_valid)
        
        # Test invalid path (mock security manager to return invalid)
        self.security_manager.validate_file_path.return_value = (False, "Invalid path")
        invalid_path = "/invalid/path"
        is_valid, message = self.path_utils.validate_path(self.user_id, invalid_path)
        self.assertFalse(is_valid)
        
        # Reset security manager mock
        self.security_manager.validate_file_path.return_value = (True, "Valid path")
        
    def test_safe_path_check(self):
        """Test safe path check"""
        safe_path = os.path.join(tempfile.gettempdir(), "safe_file.txt")
        is_safe = self.path_utils.is_safe_path(self.user_id, safe_path)
        self.assertTrue(is_safe)
        
    def test_user_directory_retrieval(self):
        """Test user directory retrieval"""
        user_dir = self.path_utils.get_user_directory(self.user_id)
        self.security_manager.get_user_directory.assert_called_with(self.user_id)
        self.assertEqual(user_dir, tempfile.gettempdir())
        
    def test_path_separator_conversion(self):
        """Test path separator conversion"""
        # Test Windows conversion
        path = "folder/subfolder/file.txt"
        windows_path = self.path_utils.convert_path_separators(path, 'windows')
        self.assertIn('\\', windows_path)
        
        # Test POSIX conversion
        path = "folder\\subfolder\\file.txt"
        posix_path = self.path_utils.convert_path_separators(path, 'posix')
        self.assertIn('/', posix_path)
        
    def test_relative_path_calculation(self):
        """Test relative path calculation"""
        # Mock user directory
        user_dir = tempfile.gettempdir()
        self.security_manager.get_user_directory.return_value = user_dir
        
        # Test valid relative path
        abs_path = os.path.join(user_dir, "subfolder", "file.txt")
        success, rel_path = self.path_utils.get_relative_path(self.user_id, abs_path)
        self.assertTrue(success)
        self.assertFalse(rel_path.startswith('..'))
        
        # Test path outside user directory
        outside_path = os.path.join(os.path.dirname(user_dir), "outside_file.txt")
        success, message = self.path_utils.get_relative_path(self.user_id, outside_path)
        self.assertFalse(success)
        self.assertIn("outside", message)
        
    def test_path_joining(self):
        """Test safe path joining"""
        # Test normal joining
        joined = self.path_utils.join_paths("folder", "subfolder", "file.txt")
        self.assertIn("folder", joined)
        self.assertIn("subfolder", joined)
        self.assertIn("file.txt", joined)
        
        # Test with empty components
        joined = self.path_utils.join_paths("folder", "", "file.txt")
        self.assertIn("folder", joined)
        self.assertIn("file.txt", joined)
        
        # Test with no components
        joined = self.path_utils.join_paths()
        self.assertEqual(joined, "")
        
    def test_filename_sanitization(self):
        """Test filename sanitization"""
        # Test normal filename
        filename = "normal_file.txt"
        sanitized = self.path_utils.sanitize_filename(filename)
        self.assertEqual(sanitized, filename)
        
        # Test filename with invalid characters
        if self.path_utils.platform == 'windows':
            invalid_filename = "file<>:\"|?*.txt"
            sanitized = self.path_utils.sanitize_filename(invalid_filename)
            self.assertNotIn('<', sanitized)
            self.assertNotIn('>', sanitized)
            self.assertNotIn(':', sanitized)
            self.assertNotIn('"', sanitized)
            self.assertNotIn('|', sanitized)
            self.assertNotIn('?', sanitized)
            self.assertNotIn('*', sanitized)
            
        # Test empty filename
        sanitized = self.path_utils.sanitize_filename("")
        self.assertEqual(sanitized, "unnamed")
        
        # Test filename with control characters
        control_filename = "file\x01\x02\x03.txt"
        sanitized = self.path_utils.sanitize_filename(control_filename)
        self.assertNotIn('\x01', sanitized)
        self.assertNotIn('\x02', sanitized)
        self.assertNotIn('\x03', sanitized)
        
    def test_path_info_retrieval(self):
        """Test path information retrieval"""
        test_path = os.path.join(self.test_dir, "test_file.txt")
        
        # Create test file
        with open(test_path, 'w') as f:
            f.write("test content")
        
        path_info = self.path_utils.get_path_info(test_path)
        
        self.assertEqual(path_info['original'], test_path)
        self.assertIn('normalized', path_info)
        self.assertIn('absolute', path_info)
        self.assertIn('exists', path_info)
        self.assertIn('is_file', path_info)
        self.assertIn('is_dir', path_info)
        self.assertIn('parent', path_info)
        self.assertIn('name', path_info)
        self.assertIn('stem', path_info)
        self.assertIn('suffix', path_info)
        self.assertIn('parts', path_info)
        self.assertIn('platform', path_info)
        
        # Test with non-existent path
        nonexistent_path = os.path.join(self.test_dir, "nonexistent.txt")
        path_info = self.path_utils.get_path_info(nonexistent_path)
        self.assertFalse(path_info['exists'])
        
    def test_cross_platform_compatibility(self):
        """Test cross-platform compatibility"""
        # Test path with mixed separators
        mixed_path = "folder\\subfolder/file.txt"
        normalized = self.path_utils._normalize_path(mixed_path)
        
        # Should not contain mixed separators after normalization
        if self.path_utils.platform == 'windows':
            self.assertNotIn('/', normalized)
        else:
            self.assertNotIn('\\', normalized)
            
    def test_error_handling(self):
        """Test error handling in path operations"""
        # Test with None security manager
        with self.assertRaises(AttributeError):
            path_utils = PathUtils(None)
            path_utils.resolve_path(self.user_id, "test")
            
        # Test with invalid path characters
        invalid_path = "test\x00path"
        is_valid, message = self.path_utils.validate_path(self.user_id, invalid_path)
        self.assertFalse(is_valid)
        
    def test_security_integration(self):
        """Test integration with security manager"""
        test_path = "test/path/file.txt"
        
        # Test successful security validation
        self.security_manager.validate_file_path.return_value = (True, "Valid")
        is_valid, message = self.path_utils.validate_path(self.user_id, test_path)
        self.assertTrue(is_valid)
        
        # Test failed security validation
        self.security_manager.validate_file_path.return_value = (False, "Security violation")
        is_valid, message = self.path_utils.validate_path(self.user_id, test_path)
        self.assertFalse(is_valid)
        self.assertIn("Security violation", message)
        
        # Verify security manager was called
        self.security_manager.validate_file_path.assert_called()


class TestPathUtilsIntegration(unittest.TestCase):
    """Integration tests with real SecurityManager"""
    
    def setUp(self):
        """Set up integration test environment"""
        # Create real security manager with temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        self.security_manager = SecurityManager(self.temp_db.name)
        self.path_utils = PathUtils(self.security_manager)
        self.user_id = "integration_test_user"
        
        # Authenticate test user
        self.user = self.security_manager.authenticate_user(12345, "test_user")
        
    def tearDown(self):
        """Clean up integration test environment"""
        self.security_manager.stop_cleanup_service()
        os.unlink(self.temp_db.name)
        
    def test_real_security_validation(self):
        """Test with real security manager validation"""
        # Test valid path within safe directories
        safe_path = os.path.join(tempfile.gettempdir(), "test_file.txt")
        is_valid, message = self.path_utils.validate_path(self.user_id, safe_path)
        self.assertTrue(is_valid)
        
        # Test path outside safe directories (should fail)
        if os.name == 'nt':
            unsafe_path = "C:\\Windows\\System32\\config"
        else:
            unsafe_path = "/etc/passwd"
            
        is_valid, message = self.path_utils.validate_path(self.user_id, unsafe_path)
        self.assertFalse(is_valid)
        
    def test_user_directory_management(self):
        """Test user directory management"""
        # Get user directory
        user_dir = self.path_utils.get_user_directory(self.user_id)
        self.assertTrue(os.path.exists(user_dir))
        
        # Test path resolution relative to user directory
        relative_path = "subfolder/test.txt"
        success, resolved = self.path_utils.resolve_path(self.user_id, relative_path)
        self.assertTrue(success)
        self.assertTrue(resolved.startswith(user_dir))


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
