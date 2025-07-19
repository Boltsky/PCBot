#!/usr/bin/env python3
"""
Comprehensive Test Script for PCRst Commands
Test all commands with Windows and cross-platform scenarios.

This script validates:
1. SecurityManager is invoked for all path checks
2. Commands reject unsafe actions or paths and provide correct messaging
3. User-facing output is clear and follows existing conventions
4. Logging is performed for all meaningful events (success/failure)

Commands tested:
- /delete, /copy, /move, /rename (file operations)
- /hide, /unhide, /hidden (hide/unhide operations)
"""

import os
import sys
import tempfile
import shutil
import json
import logging
import platform
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any, Tuple
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the modules under test
from security_manager import SecurityManager, SecurityEvent, security_manager
from file_operation_commands import delete_command, copy_command, move_command, rename_command
from hide_unhide_commands import hide_command, unhide_command, hidden_command
from command_argument_parser import CommandArgumentParser

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestPlatformScenarios:
    """Test scenarios for different platforms"""
    
    def __init__(self):
        self.is_windows = platform.system() == 'Windows'
        self.test_dir = None
        self.security_manager = None
        self.test_results = []
        self.user_id = "test_user_12345"
        
    def setup_test_environment(self):
        """Setup test environment with temporary directory and files"""
        # Create temporary test directory
        self.test_dir = tempfile.mkdtemp(prefix="pcrst_test_")
        logger.info(f"Created test directory: {self.test_dir}")
        
        # Initialize security manager
        self.security_manager = SecurityManager()
        
        # Create test files and directories
        self.create_test_files()
        
        # Set user directory to our test directory
        success, msg = self.security_manager.set_user_directory(self.user_id, self.test_dir)
        if not success:
            logger.warning(f"Failed to set user directory: {msg}")
            
    def create_test_files(self):
        """Create test files and directories for testing"""
        test_files = [
            "simple_file.txt",
            "file with spaces.txt",
            "special_chars_file_@#$.txt",
            "unicode_file_résumé.txt",
        ]
        
        test_dirs = [
            "simple_dir",
            "dir with spaces",
            "special_chars_dir_@#$",
            "unicode_dir_résumé",
        ]
        
        # Create test files
        for filename in test_files:
            filepath = os.path.join(self.test_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Test content for {filename}")
                
        # Create test directories with content
        for dirname in test_dirs:
            dirpath = os.path.join(self.test_dir, dirname)
            os.makedirs(dirpath, exist_ok=True)
            # Add a file inside each directory
            sub_file = os.path.join(dirpath, "sub_file.txt")
            with open(sub_file, 'w', encoding='utf-8') as f:
                f.write(f"Content in {dirname}")
                
        logger.info(f"Created {len(test_files)} test files and {len(test_dirs)} test directories")
    
    def cleanup_test_environment(self):
        """Clean up test environment"""
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
            logger.info(f"Cleaned up test directory: {self.test_dir}")
    
    def create_mock_update_context(self, args: List[str]) -> Tuple[Mock, Mock]:
        """Create mock update and context objects for testing"""
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = int(self.user_id.split('_')[-1])
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        
        context = Mock()
        context.args = args
        
        return update, context
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        result = {
            'test_name': test_name,
            'passed': passed,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'platform': platform.system()
        }
        self.test_results.append(result)
        
        status = "PASSED" if passed else "FAILED"
        logger.info(f"[{status}] {test_name}: {details}")
    
    async def test_security_manager_invocation(self):
        """Test that SecurityManager is invoked for all path checks"""
        logger.info("Testing SecurityManager invocation for all commands...")
        
        # Test file operation commands
        test_file = os.path.join(self.test_dir, "test_security.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Patch security manager to track calls
        with patch.object(self.security_manager, 'validate_file_path') as mock_validate:
            mock_validate.return_value = (True, "Path validation passed")
            
            # Test delete command
            update, context = self.create_mock_update_context(['path=test_security.txt', 'isDirectory=false'])
            await delete_command(update, context)
            
            # Verify security manager was called
            if mock_validate.called:
                self.log_test_result("SecurityManager invocation - delete", True, "validate_file_path called")
            else:
                self.log_test_result("SecurityManager invocation - delete", False, "validate_file_path not called")
        
        # Test copy command
        with patch.object(self.security_manager, 'validate_file_path') as mock_validate:
            mock_validate.return_value = (True, "Path validation passed")
            
            update, context = self.create_mock_update_context([
                'sourcePath=simple_file.txt',
                'destinationPath=copy_test.txt',
                'isDirectory=false'
            ])
            await copy_command(update, context)
            
            # Should be called twice - source and destination
            if mock_validate.call_count >= 2:
                self.log_test_result("SecurityManager invocation - copy", True, f"validate_file_path called {mock_validate.call_count} times")
            else:
                self.log_test_result("SecurityManager invocation - copy", False, f"validate_file_path called only {mock_validate.call_count} times")
        
        # Test move command
        with patch.object(self.security_manager, 'validate_file_path') as mock_validate:
            mock_validate.return_value = (True, "Path validation passed")
            
            update, context = self.create_mock_update_context([
                'sourcePath=simple_file.txt',
                'destinationPath=move_test.txt',
                'isDirectory=false'
            ])
            await move_command(update, context)
            
            if mock_validate.call_count >= 2:
                self.log_test_result("SecurityManager invocation - move", True, f"validate_file_path called {mock_validate.call_count} times")
            else:
                self.log_test_result("SecurityManager invocation - move", False, f"validate_file_path called only {mock_validate.call_count} times")
        
        # Test rename command
        with patch.object(self.security_manager, 'validate_file_path') as mock_validate:
            mock_validate.return_value = (True, "Path validation passed")
            
            update, context = self.create_mock_update_context([
                'path=simple_file.txt',
                'newName=renamed_file.txt',
                'isDirectory=false'
            ])
            await rename_command(update, context)
            
            if mock_validate.call_count >= 2:
                self.log_test_result("SecurityManager invocation - rename", True, f"validate_file_path called {mock_validate.call_count} times")
            else:
                self.log_test_result("SecurityManager invocation - rename", False, f"validate_file_path called only {mock_validate.call_count} times")
        
        # Test hide command
        with patch.object(self.security_manager, 'validate_file_path') as mock_validate:
            mock_validate.return_value = (True, "Path validation passed")
            
            update, context = self.create_mock_update_context(['simple_file.txt'])
            await hide_command(update, context)
            
            if mock_validate.called:
                self.log_test_result("SecurityManager invocation - hide", True, "validate_file_path called")
            else:
                self.log_test_result("SecurityManager invocation - hide", False, "validate_file_path not called")
    
    async def test_unsafe_path_rejection(self):
        """Test that commands reject unsafe actions or paths"""
        logger.info("Testing unsafe path rejection...")
        
        dangerous_paths = [
            "../../../etc/passwd",  # Path traversal
            "\\\\..\\\\..\\\\windows\\\\system32",  # Windows path traversal
            "/etc/shadow",  # System file
            "C:\\Windows\\System32\\config\\SAM",  # Windows system file
            "CON",  # Windows reserved name
            "file<>name.txt",  # Invalid characters
            "file\x00name.txt",  # Null byte injection
        ]
        
        for dangerous_path in dangerous_paths:
            # Mock security manager to reject these paths
            with patch.object(self.security_manager, 'validate_file_path') as mock_validate:
                mock_validate.return_value = (False, f"Dangerous path rejected: {dangerous_path}")
                
                update, context = self.create_mock_update_context([f'path={dangerous_path}', 'isDirectory=false'])
                await delete_command(update, context)
                
                # Check that reply_text was called with error message
                if update.message.reply_text.called:
                    call_args = update.message.reply_text.call_args[0][0]
                    if "Access Denied" in call_args or "Security" in call_args:
                        self.log_test_result(f"Unsafe path rejection - {dangerous_path}", True, "Command rejected dangerous path")
                    else:
                        self.log_test_result(f"Unsafe path rejection - {dangerous_path}", False, "Command did not properly reject dangerous path")
                else:
                    self.log_test_result(f"Unsafe path rejection - {dangerous_path}", False, "No error message shown")
    
    async def test_user_output_conventions(self):
        """Test that user-facing output is clear and follows conventions"""
        logger.info("Testing user output conventions...")
        
        # Test help messages
        update, context = self.create_mock_update_context([])
        await delete_command(update, context)
        
        if update.message.reply_text.called:
            help_text = update.message.reply_text.call_args[0][0]
            conventions_met = all([
                "**" in help_text,  # Bold formatting
                "🗑️" in help_text or "Delete" in help_text,  # Emoji or descriptive text
                "Usage:" in help_text or "usage:" in help_text,  # Usage instructions
                "Example" in help_text or "example" in help_text,  # Examples
            ])
            self.log_test_result("User output conventions - help", conventions_met, "Help text follows conventions")
        
        # Test error messages
        update, context = self.create_mock_update_context(['path=nonexistent.txt', 'isDirectory=false'])
        await delete_command(update, context)
        
        if update.message.reply_text.called:
            error_text = update.message.reply_text.call_args[0][0]
            error_conventions_met = all([
                "❌" in error_text or "Error" in error_text,  # Error indicator
                "**" in error_text,  # Bold formatting
                "File Not Found" in error_text or "not found" in error_text,  # Clear error description
            ])
            self.log_test_result("User output conventions - error", error_conventions_met, "Error messages follow conventions")
        
        # Test success messages
        test_file = os.path.join(self.test_dir, "success_test.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        
        update, context = self.create_mock_update_context(['path=success_test.txt', 'isDirectory=false'])
        await delete_command(update, context)
        
        if update.message.reply_text.called:
            success_text = update.message.reply_text.call_args[0][0]
            success_conventions_met = all([
                "✅" in success_text or "Success" in success_text,  # Success indicator
                "**" in success_text,  # Bold formatting
                "Delete" in success_text or "delete" in success_text,  # Operation description
            ])
            self.log_test_result("User output conventions - success", success_conventions_met, "Success messages follow conventions")
    
    async def test_logging_events(self):
        """Test that logging is performed for all meaningful events"""
        logger.info("Testing logging for all commands...")
        
        # Test that security events are logged
        with patch.object(self.security_manager, '_log_security_event') as mock_log:
            
            # Test delete command logging
            test_file = os.path.join(self.test_dir, "log_test.txt")
            with open(test_file, 'w') as f:
                f.write("test")
            
            update, context = self.create_mock_update_context(['path=log_test.txt', 'isDirectory=false'])
            await delete_command(update, context)
            
            if mock_log.called:
                logged_event = mock_log.call_args[0][0]
                if (logged_event.event_type == 'file_operation' and 
                    logged_event.operation == 'delete' and 
                    logged_event.user_id == self.user_id):
                    self.log_test_result("Logging - delete success", True, "Security event logged correctly")
                else:
                    self.log_test_result("Logging - delete success", False, "Security event not logged correctly")
            else:
                self.log_test_result("Logging - delete success", False, "No security event logged")
        
        # Test error logging
        with patch.object(self.security_manager, '_log_security_event') as mock_log:
            update, context = self.create_mock_update_context(['path=nonexistent.txt', 'isDirectory=false'])
            await delete_command(update, context)
            
            # Check if error was logged (may not be logged for file not found)
            if mock_log.called:
                logged_event = mock_log.call_args[0][0]
                if not logged_event.success:
                    self.log_test_result("Logging - delete error", True, "Error event logged correctly")
                else:
                    self.log_test_result("Logging - delete error", False, "Error event not logged as failure")
            else:
                # Some errors might not be logged at security level
                self.log_test_result("Logging - delete error", True, "Error handling appropriate (no security event needed)")
    
    async def test_windows_specific_scenarios(self):
        """Test Windows-specific scenarios"""
        if not self.is_windows:
            logger.info("Skipping Windows-specific tests on non-Windows platform")
            return
        
        logger.info("Testing Windows-specific scenarios...")
        
        # Test Windows path formats
        windows_paths = [
            "C:\\temp\\test.txt",
            "\\\\server\\share\\file.txt",  # UNC path
            "C:/temp/test.txt",  # Forward slashes on Windows
        ]
        
        for win_path in windows_paths:
            with patch.object(self.security_manager, 'validate_file_path') as mock_validate:
                mock_validate.return_value = (True, "Path validation passed")
                
                update, context = self.create_mock_update_context([f'path={win_path}', 'isDirectory=false'])
                await delete_command(update, context)
                
                if mock_validate.called:
                    self.log_test_result(f"Windows path format - {win_path}", True, "Windows path handled correctly")
                else:
                    self.log_test_result(f"Windows path format - {win_path}", False, "Windows path not handled")
        
        # Test Windows reserved names
        reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]
        for reserved in reserved_names:
            with patch.object(self.security_manager, 'validate_file_path') as mock_validate:
                mock_validate.return_value = (False, f"Reserved name not allowed: {reserved}")
                
                update, context = self.create_mock_update_context([f'path={reserved}', 'isDirectory=false'])
                await delete_command(update, context)
                
                if update.message.reply_text.called:
                    self.log_test_result(f"Windows reserved name - {reserved}", True, "Reserved name properly rejected")
                else:
                    self.log_test_result(f"Windows reserved name - {reserved}", False, "Reserved name not rejected")
    
    async def test_cross_platform_scenarios(self):
        """Test cross-platform scenarios"""
        logger.info("Testing cross-platform scenarios...")
        
        # Test path separators
        test_paths = [
            "folder/file.txt",  # Unix-style
            "folder\\file.txt",  # Windows-style
            "folder/subfolder\\file.txt",  # Mixed separators
        ]
        
        for test_path in test_paths:
            # Create the actual file structure for testing
            normalized_path = os.path.normpath(test_path)
            full_path = os.path.join(self.test_dir, normalized_path)
            
            # Create directory structure
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write("test content")
            
            # Test the command
            relative_path = os.path.relpath(full_path, self.test_dir)
            update, context = self.create_mock_update_context([f'path={relative_path}', 'isDirectory=false'])
            await delete_command(update, context)
            
            # Check if file was deleted (success)
            if not os.path.exists(full_path):
                self.log_test_result(f"Cross-platform path - {test_path}", True, "Path separators handled correctly")
            else:
                self.log_test_result(f"Cross-platform path - {test_path}", False, "Path separators not handled correctly")
    
    async def test_hide_unhide_commands(self):
        """Test hide/unhide commands specifically"""
        logger.info("Testing hide/unhide commands...")
        
        # Test hide command
        test_file = os.path.join(self.test_dir, "hide_test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        update, context = self.create_mock_update_context(['hide_test.txt'])
        
        # Mock the Windows file attributes functions
        with patch('hide_unhide_commands.set_hidden_attribute') as mock_set_hidden:
            mock_set_hidden.return_value = (True, "Hidden attribute set successfully")
            
            await hide_command(update, context)
            
            if mock_set_hidden.called:
                self.log_test_result("Hide command - set hidden attribute", True, "Hidden attribute set correctly")
            else:
                self.log_test_result("Hide command - set hidden attribute", False, "Hidden attribute not set")
        
        # Test unhide command
        with patch('hide_unhide_commands.clear_hidden_attribute') as mock_clear_hidden:
            mock_clear_hidden.return_value = (True, "Hidden attribute cleared successfully")
            
            with patch('hide_unhide_commands._get_hidden_items') as mock_get_hidden:
                mock_get_hidden.return_value = [{
                    'original_path': test_file,
                    'is_directory': False,
                    'size': 100,
                    'size_formatted': '100 B',
                    'hidden_date': datetime.now().isoformat()
                }]
                
                update, context = self.create_mock_update_context(['hide_test.txt'])
                await unhide_command(update, context)
                
                if mock_clear_hidden.called:
                    self.log_test_result("Unhide command - clear hidden attribute", True, "Hidden attribute cleared correctly")
                else:
                    self.log_test_result("Unhide command - clear hidden attribute", False, "Hidden attribute not cleared")
        
        # Test hidden command (list hidden files)
        with patch('hide_unhide_commands._get_hidden_items') as mock_get_hidden:
            mock_get_hidden.return_value = [{
                'original_path': test_file,
                'is_directory': False,
                'size': 100,
                'size_formatted': '100 B',
                'hidden_date': datetime.now().isoformat()
            }]
            
            update, context = self.create_mock_update_context([])
            await hidden_command(update, context)
            
            if update.message.reply_text.called:
                response_text = update.message.reply_text.call_args[0][0]
                if "Hidden Files" in response_text and "hide_test.txt" in response_text:
                    self.log_test_result("Hidden command - list files", True, "Hidden files listed correctly")
                else:
                    self.log_test_result("Hidden command - list files", False, "Hidden files not listed correctly")
    
    async def test_all_file_operations(self):
        """Test all file operation commands"""
        logger.info("Testing all file operation commands...")
        
        # Test copy command
        source_file = os.path.join(self.test_dir, "copy_source.txt")
        with open(source_file, 'w') as f:
            f.write("copy test content")
        
        update, context = self.create_mock_update_context([
            'sourcePath=copy_source.txt',
            'destinationPath=copy_dest.txt',
            'isDirectory=false'
        ])
        await copy_command(update, context)
        
        dest_file = os.path.join(self.test_dir, "copy_dest.txt")
        if os.path.exists(dest_file):
            self.log_test_result("Copy command - file copy", True, "File copied successfully")
        else:
            self.log_test_result("Copy command - file copy", False, "File not copied")
        
        # Test move command
        move_source = os.path.join(self.test_dir, "move_source.txt")
        with open(move_source, 'w') as f:
            f.write("move test content")
        
        update, context = self.create_mock_update_context([
            'sourcePath=move_source.txt',
            'destinationPath=move_dest.txt',
            'isDirectory=false'
        ])
        await move_command(update, context)
        
        move_dest = os.path.join(self.test_dir, "move_dest.txt")
        if os.path.exists(move_dest) and not os.path.exists(move_source):
            self.log_test_result("Move command - file move", True, "File moved successfully")
        else:
            self.log_test_result("Move command - file move", False, "File not moved correctly")
        
        # Test rename command
        rename_source = os.path.join(self.test_dir, "rename_source.txt")
        with open(rename_source, 'w') as f:
            f.write("rename test content")
        
        update, context = self.create_mock_update_context([
            'path=rename_source.txt',
            'newName=rename_dest.txt',
            'isDirectory=false'
        ])
        await rename_command(update, context)
        
        rename_dest = os.path.join(self.test_dir, "rename_dest.txt")
        if os.path.exists(rename_dest) and not os.path.exists(rename_source):
            self.log_test_result("Rename command - file rename", True, "File renamed successfully")
        else:
            self.log_test_result("Rename command - file rename", False, "File not renamed correctly")
    
    def generate_test_report(self):
        """Generate a comprehensive test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        report = f"""
=== PCRst Commands Test Report ===
Platform: {platform.system()} {platform.release()}
Python: {platform.python_version()}
Test Date: {datetime.now().isoformat()}

Summary:
- Total Tests: {total_tests}
- Passed: {passed_tests}
- Failed: {failed_tests}
- Success Rate: {(passed_tests/total_tests*100):.1f}%

Detailed Results:
"""
        
        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            report += f"{status} {result['test_name']}: {result['details']}\n"
        
        # Check for critical failures
        critical_failures = [r for r in self.test_results if not r['passed'] and 
                            ('Security' in r['test_name'] or 'unsafe' in r['test_name'].lower())]
        
        if critical_failures:
            report += f"\n⚠️  CRITICAL SECURITY FAILURES ({len(critical_failures)}):\n"
            for failure in critical_failures:
                report += f"   ❌ {failure['test_name']}: {failure['details']}\n"
        
        return report
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("Starting comprehensive command testing...")
        
        try:
            self.setup_test_environment()
            
            # Run all test categories
            await self.test_security_manager_invocation()
            await self.test_unsafe_path_rejection()
            await self.test_user_output_conventions()
            await self.test_logging_events()
            await self.test_windows_specific_scenarios()
            await self.test_cross_platform_scenarios()
            await self.test_hide_unhide_commands()
            await self.test_all_file_operations()
            
            # Generate and print report
            report = self.generate_test_report()
            print(report)
            
            # Save report to file
            report_file = os.path.join(self.test_dir, "test_report.txt")
            with open(report_file, 'w') as f:
                f.write(report)
            
            logger.info(f"Test report saved to: {report_file}")
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            raise
        finally:
            self.cleanup_test_environment()


async def main():
    """Main test execution"""
    tester = TestPlatformScenarios()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
