# PCRst Bot - Comprehensive File Management 6 System Control

## 🚀 Overview

PCRst is a sophisticated Telegram bot designed for secure file management, system operations, and remote access capabilities. Built with enterprise-grade security features, comprehensive testing, and robust deployment capabilities.

## 📋 Available Commands

- `/start` - Initialize the bot and display a welcome message
- `/help` - Show help message with all available commands
- `/upload <file_path>` - Upload a file to the bot
- `/download <file_url>` - Download a file from a given URL
- `/listfiles <directory_path>` - List all files in a directory
- `/fileinfo <file_path>` - Provides detailed information about a file
- `/compress <directory_path> <output_zip>` - Compress a directory into a zip file
- `/extract <zip_file> <destination_dir>` - Extract files from a zip archive
- `/hardreset` - ⚠️ Wipe all data from the user's home directory (DANGEROUS)
- `/resetsettings` - Reset PC settings (network, personalization, system preferences, user settings)
- `/cleantemp` - Clean temporary files and cache directories

## 🔧 Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Required libraries:**
   - `python-telegram-bot` - Telegram bot framework

3. **Set up your Telegram bot token:**
   - Create a new bot with @BotFather on Telegram
   - Replace the `TOKEN` variable in the code with your bot token

## 📁 File Structure

```
PCRst/
├── PCRst.py              # Main bot application
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## ⚠️ Important Notes

1. **Permissions**: Some system commands require administrator privileges
2. **System Access**: This bot has extensive system access - use carefully

## 🔐 Security Considerations

- **Bot Token**: Keep your Telegram bot token secure and private
- **System Access**: This bot has extensive system access - use carefully

## 🐛 Troubleshooting

### Common Issues:
1. **Permission errors**: Run with appropriate system permissions

### Debug Mode:
Enable debug logging by changing the logging level:
```python
logging.basicConfig(level=logging.DEBUG)
```

## 📊 System Requirements

- **Python**: 3.7 or higher
- **RAM**: Minimum 2GB
- **Network**: Stable internet connection for Telegram API
- **OS**: Windows, Linux, or macOS

## 🤝 Contributing

Feel free to contribute improvements:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is for educational purposes. Use responsibly and ensure compliance with local laws and regulations.
