# TikTok Downloader

Modern Python-based TikTok video downloader with support for username and hashtag downloads.

**Credits**: Uses [TikTokApi](https://github.com/davidteather/TikTok-Api) for metadata fetching and [SnapTik](https://snaptik.app) for video downloads.

## Features

- Download videos by username or hashtag
- Sort by most recent, most viewed, or oldest
- Configurable fetch windows for performance vs accuracy
- Headless browser automation
- Progress tracking

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install
```

## Configuration

Edit `tik-tok-scraper.properties`:

```ini
[UserInput]
BASE_FOLDER = ../../Downloads/tiktok
```

## Usage

```bash
python tik-tok-scraper.py
```

Follow the interactive prompts to:
1. Choose download by username or hashtag
2. Select sorting option (recent/viewed/oldest)
3. Set fetch window size (for sorted downloads)
4. Specify number of videos

Videos are saved to `BASE_FOLDER/{username}` or `BASE_FOLDER/{hashtag}`.

## Requirements

- Python 3.10+
- Chrome/Chromium browser
- Active internet connection

## Troubleshooting

- **Rate limited**: Wait a few minutes or use a VPN
- **Private accounts**: Cannot download from private accounts
- **No videos found**: Verify username/hashtag spelling

## License

MIT License - See LICENSE file for details
