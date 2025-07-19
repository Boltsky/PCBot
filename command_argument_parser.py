import re
import os
import shlex
from typing import Dict, List, Any, Optional, Tuple


class CommandArgumentParser:
    """
    Robust command argument parser for file/folder operations.
    Handles key=value pairs with support for spaces, quotes, and edge cases.
    """
    
    def __init__(self):
        self.supported_commands = {
            'delete': ['path', 'isDirectory'],
            'copy': ['sourcePath', 'destinationPath', 'isDirectory'],
            'move': ['sourcePath', 'destinationPath', 'isDirectory'],
            'rename': ['path', 'newName', 'isDirectory']
        }
    
    def parse_command_args(self, command_args: List[str]) -> Dict[str, str]:
        """
        Parse command arguments with robust handling of spaces and edge cases.
        
        Args:
            command_args: List of command arguments
            
        Returns:
            Dictionary of parsed key=value pairs
            
        Raises:
            ValueError: If argument format is invalid
        """
        if not command_args:
            return {}
        
        parsed_args = {}
        
        # Join all arguments and then split by space, respecting quotes
        full_arg_string = ' '.join(command_args)
        
        # Use regex to find key=value pairs, handling quoted values
        pattern = r'(\w+)=(["\']?)([^"\']*)\2(?=\s|$)'
        matches = re.findall(pattern, full_arg_string)
        
        if not matches:
            # Fallback to simple parsing if regex fails
            try:
                for arg in command_args:
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        parsed_args[key.strip()] = value.strip()
                    else:
                        raise ValueError(f"Invalid argument format: '{arg}'. Expected key=value format.")
            except ValueError as e:
                raise ValueError(f"Invalid argument format. Please use key=value format. Error: {e}")
        else:
            for match in matches:
                key, quote, value = match
                parsed_args[key] = value
        
        # Handle edge cases and clean up values
        for key, value in parsed_args.items():
            # Remove surrounding quotes if present
            if value.startswith('"') and value.endswith('"'):
                parsed_args[key] = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                parsed_args[key] = value[1:-1]
            
            # Handle escaped characters
            parsed_args[key] = parsed_args[key].replace('\\"', '"').replace("\\", "\\")
        
        return parsed_args
    
    def validate_args_for_command(self, args: Dict[str, str], command: str) -> Tuple[bool, str]:
        """
        Validate arguments for a specific command.
        
        Args:
            args: Parsed arguments dictionary
            command: Command name (delete, copy, move, rename)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if command not in self.supported_commands:
            return False, f"Unsupported command: {command}"
        
        required_keys = self.supported_commands[command]
        
        # Check for missing required arguments
        missing_keys = [key for key in required_keys if key not in args or not args[key].strip()]
        if missing_keys:
            return False, f"Missing required arguments: {', '.join(missing_keys)}"
        
        # Validate specific argument formats
        validation_errors = []
        
        # Validate paths
        path_keys = ['path', 'sourcePath', 'destinationPath']
        for key in path_keys:
            if key in args:
                error = self._validate_path(args[key], key)
                if error:
                    validation_errors.append(error)
        
        # Validate isDirectory parameter
        if 'isDirectory' in args:
            if args['isDirectory'].lower() not in ['true', 'false']:
                validation_errors.append("isDirectory must be 'true' or 'false'")
        
        # Validate newName parameter
        if 'newName' in args:
            error = self._validate_filename(args['newName'])
            if error:
                validation_errors.append(error)
        
        if validation_errors:
            return False, "; ".join(validation_errors)
        
        return True, ""
    
    def _validate_path(self, path: str, param_name: str) -> Optional[str]:
        """
        Validate a file/directory path.
        
        Args:
            path: Path to validate
            param_name: Parameter name for error reporting
            
        Returns:
            Error message if invalid, None if valid
        """
        if not path or not path.strip():
            return f"{param_name} cannot be empty"
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in path:
                return f"{param_name} contains invalid character: '{char}'"
        
        # Check for path traversal attempts
        if '..' in path:
            return f"{param_name} contains path traversal sequence '..'"
        
        # Check for Windows reserved names
        path_parts = path.split(os.sep)
        for part in path_parts:
            if part.upper() in ['CON', 'PRN', 'AUX', 'NUL'] or \
               part.upper().startswith(('COM', 'LPT')):
                return f"{param_name} contains Windows reserved name: '{part}'"
        
        return None
    
    def _validate_filename(self, filename: str) -> Optional[str]:
        """
        Validate a filename.
        
        Args:
            filename: Filename to validate
            
        Returns:
            Error message if invalid, None if valid
        """
        if not filename or not filename.strip():
            return "newName cannot be empty"
        
        # Check for path separators in filename
        if os.sep in filename or '/' in filename or '\\' in filename:
            return "newName cannot contain path separators"
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            if char in filename:
                return f"newName contains invalid character: '{char}'"
        
        # Check for Windows reserved names
        base_name = filename.split('.')[0].upper()
        if base_name in ['CON', 'PRN', 'AUX', 'NUL'] or \
           base_name.startswith(('COM', 'LPT')):
            return f"newName contains Windows reserved name: '{base_name}'"
        
        return None
    
    def get_command_help(self, command: str) -> str:
        """
        Get help text for a specific command.
        
        Args:
            command: Command name
            
        Returns:
            Help text string
        """
        help_texts = {
            'delete': """
