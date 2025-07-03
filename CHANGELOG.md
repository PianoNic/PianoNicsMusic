# Changelog

All notable changes to PianoNics-Music will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.3] - 2025-07-03

### Fixed
- 🎯 **YouTube Error Display**: Fixed issue where specific YouTube error messages (age-restricted, private videos, etc.) were being overwritten by generic error messages
- 📺 **Video Error Persistence**: YouTube-specific error messages now stay displayed in Discord instead of being replaced with "An error occurred while playing this song"
- 🛡️ **Error Message Accuracy**: Users now see the actual reason why a video cannot be played (age restrictions, privacy settings, geo-blocking, etc.)

### Technical Improvements
- 🔧 **Exception Handling Order**: Improved exception handling hierarchy in player.py to catch YouTubeError before generic Exception
- 📝 **Error Preservation**: Modified error handling to preserve specific error messages that have already been set
- 🎵 **Player Robustness**: Enhanced audio player error handling without breaking existing functionality

## [1.2.2] - 2025-07-03

### Fixed
- 🔄 **Maintenance Release**: Internal improvements and code cleanup

## [1.2.1] - 2025-07-03

### Fixed
- 🐛 **Voice Connection Error**: Improved error handling for voice channel connection failures
- 🔇 **Bot Responsiveness**: Fixed issues where bot becomes unresponsive after voice connection errors
- 🛡️ **Error Recovery**: Enhanced error recovery mechanisms in play command
- 📤 **User Feedback**: Improved error reporting to users when connection fails

### Technical Improvements
- 🔄 **Exception Handling**: Added better exception handling in voice connection flow
- 🧹 **Resource Cleanup**: Improved cleanup of voice resources on connection failures
- 📝 **Error Logging**: Enhanced error logging for debugging voice connection issues

## [1.2.0] - 2025-06-12

### Added
- ✨ **Version Management System**: Added comprehensive version tracking with `version.py`
- 🎨 **Enhanced Version Command**: Detailed version information including Python and Discord.py versions
- 📋 **Versioned Embeds**: All embeds now display the bot version in footer
- 🛡️ **Improved Error Handling**: Enhanced exception handling throughout the codebase
- 💾 **Persistent Database**: Switched from in-memory to persistent SQLite database
- 🔧 **Database Error Recovery**: Better database error handling and recovery mechanisms

### Changed
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
