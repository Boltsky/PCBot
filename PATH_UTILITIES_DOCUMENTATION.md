# Path Resolution and Validation Utilities

## Overview

The `PathUtils` class provides comprehensive cross-platform path resolution, normalization, and validation utilities for the PCRst project. It integrates with the `SecurityManager` to ensure all path operations adhere to strict security policies.

## Features

- **Cross-platform compatibility** - Works on Windows, Linux, and macOS
- **Security-first design** - Validates paths against dangerous patterns
- **Integration with SecurityManager** - Enforces permitted directory restrictions
- **Path normalization** - Handles different path separators and formats
- **Filename sanitization** - Removes invalid characters for target platform
- **Comprehensive validation** - Checks path length, reserved names, and security patterns

## Class: PathUtils

### Constructor

```python
PathUtils(security_manager: SecurityManager)
```

Initializes the PathUtils instance with a SecurityManager for validation.

### Core Methods

#### `resolve_path(user_id: str, path: str) -> Tuple[bool, str]`

Resolves a path relative to the user's base directory.

**Parameters:**
- `user_id`: User identifier
- `path`: Path to resolve (relative or absolute)

**Returns:**
- `Tuple[bool, str]`: (success, resolved_path_or_error_message)

**Example:**
```python
success, resolved = path_utils.resolve_path("user123", "documents/file.txt")
if success:
    print(f"Resolved path: {resolved}")
```

#### `validate_path(user_id: str, path: str) -> Tuple[bool, str]`

Performs comprehensive path validation with security checks.

**Parameters:**
- `user_id`: User identifier
- `path`: Path to validate

**Returns:**
- `Tuple[bool, str]`: (is_valid, error_message_or_success)

**Security Checks:**
- Path format validation
- Dangerous pattern detection
- Path length limits
- Reserved name validation
- Directory permission validation

#### `is_safe_path(user_id: str, path: str) -> bool`

Quick check if a path is safe for the user.

**Parameters:**
- `user_id`: User identifier
- `path`: Path to check

**Returns:**
- `bool`: True if path is safe

#### `sanitize_filename(filename: str) -> str`

Sanitizes a filename for the current platform.

**Parameters:**
- `filename`: Filename to sanitize

**Returns:**
- `str`: Sanitized filename

**Features:**
- Removes invalid characters
- Handles reserved names
- Strips dangerous patterns
- Ensures non-empty result

**Example:**
```python
clean_name = path_utils.sanitize_filename("file<>:\"|?*.txt")
# Result: "file_______.txt" on Windows
```

### Utility Methods

#### `get_user_directory(user_id: str) -> str`

Gets the user's base directory.

#### `convert_path_separators(path: str, target_platform: Optional[str] = None) -> str`

Converts path separators for the target platform.

**Example:**
```python
windows_path = path_utils.convert_path_separators("folder/file.txt", "windows")
# Result: "folder\\file.txt"
```

#### `get_relative_path(user_id: str, path: str) -> Tuple[bool, str]`

Gets relative path from user's base directory.

#### `join_paths(*paths: str) -> str`

Safely joins multiple path components.

**Example:**
```python
joined = path_utils.join_paths("folder", "subfolder", "file.txt")
```

#### `get_path_info(path: str) -> dict`

Gets comprehensive path information.

**Returns:**
- Dictionary with path details:
  - `original`: Original path
  - `normalized`: Normalized path
  - `absolute`: Whether path is absolute
  - `exists`: Whether path exists
  - `is_file`: Whether it's a file
  - `is_dir`: Whether it's a directory
  - `parent`: Parent directory
  - `name`: Filename
  - `stem`: Filename without extension
  - `suffix`: File extension
  - `parts`: Path components
  - `platform`: Current platform

## Security Features

### Dangerous Pattern Detection

The utility detects and blocks dangerous patterns:

