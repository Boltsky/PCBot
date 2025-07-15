# Upload Functionality Documentation

## Overview

The `/upload <file_path>` command provides secure and efficient file upload functionality with comprehensive security measures, progress tracking, and support for multiple file types and batch operations.

## Features

### 🔒 Security Features

1. **Path Traversal Prevention**
   - Prevents access to files outside safe directories
   - Validates absolute paths against sandboxed directories
   - Blocks dangerous path patterns like `../` and `\..\`

2. **File Type Validation**
   - Supports 41+ MIME types including documents, images, videos, audio, archives, and code files
   - Blocks dangerous file extensions (.exe, .bat, .cmd, .com, .pif, .scr, .vbs, .js, .jar, .msi, .dll, .sys, .scf, .lnk, .inf, .reg)
   - Auto-detects file types using MIME type analysis

3. **Filename Sanitization**
   - Removes dangerous characters (`<>:"|?*`)
   - Prevents Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
   - Handles path separators and special characters

4. **File Size Restrictions**
   - Maximum file size: 50MB (Telegram's limit)
   - Automatic size validation before upload
   - Prevents oversized directory compression

5. **Sandboxed Access**
   - Restricted to safe directories: Desktop, Documents, Downloads, Pictures, Videos, Music, Temp, Current Working Directory
   - Prevents access to system directories and sensitive files

### 📤 Upload Capabilities

1. **Single File Upload**
   ```
   /upload /path/to/file.txt
   ```

2. **Multiple File Upload**
   ```
   /upload /path/file1.txt /path/file2.jpg /path/file3.pdf
   ```

3. **Directory Upload with Auto-Compression**
   ```
   /upload /path/to/directory
   ```
   - Automatically creates ZIP archive
   - Maintains directory structure
   - Validates compressed file size

4. **Batch Upload with Wildcards**
   ```
   /upload /path/*.txt
   /upload /path/documents/*.pdf
   ```

### ⚡ Performance Features

1. **Chunked Upload**
   - 4MB chunks for large files
   - Efficient memory usage
   - Better upload reliability

2. **Real-time Progress Tracking**
   - Progress bars for large files
   - Status updates every 10% completion
   - Upload statistics and summaries

3. **Metadata Extraction**
   - File name, size, MIME type
   - Creation/modification timestamps
   - SHA-256 hash for integrity verification

## Usage Examples

### Basic File Upload
```
/upload C:\Users\Username\Documents\report.pdf
```

### Multiple Files
```
/upload C:\Users\Username\Pictures\photo1.jpg C:\Users\Username\Pictures\photo2.png
```

### Directory Upload
```
/upload C:\Users\Username\Documents\ProjectFiles
```
*Creates a ZIP archive of the entire directory*

### Wildcard Upload
```
/upload C:\Users\Username\Documents\*.docx
```
*Uploads all Word documents in the folder*

## Supported File Types

### Documents
- PDF (application/pdf)
- Microsoft Word (.docx, .doc)
- Microsoft Excel (.xlsx, .xls)
- Microsoft PowerPoint (.pptx, .ppt)
- Text files (.txt)
- CSV files (.csv)
- JSON files (.json)
- XML files (.xml)

### Images
- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- BMP (.bmp)
- TIFF (.tiff)
- WebP (.webp)

### Videos
- MP4 (.mp4)
- AVI (.avi)
- MKV (.mkv)
- MOV (.mov)
- WMV (.wmv)
- FLV (.flv)

### Audio
- MP3 (.mp3)
- WAV (.wav)
- FLAC (.flac)
- AAC (.aac)
- OGG (.ogg)

### Archives
- ZIP (.zip)
- RAR (.rar)
- 7Z (.7z)
- TAR (.tar)
- GZIP (.gz)

### Code Files
- Python (.py)
- Java (.java)
- C/C++ (.c, .cpp)
- PHP (.php)
- JavaScript (.js)
- HTML (.html)
- CSS (.css)

## Security Measures

### Blocked File Extensions
```
.exe, .bat, .cmd, .com, .pif, .scr, .vbs, .js, .jar, .msi, .dll, .sys, .scf, .lnk, .inf, .reg
```

### Safe Directories
- ~/Desktop
- ~/Documents
- ~/Downloads
- ~/Pictures
- ~/Videos
- ~/Music
- System temporary directory
- Current working directory

### Dangerous Pattern Detection
- Path traversal attempts (`../`, `\..\`)
- Invalid filename characters (`<>:"|?*`)
- Windows reserved names
- Malicious path patterns

## Error Handling

The upload system provides comprehensive error handling:

1. **File Not Found**: Clear error message with file path
2. **Permission Denied**: Informative message about access restrictions
3. **Security Violations**: Detailed explanation of security issues
4. **Size Limits**: File size information and limit explanations
5. **Upload Failures**: Network and processing error handling

## Configuration

### Upload Limits
- **Maximum File Size**: 50MB
- **Chunk Size**: 4MB
- **Progress Update Interval**: 10%

### Customization
All configuration options are centralized in the `UploadConfig` class:
- Modify `MAX_FILE_SIZE` to change size limits
- Update `ALLOWED_MIME_TYPES` to add/remove supported types
- Adjust `SAFE_DIRECTORIES` to modify accessible locations
- Customize `BLOCKED_EXTENSIONS` for additional security

## Implementation Details

### Core Components

1. **UploadConfig Class**
   - Centralized configuration management
   - Security policy definitions
   - File type and size restrictions

2. **Security Validation Functions**
   - `validate_file_security()`: Comprehensive file validation
   - `is_path_safe()`: Path safety verification
   - `sanitize_filename()`: Filename sanitization

3. **Upload Processing**
   - `upload_file_chunked()`: Efficient file upload with progress tracking
   - `create_zip_from_directory()`: Directory compression
   - `get_file_metadata()`: Metadata extraction

4. **Progress Tracking**
   - Real-time progress updates
   - Message editing for status updates
   - Completion summaries

### Error Recovery
- Automatic cleanup of temporary files
- Graceful failure handling
- Detailed error reporting
- Upload retry capabilities

## Best Practices

1. **File Organization**
   - Keep files in designated safe directories
   - Use descriptive filenames
   - Organize files by type or project

2. **Security Considerations**
   - Regularly review uploaded files
   - Monitor file sizes and types
   - Verify file integrity using provided hashes

3. **Performance Optimization**
   - Compress large directories before upload
   - Use wildcards for batch operations
   - Monitor upload progress for large files

## Troubleshooting

### Common Issues

1. **"File path is outside safe directories"**
   - Move files to Documents, Desktop, or Downloads
   - Use absolute paths to safe directories

2. **"File extension is blocked"**
   - File type not allowed for security reasons
   - Convert to supported format if possible

3. **"File size exceeds maximum"**
   - Compress large files
   - Split large files into smaller parts

4. **"Path not found"**
   - Verify file path is correct
   - Check file permissions
   - Ensure file exists

### Debug Information
- Upload logs with detailed error messages
- File metadata for troubleshooting
- Progress tracking for large uploads
- Security validation results

## Technical Specifications

- **Language**: Python 3.7+
- **Dependencies**: python-telegram-bot, hashlib, zipfile, mimetypes
- **Security**: SHA-256 hashing, path validation, MIME type checking
- **Performance**: Chunked upload, progress tracking, memory optimization
- **Compatibility**: Windows, Linux, macOS

## Future Enhancements

Potential improvements for the upload functionality:

1. **Enhanced Security**
   - Virus scanning integration
   - Advanced malware detection
   - File content analysis

2. **Performance Improvements**
   - Parallel upload processing
   - Compression optimization
   - Resume capability for interrupted uploads

3. **User Experience**
   - Drag-and-drop interface
   - Upload history and management
   - File preview capabilities

4. **Advanced Features**
   - Cloud storage integration
   - Automatic file organization
   - Scheduled uploads
