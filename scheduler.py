"""
Main scheduler — runs continuously, posting at scheduled times + engagement engine.
Posts aggressively (30+ tweets/day) and engages between posts.
"""
import json
import time
import signal
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import (
    POSTING_SCHEDULE,
    TIMEZONE,
    CONTENT_QUEUE_FILE,
    CONTENT_QUEUE_SIZE,
    REPLY_CHECK_INTERVAL,
    FOLLOW_BACK_CHECK_INTERVAL,
    PROACTIVE_REPLY_INTERVAL,
    NEWS_SHARE_INTERVAL,
    MAX_NEWS_SHARES_PER_DAY,
    TOPIC_ENGAGE_INTERVAL,
)
from content_generator import generate_tweet, fetch_news_headlines, generate_news_take
from poster import post_content, get_post_count_today, check_credentials
from engagement import reply_to_mentions, follow_back_new_followers, proactive_engage, topic_engage, viral_engage


def load_queue():
    """Load the content queue from disk."""
    queue_file = Path(CONTENT_QUEUE_FILE)
    if queue_file.exists():
        try:
            items = json.loads(queue_file.read_text())
            return [item for item in items if not item.get("posted", False)]
        except json.JSONDecodeError:
            pass
    return []


def save_queue(queue):
    """Save the content queue to disk."""
    Path(CONTENT_QUEUE_FILE).write_text(json.dumps(queue, indent=2))


def refill_queue(queue, target_size=None, max_generate=5):
    """Generate content to fill the queue. max_generate limits per call to avoid blocking."""
    if target_size is None:
        target_size = CONTENT_QUEUE_SIZE

    categories_needed = []
    existing_categories = [item["category"] for item in queue if not item.get("posted")]

    all_categories = list(set(cat for _, _, cat in POSTING_SCHEDULE))
    for cat in all_categories:
        count = existing_categories.count(cat)
        if count < 2:
            categories_needed.extend([cat] * (2 - count))

    if not categories_needed:
        return queue

    categories_needed = categories_needed[:max_generate]
    print(f"Generating {len(categories_needed)} new content items...")

    try:
        news = fetch_news_headlines()
    except Exception:
        news = []

    generated = 0
    for category in categories_needed:
        if len(queue) >= target_size:
            break
        try:
            result = generate_tweet(category, news_context=news)
            result["category"] = category
            result["generated_at"] = datetime.now().isoformat()
            result["posted"] = False
            queue.append(result)
            generated += 1
            print(f"  + [{category}] {result.get('text', '(thread)')[:50]}...")
        except Exception as e:
            err = str(e)
            if "rate" in err.lower() or "limit" in err.lower() or "daily" in err.lower():
                print(f"  Rate limit hit, stopping generation for now.")
                break
            print(f"  Error generating {category}: {e}")

    if generated > 0:
        save_queue(queue)
    return queue


def get_next_content(queue, category):
    """Get the next unposted content item for a category."""
    # Try exact category match first
    for item in queue:
        if item["category"] == category and not item.get("posted"):
            return item
    # NO FALLBACK — if we don't have the right category, generate on the fly
    # rather than posting wrong category content
    return None


def mark_posted(queue, item):
    """Mark a content item as posted."""
    item["posted"] = True
    item["posted_at"] = datetime.now().isoformat()
    save_queue(queue)


def should_post_now(hour, minute, tolerance_minutes=7):
    """Check if current time matches a schedule slot (within tolerance)."""
    now = datetime.now(ZoneInfo(TIMEZONE))
    target_minutes = hour * 60 + minute
    current_minutes = now.hour * 60 + now.minute
    diff = current_minutes - target_minutes
    # Only post if we're within tolerance AFTER the scheduled time
    # (not before, to avoid early posting)
    return 0 <= diff <= tolerance_minutes