**Windows:**
- Path traversal: `..\\`
- Control characters: `\x00-\x1f`
- Variable expansion: `${...}`
- Environment variables: `%VAR%`
- UNC path attempts: `\\.\`

**POSIX:**
- Path traversal: `../`
- Control characters: `\x00-\x1f`
- Variable expansion: `${...}`
- Command substitution: `` `...` ``
- Command separators: `|`, `;`, `&`

**Common:**
- Null bytes: `\x00`
- Hex encoded characters: `\x##`
- URL encoded characters: `%##`

### Reserved Name Validation

**Windows Reserved Names:**
- Device names: `CON`, `PRN`, `AUX`, `NUL`
- COM ports: `COM1-COM9`
- LPT ports: `LPT1-LPT9`

### Path Length Limits

- **Windows:** 260 characters (traditional limit)
- **POSIX:** 4096 characters
- **Default:** 255 characters

## Integration with SecurityManager

The PathUtils class integrates with SecurityManager to:

1. **Get user directories** - Retrieves user-specific safe directories
2. **Validate file paths** - Ensures paths are within permitted directories
3. **Log security events** - Records validation attempts and violations
4. **Enforce quotas** - Respects user storage limits

## Error Handling

All methods include comprehensive error handling:

- Invalid input validation
- Exception catching and logging
- Graceful error messages
- Security violation logging

## Platform Detection

Automatically detects the current platform:

- **Windows:** `os.name == 'nt'` or `platform.system() == 'Windows'`
- **POSIX:** `os.name == 'posix'` or Linux/Darwin
- **Other:** Fallback for unsupported platforms

## Usage Examples

### Basic Usage

```python
from path_utils import PathUtils
from security_manager import SecurityManager

# Initialize
security_manager = SecurityManager()
path_utils = PathUtils(security_manager)

# Authenticate user
user = security_manager.authenticate_user(12345, "username")
user_id = user.user_id

# Resolve path
success, resolved = path_utils.resolve_path(user_id, "documents/file.txt")

# Validate path
is_valid, message = path_utils.validate_path(user_id, resolved)

# Sanitize filename
clean_name = path_utils.sanitize_filename("user input.txt")
```

### Advanced Usage

```python
# Get comprehensive path info
info = path_utils.get_path_info("/path/to/file.txt")
print(f"File exists: {info['exists']}")
print(f"Is file: {info['is_file']}")
print(f"Parent: {info['parent']}")

# Cross-platform path conversion
windows_path = path_utils.convert_path_separators("unix/path", "windows")
unix_path = path_utils.convert_path_separators("windows\\path", "posix")

# Safe path joining
safe_path = path_utils.join_paths("base", "sub", "file.txt")

# Relative path calculation
success, relative = path_utils.get_relative_path(user_id, absolute_path)
```

## Testing

The utilities include comprehensive test coverage:

- Unit tests for all methods
- Security pattern validation tests
- Cross-platform compatibility tests
- Integration tests with SecurityManager
- Error handling tests

Run tests with:
```bash
python test_path_utils.py
```

## Security Considerations

1. **Always validate paths** before file operations
2. **Use resolved paths** for actual file operations
3. **Check user permissions** via SecurityManager
4. **Log security violations** for monitoring
5. **Sanitize user input** for filenames
6. **Respect platform limitations** for path lengths

## Best Practices

1. **Initialize once** - Create PathUtils instance once and reuse
2. **Handle errors** - Always check return values
3. **Use relative paths** when possible for user operations
4. **Sanitize filenames** from user input
5. **Validate before operations** - Don't trust user input
6. **Log security events** for audit trails

## Limitations

1. **Platform-specific** - Some features only work on specific platforms
2. **SecurityManager dependency** - Requires initialized SecurityManager
3. **Path length limits** - Enforced by platform constraints
4. **Unicode support** - Limited by underlying OS support

## Future Enhancements

1. **Extended platform support** - Additional OS support
2. **Custom validation rules** - User-defined security patterns
3. **Path caching** - Performance optimization
4. **Async operations** - Non-blocking path operations
5. **Advanced sanitization** - More sophisticated filename cleaning
