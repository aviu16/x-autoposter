#!/usr/bin/env python3
"""
X Autoposter - Main entry point.
Quick commands for common operations.

Usage:
    python run.py setup          # First-time setup & credential check
    python run.py generate       # Generate content queue
    python run.py preview        # Preview what would be posted
    python run.py post           # Post one tweet now
    python run.py post bittensor # Post a specific category
    python run.py start          # Start the daemon (runs 24/7)
    python run.py engage         # Run one engagement cycle
    python run.py stats          # Show posting stats
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()


def cmd_setup():
    """Verify setup and credentials."""
    print("=" * 50)
    print("X AUTOPOSTER SETUP CHECK")
    print("=" * 50)

    # Check .env
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        print("\n[!] No .env file found. Copy .env.example to .env and fill in your keys:")
        print("    cp .env.example .env")
        return

    from config import X_API_KEY, GROQ_API_KEY, AI_PROVIDER

    print(f"\n[{'OK' if X_API_KEY else 'MISSING'}] X API Key")
    print(f"[{'OK' if GROQ_API_KEY else 'MISSING'}] Groq API Key")
    print(f"[INFO] AI Provider: {AI_PROVIDER}")

    if X_API_KEY:
        from poster import check_credentials
        print("\nChecking X API connection...")
        check_credentials()

    if GROQ_API_KEY:
        print("\nTesting content generation...")
        from content_generator import generate_tweet
        result = generate_tweet("elon_update")
        print(f"Sample tweet: {result['text']}")

    print("\nSetup complete!")


def cmd_generate():
    """Fill the content queue."""
    from scheduler import load_queue, refill_queue
    from config import CONTENT_QUEUE_SIZE

    print("Generating content queue...")
    queue = load_queue()
    queue = refill_queue(queue, target_size=CONTENT_QUEUE_SIZE)
    unposted = [q for q in queue if not q.get("posted")]
    print(f"\nQueue now has {len(unposted)} unposted items ready to go.")


def cmd_preview():
    """Preview the content queue."""
    from scheduler import load_queue
    from config import POSTING_SCHEDULE

    queue = load_queue()
    unposted = [q for q in queue if not q.get("posted")]

    if not unposted:
        print("Queue is empty. Run: python run.py generate")
        return

    print(f"Content Queue: {len(unposted)} items\n")

    by_category = {}
    for item in unposted:
        cat = item.get("category", "unknown")
        by_category.setdefault(cat, []).append(item)

    for cat, items in sorted(by_category.items()):
        print(f"\n--- {cat.upper()} ({len(items)} queued) ---")
        for item in items[:3]:
            if item.get("type") == "thread":
                print(f"  [THREAD] {item['tweets'][0][:70]}...")
            else:
                print(f"  {item['text'][:70]}...")
        if len(items) > 3:
            print(f"  ... and {len(items) - 3} more")


def cmd_post(category=None):
    """Post one tweet now."""
    from scheduler import post_now
    cat = category or "elon_update"
    print(f"Posting one tweet (category: {cat})...")
    post_now(cat)


def cmd_start():
    """Start the daemon."""
    from scheduler import run_daemon
    run_daemon()


def cmd_engage():
    """Run one engagement cycle."""
    from engagement import run_engagement_cycle
    print("Running engagement cycle...")
    results = run_engagement_cycle()
    print(f"\nResults: {results}")


def cmd_stats():
    """Show posting statistics."""
    from config import POST_LOG_FILE, ENGAGEMENT_LOG_FILE
    log_file = Path(POST_LOG_FILE)

    if not log_file.exists():
        print("No posts yet.")
    else:
        logs = json.loads(log_file.read_text())
        total = len(logs)
        today = datetime.now(timezone.utc).date().isoformat()
        today_count = sum(1 for l in logs if l["posted_at"].startswith(today))
        print(f"Total posts: {total}")
        print(f"Posts today: {today_count}")
        if logs:
            last = logs[-1]
            print(f"Last post: {last['posted_at']}")
            print(f"Last text: {last['text'][:60]}...")

    # Engagement stats
    eng_file = Path(ENGAGEMENT_LOG_FILE)
    if eng_file.exists():
        try:
            eng = json.loads(eng_file.read_text())
            print(f"\n--- Engagement Stats ---")
            print(f"Followed back: {len(eng.get('followed_back', []))} users")
            print(f"Replies sent: {len(eng.get('replies_sent', []))}")
            print(f"Proactive replies: {len(eng.get('proactive_replies', []))}")
        except json.JSONDecodeError:
            pass


COMMANDS = {
    "setup": cmd_setup,
    "generate": cmd_generate,
    "preview": cmd_preview,
    "post": cmd_post,
    "start": cmd_start,
    "engage": cmd_engage,
    "stats": cmd_stats,
}

CATEGORY_SHORTCUTS = {
    "elon": "elon_update",
    "tesla": "tesla_spacex",
    "spacex": "tesla_spacex",
    "bittensor": "bittensor",
    "tao": "bittensor",
    "science": "science_explainer",
    "news": "news_commentary",
    "morning": "morning_news",
    "tech": "tech_update",
    "leaders": "tech_leaders",
    "politics": "global_politics",
    "hot": "hot_take",
    "philosophy": "philosophical",
    "spiritual": "spirituality",
    "question": "thought_question",
    "engage": "engagement_post",
    "thread": "thread",
}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd in COMMANDS:
        if cmd == "post" and len(sys.argv) > 2:
            cat_shortcut = sys.argv[2].lower()
            category = CATEGORY_SHORTCUTS.get(cat_shortcut, cat_shortcut)
            cmd_post(category)
        else:
            COMMANDS[cmd]()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