def run_daemon():
    """Run as a continuous daemon: posting + engagement engine."""
    print("=" * 60)
    print("X AUTOPOSTER - DAEMON MODE")
    print(f"Timezone: {TIMEZONE}")
    print(f"Schedule: {len(POSTING_SCHEDULE)} posts/day")
    print(f"Engagement: auto-reply, follow-back, proactive replies")
    print("=" * 60)

    if not check_credentials():
        print("\nERROR: API credentials not configured. Exiting.")
        sys.exit(1)

    queue = load_queue()
    unposted_count = len([q for q in queue if not q.get("posted")])
    if unposted_count < 5:
        queue = refill_queue(queue, max_generate=5)
    posted_slots = set()

    # Engagement timers
    last_reply_check = 0
    last_follow_check = 0
    last_proactive = 0
    last_news_share = 0
    last_topic_engage = 0
    last_viral_engage = 0
    news_shares_today = 0
    news_cache = []
    news_cache_time = 0

    def handle_signal(sig, frame):
        print("\nShutting down gracefully...")
        save_queue(queue)
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    unposted = [q for q in queue if not q.get("posted")]
    print(f"\nQueue size: {len(unposted)} items")
    print(f"Posts today: {get_post_count_today()}")
    print("\nRunning... (posting + engagement)\n")

    while True:
        now = datetime.now(ZoneInfo(TIMEZONE))
        now_ts = time.time()
        today_key = now.date().isoformat()

        # Reset posted_slots at midnight
        if not any(today_key in s for s in posted_slots):
            posted_slots.clear()

        # ==========================================
        # POSTING: Check ALL schedule slots
        # ==========================================
        for hour, minute, category in POSTING_SCHEDULE:
            slot_key = f"{today_key}-{hour:02d}:{minute:02d}-{category}"

            if slot_key in posted_slots:
                continue

            if should_post_now(hour, minute):
                print(f"\n[{now.strftime('%H:%M')}] Time to post: {category}")

                content = get_next_content(queue, category)
                if not content:
                    # Generate on the fly for this specific category
                    print(f"  No {category} in queue, generating fresh...")
                    try:
                        news = fetch_news_headlines()
                        result = generate_tweet(category, news_context=news)
                        result["category"] = category
                        result["generated_at"] = datetime.now().isoformat()
                        result["posted"] = False
                        queue.append(result)
                        save_queue(queue)
                        content = result
                    except Exception as e:
                        print(f"  Failed to generate {category}: {e}")
                        posted_slots.add(slot_key)  # Skip this slot
                        continue

                if content:
                    try:
                        post_content(content)
                        mark_posted(queue, content)
                        posted_slots.add(slot_key)
                        print(f"  Posted successfully!")
                    except Exception as e:
                        print(f"  Error posting: {e}")
                        posted_slots.add(slot_key)  # Don't retry failed posts

        # ==========================================
        # ENGAGEMENT: Rotate between engagement types
        # Each loop picks ONE engagement action to avoid
        # burning all API budget at once
        # ==========================================
        engagement_actions = []

        if now_ts - last_reply_check >= REPLY_CHECK_INTERVAL:
            engagement_actions.append("mentions")
        if now_ts - last_follow_check >= FOLLOW_BACK_CHECK_INTERVAL:
            engagement_actions.append("follow")
        if now_ts - last_proactive >= PROACTIVE_REPLY_INTERVAL:
            engagement_actions.append("proactive")
        if now_ts - last_topic_engage >= TOPIC_ENGAGE_INTERVAL:
            engagement_actions.append("topic")
        if now_ts - last_viral_engage >= 300:
            engagement_actions.append("viral")

        # Do up to 2 engagement actions per loop (spread the load)
        for action in engagement_actions[:2]:
            try:
                if action == "mentions":
                    replied = reply_to_mentions()
                    if replied:
                        print(f"  [Engagement] Replied to {replied} mentions")
                    last_reply_check = now_ts
                elif action == "follow":
                    followed = follow_back_new_followers()
                    if followed:
                        print(f"  [Engagement] Followed back {followed} users")
                    last_follow_check = now_ts
                elif action == "proactive":
                    proactive = proactive_engage()
                    if proactive:
                        print(f"  [Engagement] Sent {proactive} proactive replies")
                    last_proactive = now_ts
                elif action == "topic":
                    topic_replied = topic_engage()
                    if topic_replied:
                        print(f"  [Topic Engage] Replied to {topic_replied} trending tweets")
                    last_topic_engage = now_ts
                elif action == "viral":
                    viral_replied = viral_engage()
                    if viral_replied:
                        print(f"  [Viral Engage] Replied to {viral_replied} viral tweets")
                    last_viral_engage = now_ts
            except Exception as e:
                print(f"  [{action}] Error: {e}")

        # ==========================================
        # NEWS SHARING: Share breaking news with take
        # ==========================================
        if now_ts - last_news_share >= NEWS_SHARE_INTERVAL and news_shares_today < MAX_NEWS_SHARES_PER_DAY:
            try:
                # Refresh news cache every 30 min
                if now_ts - news_cache_time > 1800 or not news_cache:
                    news_cache = fetch_news_headlines()
                    news_cache_time = now_ts

                if news_cache:
                    import random
                    # Pick a random recent headline
                    headline = random.choice(news_cache[:15])
                    news_content = generate_news_take(headline)
                    if news_content:
                        post_content(news_content)
                        news_shares_today += 1
                        print(f"  [News] Shared: {headline['title'][:50]}...")
            except Exception as e:
                print(f"  [News] Error sharing news: {e}")
            last_news_share = now_ts

        # Reset news_shares_today at midnight
        if now.hour == 0 and now.minute < 1:
            news_shares_today = 0

        # ==========================================
        # QUEUE: Refill if running low (gradual)
        # ==========================================
        unposted = [q for q in queue if not q.get("posted")]
        if len(unposted) < 8:
            print("Queue running low, generating more...")
            queue = refill_queue(queue, max_generate=5)

        # Clean old posted items from queue to keep memory lean
        queue = [q for q in queue if not q.get("posted") or
                 q.get("posted_at", "") > (datetime.now().isoformat()[:10])]

        time.sleep(15)  # Check every 15 seconds — stay aggressive


