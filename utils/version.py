# Bot version information
BOT_VERSION = "1.4.0" 
BOT_NAME = "PianoNics-Music"
BOT_AUTHOR = "PianoNic"
BOT_RELEASE_DATE = "2025-10-19"

def get_version():
    """Get the current bot version"""
    return BOT_VERSION

def get_version_info():
    """Get version info as a dictionary"""
    return {
        "version": BOT_VERSION,
        "name": BOT_NAME,
        "author": BOT_AUTHOR,
        "release_date": BOT_RELEASE_DATE
    }

def get_full_version_info():
    """Get full version information including name and author"""
    return f"{BOT_NAME} v{BOT_VERSION} - Created by {BOT_AUTHOR}"

def get_footer_text():
    """Get formatted footer text for embeds"""
    return f"{BOT_NAME} v{BOT_VERSION} - Created by {BOT_AUTHOR}"
