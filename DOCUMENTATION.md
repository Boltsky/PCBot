# PCRst Bot Documentation

## Overview
PCRst is a comprehensive Telegram bot providing secure file management, system operations, and remote access capabilities. The bot features advanced security measures, file transfer capabilities, and system management tools.

## Security Features

### 🛡️ Authentication & Authorization
- **User Authentication**: Automatic user registration and session management
- **Role-based Access Control**: Different permission levels for various operations
- **Session Management**: Automatic session timeout and renewal
- **Audit Logging**: Complete audit trail of all user actions

### 🔒 File Security
- **Path Traversal Protection**: Prevents access to system files outside safe directories
- **File Type Validation**: Strict MIME type checking and extension filtering
- **Quota Management**: Per-user file size limits and usage tracking
- **Integrity Verification**: SHA-256 hash verification for all file operations

### 📊 Safe Directories
Files can only be accessed from these approved locations:
- `~/Desktop` - User's desktop directory
- `~/Documents` - User's documents directory  
- `~/Downloads` - User's downloads directory
- `~/Pictures` - User's pictures directory
- `~/Videos` - User's videos directory
- `~/Music` - User's music directory
- System temporary directory
- Current working directory

## Commands Reference

### Basic Commands

#### `/start`
Initialize the bot and display welcome message with user information.

**Usage:** `/start`

**Response:** 
- User authentication status
- Quota information
- Security features overview
- Available commands

#### `/help`
Display comprehensive help information for all available commands.

**Usage:** `/help`

**Features:**
- Complete command list
- Usage examples
- Security warnings
- Feature descriptions

---

### File Management Commands

#### `/upload <file_path> [file_path2] ...`
Upload one or more files to the bot with comprehensive security validation.

**Usage:** 
```
/upload ~/Documents/report.pdf
/upload ~/Pictures/image.jpg ~/Videos/video.mp4
```

**Features:**
- **Multi-file Support**: Upload multiple files simultaneously
- **Progress Tracking**: Real-time upload progress with speed indicators
- **Security Validation**: Path, type, and quota checks
- **Integrity Verification**: SHA-256 hash verification
- **Automatic Compression**: Directories are automatically compressed
- **Concurrent Processing**: Parallel upload handling

**Security Checks:**
- Path validation (safe directories only)
- File type validation (MIME type checking)
- File size limits (50MB per file)
- Quota enforcement (100MB default per user)
- Extension blocking (executables, scripts, etc.)

#### `/download <url> [destination_path]`
Download files from URLs with advanced resume and retry capabilities.

**Usage:**
```
/download https://example.com/file.pdf
/download https://example.com/file.pdf ~/Downloads/myfile.pdf
```

**Features:**
- **Resume Support**: Automatically resume interrupted downloads
- **Progress Tracking**: Real-time download progress with ETA
- **Retry Logic**: Automatic retry on network failures
- **Metadata Preservation**: File timestamps and attributes preserved
- **Security Validation**: URL and destination path validation
- **Bandwidth Management**: Configurable download speed limits

**Security Features:**
- URL validation (HTTP/HTTPS only)
- Destination path validation
- File size limits (100MB max)
- Extension blocking
- Safe directory enforcement

#### `/listfiles <directory_path> [options]`
List files in a directory with advanced filtering and sorting options.

**Usage:**
```
/listfiles ~/Documents
/listfiles ~/Pictures --type=image --sort=size
/listfiles ~/Downloads --pattern=*.pdf --detailed
```

**Options:**
- `--pattern=<pattern>` - Filter by filename pattern (e.g., `*.txt`)
- `--type=<type>` - Filter by file type (`image`, `video`, `audio`, `document`, `archive`)
- `--size_min=<bytes>` - Filter by minimum file size
- `--size_max=<bytes>` - Filter by maximum file size
- `--sort=<field>` - Sort by field (`name`, `size`, `modified`, `type`)
- `--detailed` - Show detailed file information
- `--hidden` - Show hidden files

