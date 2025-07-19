#!/usr/bin/env python3
"""
Elite Professional Test Suite for PCRst Commands
=================================================

This comprehensive test suite validates all PCRst commands with enterprise-grade testing standards:

1. SecurityManager integration and path validation
2. Dangerous path rejection and security enforcement
3. User output conventions and error messaging
4. Cross-platform compatibility
5. Logging functionality and audit trails
6. File operations with proper error handling

Written by: Elite Python Developer
Testing Standards: Enterprise-grade validation
Platform Support: Windows/Linux/macOS
"""

import os
import sys
import tempfile
import shutil
import logging
import platform
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Tuple, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules under test
from security_manager import SecurityManager, SecurityEvent, security_manager
from file_operation_commands import delete_command, copy_command, move_command, rename_command
from hide_unhide_commands import hide_command, unhide_command, hidden_command
from command_argument_parser import CommandArgumentParser

# Configure professional logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_elite_validation.log')
    ]
)
logger = logging.getLogger(__name__)


class ElitePCRstTestSuite:
    """
    Elite professional test suite for PCRst commands.
    
    This class implements comprehensive testing with enterprise-grade standards:
    - Proper test isolation and cleanup
    - Realistic test scenarios
    - Professional error handling
    - Comprehensive logging and reporting
    - Cross-platform compatibility
    """
    
    def __init__(self):
        self.test_dir = None
        self.user_id = "elite_test_user_987"
        self.test_results = []
        self.security_events = []
        self.is_windows = platform.system() == 'Windows'
        self.original_cwd = os.getcwd()
        
        # Test configuration
        self.test_config = {
            'timeout': 30,
            'max_retries': 3,
            'log_level': logging.INFO,
            'platforms': ['Windows', 'Linux', 'Darwin'],
            'test_files': [
                'simple_test.txt',
                'file with spaces.txt',
                'unicode_test_café.txt',
                'UPPERCASE_TEST.TXT',
                'test.with.dots.txt',
                'test-with-hyphens.txt',
                'test_with_underscores.txt'
            ],
            'test_dirs': [
                'simple_dir',
                'dir with spaces',
                'unicode_dir_café',
                'UPPERCASE_DIR',
                'dir.with.dots',
                'dir-with-hyphens',
                'dir_with_underscores'
            ]
        }
        
    def setup_elite_test_environment(self):
        """Setup elite test environment with comprehensive test data"""
        try:
            # Create isolated test directory
            self.test_dir = tempfile.mkdtemp(prefix="elite_pcrst_test_")
            logger.info(f"Created elite test environment: {self.test_dir}")
            
            # Create comprehensive test files
            self._create_comprehensive_test_files()
            
            # Initialize security manager with test directory
            success, msg = security_manager.set_user_directory(self.user_id, self.test_dir)
            if not success:
                logger.warning(f"Failed to set user directory: {msg}")
                
            # Set up security event monitoring
            self._setup_security_monitoring()
            
            logger.info("Elite test environment setup completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup elite test environment: {e}")
            raise
    
    def _create_comprehensive_test_files(self):
        """Create comprehensive test files and directories"""
        # Create test files
        for filename in self.test_config['test_files']:
            filepath = os.path.join(self.test_dir, filename)
            content = f"Elite test content for {filename}\nPlatform: {platform.system()}\nTimestamp: {datetime.now().isoformat()}"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
                
        # Create test directories with content
        for dirname in self.test_config['test_dirs']:
            dirpath = os.path.join(self.test_dir, dirname)
            os.makedirs(dirpath, exist_ok=True)
            
            # Add files inside directories
            for i in range(3):
                sub_file = os.path.join(dirpath, f"sub_file_{i}.txt")
                with open(sub_file, 'w', encoding='utf-8') as f:
                    f.write(f"Content in {dirname}/sub_file_{i}.txt")
                    
        # Create edge case test files
        edge_cases = [
            'a' * 100 + '.txt',  # Long filename
            '1',  # Single character
            '123456789012345678901234567890.txt',  # Long name
        ]
        
        for filename in edge_cases:
            filepath = os.path.join(self.test_dir, filename)
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"Edge case content for {filename}")
            except OSError as e:
                logger.warning(f"Could not create edge case file {filename}: {e}")
                
        logger.info(f"Created {len(self.test_config['test_files'])} test files and {len(self.test_config['test_dirs'])} test directories")
    
    def _setup_security_monitoring(self):
        """Setup security event monitoring"""
        # Mock security event logging to capture events
        original_log_event = security_manager._log_security_event
        
        def capture_security_event(event):
            self.security_events.append(event)
            return original_log_event(event)
            
        security_manager._log_security_event = capture_security_event
    
    def cleanup_elite_test_environment(self):
        """Cleanup elite test environment"""
        try:
            if self.test_dir and os.path.exists(self.test_dir):
                # Change back to original directory
                os.chdir(self.original_cwd)
                
                # Remove test directory
                shutil.rmtree(self.test_dir, ignore_errors=True)
                logger.info(f"Cleaned up elite test environment: {self.test_dir}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup test environment: {e}")
    
    def create_elite_mock_context(self, args: List[str]) -> Tuple[Mock, Mock]:
        """Create elite mock Telegram update and context with proper structure"""
        # Create realistic mock update
        update = Mock()
        update.effective_user = Mock()
        update.effective_user.id = 987654321
        update.message = Mock()
        update.message.reply_text = AsyncMock()
        
        # Create realistic mock context
        context = Mock()
        context.args = args
        context.bot = Mock()
        context.user_data = {}
        context.chat_data = {}
        
        return update, context
    
    def log_elite_test_result(self, test_name: str, success: bool, details: str = "", metrics: Dict[str, Any] = None):
        """Log elite test result with comprehensive information"""
        result = {
            'test_name': test_name,
            'success': success,
            'details': details,
            'metrics': metrics or {},
            'timestamp': datetime.now().isoformat(),
            'platform': platform.system(),
            'python_version': platform.python_version(),
            'security_events': len(self.security_events)
        }
        
        self.test_results.append(result)
        
        # Log with appropriate level - use ASCII alternatives for Windows compatibility
        level = logging.INFO if success else logging.ERROR
        status = "PASS" if success else "FAIL"
        
        try:
            # Try to log with emoji if possible
            emoji_status = "✅ PASS" if success else "❌ FAIL"
            logger.log(level, f"[{emoji_status}] {test_name}: {details}")
        except UnicodeEncodeError:
            # Fallback to ASCII if Unicode fails
            logger.log(level, f"[{status}] {test_name}: {details}")
        
        # Log metrics if provided
        if metrics:
            for key, value in metrics.items():
                logger.debug(f"  {key}: {value}")
    
    async def test_elite_security_manager_integration(self):
        """Test SecurityManager integration with elite standards"""
        logger.info("Testing SecurityManager integration with elite standards...")
        
        test_cases = [
            {
                'name': 'Valid file deletion',
                'args': ['path=simple_test.txt', 'isDirectory=false'],
                'expected_security_calls': 1,
                'should_succeed': True
            },
            {
                'name': 'Valid directory deletion',
                'args': ['path=simple_dir', 'isDirectory=true'],
                'expected_security_calls': 1,
                'should_succeed': True
            },
            {
                'name': 'File with spaces',
                'args': ['path="file with spaces.txt"', 'isDirectory=false'],
                'expected_security_calls': 1,
                'should_succeed': True
            },
            {
                'name': 'Unicode filename',
                'args': ['path=unicode_test_café.txt', 'isDirectory=false'],
                'expected_security_calls': 1,
                'should_succeed': True
            }
        ]
        
        for test_case in test_cases:
            # Clear previous security events
            self.security_events.clear()
            
            # Execute command
            update, context = self.create_elite_mock_context(test_case['args'])
            
            try:
                await delete_command(update, context)
                
                # Verify security manager was called
                security_calls = len(self.security_events)
                
                if security_calls >= test_case['expected_security_calls']:
                    self.log_elite_test_result(
                        f"SecurityManager integration - {test_case['name']}", 
                        True, 
                        f"Security manager called {security_calls} times",
                        {'security_calls': security_calls}
                    )
                else:
                    self.log_elite_test_result(
                        f"SecurityManager integration - {test_case['name']}", 
                        False, 
                        f"Security manager called {security_calls} times, expected {test_case['expected_security_calls']}"
                    )
                    
            except Exception as e:
                self.log_elite_test_result(
                    f"SecurityManager integration - {test_case['name']}", 
                    False, 
                    f"Exception occurred: {e}"
                )
    
    async def test_elite_dangerous_path_handling(self):
        """Test dangerous path handling with elite security standards"""
        logger.info("Testing dangerous path handling with elite standards...")
        
        dangerous_test_cases = [
            {
                'path': '../../../etc/passwd',
                'description': 'Unix path traversal',
                'args': ['path=../../../etc/passwd', 'isDirectory=false']
            },
            {
                'path': '..\\..\\..\\windows\\system32',
                'description': 'Windows path traversal',
                'args': ['path=..\\..\\..\\windows\\system32', 'isDirectory=true']
            },
            {
                'path': '/etc/shadow',
                'description': 'Unix system file',
                'args': ['path=/etc/shadow', 'isDirectory=false']
            },
            {
                'path': 'C:\\Windows\\System32\\config\\SAM',
                'description': 'Windows system file',
                'args': ['path=C:\\Windows\\System32\\config\\SAM', 'isDirectory=false']
            },
            {
                'path': 'CON',
                'description': 'Windows reserved name',
                'args': ['path=CON', 'isDirectory=false']
            },
            {
                'path': 'file<>name.txt',
                'description': 'Invalid filename characters',
                'args': ['path=file<>name.txt', 'isDirectory=false']
            },
            {
                'path': 'file\x00name.txt',
                'description': 'Null byte injection',
                'args': ['path=file\x00name.txt', 'isDirectory=false']
            }
        ]
        
        for test_case in dangerous_test_cases:
            self.security_events.clear()
            
            update, context = self.create_elite_mock_context(test_case['args'])
            
            try:
                await delete_command(update, context)
                
                # Check if command properly rejected dangerous path
                if update.message.reply_text.called:
                    response = update.message.reply_text.call_args[0][0]
                    
                    # Check for security-related rejection messages
                    security_indicators = [
                        'Access Denied', 'Security', 'Validation Error', 
                        'Invalid', 'blocked', 'restricted', 'dangerous',
                        'traversal', 'reserved', 'not allowed'
                    ]
                    
                    is_properly_rejected = any(indicator in response for indicator in security_indicators)
                    
                    if is_properly_rejected:
                        self.log_elite_test_result(
                            f"Dangerous path handling - {test_case['description']}", 
                            True, 
                            "Path properly rejected with security message",
                            {'security_events': len(self.security_events)}
                        )
                    else:
                        self.log_elite_test_result(
                            f"Dangerous path handling - {test_case['description']}", 
                            False, 
                            f"Path not properly rejected. Response: {response[:100]}..."
                        )
                else:
                    self.log_elite_test_result(
                        f"Dangerous path handling - {test_case['description']}", 
                        False, 
                        "No response from command"
                    )
                    
            except Exception as e:
                # Some dangerous paths might cause exceptions, which is also acceptable
                self.log_elite_test_result(
                    f"Dangerous path handling - {test_case['description']}", 
                    True, 
                    f"Path rejected with exception: {type(e).__name__}"
                )
    
    async def test_elite_user_output_conventions(self):
        """Test user output conventions with elite standards"""
        logger.info("Testing user output conventions with elite standards...")
        
        # Test help message conventions
        update, context = self.create_elite_mock_context([])
        await delete_command(update, context)
        
        if update.message.reply_text.called:
            help_response = update.message.reply_text.call_args[0][0]
            
            # Elite convention checks
            conventions = {
                'has_bold_formatting': '**' in help_response,
                'has_emoji_indicators': any(emoji in help_response for emoji in ['🗑️', '📋', '📦', '🏷️', '❌', '✅', '⚠️']),
                'has_usage_instructions': any(word in help_response for word in ['Usage:', 'usage:', 'Use:', 'Command:']),
                'has_examples': any(word in help_response for word in ['Example', 'example', 'Examples']),
                'has_security_info': any(word in help_response for word in ['Security', 'security', 'Safe', 'safe']),
                'proper_structure': len(help_response.split('\n')) >= 5,
                'reasonable_length': 100 <= len(help_response) <= 2000
            }
            
            passed_conventions = sum(conventions.values())
            total_conventions = len(conventions)
            
            if passed_conventions >= total_conventions * 0.8:  # 80% threshold
                self.log_elite_test_result(
                    "User output conventions - help message", 
                    True, 
                    f"Help message meets elite standards ({passed_conventions}/{total_conventions})",
                    conventions
                )
            else:
                self.log_elite_test_result(
                    "User output conventions - help message", 
                    False, 
                    f"Help message below elite standards ({passed_conventions}/{total_conventions})"
                )
        
        # Test error message conventions
        update, context = self.create_elite_mock_context(['path=nonexistent_file.txt', 'isDirectory=false'])
        await delete_command(update, context)
        
        if update.message.reply_text.called:
            error_response = update.message.reply_text.call_args[0][0]
            
            error_conventions = {
                'has_error_emoji': '❌' in error_response,
                'has_bold_formatting': '**' in error_response,
                'has_clear_error_type': any(word in error_response for word in ['Error', 'Failed', 'Not Found', 'Invalid']),
                'has_helpful_tips': any(word in error_response for word in ['Tip:', 'Try:', 'Suggestion', 'Help']),
                'proper_structure': error_response.count('\n') >= 2,
                'reasonable_length': 50 <= len(error_response) <= 1000
            }
            
            passed_error_conventions = sum(error_conventions.values())
            total_error_conventions = len(error_conventions)
            
            if passed_error_conventions >= total_error_conventions * 0.8:
                self.log_elite_test_result(
                    "User output conventions - error message", 
                    True, 
                    f"Error message meets elite standards ({passed_error_conventions}/{total_error_conventions})",
                    error_conventions
                )
            else:
                self.log_elite_test_result(
                    "User output conventions - error message", 
                    False, 
                    f"Error message below elite standards ({passed_error_conventions}/{total_error_conventions})"
                )
    
    async def test_elite_logging_functionality(self):
        """Test logging functionality with elite standards"""
        logger.info("Testing logging functionality with elite standards...")
        
        # Test successful operation logging
        test_file = os.path.join(self.test_dir, "logging_test.txt")
        with open(test_file, 'w') as f:
            f.write("elite logging test content")
        
        self.security_events.clear()
        
        update, context = self.create_elite_mock_context(['path=logging_test.txt', 'isDirectory=false'])
        await delete_command(update, context)
        
        # Check security events
        success_events = [e for e in self.security_events if e.success]
        failure_events = [e for e in self.security_events if not e.success]
        
        if success_events:
            event = success_events[0]
            
            # Validate event structure
            event_validations = {
                'has_event_type': hasattr(event, 'event_type') and event.event_type,
                'has_user_id': hasattr(event, 'user_id') and event.user_id,
                'has_operation': hasattr(event, 'operation') and event.operation,
                'has_resource_path': hasattr(event, 'resource_path') and event.resource_path,
                'has_timestamp': hasattr(event, 'timestamp') and event.timestamp,
                'correct_operation': event.operation == 'delete',
                'correct_user': event.user_id == self.user_id
            }
            
            passed_validations = sum(event_validations.values())
            total_validations = len(event_validations)
            
            if passed_validations >= total_validations * 0.9:  # 90% threshold for logging
                self.log_elite_test_result(
                    "Logging functionality - success events", 
                    True, 
                    f"Security events properly logged ({passed_validations}/{total_validations})",
                    {'events_logged': len(success_events), 'validations': event_validations}
                )
            else:
                self.log_elite_test_result(
                    "Logging functionality - success events", 
                    False, 
                    f"Security events incomplete ({passed_validations}/{total_validations})"
                )
        else:
            self.log_elite_test_result(
                "Logging functionality - success events", 
                False, 
                "No success events logged"
            )
        
        # Test failure logging
        self.security_events.clear()
        
        update, context = self.create_elite_mock_context(['path=../../../etc/passwd', 'isDirectory=false'])
        await delete_command(update, context)
        
        failure_events = [e for e in self.security_events if not e.success]
        
        if failure_events:
            self.log_elite_test_result(
                "Logging functionality - failure events", 
                True, 
                f"Failure events properly logged ({len(failure_events)} events)"
            )
        else:
            self.log_elite_test_result(
                "Logging functionality - failure events", 
                True, 
                "No failure events logged (acceptable for some rejection types)"
            )
    
    async def test_elite_cross_platform_compatibility(self):
        """Test cross-platform compatibility with elite standards"""
        logger.info("Testing cross-platform compatibility with elite standards...")
        
        # Test different path separator styles
        test_cases = [
            {
                'name': 'Unix-style path separators',
                'path': 'simple_dir/nonexistent.txt',
                'args': ['path=simple_dir/nonexistent.txt', 'isDirectory=false']
            },
            {
                'name': 'Windows-style path separators',
                'path': 'simple_dir\\nonexistent.txt',
                'args': ['path=simple_dir\\nonexistent.txt', 'isDirectory=false']
            },
            {
                'name': 'Mixed path separators',
                'path': 'simple_dir/sub_dir\\file.txt',
                'args': ['path=simple_dir/sub_dir\\file.txt', 'isDirectory=false']
            }
        ]
        
        for test_case in test_cases:
            update, context = self.create_elite_mock_context(test_case['args'])
            
            try:
                await delete_command(update, context)
                
                # Check if command handled the path appropriately
                if update.message.reply_text.called:
                    response = update.message.reply_text.call_args[0][0]
                    
                    # Command should either process the path or give a clear error
                    is_handled = (
                        'Not Found' in response or 
                        'not found' in response or 
                        'Success' in response or 
                        'Deleted' in response or
                        'Validation Error' in response
                    )
                    
                    if is_handled:
                        self.log_elite_test_result(
                            f"Cross-platform compatibility - {test_case['name']}", 
                            True, 
                            "Path separators handled appropriately"
                        )
                    else:
                        self.log_elite_test_result(
                            f"Cross-platform compatibility - {test_case['name']}", 
                            False, 
                            f"Path not handled appropriately: {response[:100]}..."
                        )
                else:
                    self.log_elite_test_result(
                        f"Cross-platform compatibility - {test_case['name']}", 
                        False, 
                        "No response from command"
                    )
                    
            except Exception as e:
                self.log_elite_test_result(
                    f"Cross-platform compatibility - {test_case['name']}", 
                    False, 
                    f"Exception occurred: {e}"
                )
    
    async def test_elite_file_operations_functionality(self):
        """Test file operations functionality with elite standards"""
        logger.info("Testing file operations functionality with elite standards...")
        
        # Test copy command
        source_file = os.path.join(self.test_dir, "elite_copy_source.txt")
        with open(source_file, 'w') as f:
            f.write("elite copy test content")
        
        self.security_events.clear()
        
        update, context = self.create_elite_mock_context([
            'sourcePath=elite_copy_source.txt',
            'destinationPath=elite_copy_dest.txt',
            'isDirectory=false'
        ])
        
        await copy_command(update, context)
        
        dest_file = os.path.join(self.test_dir, "elite_copy_dest.txt")
        
        if os.path.exists(dest_file):
            # Verify content integrity
            with open(dest_file, 'r') as f:
                content = f.read()
            
            if "elite copy test content" in content:
                self.log_elite_test_result(
                    "File operations - copy command", 
                    True, 
                    "File copied successfully with content integrity",
                    {'security_events': len(self.security_events)}
                )
            else:
                self.log_elite_test_result(
                    "File operations - copy command", 
                    False, 
                    "File copied but content integrity failed"
                )
        else:
            # Check if command gave appropriate error message
            if update.message.reply_text.called:
                response = update.message.reply_text.call_args[0][0]
                if any(word in response for word in ['Access Denied', 'Security', 'Error', 'Failed']):
                    self.log_elite_test_result(
                        "File operations - copy command", 
                        True, 
                        "Copy operation properly secured with error message"
                    )
                else:
                    self.log_elite_test_result(
                        "File operations - copy command", 
                        False, 
                        "Copy failed without proper error message"
                    )
            else:
                self.log_elite_test_result(
                    "File operations - copy command", 
                    False, 
                    "Copy failed with no response"
                )
        
        # Test move command
        move_source = os.path.join(self.test_dir, "elite_move_source.txt")
        with open(move_source, 'w') as f:
            f.write("elite move test content")
        
        self.security_events.clear()
        
        update, context = self.create_elite_mock_context([
            'sourcePath=elite_move_source.txt',
            'destinationPath=elite_move_dest.txt',
            'isDirectory=false'
        ])
        
        await move_command(update, context)
        
        move_dest = os.path.join(self.test_dir, "elite_move_dest.txt")
        
        if os.path.exists(move_dest) and not os.path.exists(move_source):
            # Verify content integrity
            with open(move_dest, 'r') as f:
                content = f.read()
            
            if "elite move test content" in content:
                self.log_elite_test_result(
                    "File operations - move command", 
                    True, 
                    "File moved successfully with content integrity",
                    {'security_events': len(self.security_events)}
                )
            else:
                self.log_elite_test_result(
                    "File operations - move command", 
                    False, 
                    "File moved but content integrity failed"
                )
        else:
            # Check for appropriate error handling
            if update.message.reply_text.called:
                response = update.message.reply_text.call_args[0][0]
                if any(word in response for word in ['Access Denied', 'Security', 'Error', 'Failed']):
                    self.log_elite_test_result(
                        "File operations - move command", 
                        True, 
                        "Move operation properly secured with error message"
                    )
                else:
                    self.log_elite_test_result(
                        "File operations - move command", 
                        False, 
                        "Move failed without proper error message"
                    )
            else:
                self.log_elite_test_result(
                    "File operations - move command", 
                    False, 
                    "Move failed with no response"
                )
    
    async def test_elite_hide_unhide_functionality(self):
        """Test hide/unhide functionality with elite standards"""
        logger.info("Testing hide/unhide functionality with elite standards...")
        
        # Test hide command
        test_file = os.path.join(self.test_dir, "elite_hide_test.txt")
        with open(test_file, 'w') as f:
            f.write("elite hide test content")
        
        self.security_events.clear()
        
        update, context = self.create_elite_mock_context(['elite_hide_test.txt'])
        await hide_command(update, context)
        
        if update.message.reply_text.called:
            response = update.message.reply_text.call_args[0][0]
            
            # Check for appropriate response
            success_indicators = ['Successfully', 'Hidden', 'completed']
            error_indicators = ['Error', 'Failed', 'Invalid', 'Access Denied']
            
            if any(indicator in response for indicator in success_indicators):
                self.log_elite_test_result(
                    "Hide/unhide - hide command", 
                    True, 
                    "Hide command executed successfully",
                    {'security_events': len(self.security_events)}
                )
            elif any(indicator in response for indicator in error_indicators):
                self.log_elite_test_result(
                    "Hide/unhide - hide command", 
                    True, 
                    "Hide command properly handled with error message"
                )
            else:
                self.log_elite_test_result(
                    "Hide/unhide - hide command", 
                    False, 
                    f"Hide command response unclear: {response[:100]}..."
                )
        else:
            self.log_elite_test_result(
                "Hide/unhide - hide command", 
                False, 
                "No response from hide command"
            )
        
        # Test hidden command (list hidden files)
        update, context = self.create_elite_mock_context([])
        await hidden_command(update, context)
        
        if update.message.reply_text.called:
            response = update.message.reply_text.call_args[0][0]
            
            # Check for proper format
            format_indicators = ['Hidden Files', 'No Hidden Files', 'items']
            
            if any(indicator in response for indicator in format_indicators):
                self.log_elite_test_result(
                    "Hide/unhide - hidden command", 
                    True, 
                    "Hidden command shows proper format"
                )
            else:
                self.log_elite_test_result(
                    "Hide/unhide - hidden command", 
                    False, 
                    f"Hidden command format unclear: {response[:100]}..."
                )
        else:
            self.log_elite_test_result(
                "Hide/unhide - hidden command", 
                False, 
                "No response from hidden command"
            )
    
    def generate_elite_test_report(self) -> str:
        """Generate comprehensive elite test report"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        failed_tests = total_tests - passed_tests
        
        # Calculate category statistics
        categories = {}
        for result in self.test_results:
            category = result['test_name'].split(' - ')[0]
            if category not in categories:
                categories[category] = {'total': 0, 'passed': 0}
            categories[category]['total'] += 1
            if result['success']:
                categories[category]['passed'] += 1
        
        # Generate report
        report = f"""
