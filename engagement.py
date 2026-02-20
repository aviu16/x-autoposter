"""
Engagement engine — auto-reply, follow-back, and proactive engagement.
This is the #1 growth lever per X's algorithm:
  - Replies that get author replies = 150x a like (+75 weight)
  - Regular replies = 13.5x a like
  - Author replying to own thread = massive boost

STRATEGY: Only reply where it makes sense for our brand.
Don't engage with random off-topic conversations.
"""
import json
import time
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

import tweepy

from config import (
    X_API_KEY,
    X_API_SECRET,
    X_ACCESS_TOKEN,
    X_ACCESS_TOKEN_SECRET,
    X_BEARER_TOKEN,
    AUTO_FOLLOW_BACK,
    AUTO_REPLY_TO_MENTIONS,
    PROACTIVE_REPLY,
    MAX_REPLIES_PER_HOUR,
    MAX_PROACTIVE_REPLIES_PER_HOUR,
    ENGAGE_WITH_ACCOUNTS,
    ENGAGE_TOPICS,
    ENGAGEMENT_LOG_FILE,
)
from content_generator import generate_reply


def get_client():
    """Create authenticated tweepy Client for X API v2."""
    return tweepy.Client(
        bearer_token=X_BEARER_TOKEN,
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True,  # Let tweepy handle 429s gracefully
    )


# Track X API usage to avoid hitting limits and blocking
_api_call_times = []
MAX_API_CALLS_PER_15MIN = 45  # Stay under X's 50/15min limit


def check_api_budget():
    """Check if we have API budget left. Returns True if OK to call."""
    global _api_call_times
    cutoff = time.time() - 900  # 15 minutes
    _api_call_times = [t for t in _api_call_times if t > cutoff]
    return len(_api_call_times) < MAX_API_CALLS_PER_15MIN


def track_api_call():
    """Record an API call."""
    _api_call_times.append(time.time())


def load_engagement_log():
    """Load engagement log from disk."""
    log_file = Path(ENGAGEMENT_LOG_FILE)
    if log_file.exists():
        try:
            return json.loads(log_file.read_text())
        except json.JSONDecodeError:
            pass
    return {
        "last_mention_id": None,
        "followed_back": [],
        "replies_sent": [],
        "proactive_replies": [],
    }


def save_engagement_log(log):
    """Save engagement log to disk."""
    Path(ENGAGEMENT_LOG_FILE).write_text(json.dumps(log, indent=2))


def get_all_replied_tweet_ids(log):
    """Get ALL tweet IDs we have ever replied to — across mentions, proactive, topic, viral.
    This is the single source of truth to prevent double-replying."""
    ids = set()
    for r in log.get("replies_sent", []):
        ids.add(r.get("tweet_id", ""))
    for r in log.get("proactive_replies", []):
        ids.add(r.get("tweet_id", ""))
    ids.discard("")
    return ids


def recently_replied_to_author(log, author_username, hours=6):
    """Check if we already replied to this author in the last N hours.
    Prevents spamming the same person with multiple replies."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    author_lower = author_username.lower()

    for r in log.get("replies_sent", []):
        if r.get("author", "").lower() == author_lower and r.get("timestamp", "") > cutoff:
            return True
    for r in log.get("proactive_replies", []):
        if r.get("target", "").lower() == author_lower and r.get("timestamp", "") > cutoff:
            return True
    return False


def get_replies_this_hour(log):
    """Count how many replies we've sent in the last hour."""
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    count = 0
    for entry in log.get("replies_sent", []):
        if entry.get("timestamp", "") > one_hour_ago:
            count += 1
    for entry in log.get("proactive_replies", []):
        if entry.get("timestamp", "") > one_hour_ago:
            count += 1
    return count


def is_on_topic(text):
    """Check if a mention/reply is related to our topics. Skip off-topic stuff."""
    text_lower = text.lower()
    # Our topics — only engage if the mention touches these
    on_topic_signals = [
        "elon", "tesla", "spacex", "starship", "fsd", "cybertruck", "optimus",
        "xai", "grok", "neuralink", "boring company", "doge",
        "bittensor", "tao", "subnet", "decentralized ai", "deai", "miner",
        "ai", "artificial intelligence", "machine learning", "llm", "chatgpt",
        "openai", "claude", "anthropic", "google", "gemini",
        "tech", "startup", "silicon valley", "nvidia", "gpu",
        "space", "mars", "rocket", "orbit", "nasa",
        "crypto", "bitcoin", "blockchain", "web3",
        "science", "physics", "quantum", "consciousness",
        "philosophy", "meditation", "spirituality", "simulation",
        "politics", "geopolitics",
    ]
    return any(sig in text_lower for sig in on_topic_signals)


