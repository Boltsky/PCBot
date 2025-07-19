# PCBot - Telegram Bot with File Management and Security Features

## Overview

PCBot is a secure Telegram bot designed for remote PC management with advanced file operations, system monitoring, and security features. The bot provides secure file hiding/unhiding capabilities, system screenshots, and comprehensive audit logging.

## Project Structure

```
PCBot/
│
├── src/
│   ├── PCBot.py             # Main bot entry point
│   ├── commands.py          # Consolidated command handlers
│   ├── security_manager.py  # Security and authorization
│   ├── utilities.py         # Consolidated utility functions
│   ├── monitor.py           # System monitoring functions
│   └── secure_delete.py     # Secure file deletion
├── docs/
│   └── TESTING_REPORT.md    # Comprehensive testing report
├── backup/
│   └── [archived files]     # Backup of original modular files
├── config.json              # Bot configuration
├── requirements.txt         # Python dependencies
├── run_pcbot.py            # Bot launcher script
└── README.md               # This file
```

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Boltsky/PCBot.git
   cd PCBot
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the Bot**
   - Update `config.json` with your Telegram bot token
   - Add authorized user IDs to the configuration

4. **Run PCBot**
   
   **Quick Deployment (Recommended)**
   
   For Linux/Unix systems:
   ```bash
   ./deploy.sh
   ```
   
   For Windows systems:
   ```batch
   deploy.bat
   ```
   
   **Manual Execution**
   ```bash
   python run_pcbot.py
   ```
   
   Or directly:
   ```bash
   python src/PCBot.py
   ```

## Usage Examples

### File Management Commands

#### Hide Files
```
/hide document.pdf
/hide "file with spaces.txt"
/hide folder_name
```

#### Unhide Files
```
/unhide document.pdf
/unhide "file with spaces.txt"
/unhide folder_name
```

#### List Hidden Files
```
/hidden
```

### System Commands
```
/screenshot    # Capture and send system screenshot
/help         # Display all available commands
```

## Security Features

- **User Authorization**: Only configured users can access PCBot commands
- **Path Validation**: Protection against path traversal attacks
- **Audit Logging**: Comprehensive logging of all operations
- **Secure File Operations**: Safe file hiding/unhiding with validation
- **Input Sanitization**: Protection against malicious input

## Configuration

Update `config.json` with your settings:

```json
{
  "bot_token": "your_telegram_bot_token_here",
  "authorized_users": [
    123456789,
    987654321
  ]
}
```

## Testing

Run the test suite to verify PCBot functionality:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src

# Run specific test category
pytest tests/test_file_operations.py -v
```

## Backup and Recovery

### Creating a Backup
PCBot automatically creates backups during critical operations. You can also manually backup:

1. Stop PCBot
2. Create archive of the project directory
3. Store in the `backups/` directory

### Restoring from Backup

1. **Locate the Backup File**
   - Navigate to the `PCBot/backups/` directory

2. **Extract the Backup**
   - Unzip the backup file to the project root
   - Ensure extraction doesn't overwrite uncommitted changes

3. **Verification**
   - Verify all files are restored correctly
   - Run tests to ensure functionality: `pytest tests/`
   - Start PCBot: `python run_pcbot.py`

## Contributing

When contributing to PCBot:

1. Follow the existing code structure and patterns
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure security best practices are maintained

## Support

For issues or questions about PCBot, please refer to the testing report in `TESTING_REPORT.md` for detailed functionality validation and troubleshooting guidance.
