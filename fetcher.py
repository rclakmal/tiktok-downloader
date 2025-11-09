"""Video fetching and sorting logic with PEP 8 compliance."""
from typing import Optional, List, Any, AsyncIterator


async def fetch_and_sort_videos(
    video_iterator: AsyncIterator[Any],
    count: int,
    sort_choice: str = "1",
    window_size: Optional[int] = None,
    source_name: str = ""
) -> List[Any]:
    """
    Fetch and sort videos from any source (user, trending).

    Reusable function to eliminate code duplication across different
    video sources.

    Args:
        video_iterator: Async iterator yielding video objects.
        count: Number of videos to return after sorting.
        sort_choice: Sorting method - '1' (recent), '2' (most viewed),
            '3' (oldest).
        window_size: Fetch window size for sorting (50, 200, 500, or
            None for ALL).
        source_name: Source identifier for error messages.

    Returns:
        List[Any]: Sorted list of video objects.
    """
    videos = []

    # Determine fetch count based on sorting
    if sort_choice in ["2", "3"]:
        fetch_count = 999999 if window_size is None else window_size
    else:
        fetch_count = count

    # Fetch videos with progress feedback
    print("📡 Fetching videos", end="", flush=True)
    error_msg = None

    try:
        async for video in video_iterator:
            videos.append(video)
            if len(videos) >= fetch_count:
                break
            if len(videos) % 20 == 0:
                print(".", end="", flush=True)
    except Exception as fetch_error:
        error_msg = str(fetch_error)
        print(f"\n✗ Fetch error: {error_msg}")

        # Provide specific hints based on error
        if "user" in error_msg.lower():
            print("   Hint: User might be private, deleted, or "
                  "username incorrect")
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            print("   Hint: Rate limited - try again later or use VPN")
        elif "session" in error_msg.lower():
            print("   Hint: Session expired - restart the application")

        if not videos:
            return []

    print(f" ✓ ({len(videos)} fetched)")

    # Note about potential discrepancy
    if fetch_count > 500 and len(videos) < fetch_count:
        print(f"   Note: TikTok API returned {len(videos)} videos "
              f"(some may be private/deleted/restricted)")

    # Diagnose why 0 videos were fetched
    if not videos:
        if not error_msg:  # No exception, but also no videos
            print("\n⚠ Diagnosis: API returned 0 videos (likely causes):")
            print("   • TikTok is blocking API access to this content")
            print("   • Content is region-restricted (try VPN)")
            print("   • Rate limiting (wait 5-10 minutes or restart)")
        return []

    # Sort videos based on choice
    if sort_choice == "2":  # Most viewed
        def get_view_count(v: Any) -> int:
            """Extract view count from video object."""
            try:
                has_stats = hasattr(v, 'stats')
                is_dict = isinstance(v.stats, dict) if has_stats else False
                views = (v.stats.get('playCount', 0)
                         if has_stats and is_dict else 0)
                return int(views) if views else 0
            except Exception:
                return 0

        videos.sort(key=get_view_count, reverse=True)
        videos = videos[:count]
    elif sort_choice == "3":  # Oldest
        videos = list(reversed(videos))[:count]
    else:  # Most recent
        videos = videos[:count]

    return videos


async def get_user_posts(
    api: Any,
    username: str,
    count: int,
    sort_choice: str = "1",
    window_size: Optional[int] = None
) -> List[Any]:
    """
    Fetch and sort user posts from TikTok.

    Args:
        api: TikTokApi instance.
        username: TikTok username (without @ symbol).
        count: Number of videos to return.
        sort_choice: Sorting method ('1', '2', or '3').
        window_size: Fetch window for sorting operations.

    Returns:
        List[Any]: Sorted list of user video objects.
    """
    try:
        user = api.user(username)

        # Create video iterator
        if sort_choice in ["2", "3"] and window_size is None:
            fetch_count = 999999
        else:
            fetch_count = window_size or count
        video_iterator = user.videos(count=fetch_count)

        # Use shared fetch and sort logic
        return await fetch_and_sort_videos(
            video_iterator, count, sort_choice, window_size, f"@{username}"
        )

    except Exception as e:
        error_msg = str(e)
        print(f"\n✗ Error fetching @{username}: {error_msg}")

        if "user" in error_msg.lower():
            print("   Hint: User might be private, deleted, or "
                  "username incorrect")
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            print("   Hint: Rate limited - try again later or use VPN")

        return []


async def get_trending_posts(api: Any, count: int) -> List[Any]:
    """
    Fetch trending posts from TikTok's For You Page.

    Note: TikTok's trending API only accepts a count parameter.
    Videos are returned in TikTok's algorithmically curated order.
    No client-side sorting is applied.

    Args:
        api: TikTokApi instance.
        count: Number of trending videos to return.

    Returns:
        List[Any]: List of trending video objects in API order.
    """
    try:
        # Create video iterator - trending API only supports count
        video_iterator = api.trending.videos(count=count)

        # Fetch without sorting (trending is pre-sorted by TikTok)
        videos = []
        print("📡 Fetching trending videos", end="", flush=True)

        try:
            async for video in video_iterator:
                videos.append(video)
                if len(videos) >= count:
                    break
                if len(videos) % 20 == 0:
                    print(".", end="", flush=True)
        except Exception as fetch_error:
            error_msg = str(fetch_error)
            print(f"\n✗ Fetch error: {error_msg}")

            if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                print("   Hint: Rate limited - try again later or use VPN")
            elif "session" in error_msg.lower():
                print("   Hint: Session expired - restart the application")

            if not videos:
                return []

        print(f" ✓ ({len(videos)} fetched)")
        return videos

    except Exception as e:
        error_msg = str(e)
        print(f"\n✗ Error fetching trending videos: {error_msg}")

        if "rate" in error_msg.lower() or "limit" in error_msg.lower():
            print("   Hint: Rate limited - try again later or use VPN")
        elif "session" in error_msg.lower():
            print("   Hint: Session expired - restart the application")

        return []


async def get_user_info(api: Any, username: str) -> bool:
    """
    Fetch and display user information.

    Args:
        api: TikTokApi instance.
        username: TikTok username (without @ symbol).

    Returns:
        bool: True if user info was successfully fetched and displayed,
            False otherwise.
    """
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
            likes = (stats_data.get('heartCount', 0) or
                     stats_data.get('heart', 0))
            videos = stats_data.get('videoCount', 0)

            # Format numbers
            def format_number(num: int) -> str:
                """Format number with K/M suffixes."""
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