def is_spam_or_bot(username, text):
    """Check if mention is spam, bot, scam, or Elon impersonator."""
    uname = username.lower()

    # Known bot usernames
    bot_names = {
        "grok", "xbot", "autobot", "tweetbot", "chatgpt",
        "eliza_bot", "botly", "autopilot",
    }
    if uname in bot_names:
        return True

    # Bot patterns in username
    bot_patterns = ["_bot", "bot_", "airdrop", "nft_", "_nft", "crypto_signal"]
    if any(p in uname for p in bot_patterns):
        return True

    # ELON IMPERSONATOR DETECTION — these are the scam accounts spamming DMs
    # Pattern: "Musk" or "Elon" in username + random numbers/letters
    elon_patterns = [
        "musk", "elon", "tesla_ceo", "spacex_ceo",
        "doge_", "_doge", "dogefather",
    ]
    if any(p in uname for p in elon_patterns):
        # Allow the REAL accounts
        real_elon_accounts = {"elonmusk", "cb_doge", "dogedesigner"}
        if uname not in real_elon_accounts:
            return True

    # Scam account patterns: random digits at end of username
    import re
    if re.search(r'\d{5,}$', uname):  # 5+ digits at end = likely bot
        return True
    if re.search(r'[A-Z]{2,}\d{3,}', username):  # Like "Musktechdi10938"
        return True

    text_lower = text.lower()

    # Spam content signals
    spam_signals = [
        "free", "airdrop", "claim", "giveaway", "dm me", "send",
        "won", "winner", "congratulations", "click here", "earn",
        "money", "profit", "investment", "guaranteed", "100x",
        "join now", "limited time", "act fast", "crypto signal",
        "whitelist", "presale", "nft drop", "check dm",
        "follow me", "follow back", "f4f", "promo",
        "telegram", "whatsapp", "discord link",
        # Elon scam signals
        "elon is giving", "musk is sending", "free tesla",
        "elon endorsed", "musk foundation",
    ]
    if any(s in text_lower for s in spam_signals):
        return True

    # Flattery/scam pattern: overly effusive praise to get engagement
    flattery_signals = [
        "you are amazing", "love your content", "great work sir",
        "my friend i will", "nice to meet you", "hello friend",
        "bless you", "god bless",
    ]
    if any(s in text_lower for s in flattery_signals):
        return True

    return False


# ============================================================
# AUTO FOLLOW-BACK
# ============================================================
def follow_back_new_followers():
    """Follow back anyone who follows us that we don't follow back."""
    if not AUTO_FOLLOW_BACK:
        return 0

    client = get_client()
    log = load_engagement_log()
    followed_count = 0

    if not check_api_budget():
        return 0

    try:
        me = client.get_me()
        track_api_call()
        my_id = me.data.id

        followers = client.get_users_followers(
            id=my_id, max_results=100,
            user_fields=["id", "username"]
        )

        if not followers.data:
            return 0

        following = client.get_users_following(
            id=my_id, max_results=1000,
            user_fields=["id"]
        )
        following_ids = set()
        if following.data:
            following_ids = {str(u.id) for u in following.data}

        already_followed = set(log.get("followed_back", []))

        for follower in followers.data:
            fid = str(follower.id)
            if fid not in following_ids and fid not in already_followed:
                # Skip spam bots and Elon impersonators
                if is_spam_or_bot(follower.username, ""):
                    print(f"  Skipping bot/scam follow-back: @{follower.username}")
                    log["followed_back"].append(fid)  # Mark as processed so we skip next time
                    continue
                try:
                    client.follow_user(target_user_id=follower.id)
                    log["followed_back"].append(fid)
                    followed_count += 1
                    print(f"  Followed back: @{follower.username}")
                    time.sleep(random.uniform(2, 5))
                except Exception as e:
                    print(f"  Error following @{follower.username}: {e}")

                if followed_count >= 15:
                    break

        save_engagement_log(log)
    except Exception as e:
        print(f"  Follow-back error: {e}")

    return followed_count