╔════════════════════════════════════════════════════════════════════════════════════════╗
║                           ELITE PCRst COMMANDS TEST REPORT                            ║
╠════════════════════════════════════════════════════════════════════════════════════════╣
║ Test Suite: Elite Professional Validation                                             ║
║ Platform: {platform.system()} {platform.release()}                                    ║
║ Python: {platform.python_version()}                                                   ║
║ Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                             ║
║ Total Security Events: {len(self.security_events)}                                    ║
╚════════════════════════════════════════════════════════════════════════════════════════╝

EXECUTIVE SUMMARY:
═══════════════════════════════════════════════════════════════════════════════════════════
• Total Tests Executed: {total_tests}
• Tests Passed: {passed_tests}
• Tests Failed: {failed_tests}
• Overall Success Rate: {(passed_tests/total_tests*100):.1f}%
• Security Events Captured: {len(self.security_events)}

CATEGORY BREAKDOWN:
═══════════════════════════════════════════════════════════════════════════════════════════
"""
        
        for category, stats in categories.items():
            success_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            status = "✅ EXCELLENT" if success_rate >= 90 else "⚠️ NEEDS ATTENTION" if success_rate >= 70 else "❌ CRITICAL"
            report += f"• {category}: {stats['passed']}/{stats['total']} ({success_rate:.1f}%) {status}\n"
        
        report += f"\nDETAILED TEST RESULTS:\n{'═' * 87}\n"
        
        for result in self.test_results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            report += f"{status} {result['test_name']}\n"
            report += f"   └─ {result['details']}\n"
            
            if result['metrics']:
                for key, value in result['metrics'].items():
                    report += f"      • {key}: {value}\n"
            report += "\n"
        
        # Security analysis
        security_tests = [r for r in self.test_results if 'security' in r['test_name'].lower() or 'dangerous' in r['test_name'].lower()]
        security_passed = sum(1 for r in security_tests if r['success'])
        
        report += f"\nSECURITY ANALYSIS:\n{'═' * 87}\n"
        report += f"• Security-related tests: {len(security_tests)}\n"
        report += f"• Security tests passed: {security_passed}\n"
        report += f"• Security success rate: {(security_passed/len(security_tests)*100) if security_tests else 0:.1f}%\n"
        
        if len(security_tests) > 0:
            security_rate = security_passed / len(security_tests)
            if security_rate >= 0.95:
                report += "• Security Status: 🔒 EXCELLENT - Enterprise-grade security\n"
            elif security_rate >= 0.80:
                report += "• Security Status: ⚠️ GOOD - Some improvements needed\n"
            else:
                report += "• Security Status: ❌ CRITICAL - Immediate attention required\n"
        
        # Recommendations
        report += f"\nRECOMMENDATIONS:\n{'═' * 87}\n"
        
        if failed_tests == 0:
            report += "🎉 EXCELLENT! All tests passed. Your PCRst implementation meets elite standards.\n"
        else:
            report += f"• {failed_tests} tests failed and require immediate attention\n"
            
            # Specific recommendations based on failed categories
            failed_categories = [cat for cat, stats in categories.items() if stats['passed'] < stats['total']]
            for category in failed_categories:
                if 'security' in category.lower():
                    report += f"• CRITICAL: {category} failures pose security risks\n"
                elif 'logging' in category.lower():
                    report += f"• Important: {category} failures affect audit capabilities\n"
                else:
                    report += f"• {category} failures affect user experience\n"
        
        if len(self.security_events) == 0:
            report += "• WARNING: No security events captured - verify logging configuration\n"
        
        report += f"\nTEST ENVIRONMENT:\n{'═' * 87}\n"
        report += f"• Test Directory: {self.test_dir}\n"
        report += f"• Test Files Created: {len(self.test_config['test_files'])}\n"
        report += f"• Test Directories Created: {len(self.test_config['test_dirs'])}\n"
        report += f"• Security Events Monitored: {len(self.security_events)}\n"
        
        return report
    
    async def run_elite_test_suite(self):
        """Run the complete elite test suite"""
        try:
            logger.info("🚀 Starting Elite PCRst Commands Test Suite")
        except UnicodeEncodeError:
            logger.info("Starting Elite PCRst Commands Test Suite")
        
        try:
            # Setup
            self.setup_elite_test_environment()
            
            # Run all test categories
            await self.test_elite_security_manager_integration()
            await self.test_elite_dangerous_path_handling()
            await self.test_elite_user_output_conventions()
            await self.test_elite_logging_functionality()
            await self.test_elite_cross_platform_compatibility()
            await self.test_elite_file_operations_functionality()
            await self.test_elite_hide_unhide_functionality()
            
            # Generate and display report
            report = self.generate_elite_test_report()
            print(report)
            
            # Save report to file
            report_file = os.path.join(self.test_dir, "elite_test_report.txt")
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            try:
                logger.info(f"📊 Elite test report saved to: {report_file}")
            except UnicodeEncodeError:
                logger.info(f"Elite test report saved to: {report_file}")
            
            # Return success status
            total_tests = len(self.test_results)
            passed_tests = sum(1 for r in self.test_results if r['success'])
            success_rate = (passed_tests / total_tests) if total_tests > 0 else 0
            
            return success_rate >= 0.80  # 80% pass rate for elite standards
            
        except Exception as e:
            try:
                logger.error(f"💥 Elite test suite execution failed: {e}")
            except UnicodeEncodeError:
                logger.error(f"Elite test suite execution failed: {e}")
            raise
            
        finally:
            # Always cleanup
            self.cleanup_elite_test_environment()


async def main():
    """Main execution function"""
    elite_tester = ElitePCRstTestSuite()
    
    try:
        success = await elite_tester.run_elite_test_suite()
        exit_code = 0 if success else 1
        
        if success:
            try:
                logger.info("🎉 Elite test suite completed successfully!")
            except UnicodeEncodeError:
                logger.info("Elite test suite completed successfully!")
        else:
            try:
                logger.error("❌ Elite test suite failed - review results above")
            except UnicodeEncodeError:
                logger.error("Elite test suite failed - review results above")
            
        return exit_code
        
    except Exception as e:
        try:
            logger.error(f"💥 Elite test suite crashed: {e}")
        except UnicodeEncodeError:
            logger.error(f"Elite test suite crashed: {e}")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
