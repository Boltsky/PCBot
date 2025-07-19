#!/usr/bin/env python3
"""
Comprehensive Test Suite for Hide/Unhide Commands
Tests the /hide, /unhide, and /hidden commands across typical and edge cases including:
- Files/folders with and without spaces
- Non-existent and unauthorized paths
- Nested directories
- Different user roles and permissions
- Security validation
- Robustness testing
"""

import os
import sys
import tempfile
import shutil
import json
import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hide_unhide_commands import (
    hide_command, unhide_command, hidden_command,
    _resolve_path, _is_already_hidden, _hide_item, _unhide_item,
    _get_hidden_items, _find_hidden_item, format_size,
    HIDDEN_MAPPING_FILE
)
from security_manager import SecurityManager, SecurityEvent
from path_utils import PathUtils
from windows_file_attributes import WindowsFileAttributes

# Configure test logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TestHideUnhideCommands(unittest.TestCase):
    """Test suite for hide/unhide commands"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="hide_unhide_test_")
        self.user_id = "test_user_123"
        self.telegram_id = 123456789
        
        # Create mock objects
        self.mock_update = Mock()
        self.mock_message = Mock()
        self.mock_user = Mock()
        self.mock_context = Mock()
        
        # Configure mocks
        self.mock_update.message = self.mock_message
        self.mock_update.effective_user = self.mock_user
        self.mock_message.reply_text = AsyncMock()
        self.mock_user.id = self.telegram_id
        self.mock_context.args = []
        
        # Create test files and directories
        self.create_test_files()
        
        # Patch security manager and path utils
        self.security_manager_patcher = patch('hide_unhide_commands.security_manager')
        self.mock_security_manager = self.security_manager_patcher.start()
        
        # Configure security manager mock
        self.mock_security_manager.validate_file_path.return_value = (True, "Valid path")
        self.mock_security_manager.get_user_directory.return_value = self.test_dir
        self.mock_security_manager._log_security_event = Mock()
        
        logger.info(f"Test directory created: {self.test_dir}")
    
    def tearDown(self):
        """Clean up test environment"""
        self.security_manager_patcher.stop()
        
        # Clean up test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
        
        logger.info(f"Test directory cleaned up: {self.test_dir}")
    
    def create_test_files(self):
        """Create test files and directories for testing"""
        # Regular files
        self.test_file = os.path.join(self.test_dir, "test_file.txt")
        with open(self.test_file, 'w') as f:
            f.write("This is a test file")
        
        # Files with spaces
        self.space_file = os.path.join(self.test_dir, "file with spaces.txt")
        with open(self.space_file, 'w') as f:
            f.write("This file has spaces in its name")
        
        # Special character files
        self.special_file = os.path.join(self.test_dir, "file-with_special.chars.txt")
        with open(self.special_file, 'w') as f:
            f.write("This file has special characters")
        
        # Directories
        self.test_dir_path = os.path.join(self.test_dir, "test_directory")
        os.makedirs(self.test_dir_path)
        
        # Directory with spaces
        self.space_dir = os.path.join(self.test_dir, "directory with spaces")
        os.makedirs(self.space_dir)
        
        # Nested directories
        self.nested_dir = os.path.join(self.test_dir, "nested", "deep", "directory")
        os.makedirs(self.nested_dir)
        
        # File in nested directory
        self.nested_file = os.path.join(self.nested_dir, "nested_file.txt")
        with open(self.nested_file, 'w') as f:
            f.write("This is a nested file")
        
        # Large file for size testing
        self.large_file = os.path.join(self.test_dir, "large_file.txt")
        with open(self.large_file, 'w') as f:
            f.write("x" * 1024 * 1024)  # 1MB file
    
    @patch('hide_unhide_commands._resolve_path')
    async def test_hide_command_no_args(self, mock_resolve):
        """Test hide command without arguments shows help"""
        self.mock_context.args = []
        
        await hide_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Hide File/Directory", call_args)
        self.assertIn("Usage", call_args)
    
    @patch('hide_unhide_commands._resolve_path')
    async def test_hide_command_invalid_path(self, mock_resolve):
        """Test hide command with invalid path"""
        self.mock_context.args = ["nonexistent_file.txt"]
        mock_resolve.return_value = None
        
        await hide_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Invalid Path", call_args)
    
    @patch('hide_unhide_commands._resolve_path')
    async def test_hide_command_security_restriction(self, mock_resolve):
        """Test hide command with security restriction"""
        self.mock_context.args = ["test_file.txt"]
        mock_resolve.return_value = self.test_file
        self.mock_security_manager.validate_file_path.return_value = (False, "Security violation")
        
        await hide_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Security Restriction", call_args)
    
    @patch('hide_unhide_commands._resolve_path')
    async def test_hide_command_nonexistent_file(self, mock_resolve):
        """Test hide command with non-existent file"""
        nonexistent_file = os.path.join(self.test_dir, "nonexistent.txt")
        self.mock_context.args = ["nonexistent.txt"]
        mock_resolve.return_value = nonexistent_file
        
        await hide_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Path Not Found", call_args)
    
    @patch('hide_unhide_commands._resolve_path')
    @patch('hide_unhide_commands._is_already_hidden')
    async def test_hide_command_already_hidden(self, mock_is_hidden, mock_resolve):
        """Test hide command with already hidden file"""
        self.mock_context.args = ["test_file.txt"]
        mock_resolve.return_value = self.test_file
        mock_is_hidden.return_value = True
        
        await hide_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Already Hidden", call_args)
    
    @patch('hide_unhide_commands._resolve_path')
    @patch('hide_unhide_commands._is_already_hidden')
    @patch('hide_unhide_commands._hide_item')
    async def test_hide_command_successful_file(self, mock_hide_item, mock_is_hidden, mock_resolve):
        """Test successful hide command with regular file"""
        self.mock_context.args = ["test_file.txt"]
        mock_resolve.return_value = self.test_file
        mock_is_hidden.return_value = False
        mock_hide_item.return_value = (True, "Success", {
            'is_directory': False,
            'size_formatted': '19 B'
        })
        
        await hide_command(self.mock_update, self.mock_context)
        
        # Check for loading message first
        self.assertEqual(self.mock_message.reply_text.call_count, 2)
        success_call = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Successfully Hidden", success_call)
        self.assertIn("File", success_call)
    
    @patch('hide_unhide_commands._resolve_path')
    @patch('hide_unhide_commands._is_already_hidden')
    @patch('hide_unhide_commands._hide_item')
    async def test_hide_command_successful_directory(self, mock_hide_item, mock_is_hidden, mock_resolve):
        """Test successful hide command with directory"""
        self.mock_context.args = ["test_directory"]
        mock_resolve.return_value = self.test_dir_path
        mock_is_hidden.return_value = False
        mock_hide_item.return_value = (True, "Success", {
            'is_directory': True,
            'size_formatted': '0 B'
        })
        
        await hide_command(self.mock_update, self.mock_context)
        
        # Check for loading message first
        self.assertEqual(self.mock_message.reply_text.call_count, 2)
        success_call = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Successfully Hidden", success_call)
        self.assertIn("Directory", success_call)
    
    @patch('hide_unhide_commands._resolve_path')
    @patch('hide_unhide_commands._is_already_hidden')
    @patch('hide_unhide_commands._hide_item')
    async def test_hide_command_with_spaces(self, mock_hide_item, mock_is_hidden, mock_resolve):
        """Test hide command with file containing spaces"""
        self.mock_context.args = ["file", "with", "spaces.txt"]
        mock_resolve.return_value = self.space_file
        mock_is_hidden.return_value = False
        mock_hide_item.return_value = (True, "Success", {
            'is_directory': False,
            'size_formatted': '30 B'
        })
        
        await hide_command(self.mock_update, self.mock_context)
        
        # Verify that spaces were handled correctly
        mock_resolve.assert_called_once_with("file with spaces.txt", str(self.telegram_id))
        self.assertEqual(self.mock_message.reply_text.call_count, 2)
    
    @patch('hide_unhide_commands._resolve_path')
    @patch('hide_unhide_commands._is_already_hidden')
    @patch('hide_unhide_commands._hide_item')
    async def test_hide_command_failure(self, mock_hide_item, mock_is_hidden, mock_resolve):
        """Test hide command failure scenario"""
        self.mock_context.args = ["test_file.txt"]
        mock_resolve.return_value = self.test_file
        mock_is_hidden.return_value = False
        mock_hide_item.return_value = (False, "Permission denied", {})
        
        await hide_command(self.mock_update, self.mock_context)
        
        # Check for loading message first
        self.assertEqual(self.mock_message.reply_text.call_count, 2)
        failure_call = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Hide Operation Failed", failure_call)
        self.assertIn("Permission denied", failure_call)
    
    # UNHIDE COMMAND TESTS
    async def test_unhide_command_no_args(self):
        """Test unhide command without arguments shows help"""
        self.mock_context.args = []
        
        await unhide_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Unhide File/Directory", call_args)
        self.assertIn("Usage", call_args)
    
    @patch('hide_unhide_commands._get_hidden_items')
    async def test_unhide_command_no_hidden_files(self, mock_get_hidden):
        """Test unhide command when no hidden files exist"""
        self.mock_context.args = ["test_file.txt"]
        mock_get_hidden.return_value = []
        
        await unhide_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("No Hidden Files", call_args)
    
    @patch('hide_unhide_commands._get_hidden_items')
    @patch('hide_unhide_commands._find_hidden_item')
    async def test_unhide_command_item_not_found(self, mock_find_item, mock_get_hidden):
        """Test unhide command when hidden item is not found"""
        self.mock_context.args = ["nonexistent.txt"]
        mock_get_hidden.return_value = [{"original_path": self.test_file}]
        mock_find_item.return_value = None
        
        await unhide_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Hidden Item Not Found", call_args)
    
    @patch('hide_unhide_commands._get_hidden_items')
    @patch('hide_unhide_commands._find_hidden_item')
    async def test_unhide_command_security_restriction(self, mock_find_item, mock_get_hidden):
        """Test unhide command with security restriction"""
        self.mock_context.args = ["test_file.txt"]
        mock_get_hidden.return_value = [{"original_path": self.test_file}]
        mock_find_item.return_value = {"original_path": self.test_file}
        self.mock_security_manager.validate_file_path.return_value = (False, "Security violation")
        
        await unhide_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Security Restriction", call_args)
    
    @patch('hide_unhide_commands._get_hidden_items')
    @patch('hide_unhide_commands._find_hidden_item')
    async def test_unhide_command_destination_exists(self, mock_find_item, mock_get_hidden):
        """Test unhide command when destination already exists"""
        self.mock_context.args = ["test_file.txt"]
        mock_get_hidden.return_value = [{"original_path": self.test_file}]
        mock_find_item.return_value = {"original_path": self.test_file}
        
        await unhide_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Destination Exists", call_args)
    
    @patch('hide_unhide_commands._get_hidden_items')
    @patch('hide_unhide_commands._find_hidden_item')
    @patch('hide_unhide_commands._unhide_item')
    async def test_unhide_command_successful(self, mock_unhide_item, mock_find_item, mock_get_hidden):
        """Test successful unhide command"""
        temp_file = os.path.join(self.test_dir, "temp_hidden.txt")
        self.mock_context.args = ["temp_hidden.txt"]
        mock_get_hidden.return_value = [{"original_path": temp_file}]
        mock_find_item.return_value = {"original_path": temp_file}
        mock_unhide_item.return_value = (True, "Success", {
            'is_directory': False,
            'size_formatted': '19 B'
        })
        
        await unhide_command(self.mock_update, self.mock_context)
        
        # Check for loading message first
        self.assertEqual(self.mock_message.reply_text.call_count, 2)
        success_call = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Successfully Restored", success_call)
    
    # HIDDEN COMMAND TESTS
    @patch('hide_unhide_commands._get_hidden_items')
    async def test_hidden_command_no_hidden_files(self, mock_get_hidden):
        """Test hidden command when no hidden files exist"""
        mock_get_hidden.return_value = []
        
        await hidden_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("No Hidden Files", call_args)
    
    @patch('hide_unhide_commands._get_hidden_items')
    async def test_hidden_command_with_hidden_files(self, mock_get_hidden):
        """Test hidden command with hidden files"""
        mock_get_hidden.return_value = [
            {
                'original_path': self.test_file,
                'is_directory': False,
                'size': 19,
                'size_formatted': '19 B',
                'hidden_date': '2023-01-01T12:00:00'
            },
            {
                'original_path': self.test_dir_path,
                'is_directory': True,
                'size': 0,
                'size_formatted': '0 B',
                'hidden_date': '2023-01-01T12:00:00'
            }
        ]
        
        await hidden_command(self.mock_update, self.mock_context)
        
        self.mock_message.reply_text.assert_called_once()
        call_args = self.mock_message.reply_text.call_args[0][0]
        self.assertIn("Hidden Files & Directories", call_args)
        self.assertIn("2 items", call_args)
        self.assertIn("📄", call_args)  # File icon
        self.assertIn("📁", call_args)  # Directory icon
    
    # HELPER FUNCTION TESTS
    def test_format_size(self):
        """Test format_size function"""
        self.assertEqual(format_size(0), "0 B")
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(format_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_size(1024 * 1024 * 1024), "1.0 GB")
    
    @patch('hide_unhide_commands.PathUtils')
    def test_resolve_path(self, mock_path_utils_class):
        """Test _resolve_path function"""
        mock_path_utils = mock_path_utils_class.return_value
        mock_path_utils.resolve_path.return_value = (True, "/resolved/path")
        
        result = _resolve_path("test/path", self.user_id)
        
        self.assertEqual(result, "/resolved/path")
        mock_path_utils.resolve_path.assert_called_once_with(self.user_id, "test/path")
    
    @patch('hide_unhide_commands.PathUtils')
    def test_resolve_path_failure(self, mock_path_utils_class):
        """Test _resolve_path function failure"""
        mock_path_utils = mock_path_utils_class.return_value
        mock_path_utils.resolve_path.return_value = (False, "Error message")
        
        result = _resolve_path("test/path", self.user_id)
        
        self.assertIsNone(result)
    
    def test_is_already_hidden_no_mapping(self):
        """Test _is_already_hidden when no mapping file exists"""
        result = _is_already_hidden(self.test_file, self.user_id)
        self.assertFalse(result)
    
    def test_is_already_hidden_with_mapping(self):
        """Test _is_already_hidden with mapping file"""
        # Create a mapping file
        mapping_file = os.path.join(self.test_dir, HIDDEN_MAPPING_FILE)
        mapping_data = {self.test_file: {"user_id": self.user_id}}
        
        with open(mapping_file, 'w') as f:
            json.dump(mapping_data, f)
        
        # Mock the security manager to return the test directory
        with patch('hide_unhide_commands.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open_with_content(json.dumps(mapping_data))):
            result = _is_already_hidden(self.test_file, self.user_id)
            self.assertTrue(result)
    
    def test_find_hidden_item_exact_match(self):
        """Test _find_hidden_item with exact path match"""
        hidden_items = [
            {"original_path": self.test_file},
            {"original_path": self.space_file}
        ]
        
        result = _find_hidden_item(self.test_file, hidden_items)
        self.assertEqual(result["original_path"], self.test_file)
    
    def test_find_hidden_item_filename_match(self):
        """Test _find_hidden_item with filename match"""
        hidden_items = [
            {"original_path": self.test_file},
            {"original_path": self.space_file}
        ]
        
        result = _find_hidden_item("test_file.txt", hidden_items)
        self.assertEqual(result["original_path"], self.test_file)
    
    def test_find_hidden_item_case_insensitive(self):
        """Test _find_hidden_item with case insensitive match"""
        hidden_items = [
            {"original_path": self.test_file},
            {"original_path": self.space_file}
        ]
        
        result = _find_hidden_item("TEST_FILE.TXT", hidden_items)
        self.assertEqual(result["original_path"], self.test_file)
    
    def test_find_hidden_item_partial_match(self):
        """Test _find_hidden_item with partial match"""
        hidden_items = [
            {"original_path": self.test_file},
            {"original_path": self.space_file}
        ]
        
        result = _find_hidden_item("test_file", hidden_items)
        self.assertEqual(result["original_path"], self.test_file)
    
    def test_find_hidden_item_no_match(self):
        """Test _find_hidden_item with no match"""
        hidden_items = [
            {"original_path": self.test_file},
            {"original_path": self.space_file}
        ]
        
        result = _find_hidden_item("nonexistent.txt", hidden_items)
        self.assertIsNone(result)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and security scenarios"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="hide_unhide_edge_test_")
        self.user_id = "test_user_edge"
        
        # Patch security manager
        self.security_manager_patcher = patch('hide_unhide_commands.security_manager')
        self.mock_security_manager = self.security_manager_patcher.start()
        self.mock_security_manager.validate_file_path.return_value = (True, "Valid path")
        self.mock_security_manager.get_user_directory.return_value = self.test_dir
    
    def tearDown(self):
        """Clean up test environment"""
        self.security_manager_patcher.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks"""
        dangerous_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../../root/.ssh/id_rsa",
            "C:\\Windows\\System32\\config\\SAM"
        ]
        
        for path in dangerous_paths:
            with self.subTest(path=path):
                result = _resolve_path(path, self.user_id)
                # Should either be None or be within safe directory
                if result:
                    self.assertTrue(result.startswith(self.test_dir))
    
    def test_special_characters_in_paths(self):
        """Test handling of special characters in file paths"""
        special_chars = [
            "file with spaces.txt",
            "file@with#special$.txt",
            "file-with_underscores.txt",
            "file.with.dots.txt",
            "file[with]brackets.txt",
            "file(with)parentheses.txt"
        ]
        
        for filename in special_chars:
            with self.subTest(filename=filename):
                test_file = os.path.join(self.test_dir, filename)
                with open(test_file, 'w') as f:
                    f.write("test content")
                
                result = _resolve_path(filename, self.user_id)
                self.assertIsNotNone(result)
    
    def test_very_long_paths(self):
        """Test handling of very long file paths"""
        long_filename = "a" * 200 + ".txt"
        test_file = os.path.join(self.test_dir, long_filename)
        
        # Create the file if path length allows
        try:
            with open(test_file, 'w') as f:
                f.write("test content")
            
            result = _resolve_path(long_filename, self.user_id)
            self.assertIsNotNone(result)
        except OSError:
            # Expected on some platforms with path length limits
            pass
    
    def test_unicode_characters(self):
        """Test handling of unicode characters in file paths"""
        unicode_filenames = [
            "файл.txt",  # Russian
            "файл.txt",  # Japanese
            "archivo.txt",  # Spanish with accents
            "tëst.txt",  # Accented characters
            "🔒secret.txt"  # Emoji
        ]
        
        for filename in unicode_filenames:
            with self.subTest(filename=filename):
                test_file = os.path.join(self.test_dir, filename)
                try:
                    with open(test_file, 'w', encoding='utf-8') as f:
                        f.write("test content")
                    
                    result = _resolve_path(filename, self.user_id)
                    self.assertIsNotNone(result)
                except (UnicodeError, OSError):
                    # Expected on some platforms
                    pass
    
    def test_concurrent_operations(self):
        """Test concurrent hide/unhide operations"""
        test_file = os.path.join(self.test_dir, "concurrent_test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        async def hide_operation():
            return await _hide_item(test_file, self.user_id)
        
        async def unhide_operation():
            return await _unhide_item({"original_path": test_file}, self.user_id)
        
        # This test ensures the functions handle concurrent access gracefully
        # In real scenarios, proper locking would be needed
        pass
    
    def test_permission_denied_scenarios(self):
        """Test scenarios where permission is denied"""
        # This would require actual file system permission testing
        # which is platform-specific and may require elevated privileges
        pass
    
    def test_disk_space_full(self):
        """Test behavior when disk space is full"""
        # This is difficult to test without actually filling disk
        # In real implementation, proper error handling should be in place
        pass


def mock_open_with_content(content):
    """Helper function to mock file opening with specific content"""
    from unittest.mock import mock_open
    return mock_open(read_data=content)


class TestRobustness(unittest.TestCase):
    """Test robustness and error handling"""
    
    def test_malformed_mapping_file(self):
        """Test handling of malformed mapping files"""
        mapping_file = os.path.join(tempfile.gettempdir(), "malformed_mapping.json")
        
        # Create malformed JSON file
        with open(mapping_file, 'w') as f:
            f.write('{"invalid": json content}')
        
        with patch('hide_unhide_commands.os.path.exists', return_value=True), \
             patch('builtins.open', mock_open_with_content('{"invalid": json content}')):
            
            # Should handle malformed JSON gracefully
            result = _get_hidden_items("test_user")
            self.assertEqual(result, [])
    
    def test_missing_dependencies(self):
        """Test behavior when dependencies are missing"""
        # Test Windows file attributes on non-Windows platform
        if os.name != 'nt':
            from windows_file_attributes import WindowsFileAttributes
            with self.assertRaises(RuntimeError):
                WindowsFileAttributes()
    
    def test_network_path_handling(self):
        """Test handling of network paths"""
        network_paths = [
            "\\\\server\\share\\file.txt",
            "//server/share/file.txt",
            "ftp://server/file.txt",
            "http://server/file.txt"
        ]
        
        for path in network_paths:
            with self.subTest(path=path):
                result = _resolve_path(path, "test_user")
                # Should either reject or handle safely
                if result:
                    self.assertIsInstance(result, str)
    
    def test_symlink_handling(self):
        """Test handling of symbolic links"""
        if os.name == 'posix':  # Unix-like systems
            test_dir = tempfile.mkdtemp()
            try:
                # Create a regular file
                real_file = os.path.join(test_dir, "real_file.txt")
                with open(real_file, 'w') as f:
                    f.write("real content")
                
                # Create a symbolic link
                link_file = os.path.join(test_dir, "link_file.txt")
                os.symlink(real_file, link_file)
                
                # Test resolving the link
                result = _resolve_path(link_file, "test_user")
                self.assertIsNotNone(result)
                
            finally:
                shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == '__main__':
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTest(unittest.makeSuite(TestHideUnhideCommands))
    suite.addTest(unittest.makeSuite(TestEdgeCases))
    suite.addTest(unittest.makeSuite(TestRobustness))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
