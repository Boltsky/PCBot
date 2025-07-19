"""
Windows File Attribute Modification Logic

This module provides platform-specific implementations for setting and clearing
the Windows "hidden" attribute using multiple approaches:
1. ctypes with Windows API
2. os module
3. attrib command via subprocess

Supports both files and directories with proper error handling and validation.
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple, Union
from enum import Enum

# Only import ctypes on Windows
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

logger = logging.getLogger(__name__)


class AttributeMethod(Enum):
    """Available methods for setting file attributes."""
    CTYPES_API = "ctypes_api"
    OS_MODULE = "os_module"
    ATTRIB_COMMAND = "attrib_command"


class WindowsFileAttributes:
    """Windows file attribute manipulation using multiple methods."""
    
    # Windows file attribute constants
    FILE_ATTRIBUTE_HIDDEN = 0x02
    FILE_ATTRIBUTE_NORMAL = 0x80
    
    def __init__(self, preferred_method: AttributeMethod = AttributeMethod.CTYPES_API):
        """
        Initialize the Windows file attributes handler.
        
        Args:
            preferred_method: Preferred method for attribute manipulation
        """
        self.preferred_method = preferred_method
        self._validate_platform()
        self._setup_ctypes_api()
    
    def _validate_platform(self):
        """Validate that we're running on Windows."""
        if sys.platform != "win32":
            raise RuntimeError("Windows file attributes can only be modified on Windows platform")
    
    def _setup_ctypes_api(self):
        """Set up ctypes Windows API functions."""
        if sys.platform != "win32":
            return
            
        try:
            # Get Windows API functions
            self.kernel32 = ctypes.windll.kernel32
            
            # Define function signatures
            self.kernel32.GetFileAttributesW.argtypes = [wintypes.LPCWSTR]
            self.kernel32.GetFileAttributesW.restype = wintypes.DWORD
            
            self.kernel32.SetFileAttributesW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD]
            self.kernel32.SetFileAttributesW.restype = wintypes.BOOL
            
            self.ctypes_available = True
            logger.debug("ctypes Windows API initialized successfully")
        except Exception as e:
            self.ctypes_available = False
            logger.warning(f"Failed to initialize ctypes Windows API: {e}")
    
    def is_hidden(self, path: Union[str, Path]) -> bool:
        """
        Check if a file or directory has the hidden attribute.
        
        Args:
            path: Path to the file or directory
            
        Returns:
            True if hidden, False otherwise
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")
        
        try:
            # Try ctypes method first
            if self.ctypes_available:
                return self._is_hidden_ctypes(path)
            
            # Fallback to os.stat method
            return self._is_hidden_os_stat(path)
            
        except Exception as e:
            logger.error(f"Failed to check hidden attribute for {path}: {e}")
            return False
    
    def set_hidden(self, path: Union[str, Path], method: Optional[AttributeMethod] = None) -> Tuple[bool, str]:
        """
        Set the hidden attribute on a file or directory.
        
        Args:
            path: Path to the file or directory
            method: Specific method to use (defaults to preferred_method)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        path = Path(path)
        method = method or self.preferred_method
        
        if not path.exists():
            return False, f"Path does not exist: {path}"
        
        try:
            if method == AttributeMethod.CTYPES_API:
                return self._set_hidden_ctypes(path)
            elif method == AttributeMethod.OS_MODULE:
                return self._set_hidden_os_module(path)
            elif method == AttributeMethod.ATTRIB_COMMAND:
                return self._set_hidden_attrib_command(path)
            else:
                return False, f"Unknown method: {method}"
        except Exception as e:
            error_msg = f"Failed to set hidden attribute: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def clear_hidden(self, path: Union[str, Path], method: Optional[AttributeMethod] = None) -> Tuple[bool, str]:
        """
        Clear the hidden attribute from a file or directory.
        
        Args:
            path: Path to the file or directory
            method: Specific method to use (defaults to preferred_method)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        path = Path(path)
        method = method or self.preferred_method
        
        if not path.exists():
            return False, f"Path does not exist: {path}"
        
        try:
            if method == AttributeMethod.CTYPES_API:
                return self._clear_hidden_ctypes(path)
            elif method == AttributeMethod.OS_MODULE:
                return self._clear_hidden_os_module(path)
            elif method == AttributeMethod.ATTRIB_COMMAND:
                return self._clear_hidden_attrib_command(path)
            else:
                return False, f"Unknown method: {method}"
        except Exception as e:
            error_msg = f"Failed to clear hidden attribute: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    # Method 1: ctypes with Windows API
    def _is_hidden_ctypes(self, path: Path) -> bool:
        """Check if hidden using ctypes Windows API."""
        if not self.ctypes_available:
            raise RuntimeError("ctypes Windows API not available")
        
        attributes = self.kernel32.GetFileAttributesW(str(path))
        if attributes == 0xFFFFFFFF:  # INVALID_FILE_ATTRIBUTES
            raise OSError(f"Failed to get file attributes for {path}")
        
        return bool(attributes & self.FILE_ATTRIBUTE_HIDDEN)
    
    def _set_hidden_ctypes(self, path: Path) -> Tuple[bool, str]:
        """Set hidden attribute using ctypes Windows API."""
        if not self.ctypes_available:
            return False, "ctypes Windows API not available"
        
        # Get current attributes
        current_attrs = self.kernel32.GetFileAttributesW(str(path))
        if current_attrs == 0xFFFFFFFF:
            return False, f"Failed to get current file attributes for {path}"
        
        # Add hidden attribute
        new_attrs = current_attrs | self.FILE_ATTRIBUTE_HIDDEN
        
        # Set new attributes
        success = self.kernel32.SetFileAttributesW(str(path), new_attrs)
        if success:
            return True, f"Successfully set hidden attribute on {path}"
        else:
            return False, f"Failed to set hidden attribute on {path}"
    
    def _clear_hidden_ctypes(self, path: Path) -> Tuple[bool, str]:
        """Clear hidden attribute using ctypes Windows API."""
        if not self.ctypes_available:
            return False, "ctypes Windows API not available"
        
        # Get current attributes
        current_attrs = self.kernel32.GetFileAttributesW(str(path))
        if current_attrs == 0xFFFFFFFF:
            return False, f"Failed to get current file attributes for {path}"
        
        # Remove hidden attribute
        new_attrs = current_attrs & ~self.FILE_ATTRIBUTE_HIDDEN
        
        # If no attributes left, set to normal
        if new_attrs == 0:
            new_attrs = self.FILE_ATTRIBUTE_NORMAL
        
        # Set new attributes
        success = self.kernel32.SetFileAttributesW(str(path), new_attrs)
        if success:
            return True, f"Successfully cleared hidden attribute from {path}"
        else:
            return False, f"Failed to clear hidden attribute from {path}"
    
    # Method 2: os module (limited functionality)
    def _is_hidden_os_stat(self, path: Path) -> bool:
        """Check if hidden using os.stat (limited on Windows)."""
        try:
            # On Windows, os.stat doesn't directly expose file attributes
            # This is a workaround using file name patterns
            return path.name.startswith('.')
        except Exception:
            return False
    
    def _set_hidden_os_module(self, path: Path) -> Tuple[bool, str]:
        """Set hidden attribute using os module (limited functionality)."""
        # Note: os module doesn't provide direct access to Windows file attributes
        # This method has limited functionality compared to ctypes
        return False, "os module doesn't support setting Windows file attributes directly"
    
    def _clear_hidden_os_module(self, path: Path) -> Tuple[bool, str]:
        """Clear hidden attribute using os module (limited functionality)."""
        # Note: os module doesn't provide direct access to Windows file attributes
        return False, "os module doesn't support clearing Windows file attributes directly"
    
    # Method 3: attrib command via subprocess
    def _set_hidden_attrib_command(self, path: Path) -> Tuple[bool, str]:
        """Set hidden attribute using attrib command."""
        try:
            # Use attrib command to set hidden attribute
            result = subprocess.run(
                ["attrib", "+H", str(path)],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True, f"Successfully set hidden attribute on {path}"
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                return False, f"attrib command failed: {error_msg}"
        
        except subprocess.SubprocessError as e:
            return False, f"Failed to execute attrib command: {e}"
        except Exception as e:
            return False, f"Unexpected error with attrib command: {e}"
    
    def _clear_hidden_attrib_command(self, path: Path) -> Tuple[bool, str]:
        """Clear hidden attribute using attrib command."""
        try:
            # Use attrib command to clear hidden attribute
            result = subprocess.run(
                ["attrib", "-H", str(path)],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True, f"Successfully cleared hidden attribute from {path}"
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                return False, f"attrib command failed: {error_msg}"
        
        except subprocess.SubprocessError as e:
            return False, f"Failed to execute attrib command: {e}"
        except Exception as e:
            return False, f"Unexpected error with attrib command: {e}"
    
    def get_available_methods(self) -> list[AttributeMethod]:
        """Get list of available methods on current system."""
        available = []
        
        # Check ctypes availability
        if self.ctypes_available:
            available.append(AttributeMethod.CTYPES_API)
        
        # OS module is always available but has limited functionality
        available.append(AttributeMethod.OS_MODULE)
        
        # Check attrib command availability
        try:
            result = subprocess.run(
                ["attrib", "/?"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                available.append(AttributeMethod.ATTRIB_COMMAND)
        except Exception:
            pass
        
        return available
    
    def test_method(self, method: AttributeMethod, test_path: Optional[Union[str, Path]] = None) -> Tuple[bool, str]:
        """
        Test a specific method to ensure it works properly.
        
        Args:
            method: Method to test
            test_path: Optional path to test with (creates temp file if not provided)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        import tempfile
        
        if test_path is None:
            # Create a temporary file for testing
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                test_path = Path(tmp.name)
        else:
            test_path = Path(test_path)
        
        try:
            # Test setting hidden attribute
            success, msg = self.set_hidden(test_path, method)
            if not success:
                return False, f"Failed to set hidden: {msg}"
            
            # Test checking hidden attribute
            if not self.is_hidden(test_path):
                return False, "Hidden attribute not properly set"
            
            # Test clearing hidden attribute
            success, msg = self.clear_hidden(test_path, method)
            if not success:
                return False, f"Failed to clear hidden: {msg}"
            
            # Test that hidden attribute is cleared
            if self.is_hidden(test_path):
                return False, "Hidden attribute not properly cleared"
            
            return True, f"Method {method.value} works correctly"
        
        except Exception as e:
            return False, f"Method {method.value} test failed: {e}"
        
        finally:
            # Clean up temp file
            if test_path.exists():
                try:
                    test_path.unlink()
                except Exception:
                    pass


