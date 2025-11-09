"""User interface and interaction logic with PEP 8 compliance."""
from typing import Optional, List, Tuple, Any
from fetcher import get_user_info, get_user_posts, get_trending_posts
from downloader import download_post


def get_sorting_choice() -> Optional[str]:
    """
    Prompt user to select video sorting method.

    Returns:
        Optional[str]: Sorting choice ('1', '2', '3') or None if user
            wants to go back.
    """
    sort_choice = input(
        "\nDownload which videos:\n"
        "  [1] Most recent (default)\n"
        "  [2] Most viewed/popular\n"
        "  [3] Oldest\n"
        "  [b] Back\n\n"
        "Choice: "
    ).strip() or "1"

    if sort_choice.lower() in ['b', 'back']:
        return None

    return sort_choice


def get_fetch_window(sort_choice: str) -> Optional[int]:
    """
    Prompt user to select fetch window size for sorting operations.

    Args:
        sort_choice: The sorting method ('2' for most viewed, '3' for
            oldest).

    Returns:
        Optional[int]: Window size (50, 200, 500, or None for ALL) or
            -1 if user wants to go back.
    """
    if sort_choice not in ["2", "3"]:
        return None

    window_label = "most viewed" if sort_choice == "2" else "oldest"
    window_input = input(
        f"\nFetch window for {window_label}:\n"
        "  [1] Recent 50 videos (fast)\n"
        "  [2] Recent 200 videos (medium)\n"
        "  [3] Recent 500 videos (slow)\n"
        "  [4] ALL videos (very slow)\n"
        "  [b] Back\n\n"
        "Choice: "
    ).strip() or "1"

    if window_input.lower() in ['b', 'back']:
        return -1

    return {"1": 50, "2": 200, "3": 500, "4": None}.get(window_input, 50)


def get_download_count() -> Optional[int]:
    """
    Prompt user to specify number of videos to download.

    Returns:
        Optional[int]: Number of videos to download or None if user
            wants to go back.
    """
    count_input = input(
        "\n📊 Number of videos to download "
        "(default 10, or 'b' to go back): "
    ).strip()

    if count_input.lower() in ['b', 'back']:
        return None

    return int(count_input) if count_input.isdigit() else 10


def print_fetch_status(
    count: int,
    sort_choice: str,
    window_size: Optional[int],
    source_name: str
) -> None:
    """
    Display fetch status message based on sorting parameters.

    Args:
        count: Number of videos to download.
        sort_choice: Sorting method ('1', '2', or '3').
        window_size: Fetch window size (50, 200, 500, None for ALL).
        source_name: Source identifier (username or "trending").
    """
    prefix = f"of @{source_name}" if source_name != "trending" else ""

    if sort_choice == "2":
        window_msg = (
            f"recent {window_size}"
            if window_size
            else "ALL video metadata"
        )
        msg = f"top {count} most viewed from {window_msg}"
        print(f"\n🔍 Fetching {msg} {prefix}...")
    elif sort_choice == "3":
        window_msg = (
            f"recent {window_size}"
            if window_size
            else "ALL video metadata"
        )
        msg = f"{count} oldest from {window_msg}"
        print(f"\n🔍 Fetching {msg} {prefix}...")
    else:
        video_label = "video(s)" if source_name != "trending" else \
            "trending video(s)"
        print(f"\n🔍 Fetching {count} most recent {video_label} {prefix}...")


async def handle_username_download(api: Any) -> None:
    """
    Handle username-based video downloads with sorting options.

    Args:
        api: TikTokApi instance for fetching videos.
    """
    username = input(
        "\n👤 TikTok username (or 'b' to go back): @"
    ).strip()

    if username.lower() in ['b', 'back']:
        return

    if not username:
        username = "tiktok"

    # Fetch and display user info
    print(f"\n🔍 Fetching user info for @{username}...")
    user_info_success = await get_user_info(api, username)

    if not user_info_success:
        retry = input("\nContinue anyway? [y/n]: ").strip().lower()
        if retry not in ['y', 'yes']:
            return

    # Get sorting choice
    sort_choice = get_sorting_choice()
    if sort_choice is None:
        return

    # Get fetch window if needed
    window_size = get_fetch_window(sort_choice)
    if window_size == -1:
        return

    # Get download count
    count = get_download_count()
    if count is None:
        return

    # Display fetch status
    print_fetch_status(count, sort_choice, window_size, username)

    # Fetch videos
    videos = await get_user_posts(
        api, username, count, sort_choice, window_size
    )

    if not videos:
        print("⚠ No videos found or blocked by TikTok")
        return

    print(f"✓ Found {len(videos)} video(s)\n")
    await download_videos(videos, username, sort_choice)


async def handle_trending_download(api: Any) -> None:
    """
    Handle trending video downloads.

    Note: TikTok's trending API returns algorithmically curated videos
    from the For You Page. No sorting options are applied as trending
    videos are already pre-sorted by TikTok's algorithm.

    Args:
        api: TikTokApi instance for fetching videos.
    """
    count = get_download_count()
    if count is None:
        return

    print(f"\n🔍 Fetching {count} trending videos from For You Page...")

    videos = await get_trending_posts(api, count)

    if not videos:
        print("⚠ No videos found or blocked by TikTok")
        return

    print(f"✓ Found {len(videos)} video(s)\n")
    await download_videos(videos, "trending", "1")


async def download_videos(
    videos: List[Any],
    folder_name: str,
    sort_choice: str
) -> None:
    """
    Download a list of videos and display results with failure summary.

    Args:
        videos: List of video objects to download.
        folder_name: Destination folder name for downloads.
        sort_choice: Sorting method used ('1', '2', or '3').
    """
    # Display table header
    print("📥 Downloading videos...\n")
    print("─" * 70)
    print(f"{'#':<4} {'Video ID':<20} {'Views':<15} "
          f"{'Date':<12} {'Status':<20}")
    print("─" * 70)

    success_count = 0
    failures = []  # Collect failure details

    for i, video in enumerate(videos, 1):
        result = await download_post(video, folder_name, i, sort_choice)
        success, video_id, views, date, error_detail = result

        if success:
            success_count += 1
        elif error_detail:
            failures.append(error_detail)

    print("─" * 70)
    print(f"\n✓ Completed: {success_count}/{len(videos)} "
          f"successful downloads")

    # Display failure summary if any failures occurred
    if failures:
        print("\n⚠ Download Failures Summary:")
        print("─" * 70)
        for detail in failures:
            print(f"  • {detail}")
        print("─" * 70)
