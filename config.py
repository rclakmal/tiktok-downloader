"""Configuration settings for TikTok downloader with PEP 8 compliance."""
import os
from typing import Optional


def read_property(
    property_name: str,
    default_value: Optional[str] = None
) -> Optional[str]:
    """
    Read a property from tik-tok-scraper.properties file.

    Args:
        property_name: Name of the property to read.
        default_value: Default value if property not found.

    Returns:
        Optional[str]: Property value or default_value if not found.
    """
    try:
        with open('tik-tok-scraper.properties', 'r') as file:
            for line in file:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    if key.strip() == property_name:
                        return value.strip()
    except FileNotFoundError:
        pass
    return default_value


def get_folder_path(folder_name: str) -> str:
    """
    Get the download folder path from properties.

    Creates the folder if it doesn't exist.

    Args:
        folder_name: Name of the subfolder within download path.

    Returns:
        str: Full path to the download folder.
    """
    base_folder = read_property('BASE_FOLDER', 'downloads')
    folder = f"{base_folder}/{folder_name}"
    os.makedirs(folder, exist_ok=True)
    return folder