# Convenience functions for easy usage
def set_hidden_attribute(path: Union[str, Path], method: Optional[AttributeMethod] = None) -> Tuple[bool, str]:
    """
    Convenience function to set hidden attribute.
    
    Args:
        path: Path to file or directory
        method: Method to use (defaults to ctypes API)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    if sys.platform != "win32":
        return False, "Windows file attributes only supported on Windows"
    
    try:
        handler = WindowsFileAttributes(method or AttributeMethod.CTYPES_API)
        return handler.set_hidden(path, method)
    except Exception as e:
        return False, f"Failed to set hidden attribute: {e}"


def clear_hidden_attribute(path: Union[str, Path], method: Optional[AttributeMethod] = None) -> Tuple[bool, str]:
    """
    Convenience function to clear hidden attribute.
    
    Args:
        path: Path to file or directory
        method: Method to use (defaults to ctypes API)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    if sys.platform != "win32":
        return False, "Windows file attributes only supported on Windows"
    
    try:
        handler = WindowsFileAttributes(method or AttributeMethod.CTYPES_API)
        return handler.clear_hidden(path, method)
    except Exception as e:
        return False, f"Failed to clear hidden attribute: {e}"


def is_hidden_attribute(path: Union[str, Path]) -> bool:
    """
    Convenience function to check if file/directory has hidden attribute.
    
    Args:
        path: Path to file or directory
        
    Returns:
        True if hidden, False otherwise
    """
    if sys.platform != "win32":
        return False
    
    try:
        handler = WindowsFileAttributes()
        return handler.is_hidden(path)
    except Exception as e:
        logger.error(f"Failed to check hidden attribute: {e}")
        return False


