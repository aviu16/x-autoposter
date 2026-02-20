# X Autoposter — AI-Powered Twitter/X Automation

Automated content creation and posting system for X (Twitter) using AI for content generation, smart scheduling, and engagement optimization.

## Features

- **AI Content Generation** — uses Groq (Llama 3.3 70B) as primary, Claude as fallback for generating tweets, threads, and replies
- **Algorithm-Aware Scheduling** — posts at optimal times based on X algorithm research for maximum reach
- **Engagement Tracking** — monitors likes, retweets, replies, and impressions; adjusts strategy based on performance
- **Thread Support** — generates multi-tweet threads with proper formatting
- **News Integration** — pulls from RSS feeds to generate timely, relevant content
- **Rate Limiting** — respects X API limits with automatic backoff and retry logic

## Tech Stack

- **Python** — core runtime
- **Groq API** — Llama 3.3 70B for fast, free content generation
- **Anthropic API** — Claude as fallback AI provider
- **X/Twitter API v2** — posting, engagement tracking
- **feedparser** — RSS news ingestion
- **SQLite** — local engagement data storage

## Architecture

```
x-autoposter/
├── run.py                 # Entry point — starts scheduler
├── config.py              # Configuration & env var loading
├── content_generator.py   # AI-powered tweet/thread generation
├── poster.py              # X API integration — posting & media
├── scheduler.py           # Smart scheduling engine
├── engagement.py          # Engagement tracking & analytics
├── requirements.txt       # Python dependencies
└── X_ALGORITHM_DEEP_DIVE.md  # Research on X algorithm optimization
```

## Setup

1. Clone the repo
2. `pip install -r requirements.txt`
3. Create `.env` with your API keys:
   ```
   X_API_KEY=...
   X_API_SECRET=...
   X_ACCESS_TOKEN=...
   X_ACCESS_TOKEN_SECRET=...
   X_BEARER_TOKEN=...
   GROQ_API_KEY=...          # Primary (free)
   ANTHROPIC_API_KEY=...     # Fallback
   ```
4. `python run.py`

## License

MIT