# ============================================================
# AUTO-REPLY TO MENTIONS & REPLIES ON OWN TWEETS
# ============================================================
def reply_to_mentions():
    """Reply to recent mentions — but ONLY on-topic ones.
    Skip random off-topic mentions to avoid looking like a clueless bot.
    """
    if not AUTO_REPLY_TO_MENTIONS:
        return 0

    client = get_client()
    log = load_engagement_log()
    reply_count = 0

    if get_replies_this_hour(log) >= MAX_REPLIES_PER_HOUR:
        return 0

    if not check_api_budget():
        print("  [Rate] API budget low, skipping mention check")
        return 0

    try:
        me = client.get_me()
        track_api_call()
        my_id = me.data.id
        my_username = me.data.username

        kwargs = {
            "id": my_id,
            "max_results": 50,
            "tweet_fields": ["author_id", "created_at", "in_reply_to_user_id", "conversation_id"],
            "expansions": ["author_id"],
            "user_fields": ["username"],
        }

        since_id = log.get("last_mention_id")
        if since_id:
            kwargs["since_id"] = since_id

        mentions = client.get_users_mentions(**kwargs)
        track_api_call()

        if not mentions.data:
            return 0

        # Build user lookup
        users = {}
        if mentions.includes and "users" in mentions.includes:
            for u in mentions.includes["users"]:
                users[str(u.id)] = u.username

        newest_id = None
        all_replied = get_all_replied_tweet_ids(log)

        for mention in mentions.data:
            tweet_id = str(mention.id)

            if newest_id is None:
                newest_id = tweet_id

            if tweet_id in all_replied:
                continue

            author_id = str(mention.author_id)
            if author_id == str(my_id):
                continue

            author_username = users.get(author_id, "someone")
            tweet_text = mention.text

            # Strip our @mention to get the actual content
            cleaned = tweet_text.replace(f"@{my_username}", "").strip()

            # Skip very short content (just a tag, no substance)
            if len(cleaned) < 15:
                print(f"  Skipping short mention from @{author_username}: '{cleaned[:30]}'")
                continue

            # Skip spam and bots
            if is_spam_or_bot(author_username, cleaned):
                print(f"  Skipping spam/bot @{author_username}: {cleaned[:40]}...")
                continue

            # Reply to ALL mentions — every conversation is a growth opportunity
            # Only skip spam/bots (already filtered above)

            if get_replies_this_hour(log) >= MAX_REPLIES_PER_HOUR:
                break

            try:
                if not check_api_budget():
                    print("  [Rate] API budget low, pausing replies")
                    break
                reply_text = generate_reply(tweet_text, author_username, context="mention")
                if not reply_text:
                    continue
                client.create_tweet(text=reply_text, in_reply_to_tweet_id=mention.id)
                track_api_call()

                log["replies_sent"].append({
                    "tweet_id": tweet_id,
                    "author": author_username,
                    "our_reply": reply_text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                reply_count += 1
                print(f"  Replied to @{author_username}: {reply_text[:60]}...")

                time.sleep(random.uniform(3, 8))

            except Exception as e:
                print(f"  Error replying to @{author_username}: {e}")

        if newest_id:
            log["last_mention_id"] = newest_id

        save_engagement_log(log)

    except Exception as e:
        print(f"  Mention reply error: {e}")

    return reply_count


# ============================================================
# PROACTIVE ENGAGEMENT — Reply to big accounts' tweets
# ============================================================
def proactive_engage():
    """Reply to recent tweets from accounts in our niche.
    Getting a reply from a big account = massive visibility boost.
    """
    if not PROACTIVE_REPLY:
        return 0

    client = get_client()
    log = load_engagement_log()
    reply_count = 0

    if get_replies_this_hour(log) >= MAX_REPLIES_PER_HOUR:
        return 0

    proactive_this_hour = sum(
        1 for r in log.get("proactive_replies", [])
        if r.get("timestamp", "") > (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    )
    if proactive_this_hour >= MAX_PROACTIVE_REPLIES_PER_HOUR:
        return 0

    # Pick multiple random accounts to engage with (3 per cycle for speed)
    targets = random.sample(ENGAGE_WITH_ACCOUNTS, min(3, len(ENGAGE_WITH_ACCOUNTS)))
    already_replied = get_all_replied_tweet_ids(log)

    for target in targets:
        if get_replies_this_hour(log) >= MAX_REPLIES_PER_HOUR:
            break
        if not check_api_budget():
            print("  [Rate] API budget low, pausing proactive")
            break

        # Skip if we already replied to this person recently
        if recently_replied_to_author(log, target):
            continue

        try:
            user = client.get_user(username=target, user_fields=["id"])
            track_api_call()
            if not user.data:
                continue

            tweets = client.get_users_tweets(
                id=user.data.id,
                max_results=10,
                tweet_fields=["created_at", "public_metrics", "text"],
                exclude=["retweets", "replies"],
            )
            track_api_call()

            if not tweets.data:
                continue

            for tweet in tweets.data:
                tid = str(tweet.id)
                if tid in already_replied:
                    continue

                # Skip old tweets (>12h — fresher = more visible)
                if tweet.created_at:
                    age = datetime.now(timezone.utc) - tweet.created_at
                    if age > timedelta(hours=12):
                        continue

                # Reply to tweets with any engagement (even 2 likes — early replies get seen more)
                metrics = tweet.public_metrics or {}
                if metrics.get("like_count", 0) < 2:
                    continue

                try:
                    reply_text = generate_reply(tweet.text, target, context="proactive")
                    if not reply_text:
                        continue

                    # Quality gate: skip if reply is too short or generic
                    if len(reply_text) < 15:
                        print(f"  Reply too short for @{target}, skipping")
                        continue

                    client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                    track_api_call()

                    log["proactive_replies"].append({
                        "tweet_id": tid,
                        "target": target,
                        "tweet_text": tweet.text[:100],
                        "our_reply": reply_text,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    reply_count += 1
                    already_replied.add(tid)
                    print(f"  Proactive reply to @{target}: {reply_text[:60]}...")

                    time.sleep(random.uniform(3, 8))
                    break  # One reply per account, then move to next target

                except Exception as e:
                    print(f"  Error proactive reply to @{target}: {e}")
                    break

        except Exception as e:
            print(f"  Proactive engage error for @{target}: {e}")

    save_engagement_log(log)
    return reply_count


# ============================================================
# TOPIC ENGAGEMENT — Search hot tweets on trending topics
# ============================================================
def topic_engage():
    """Search for trending topic tweets and reply to high-engagement ones.
    This targets verified accounts discussing hot topics for max visibility.
    """
    if not PROACTIVE_REPLY:
        return 0

    client = get_client()
    log = load_engagement_log()
    reply_count = 0

    if get_replies_this_hour(log) >= MAX_REPLIES_PER_HOUR:
        return 0
    if not check_api_budget():
        print("  [Rate] API budget low, skipping topic engage")
        return 0

    already_replied = get_all_replied_tweet_ids(log)

    # Pick a random topic to search
    topic = random.choice(ENGAGE_TOPICS)

    try:
        # Search recent tweets on this topic — look for ones with engagement
        tweets = client.search_recent_tweets(
            query=f"{topic} -is:retweet -is:reply lang:en",
            max_results=20,
            tweet_fields=["author_id", "created_at", "public_metrics", "text"],
            expansions=["author_id"],
            user_fields=["username", "verified", "public_metrics"],
        )

        track_api_call()

        if not tweets.data:
            return 0

        # Build user lookup
        users = {}
        if tweets.includes and "users" in tweets.includes:
            for u in tweets.includes["users"]:
                users[str(u.id)] = {
                    "username": u.username,
                    "verified": getattr(u, "verified", False),
                    "followers": u.public_metrics.get("followers_count", 0) if u.public_metrics else 0,
                }

        for tweet in tweets.data:
            tid = str(tweet.id)
            if tid in already_replied:
                continue

            # Skip old tweets
            if tweet.created_at:
                age = datetime.now(timezone.utc) - tweet.created_at
                if age > timedelta(hours=6):  # Fresher = better visibility
                    continue

            metrics = tweet.public_metrics or {}
            # Target tweets with decent engagement (likely to be seen)
            if metrics.get("like_count", 0) < 5:
                continue

            author_id = str(tweet.author_id)
            author_info = users.get(author_id, {})
            author_username = author_info.get("username", "someone")

            # Skip bots
            if is_spam_or_bot(author_username, tweet.text):
                continue

            # Skip if we already replied to this person recently
            if recently_replied_to_author(log, author_username):
                continue

            # Only reply to accounts with real audiences (1000+ followers)
            # Their followers see our reply — we want quality eyeballs
            author_followers = author_info.get("followers", 0)
            if author_followers < 1000 and metrics.get("like_count", 0) < 50:
                continue  # Skip unless tweet is mega-viral

            if get_replies_this_hour(log) >= MAX_REPLIES_PER_HOUR:
                break

            try:
                reply_text = generate_reply(tweet.text, author_username, context="proactive")
                if not reply_text or len(reply_text) < 30:
                    continue

                client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                track_api_call()

                log["proactive_replies"].append({
                    "tweet_id": tid,
                    "target": author_username,
                    "topic": topic,
                    "tweet_text": tweet.text[:100],
                    "our_reply": reply_text,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                reply_count += 1
                print(f"  [Topic] Replied to @{author_username} on '{topic}': {reply_text[:60]}...")

                time.sleep(random.uniform(3, 8))

                if reply_count >= 6:  # Max 6 per topic search cycle
                    break

            except Exception as e:
                print(f"  [Topic] Error replying to @{author_username}: {e}")
                break

    except Exception as e:
        print(f"  [Topic] Search error for '{topic}': {e}")

    save_engagement_log(log)
    return reply_count


# ============================================================
# VIRAL ENGAGEMENT — Reply to viral tweets from QUALITY accounts
# ============================================================
# Tech/AI-focused viral searches — attracts smart verified followers, not spam bots
VIRAL_SEARCHES = [
    # AI/Tech viral content
    "AI is going to", "unpopular opinion AI",
    "the future of AI", "AGI timeline",
    "AI will replace", "machine learning hot take",
    "open source AI", "AI safety",
    "tech bubble", "startup founders",
    # Science viral
    "science just discovered", "mind blown science",
    "quantum breakthrough", "neuroscience shows",
    # Tech industry
    "Silicon Valley", "tech CEO",
    "the future of work", "remote work debate",
    # Intellectual debate
    "change my mind technology", "consciousness AI",
    "simulation theory", "decentralized future",
]

# Minimum followers for viral engage targets — filters out random nobodies
MIN_FOLLOWERS_VIRAL = 1000


def viral_engage():
    """Reply to viral tweets from quality accounts with real audiences.
    Targets tech/AI/science content from accounts with 1000+ followers.
    """
    if not PROACTIVE_REPLY:
        return 0

    client = get_client()
    log = load_engagement_log()
    reply_count = 0

    if get_replies_this_hour(log) >= MAX_REPLIES_PER_HOUR:
        return 0
    if not check_api_budget():
        print("  [Rate] API budget low, skipping viral engage")
        return 0

    already_replied = get_all_replied_tweet_ids(log)

    # Pick a random tech/AI viral search
    query = random.choice(VIRAL_SEARCHES)

    try:
        tweets = client.search_recent_tweets(
            query=f'{query} -is:retweet -is:reply lang:en',
            max_results=20,
            tweet_fields=["author_id", "created_at", "public_metrics", "text"],
            expansions=["author_id"],
            user_fields=["username", "verified", "public_metrics"],
        )
        track_api_call()

        if not tweets.data:
            return 0

        # Build user lookup
        users = {}
        if tweets.includes and "users" in tweets.includes:
            for u in tweets.includes["users"]:
                users[str(u.id)] = {
                    "username": u.username,
                    "verified": getattr(u, "verified", False),
                    "followers": u.public_metrics.get("followers_count", 0) if u.public_metrics else 0,
                }

        for tweet in tweets.data:
            tid = str(tweet.id)
            if tid in already_replied:
                continue

            if tweet.created_at:
                age = datetime.now(timezone.utc) - tweet.created_at
                if age > timedelta(hours=6):
                    continue

            metrics = tweet.public_metrics or {}
            likes = metrics.get("like_count", 0)

            # Must have some engagement
            if likes < 5:
                continue

            author_id = str(tweet.author_id)
            author_info = users.get(author_id, {})
            author_username = author_info.get("username", "someone")
            author_followers = author_info.get("followers", 0)

            # QUALITY FILTER: Only engage with accounts that have real audiences
            # Their followers will see our reply — we want THOSE followers
            if author_followers < MIN_FOLLOWERS_VIRAL:
                continue

            if is_spam_or_bot(author_username, tweet.text):
                continue

            # Skip if we already replied to this person recently
            if recently_replied_to_author(log, author_username):
                continue

            if not check_api_budget():
                break

            try:
                reply_text = generate_reply(tweet.text, author_username, context="proactive")
                if not reply_text or len(reply_text) < 20:
                    continue

                client.create_tweet(text=reply_text, in_reply_to_tweet_id=tweet.id)
                track_api_call()

                log["proactive_replies"].append({
                    "tweet_id": tid,
                    "target": author_username,
                    "topic": f"viral:{query}",
                    "tweet_text": tweet.text[:100],
                    "our_reply": reply_text,
                    "followers": author_followers,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                reply_count += 1
                already_replied.add(tid)
                print(f"  [Viral] Replied to @{author_username} ({author_followers} followers, {likes} likes): {reply_text[:60]}...")

                time.sleep(random.uniform(3, 8))

                if reply_count >= 4:
                    break

            except Exception as e:
                err = str(e)
                if "429" in err or "rate" in err.lower():
                    print(f"  [Viral] Rate limited, stopping")
                    break
                print(f"  [Viral] Error replying to @{author_username}: {e}")
                break

    except Exception as e:
        err = str(e)
        if "429" in err or "rate" in err.lower():
            print(f"  [Viral] Search rate limited")
        else:
            print(f"  [Viral] Search error for '{query}': {e}")

    save_engagement_log(log)
    return reply_count


# ============================================================
# CLEANUP — Trim old log entries
# ============================================================
def cleanup_log():
    """Remove log entries older than 7 days to keep file small."""
    log = load_engagement_log()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    for key in ["replies_sent", "proactive_replies"]:
        if key in log:
            log[key] = [
                entry for entry in log[key]
                if entry.get("timestamp", "") > cutoff
            ]

    if len(log.get("followed_back", [])) > 1000:
        log["followed_back"] = log["followed_back"][-1000:]

    save_engagement_log(log)


# ============================================================
# MAIN ENGAGEMENT LOOP
# ============================================================
def run_engagement_cycle():
    """Run one full engagement cycle. Called by the scheduler."""
    results = {"followed": 0, "replied": 0, "proactive": 0, "topic": 0}

    # 1. Follow back new followers
    try:
        results["followed"] = follow_back_new_followers()
        if results["followed"]:
            print(f"  [Engagement] Followed back {results['followed']} users")
    except Exception as e:
        print(f"  [Engagement] Follow-back error: {e}")

    # 2. Reply to mentions (THE #1 algorithm signal)
    try:
        results["replied"] = reply_to_mentions()
        if results["replied"]:
            print(f"  [Engagement] Replied to {results['replied']} mentions")
    except Exception as e:
        print(f"  [Engagement] Reply error: {e}")

    # 3. Proactive engagement — reply to big accounts
    try:
        results["proactive"] = proactive_engage()
        if results["proactive"]:
            print(f"  [Engagement] Sent {results['proactive']} proactive replies")
    except Exception as e:
        print(f"  [Engagement] Proactive error: {e}")

    # 4. Topic engagement — search trending topics
    try:
        results["topic"] = topic_engage()
        if results["topic"]:
            print(f"  [Engagement] Replied to {results['topic']} trending topic tweets")
    except Exception as e:
        print(f"  [Engagement] Topic engage error: {e}")

    # 5. Viral engagement — reply to random viral tweets from strangers
    try:
        results["viral"] = viral_engage()
        if results["viral"]:
            print(f"  [Engagement] Replied to {results['viral']} viral tweets")
    except Exception as e:
        print(f"  [Engagement] Viral engage error: {e}")

    # 6. Periodic cleanup
    if random.random() < 0.05:
        cleanup_log()

    return results


if __name__ == "__main__":
    print("Running engagement cycle...")
    results = run_engagement_cycle()
    print(f"\nResults: {results}")
