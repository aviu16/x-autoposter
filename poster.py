"""
X API posting module.
Handles authentication, posting tweets, threads, and reply management.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import tweepy

from config import (
    X_API_KEY,
    X_API_SECRET,
    X_ACCESS_TOKEN,
    X_ACCESS_TOKEN_SECRET,
    X_BEARER_TOKEN,
    POST_LOG_FILE,
    INCLUDE_LINKS_IN_REPLY,
)


def get_client():
    """Create authenticated tweepy Client for X API v2."""
    client = tweepy.Client(
        bearer_token=X_BEARER_TOKEN,
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True,
    )
    return client


def post_tweet(text, reply_to_id=None):
    """Post a single tweet. Returns the tweet ID."""
    client = get_client()

    kwargs = {"text": text}
    if reply_to_id:
        kwargs["in_reply_to_tweet_id"] = reply_to_id

    response = client.create_tweet(**kwargs)
    tweet_id = response.data["id"]

    log_post(tweet_id, text, reply_to_id=reply_to_id)
    return tweet_id


def post_thread(tweets):
    """Post a thread of tweets. Returns list of tweet IDs."""
    tweet_ids = []
    reply_to = None

    for i, text in enumerate(tweets):
        tweet_id = post_tweet(text, reply_to_id=reply_to)
        tweet_ids.append(tweet_id)
        reply_to = tweet_id

        if i < len(tweets) - 1:
            time.sleep(2)  # Small delay between thread tweets

    return tweet_ids


def post_with_link_reply(main_text, link_url, link_context=""):
    """
    Post a tweet, then add the link as a reply.
    This avoids the 30-50% reach penalty for links in main tweets.
    """
    main_id = post_tweet(main_text)

    reply_text = link_url
    if link_context:
        reply_text = f"{link_context}\n{link_url}"

    if INCLUDE_LINKS_IN_REPLY and link_url:
        time.sleep(2)
        post_tweet(reply_text, reply_to_id=main_id)

    return main_id


def quote_tweet(text, quote_tweet_id):
    """Post a quote tweet (retweet with comment). Returns the tweet ID."""
    client = get_client()
    response = client.create_tweet(text=text, quote_tweet_id=quote_tweet_id)
    tweet_id = response.data["id"]
    log_post(tweet_id, text, reply_to_id=None)
    print(f"  Quote tweeted: {text[:50]}...")
    return tweet_id


def retweet(tweet_id):
    """Retweet a tweet. Returns True if successful."""
    client = get_client()
    me = client.get_me()
    client.retweet(tweet_id=tweet_id, user_auth=True)
    log_post(tweet_id, f"[RETWEET] {tweet_id}")
    return True


def post_content(content):
    """Post a content item (single tweet, thread, or quote tweet) from the content queue."""
    if content["type"] == "thread":
        tweet_ids = post_thread(content["tweets"])
        print(f"  Posted thread ({len(tweet_ids)} tweets): {content['tweets'][0][:50]}...")
        return tweet_ids[0]
    elif content["type"] == "quote_tweet":
        tweet_id = quote_tweet(content["text"], content["quote_tweet_id"])
        # Add source link as reply to avoid reach penalty
        if content.get("source_link"):
            time.sleep(2)
            post_tweet(f"Source: {content['source_link']}", reply_to_id=tweet_id)
        return tweet_id
    elif content["type"] == "news_share":
        # Post the take, then add link in reply
        tweet_id = post_tweet(content["text"])
        if content.get("source_link"):
            time.sleep(2)
            post_tweet(f"📰 {content['source_link']}", reply_to_id=tweet_id)
        print(f"  Posted news share: {content['text'][:50]}...")
        return tweet_id
    else:
        tweet_id = post_tweet(content["text"])
        print(f"  Posted tweet: {content['text'][:50]}...")
        return tweet_id


def log_post(tweet_id, text, reply_to_id=None):
    """Log posted tweets for tracking."""
    log_file = Path(POST_LOG_FILE)
    logs = []
    if log_file.exists():
        try:
            logs = json.loads(log_file.read_text())
        except json.JSONDecodeError:
            logs = []

    logs.append({
        "tweet_id": str(tweet_id),
        "text": text,
        "reply_to": str(reply_to_id) if reply_to_id else None,
        "posted_at": datetime.now(timezone.utc).isoformat(),
    })

    log_file.write_text(json.dumps(logs, indent=2))


def get_post_count_today():
    """Get number of posts made today."""
    log_file = Path(POST_LOG_FILE)
    if not log_file.exists():
        return 0

    try:
        logs = json.loads(log_file.read_text())
    except json.JSONDecodeError:
        return 0

    today = datetime.now(timezone.utc).date().isoformat()
    return sum(1 for log in logs if log["posted_at"].startswith(today))


def check_credentials():
    """Verify API credentials are working."""
    try:
        client = get_client()
        me = client.get_me()
        if me.data:
            print(f"Authenticated as: @{me.data.username} (ID: {me.data.id})")
            return True
    except Exception as e:
        print(f"Authentication failed: {e}")
    return False


if __name__ == "__main__":
    print("Checking X API credentials...")
    if check_credentials():
        print("Credentials OK!")
    else:
        print("\nPlease set your API credentials in .env or config.py")
        print("Get them from: https://developer.x.com/en/portal/dashboard")