**Delete Command Usage:**
`/delete path=<file_or_dir_path> isDirectory=<true/false>`

**Examples:**
• `/delete path="my file.txt" isDirectory=false`
• `/delete path=/home/user/folder isDirectory=true`
• `/delete path="C:\\Users\\Name\\Documents\\file.doc" isDirectory=false`

**Required Parameters:**
• `path` - Path to the file or directory to delete
• `isDirectory` - Set to 'true' for directories, 'false' for files

**Notes:**
• Use quotes around paths containing spaces
• Paths are validated for security
• Directory deletion may require confirmation
            """,
            'copy': """
**Copy Command Usage:**
`/copy sourcePath=<source_path> destinationPath=<dest_path> isDirectory=<true/false>`

**Examples:**
• `/copy sourcePath="source file.txt" destinationPath="dest file.txt" isDirectory=false`
• `/copy sourcePath=/home/user/folder destinationPath=/home/user/backup isDirectory=true`

**Required Parameters:**
• `sourcePath` - Path to the source file or directory
• `destinationPath` - Path where the copy should be created
• `isDirectory` - Set to 'true' for directories, 'false' for files
            """,
            'move': """
**Move Command Usage:**
`/move sourcePath=<source_path> destinationPath=<dest_path> isDirectory=<true/false>`

**Examples:**
• `/move sourcePath="old file.txt" destinationPath="new file.txt" isDirectory=false`
• `/move sourcePath=/home/user/old_folder destinationPath=/home/user/new_folder isDirectory=true`

**Required Parameters:**
• `sourcePath` - Path to the source file or directory
• `destinationPath` - Path where the item should be moved
• `isDirectory` - Set to 'true' for directories, 'false' for files
            """,
            'rename': """
**Rename Command Usage:**
`/rename path=<current_path> newName=<new_name> isDirectory=<true/false>`

**Examples:**
• `/rename path="old file.txt" newName="new file.txt" isDirectory=false`
• `/rename path=/home/user/old_folder newName=new_folder isDirectory=true`

**Required Parameters:**
• `path` - Path to the file or directory to rename
• `newName` - New name for the file or directory (not full path)
• `isDirectory` - Set to 'true' for directories, 'false' for files
            """
        }
        
        return help_texts.get(command, "Command not found")


# Global parser instance
command_parser = CommandArgumentParser()


# Legacy functions for backward compatibility
def parse_command_args(command_args: List[str]) -> Dict[str, str]:
    """Legacy function for backward compatibility."""
    return command_parser.parse_command_args(command_args)


def validate_args_for_command(args: Dict[str, str], required_keys: List[str]) -> None:
    """Legacy function for backward compatibility."""
    missing_keys = [key for key in required_keys if key not in args or not args[key].strip()]
    if missing_keys:
        raise ValueError(f"Missing required arguments: {', '.join(missing_keys)}")
