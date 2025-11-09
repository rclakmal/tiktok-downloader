"""Video downloading functionality using SnapTik."""
import os
import sys
from typing import Optional, Tuple, Callable, Any
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from config import get_folder_path


# Global browser instance
browser = None


def init_browser() -> webdriver.Chrome:
    """
    Initialize Chrome browser for downloads.

    Returns:
        webdriver.Chrome: Configured Chrome WebDriver instance.
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def download_file(
    url: str,
    filepath: str,
    progress_callback: Optional[Callable[[int], None]] = None
) -> bool:
    """
    Download a file from URL with progress tracking.

    Args:
        url: URL to download from.
        filepath: Destination file path.
        progress_callback: Optional callback for progress updates (0-100).

    Returns:
        bool: True if download succeeded, False otherwise.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://snaptik.app/'
        }
        
        response = requests.get(url, stream=True, timeout=30, headers=headers, allow_redirects=True)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)

                if progress_callback and total_size > 0:
                    progress = int((downloaded / total_size) * 100)
                    progress_callback(progress)

        return True
    except Exception:
        return False


def download_via_snaptik(
    username: str,
    video_id: str,
    folder: str,
    progress_callback: Optional[Callable[[int], None]] = None,
    filename: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Download TikTok video using SnapTik service.

    Args:
        username: TikTok username.
        video_id: TikTok video ID.
        folder: Destination folder name.
        progress_callback: Optional callback for progress updates.
        filename: Optional custom filename (without extension).

    Returns:
        Tuple[bool, Optional[str], Optional[str]]: Success status,
            error code, error detail.
    """
    global browser

    video_url = f"https://www.tiktok.com/@{username}/video/{video_id}"

    if filename:
        filepath = f"{get_folder_path(folder)}/{filename}.mp4"
    else:
        filepath = f"{get_folder_path(folder)}/{video_id}.mp4"

    if os.path.isfile(filepath):
        return True, "exists", None

    try:
        if browser is None:
            browser = init_browser()

        # Check browser health
        try:
            browser.title
        except Exception:
            browser.quit()
            browser = init_browser()

        # Go to SnapTik
        browser.get("https://snaptik.app/")
        wait = WebDriverWait(browser, 15)

        # Enter TikTok URL
        url_input = wait.until(EC.presence_of_element_located((By.NAME, "url")))
        url_input.clear()
        url_input.send_keys(video_url)

        # Click the submit button
        submit_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        submit_button.click()

        # Wait for download button to appear
        download_button = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "download-file"))
        )
        download_link = download_button.get_attribute("href")
        
        if not download_link:
            return False, "No link", f"Could not find download button | {video_url}"
        
        # Download the video
        success = download_file(download_link, filepath, progress_callback)
        
        if not success:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            return False, "DL failed", f"Download failed | {video_url}"
        
        return True, None, None

    except Exception as e:
        error_detail = f"Error: {str(e)[:100]} | {video_url}"
        
        if "chrome" in str(e).lower() or "driver" in str(e).lower():
            try:
                if browser:
                    browser.quit()
                browser = None
            except Exception:
                pass
        
        return False, "Exception", error_detail


def get_video_metadata(video: Any) -> Tuple[str, int, str]:
    """
    Extract metadata from video object.

    Args:
        video: Video object from TikTok API.

    Returns:
        Tuple[str, int, str]: Video ID, view count, creation date.
    """
    try:
        # Get view count
        views = 0
        if hasattr(video, 'stats') and isinstance(video.stats, dict):
            views = int(video.stats.get('playCount', 0) or 0)

        # Get creation date
        date_str = "N/A"
        if hasattr(video, 'create_time'):
            if isinstance(video.create_time, datetime):
                date_str = video.create_time.strftime("%Y-%m-%d")
            else:
                try:
                    date_obj = datetime.fromtimestamp(int(video.create_time))
                    date_str = date_obj.strftime("%Y-%m-%d")
                except Exception:
                    pass

        # Get video ID
        video_id = str(video.id if hasattr(video, 'id') else 'unknown')

        return video_id, views, date_str
    except Exception:
        return 'unknown', 0, 'N/A'


async def download_post(
    video: Any,
    folder_name: str,
    row_num: int,
    sort_choice: str = "1"
) -> Tuple[bool, str, int, str, Optional[str]]:
    """
    Extract video info and initiate download with progress display.

    Args:
        video: Video object from TikTok API.
        folder_name: Destination folder name.
        row_num: Row number for display.
        sort_choice: Sorting method ('1', '2', or '3').

    Returns:
        Tuple[bool, str, int, str, Optional[str]]: Success status,
            video ID, views, date, error detail.
    """
    try:
        video_id = str(
            video.id if hasattr(video, 'id')
            else video.get('id', 'unknown')
        )

        author = 'unknown'
        if hasattr(video, 'author'):
            # Try username first (most common)
            if hasattr(video.author, 'username'):
                author = video.author.username
            elif hasattr(video.author, 'unique_id'):
                author = video.author.unique_id
            elif hasattr(video.author, 'uniqueId'):
                author = video.author.uniqueId
            elif isinstance(video.author, dict):
                author = (video.author.get('username') or
                          video.author.get('unique_id') or
                          video.author.get('uniqueId', 'unknown'))
        elif isinstance(video, dict) and 'author' in video:
            author_data = video['author']
            author = (author_data.get('username') or
                      author_data.get('unique_id') or
                      author_data.get('uniqueId', 'unknown'))

        # Get metadata
        video_id, views, date = get_video_metadata(video)
        views_str = f"{views:,}" if views > 0 else "N/A"

        # Generate filename based on sort option
        index = f"{row_num:02d}"

        if sort_choice == "2":  # Most viewed
            metadata = f"{views:010d}v" if views > 0 else "0000000000v"
        elif sort_choice == "3":  # Oldest
            date_clean = (date.replace("-", "") if date != "N/A" else "00000000")
            metadata = date_clean
        else:  # Most recent (default)
            date_clean = (date.replace("-", "") if date != "N/A" else "00000000")
            metadata = date_clean

        filename = f"{index}_{metadata}_{video_id}"

        # Create progress callback to update the status column
        def update_progress(percent: int) -> None:
            """Update progress bar in terminal."""
            bar_width = 10
            filled = int(bar_width * percent / 100)
            bar = '█' * filled + '░' * (bar_width - filled)
            status = f"{bar} {percent}%"

            sys.stdout.write(
                f"\r{row_num:<4} {video_id:<20} {views_str:<15} "
                f"{date:<12} {status:<20}"
            )
            sys.stdout.flush()

        # Print initial row
        sys.stdout.write(
            f"{row_num:<4} {video_id:<20} {views_str:<15} "
            f"{date:<12} {'Starting...':<20}"
        )
        sys.stdout.flush()

        # Download with progress using SnapTik
        result = download_via_snaptik(
            author, video_id, folder_name, update_progress, filename
        )
        success, error_code, error_detail = result

        # Final status
        if success:
            if error_code == "exists":
                status = "⊘ Exists"
            else:
                status = "✓"
            error_detail = None
        else:
            status = f"✗ {error_code}" if error_code else "✗ Failed"

        # Update final line
        sys.stdout.write(
            f"\r{row_num:<4} {video_id:<20} {views_str:<15} "
            f"{date:<12} {status:<20}\n"
        )
        sys.stdout.flush()

        return success, video_id, views, date, error_detail

    except Exception as e:
        error_msg = str(e)[:15]
        sys.stdout.write(
            f"\r{row_num:<4} {'unknown':<20} {'N/A':<15} "
            f"{'N/A':<12} {'✗ ' + error_msg:<20}\n"
        )
        sys.stdout.flush()
        error_detail = f"Exception during download (video: {row_num}): {str(e)[:100]}"
        return False, 'unknown', 0, 'N/A', error_detail


def cleanup_browser() -> None:
    """Cleanup browser instance."""
    global browser
    if browser:
        try:
            browser.quit()
        except Exception:
            pass
        browser = None
