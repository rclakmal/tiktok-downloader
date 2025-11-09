#!/usr/bin/env python3
"""
TikTok Video Downloader with PEP 8 compliance.

Downloads videos from TikTok by username or trending videos from the
For You Page.
"""
import asyncio
import sys
from typing import NoReturn
from TikTokApi import TikTokApi
from ui import handle_username_download, handle_trending_download
from downloader import cleanup_browser


async def create_tiktok_session(api: TikTokApi) -> None:
    """
    Create TikTok API session with retry logic.

    Args:
        api: TikTokApi instance to initialize.

    Raises:
        Exception: If session creation fails after all retries.
    """
    sys.stdout.write("   Creating session (this may take 30-60 seconds)")
    sys.stdout.flush()

    max_retries = 3
    for attempt in range(max_retries):
        try:
            await api.create_sessions(
                num_sessions=1,
                sleep_after=3,
                headless=True,
                browser='chromium',
                context_options={
                    'viewport': {'width': 1920, 'height': 1080},
                    'user_agent': (
                        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                        'AppleWebKit/537.36'
                    )
                },
                timeout=60000  # 60 second timeout
            )
            sys.stdout.write(" ✓\n")
            sys.stdout.flush()
            break
        except Exception as session_error:
            if attempt < max_retries - 1:
                sys.stdout.write(f"\n   Retry {attempt + 1}/"
                                 f"{max_retries - 1}...")
                sys.stdout.flush()
                await asyncio.sleep(2)
            else:
                raise session_error


async def main() -> None:
    """Main application entry point with error handling."""
    print("\n" + "=" * 60)
    print("  TikTok Downloader")
    print("=" * 60)

    try:
        async with TikTokApi() as api:
            print("\n⚙ Initializing TikTok API...")
            await create_tiktok_session(api)
            print("✓ Ready\n")

            while True:
                print("-" * 60)
                choice = input(
                    "Download by:\n"
                    "  [1] Username\n"
                    "  [2] Trending\n"
                    "  [q] Quit\n\n"
                    "Choice: "
                ).strip().lower()

                if choice in ['q', 'quit', 'exit']:
                    break

                if choice == "1":
                    await handle_username_download(api)

                elif choice == "2":
                    await handle_trending_download(api)

                else:
                    print("⚠ Invalid choice. Please enter 1, 2, or q")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("  • Run: python -m playwright install chromium")
        print("  • Check internet connection (TikTok.com accessible?)")
        print("  • Try using VPN if TikTok is blocked in your region")
        print("  • Firewall may be blocking browser automation")
        print("  • If timeout persists, TikTok may be rate-limiting "
              "your IP")

    finally:
        cleanup_browser()
        print("\n" + "=" * 60)
        print("  Goodbye!")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
