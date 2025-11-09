__author__ = "@CuriousYoda"
__copyright__ = "Copyright (C) 2025 @CuriousYoda"
__license__ = "MIT"

import asyncio
import configparser
import logging
import os
import sys
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from TikTokApi import TikTokApi
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

# Suppress unnecessary logs
logging.getLogger().setLevel(logging.ERROR)
os.environ["WDM_LOG_LEVEL"] = str(logging.WARNING)

browser = None


def init_browser():
    """Initialize headless Chrome browser for downloads."""
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--log-level=3')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(30)
    return driver


def read_property(property_name, optional=False):
    """Read configuration property from properties file."""
    config = configparser.RawConfigParser()
    with open('tik-tok-scraper.properties', encoding="utf-8") as f:
        config.read_file(f)
    
    value = config.get("UserInput", property_name)
    if not value and not optional:
        print(f"Missing property: {property_name}")
        sys.exit(1)
    return value


def get_folder_path(folder_name):
    """Get or create folder path for downloads."""
    folder_path = f"{read_property('BASE_FOLDER')}/{folder_name}"
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def download_file(url, filepath, progress_callback=None):
    """Download file from URL with optional progress callback."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.tiktok.com/'
        }
        
        response = requests.get(url, stream=True, timeout=30, headers=headers)
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
    except Exception as e:
        return False


def download_via_third_party(username, video_id, folder, progress_callback=None, filename=None):
    """Download TikTok video via third-party downloader site."""
    global browser
    
    video_url = f"https://www.tiktok.com/@{username}/video/{video_id}"
    
    # Use custom filename if provided, otherwise default to video_id
    if filename:
        filepath = f"{get_folder_path(folder)}/{filename}.mp4"
    else:
        filepath = f"{get_folder_path(folder)}/{video_id}.mp4"
    
    if os.path.isfile(filepath):
        return True, "exists"
    
    try:
        if browser is None:
            browser = init_browser()
        
        # Check browser health
        try:
            browser.title
        except:
            browser.quit()
            browser = init_browser()
        
        browser.get("https://snaptik.app/")
        wait = WebDriverWait(browser, 15)
        
        # Close any popups
        try:
            WebDriverWait(browser, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".modal-close, .close, button[aria-label='Close']"))
            )
            for btn in browser.find_elements(By.CSS_SELECTOR, ".modal-close, .close, button[aria-label='Close']"):
                try:
                    if btn.is_displayed():
                        btn.click()
                except:
                    pass
        except:
            pass
        
        # Enter video URL
        url_input = wait.until(EC.presence_of_element_located((By.ID, "url")))
        browser.execute_script("""
            var input = arguments[0];
            input.value = arguments[1];
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
        """, url_input, video_url)
        
        # Submit
        submit_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        browser.execute_script("arguments[0].click();", submit_btn)
        
        # Extract download link
        download_link = None
        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "download-file")))
            
            for link in browser.find_elements(By.CSS_SELECTOR, "a.download-file"):
                href = link.get_attribute("href")
                if href and any(cdn in href for cdn in ['tikcdn.io', 'tiktokcdn.com', 'muscdn.com', 'v16-webapp']):
                    download_link = href
                    break
            
            if not download_link:
                for btn in browser.find_elements(By.XPATH, "//a[contains(@class, 'download') or contains(text(), 'Download')]"):
                    href = btn.get_attribute("href")
                    if href and href.startswith("http") and not href.endswith("#") and "snaptik.app" not in href:
                        download_link = href
                        break
        except Exception as e:
            return False, f"Link error"
        
        if not download_link:
            return False, "No link"
        
        success = download_file(download_link, filepath, progress_callback)
        return success, None
        
    except Exception as e:
        error_msg = str(e)[:20]
        try:
            if browser:
                browser.quit()
            browser = None
        except:
            pass
        return False, error_msg


def get_video_metadata(video):
    """Extract metadata from video object."""
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
                except:
                    pass
        
        # Get video ID
        video_id = str(video.id if hasattr(video, 'id') else 'unknown')
        
        return video_id, views, date_str
    except:
        return 'unknown', 0, 'N/A'


async def download_post(video, folder_name, row_num, total, sort_choice="1"):
    """Extract video info and initiate download with progress display."""
    try:
        video_id = str(video.id if hasattr(video, 'id') else video.get('id', 'unknown'))
        
        author = 'unknown'
        if hasattr(video, 'author'):
            if hasattr(video.author, 'unique_id'):
                author = video.author.unique_id
            elif hasattr(video.author, 'uniqueId'):
                author = video.author.uniqueId
            elif isinstance(video.author, dict):
                author = video.author.get('unique_id') or video.author.get('uniqueId', 'unknown')
        elif isinstance(video, dict) and 'author' in video:
            author_data = video['author']
            author = author_data.get('unique_id') or author_data.get('uniqueId', 'unknown')
        
        # Get metadata
        video_id, views, date = get_video_metadata(video)
        views_str = f"{views:,}" if views > 0 else "N/A"
        
        # Generate filename based on sort option
        # Format: {index:02d}_{metadata}_{video_id}
        index = f"{row_num:02d}"
        
        if sort_choice == "2":  # Most viewed
            # Format: 01_0001234567v_7123456789012345
            metadata = f"{views:010d}v" if views > 0 else "0000000000v"
        elif sort_choice == "3":  # Oldest
            # Format: 01_20240315_7123456789012345
            date_clean = date.replace("-", "") if date != "N/A" else "00000000"
            metadata = date_clean
        else:  # Most recent (default)
            # Format: 01_20240315_7123456789012345
            date_clean = date.replace("-", "") if date != "N/A" else "00000000"
            metadata = date_clean
        
        filename = f"{index}_{metadata}_{video_id}"
        
        # Create progress callback to update the status column
        def update_progress(percent):
            # Create mini progress bar for status column
            bar_width = 10
            filled = int(bar_width * percent / 100)
            bar = '█' * filled + '░' * (bar_width - filled)
            status = f"{bar} {percent}%"
            
            # Update line in place
            sys.stdout.write(f"\r{row_num:<4} {video_id:<20} {views_str:<15} {date:<12} {status:<20}")
            sys.stdout.flush()
        
        # Print initial row
        sys.stdout.write(f"{row_num:<4} {video_id:<20} {views_str:<15} {date:<12} {'Starting...':<20}")
        sys.stdout.flush()
        
        # Download with progress
        success, error = download_via_third_party(author, video_id, folder_name, update_progress, filename)
        
        # Final status
        if success:
            if error == "exists":
                status = "⊘ Exists"
            else:
                status = "✓"
        else:
            status = f"✗ {error}" if error else "✗ Failed"
        
        # Update final line
        sys.stdout.write(f"\r{row_num:<4} {video_id:<20} {views_str:<15} {date:<12} {status:<20}\n")
        sys.stdout.flush()
        
        return success, video_id, views, date
        
    except Exception as e:
        error_msg = str(e)[:15]
        sys.stdout.write(f"\r{row_num:<4} {'unknown':<20} {'N/A':<15} {'N/A':<12} {'✗ ' + error_msg:<20}\n")
        sys.stdout.flush()
        return False, 'unknown', 0, 'N/A'


async def get_user_info(api, username):
    """Fetch and display user information."""
    try:
        user = api.user(username)
        await user.info()
        
        # Extract user stats
        stats = {}
        if hasattr(user, 'as_dict') and user.as_dict:
            user_data = user.as_dict
            
            # Try different possible structures
            if 'userInfo' in user_data:
                stats_data = user_data.get('userInfo', {}).get('stats', {})
            elif 'stats' in user_data:
                stats_data = user_data.get('stats', {})
            else:
                stats_data = {}
            
            # Get stats with fallbacks
            followers = stats_data.get('followerCount', 0)
            following = stats_data.get('followingCount', 0)
            likes = stats_data.get('heartCount', 0) or stats_data.get('heart', 0)
            videos = stats_data.get('videoCount', 0)
            
            # Format numbers
            def format_number(num):
                if num >= 1_000_000:
                    return f"{num/1_000_000:.1f}M"
                elif num >= 1_000:
                    return f"{num/1_000:.1f}K"
                return str(num)
            
            # Display user info
            print(f"\n📊 User Info: @{username}")
            print("─" * 50)
            print(f"  Videos:    {format_number(videos)}")
            print(f"  Followers: {format_number(followers)}")
            print(f"  Following: {format_number(following)}")
            print(f"  Likes:     {format_number(likes)}")
            print("─" * 50)
            
            return True
        else:
            return False
            
    except Exception as e:
        print(f"\n⚠ Could not fetch user info: {str(e)[:50]}")
        return False


async def get_user_posts(api, username, count, sort_choice="1", window_size=None):
    """Fetch and sort user posts from TikTok."""
    try:
        user = api.user(username)
        videos = []
        
        # Determine fetch count based on sorting
        if sort_choice in ["2", "3"]:
            fetch_count = 999999 if window_size is None else window_size
        else:
            fetch_count = count
        
        # Fetch videos
        print(f"📡 Fetching videos", end="", flush=True)
        try:
            async for video in user.videos(count=fetch_count):
                videos.append(video)
                if len(videos) >= fetch_count:
                    break
                if len(videos) % 20 == 0:
                    print(".", end="", flush=True)
        except Exception as fetch_error:
            print(f"\n✗ Fetch error: {str(fetch_error)}")
            if not videos:
                return []
        
        print(f" ✓ ({len(videos)} fetched)")
        
        if not videos:
            return []
        
        # Sort videos
        if sort_choice == "2":  # Most viewed
            def get_view_count(v):
                try:
                    # stats is a dictionary, not an object - convert to int for comparison
                    views = v.stats.get('playCount', 0) if hasattr(v, 'stats') and isinstance(v.stats, dict) else 0
                    return int(views) if views else 0
                except:
                    return 0
            
            videos.sort(key=get_view_count, reverse=True)
            videos = videos[:count]
        elif sort_choice == "3":  # Oldest
            videos = list(reversed(videos))[:count]
        else:  # Most recent
            videos = videos[:count]
        
        return videos
    except Exception as e:
        error_msg = str(e)
        print(f"\n✗ Error fetching @{username}: {error_msg}")
        
        if "user" in error_msg.lower():
            print("   Hint: User might be private, deleted, or username incorrect")
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            print("   Hint: Rate limited - try again later or use VPN")
        
        return []


async def get_hashtag_posts(api, hashtag, count):
    """Fetch posts from a TikTok hashtag."""
    try:
        tag = api.hashtag(name=hashtag)
        videos = []
        async for video in tag.videos(count=count):
            videos.append(video)
            if len(videos) >= count:
                break
        return videos
    except Exception as e:
        print(f"\n✗ Error fetching #{hashtag}: {str(e)}")
        return []


async def main():
    """Main application entry point."""
    print("\n" + "=" * 60)
    print("  TikTok Downloader")
    print("=" * 60)
    
    try:
        async with TikTokApi() as api:
            print("\n⚙ Initializing TikTok API...")
            sys.stdout.write("   Creating session")
            sys.stdout.flush()
            
            await api.create_sessions(
                num_sessions=1,
                sleep_after=5,
                headless=True,
                browser='chromium',
                context_options={
                    'viewport': {'width': 1920, 'height': 1080},
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            sys.stdout.write(" ✓\n")
            sys.stdout.flush()
            print("✓ Ready\n")
            
            while True:
                print("-" * 60)
                choice = input("Download by:\n  [1] Username\n  [2] Hashtag\n  [q] Quit\n\nChoice: ").strip().lower()
                
                if choice in ['q', 'quit', 'exit']:
                    break
                
                if choice == "1":
                    username = input("\n👤 TikTok username (or 'b' to go back): @").strip()
                    
                    if username.lower() in ['b', 'back']:
                        continue
                    
                    if not username:
                        username = "tiktok"
                    
                    # Fetch and display user info
                    print(f"\n🔍 Fetching user info for @{username}...")
                    user_info_success = await get_user_info(api, username)
                    
                    if not user_info_success:
                        retry = input("\nContinue anyway? [y/n]: ").strip().lower()
                        if retry not in ['y', 'yes']:
                            continue
                    
                    sort_choice = input("\nDownload which videos:\n  [1] Most recent (default)\n  [2] Most viewed/popular\n  [3] Oldest\n  [b] Back\n\nChoice: ").strip() or "1"
                    
                    if sort_choice.lower() in ['b', 'back']:
                        continue
                    
                    window_size = None
                    if sort_choice in ["2", "3"]:
                        window_label = "most viewed" if sort_choice == "2" else "oldest"
                        window_input = input(f"\nFetch window for {window_label}:\n  [1] Recent 50 videos (fast)\n  [2] Recent 200 videos (medium)\n  [3] Recent 500 videos (slow)\n  [4] ALL videos (very slow)\n  [b] Back\n\nChoice: ").strip() or "1"
                        
                        if window_input.lower() in ['b', 'back']:
                            continue
                        
                        window_size = {"1": 50, "2": 200, "3": 500, "4": None}.get(window_input, 50)
                    
                    count = input("\n📊 Number of videos to download (default 10, or 'b' to go back): ").strip()
                    
                    if count.lower() in ['b', 'back']:
                        continue
                    
                    count = int(count) if count.isdigit() else 10
                    
                    if sort_choice == "2":
                        msg = f"top {count} most viewed from recent {window_size}" if window_size else f"ALL videos to find top {count} most viewed"
                        print(f"\n🔍 Fetching {msg} of @{username}...")
                    elif sort_choice == "3":
                        msg = f"{count} oldest from recent {window_size}" if window_size else f"ALL videos to find {count} oldest"
                        print(f"\n🔍 Fetching {msg} of @{username}...")
                    else:
                        print(f"\n🔍 Fetching {count} most recent video(s) from @{username}...")
                    
                    videos = await get_user_posts(api, username, count, sort_choice, window_size)
                    
                    if not videos:
                        print("⚠ No videos found or blocked by TikTok")
                        continue
                    
                    print(f"✓ Found {len(videos)} video(s)\n")
                    
                    # Display table header
                    print("📥 Downloading videos...\n")
                    print("─" * 70)
                    print(f"{'#':<4} {'Video ID':<20} {'Views':<15} {'Date':<12} {'Status':<20}")
                    print("─" * 70)
                    
                    success_count = 0
                    
                    for i, video in enumerate(videos, 1):
                        success, video_id, views, date = await download_post(video, username, i, len(videos), sort_choice)
                        if success:
                            success_count += 1
                    
                    print("─" * 70)
                    print(f"\n✓ Completed: {success_count}/{len(videos)} successful downloads")
                
                elif choice == "2":
                    hashtag = input("\n#️⃣  Hashtag (without #, or 'b' to go back): ").strip()
                    
                    if hashtag.lower() in ['b', 'back']:
                        continue
                    
                    if not hashtag:
                        hashtag = "tiktok"
                    
                    count = input("📊 Number of videos (default 10, or 'b' to go back): ").strip()
                    
                    if count.lower() in ['b', 'back']:
                        continue
                    
                    count = int(count) if count.isdigit() else 10
                    
                    print(f"\n🔍 Fetching {count} video(s) for #{hashtag}...")
                    videos = await get_hashtag_posts(api, hashtag, count)
                    
                    if not videos:
                        print("⚠ No videos found or blocked by TikTok")
                        continue
                    
                    print(f"✓ Found {len(videos)} video(s)\n")
                    
                    # Display table header
                    print("📥 Downloading videos...\n")
                    print("─" * 70)
                    print(f"{'#':<4} {'Video ID':<20} {'Views':<15} {'Date':<12} {'Status':<20}")
                    print("─" * 70)
                    
                    success_count = 0
                    
                    for i, video in enumerate(videos, 1):
                        # Hashtag downloads default to most recent sorting (no sort option)
                        success, video_id, views, date = await download_post(video, hashtag, i, len(videos), "1")
                        if success:
                            success_count += 1
                    
                    print("─" * 70)
                    print(f"\n✓ Completed: {success_count}/{len(videos)} successful downloads")
                
                else:
                    print("⚠ Invalid choice. Please enter 1, 2, or q")
    
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nTroubleshooting:")
        print("  • Run: python -m playwright install")
        print("  • Check internet connection")
        print("  • Try using VPN if blocked")
    
    finally:
        if browser:
            browser.quit()
        print("\n" + "=" * 60)
        print("  Goodbye!")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