**Features:**
- **Smart Filtering**: Multiple filter criteria support
- **Flexible Sorting**: Sort by various file attributes
- **File Type Icons**: Visual file type identification
- **Size Formatting**: Human-readable file sizes
- **Directory Statistics**: Total files and size information

#### `/fileinfo <file_path>`
Display detailed information about a specific file.

**Usage:** `/fileinfo ~/Documents/report.pdf`

**Information Provided:**
- File name and extension
- File size (formatted)
- MIME type
- Creation and modification dates
- SHA-256 hash
- File permissions
- Security validation status

#### `/compress <directory_path> [output_path]`
Compress a directory into a ZIP archive.

**Usage:**
```
/compress ~/Documents/project
/compress ~/Pictures/vacation ~/Downloads/vacation.zip
```

**Features:**
- **Recursive Compression**: Includes all subdirectories
- **Progress Tracking**: Real-time compression progress
- **Size Validation**: Ensures compressed file fits within limits
- **Security Checks**: Validates all files before compression

#### `/extract <archive_path> [destination_dir]`
Extract files from a ZIP archive.

**Usage:**
```
/extract ~/Downloads/archive.zip
/extract ~/Downloads/archive.zip ~/Documents/extracted
```

**Features:**
- **Safe Extraction**: Prevents zip bombs and path traversal
- **Progress Tracking**: Real-time extraction progress
- **Validation**: Verifies archive integrity before extraction

---

### System Management Commands

#### `/screenshot`
Capture a screenshot of the current screen.

**Usage:** `/screenshot`

**Features:**
- **High Quality**: Full resolution screenshot capture
- **Cross-platform**: Works on Windows, Linux, and macOS
- **Automatic Cleanup**: Temporary files automatically removed
- **Timestamp**: Screenshots include capture timestamp

#### `/screenrecord [duration]`
Record the screen for a specified duration.

**Usage:**
```
/screenrecord
/screenrecord 30
/screenrecord 120
```

**Parameters:**
- `duration` - Recording duration in seconds (default: 60, max: 300)

**Features:**
- **Configurable Duration**: 1-300 seconds recording time
- **Progress Tracking**: Real-time recording progress
- **Automatic Cleanup**: Temporary files removed after upload
- **File Size Validation**: Ensures recording fits Telegram limits

#### `/hardreset`
⚠️ **DANGEROUS** - Permanently delete all data from user's home directory.

**Usage:** `/hardreset`

**Security:**
- Requires admin privileges
- Comprehensive logging
- Warning messages
- Cannot be undone

#### `/resetsettings`
Reset various PC settings to default values.

**Usage:** `/resetsettings`

**Reset Categories:**
- **Network Settings**: IP configuration, DNS, firewall
- **Personalization**: Desktop background, theme, taskbar
- **System Preferences**: Power management, updates, privacy
- **User Preferences**: Start menu, Explorer settings, recent items

**Features:**
- **Comprehensive Reset**: Multiple setting categories
- **Progress Tracking**: Real-time reset progress
- **Error Handling**: Graceful handling of permission issues
- **Detailed Reporting**: Success/failure status for each operation

#### `/cleantemp`
Clean temporary files and cache directories.

**Usage:** `/cleantemp`

**Cleaned Locations:**
- System temporary directories
- User cache directories
- Browser cache (if accessible)
- Application temporary files
- Security manager temporary files

**Features:**
- **Safe Cleaning**: Only removes safe temporary files
- **Size Reporting**: Shows space freed
- **Error Handling**: Handles permission denied gracefully
- **Cross-platform**: Works on Windows, Linux, macOS

---

### Security Commands

#### `/quota`
Display current file quota usage and statistics.

**Usage:** `/quota`

**Information:**
- Total quota allocation
- Used quota (bytes and percentage)
- Available quota
- File count
- Maximum file size
- Last cleanup date
- Usage recommendations

#### `/secstats` (Admin Only)
Display comprehensive security statistics.

**Usage:** `/secstats`