def post_now(category=None):
    """Post one tweet immediately (for testing or manual triggers)."""
    if not check_credentials():
        print("ERROR: API credentials not configured.")
        return

    queue = load_queue()

    if category:
        content = get_next_content(queue, category)
    else:
        content = next((q for q in queue if not q.get("posted")), None)

    if not content:
        print(f"No content in queue for {category or 'any'}. Generating...")
        news = fetch_news_headlines()
        cat = category or "hot_take"
        content = generate_tweet(cat, news_context=news)
        content["category"] = cat
        content["generated_at"] = datetime.now().isoformat()

    post_content(content)
    if "posted" in content:
        mark_posted(queue, content)
    print("Done!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="X Autoposter Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run as continuous daemon")
    parser.add_argument("--post-now", type=str, nargs="?", const="hot_take",
                        help="Post one tweet now (optional: specify category)")
    parser.add_argument("--fill-queue", action="store_true", help="Fill the content queue")
    parser.add_argument("--show-queue", action="store_true", help="Show queue contents")
    parser.add_argument("--engage", action="store_true", help="Run one engagement cycle")

    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    elif args.post_now:
        post_now(args.post_now)
    elif args.fill_queue:
        queue = load_queue()
        queue = refill_queue(queue, target_size=CONTENT_QUEUE_SIZE)
        print(f"\nQueue now has {len([q for q in queue if not q.get('posted')])} unposted items")
    elif args.show_queue:
        queue = load_queue()
        unposted = [q for q in queue if not q.get("posted")]
        print(f"Queue: {len(unposted)} unposted items\n")
        for i, item in enumerate(unposted[:20]):
            cat = item.get("category", "unknown")
            text = item.get("text", item.get("tweets", [""])[0])[:60]
            print(f"  [{i+1}] ({cat}) {text}...")
    elif args.engage:
        from engagement import run_engagement_cycle
        print("Running engagement cycle...")
        run_engagement_cycle()
    else:
        parser.print_help()
