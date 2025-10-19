import subprocess
import logging
import asyncio
from datetime import timedelta
from typing import tuple

logger = logging.getLogger(__name__)

CHECK_INTERVAL = timedelta(hours=24)


async def check_for_updates() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["pip", "list", "--outdated"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            if "yt-dlp" in result.stdout:
                logger.info("yt-dlp update available")
                return True, "yt-dlp update available"
            else:
                logger.info("yt-dlp is up to date")
                return False, "yt-dlp is up to date"
        else:
            logger.warning(f"pip list failed: {result.stderr}")
            return False, "Failed to check pip list"

    except Exception as e:
        logger.error(f"Error checking for updates: {e}")
        return False, f"Error: {e}"


async def install_updates() -> tuple[bool, str]:
    try:
        logger.info("Installing yt-dlp updates...")
        result = subprocess.run(
            ["pip", "install", "--upgrade", "yt-dlp"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            logger.info("yt-dlp successfully updated")
            return True, "yt-dlp successfully updated"
        else:
            logger.error(f"Update installation failed: {result.stderr}")
            return False, f"Update installation failed: {result.stderr}"

    except subprocess.TimeoutExpired:
        logger.error("Update installation timed out")
        return False, "Update installation timed out"
    except Exception as e:
        logger.error(f"Error installing updates: {e}")
        return False, f"Error installing updates: {e}"


async def restart_bot() -> None:
    logger.warning("Restarting bot due to yt-dlp update...")
    logger.info("Exit code: 42 (signals Docker to restart the container)")
    exit(42)


async def scheduled_update_check() -> None:
    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL.total_seconds())

            logger.info("Running scheduled yt-dlp update check...")
            has_updates, message = await check_for_updates()

            if has_updates:
                logger.warning(f"Update available: {message}")
                success, install_msg = await install_updates()

                if success:
                    logger.warning("Update installed. Restarting bot...")
                    await asyncio.sleep(5)
                    await restart_bot()
                else:
                    logger.error(f"Failed to install update: {install_msg}")
            else:
                logger.info(f"No updates available: {message}")

        except asyncio.CancelledError:
            logger.info("Update check task cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in update check: {e}")
            await asyncio.sleep(300)