**Statistics:**
- Total users and active sessions
- Recent security events (24h)
- Temporary files statistics
- Active security features
- System health metrics

#### `/cleanup [force]` (Admin Only)
Force cleanup of temporary files and expired resources.

**Usage:**
```
/cleanup
/cleanup force
```

**Options:**
- `force` - Force cleanup of all temporary files regardless of age

**Features:**
- **Selective Cleanup**: Only expired files by default
- **Force Mode**: Clean all temporary files
- **Detailed Reporting**: Files cleaned and space freed
- **Error Reporting**: Permission and access issues

#### `/transfers`
Display status of active file transfers.

**Usage:** `/transfers`

**Information:**
- Active uploads and downloads
- Progress percentage
- Transfer speed
- Estimated time remaining
- File names and sizes

#### `/sechelp`
Display security-related help and command information.

**Usage:** `/sechelp`

**Information:**
- Security command reference
- Feature descriptions
- File restrictions
- Safe directories
- Configuration limits

---

## Configuration

### File Limits
- **Maximum File Size**: 50MB per file
- **User Quota**: 100MB default (500MB maximum)
- **Concurrent Transfers**: 5 simultaneous transfers
- **Bandwidth Limit**: 10MB/s default

### Security Settings
- **Session Timeout**: 1 hour
- **Temporary File Retention**: 24 hours
- **Cleanup Interval**: 60 minutes
- **Audit Log Retention**: 30 days

### Blocked Extensions
The following file extensions are blocked for security:
`.exe`, `.bat`, `.cmd`, `.com`, `.pif`, `.scr`, `.vbs`, `.js`, `.jar`, `.msi`, `.dll`, `.sys`, `.scf`, `.lnk`, `.inf`, `.reg`, `.hta`, `.ps1`

### Allowed MIME Types
- **Documents**: PDF, Word, Excel, PowerPoint, plain text, CSV, JSON, XML
- **Images**: JPEG, PNG, GIF, BMP, TIFF, WebP
- **Videos**: MP4, AVI, MKV, MOV, WMV, FLV
- **Audio**: MP3, WAV, FLAC, AAC, OGG
- **Archives**: ZIP, RAR, 7Z, TAR, GZIP
- **Code**: Python, Java, C, C++, PHP, JavaScript, HTML, CSS

## Error Handling

### Common Errors
- **Permission Denied**: File or directory access restricted
- **Quota Exceeded**: File size exceeds user quota
- **Invalid Path**: Path outside safe directories
- **Blocked Extension**: File type not allowed
- **Network Error**: Download/upload connectivity issues

### Recovery Procedures
1. **Quota Issues**: Use `/cleantemp` to free space
2. **Permission Errors**: Check file/directory permissions
3. **Network Issues**: Retry operation or check connectivity
4. **Security Violations**: Review file paths and types

## Best Practices

### File Management
- Use descriptive filenames
- Organize files in appropriate directories
- Regularly clean temporary files
- Monitor quota usage
- Verify file integrity after transfers

### Security
- Only access files from safe directories
- Avoid uploading sensitive files
- Use strong, unique passwords
- Regularly review security logs
- Report suspicious activity

### Performance
- Upload/download during off-peak hours
- Use file compression for large directories
- Monitor transfer speeds
- Clean temporary files regularly
- Limit concurrent operations

## Troubleshooting

### Upload Issues
1. Check file size limits
2. Verify file type is allowed
3. Ensure path is in safe directory
4. Check quota availability
5. Verify file permissions

### Download Issues
1. Verify URL is valid and accessible
2. Check destination path permissions
3. Ensure sufficient disk space
4. Verify network connectivity
5. Check file size limits

### Security Issues
1. Review audit logs
2. Check user permissions
3. Verify session validity
4. Review security settings
5. Contact administrator if needed

## Support

For additional support or reporting issues:
1. Check this documentation
2. Review error messages
3. Check security logs
4. Contact system administrator
5. Review audit trail

---

*Last Updated: December 2024*
*Version: 2.0*