# Example usage and testing
def main():
    """Example usage of the Windows file attributes module."""
    if sys.platform != "win32":
        print("This module only works on Windows")
        return
    
    # Initialize handler
    handler = WindowsFileAttributes()
    
    # Show available methods
    available_methods = handler.get_available_methods()
    print(f"Available methods: {[m.value for m in available_methods]}")
    
    # Test each method
    for method in available_methods:
        success, msg = handler.test_method(method)
        print(f"{method.value}: {'✓' if success else '✗'} {msg}")
    
    # Example with a real file (create a test file)
    test_file = Path("test_hidden_file.txt")
    test_file.write_text("This is a test file")
    
    try:
        print(f"\nTesting with file: {test_file}")
        
        # Test setting hidden
        success, msg = handler.set_hidden(test_file)
        print(f"Set hidden: {'✓' if success else '✗'} {msg}")
        
        # Check if hidden
        is_hidden = handler.is_hidden(test_file)
        print(f"Is hidden: {is_hidden}")
        
        # Clear hidden
        success, msg = handler.clear_hidden(test_file)
        print(f"Clear hidden: {'✓' if success else '✗'} {msg}")
        
        # Check if still hidden
        is_hidden = handler.is_hidden(test_file)
        print(f"Is still hidden: {is_hidden}")
        
    finally:
        # Clean up
        if test_file.exists():
            test_file.unlink()


if __name__ == "__main__":
    main()
