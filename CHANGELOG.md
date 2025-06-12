# Changelog

All notable changes to PianoNics-Music will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-06-12

### Added
- ✨ **Version Management System**: Added comprehensive version tracking with `version.py`
- 🎨 **Enhanced Version Command**: Detailed version information including Python and Discord.py versions
- 📋 **Versioned Embeds**: All embeds now display the bot version in footer
- 🛡️ **Improved Error Handling**: Enhanced exception handling throughout the codebase
- 💾 **Persistent Database**: Switched from in-memory to persistent SQLite database
- ⏱️ **Song Timeout Protection**: Added 30-minute timeout per song to prevent infinite loops
- 🔧 **Database Error Recovery**: Better database error handling and recovery mechanisms

### Changed
- 🗂️ **Database Storage**: Changed from in-memory (`:memory:`) to persistent file-based database
- 📊 **Error Reporting**: Improved error logging and user feedback
- 🎵 **Player Reliability**: Enhanced audio player with better error recovery
- 🔄 **Queue Management**: More robust queue handling with error recovery

### Fixed
- 🐛 **Bot Stuck Issues**: Fixed cases where bot would get stuck after exceptions
- 🔇 **Voice Channel Disconnection**: Better handling of voice channel disconnections
- 🎶 **Song Skipping**: Fixed issues with song skipping and queue progression
- 📤 **Command Responses**: Improved command response reliability

### Technical Improvements
- 🔄 **Exception Handling**: Added try-catch blocks throughout critical functions
- 🧹 **Cleanup Operations**: Better cleanup of resources on errors
- 📝 **Code Documentation**: Improved code comments and error messages
- 🔍 **Debugging**: Enhanced error logging for better troubleshooting

## [1.1.0] - Previous Version
### Features
- Basic music playback functionality
- Queue management
- Loop and shuffle modes
- Multi-platform support (Spotify, YouTube, SoundCloud, TikTok)

## [1.0.0] - Initial Release
### Features
- Basic Discord music bot functionality
- Simple command system
- Basic audio playback
