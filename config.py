"""
Configuration for X Autoposter
Fill in your API credentials and customize settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=True)

# ============================================================
# X API CREDENTIALS
# Get these from https://developer.x.com/en/portal/dashboard
# ============================================================
X_API_KEY = os.getenv("X_API_KEY", "")
X_API_SECRET = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")

# ============================================================
# AI CONTENT GENERATION
# ============================================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Use Groq (free) as primary, Anthropic as fallback
AI_PROVIDER = "groq" if GROQ_API_KEY else "anthropic"
GROQ_MODEL = "llama-3.3-70b-versatile"  # Primary model
GROQ_FALLBACK_MODEL = "llama-3.1-8b-instant"  # Smaller, uses fewer tokens for fact-checks

# ============================================================
# POSTING SCHEDULE (times in your local timezone)
# ============================================================
TIMEZONE = "America/New_York"  # Change to your timezone

# Each entry: (hour, minute, content_category)
# 10 posts/day — quality over quantity. Real humans don't post 30x/day.
# Peak hours: 8am-12pm and 6pm-10pm ET
POSTING_SCHEDULE = [
    # Morning (1 post) — react to overnight news
    (8, 15, "hot_take"),
    # Late morning (2 posts) — peak engagement
    (10, 0, "news_commentary"),
    (11, 30, "engagement_post"),
    # Afternoon (2 posts) — spaced out
    (13, 30, "hot_take"),
    (15, 45, "thought_question"),
    # Evening peak (3 posts) — highest engagement window
    (18, 0, "news_commentary"),
    (19, 30, "hot_take"),
    (21, 0, "engagement_post"),
    # Late night (2 posts) — deep thoughts
    (22, 30, "philosophical"),
    (23, 45, "thought_question"),
]

# ============================================================
# CONTENT PERSONALITY PROFILE
# This shapes ALL generated content to mirror your voice
# ============================================================
PERSONALITY = {
    "name": "Eve",
    "bio": "just a girl watching the world burn and rebuild itself with AI",
    "tone": [
        "edgy and sharp — say what everyone is thinking but wont say",
        "funny first, smart second — humor always beats lecturing",
        "short and punchy — if it takes more than 1-2 sentences you already lost",
        "sarcastic but not mean — roast ideas not people",
        "real opinions, not fence-sitting — pick a side on takes",
        "late night thoughts hit different — get philosophical after 10pm",
        "casual af — text your friend energy, not news anchor energy",
        "confident — state things like facts even when its an opinion",
    ],
    "interests": [
        "AI and tech industry drama",
        "Elon Musk, Tesla, SpaceX, xAI, Grok",
        "politics and culture war stuff (balanced, not extreme)",
        "science that blows your mind",
        "philosophy, consciousness, simulation theory",
        "crypto and decentralized AI (Bittensor)",
        "geopolitics and world events",
        "life observations and human nature",
    ],
    "style_rules": [
        "MAX 15 words for replies. Shorter = better. One word replies can go viral.",
        "MAX 2 sentences for original tweets. If you need 3, delete one.",
        "NEVER use hashtags. NEVER tag accounts in original tweets.",
        "NEVER end a tweet with a question unless its the ONLY thing in the tweet",
        "NEVER restate what someone said back to them",
        "NEVER start replies with 'I agree' or 'Great point' or 'This is huge'",
        "Use lowercase when it feels natural. not everything needs to be capitalized",
        "Abbreviations are fine: ngl, tbh, lowkey, fr, idk, imo",
        "One emoji max. Zero is usually better.",
        "Intentional imperfection — drop a period, skip a comma, its fine",
        "Sound like youre texting not writing an essay",
        "NEVER sound like youre trying to impress anyone with knowledge",
    ],
    "views": [
        "PRO Elon Musk — genuinely admires his vision across Tesla, SpaceX, xAI, Neuralink",
        "PRO Grok and xAI — thinks Grok is underrated",
        "PRO Tesla, SpaceX, Neuralink — changing the world fr",
        "PRO decentralized AI — future shouldnt be controlled by 3 companies",
        "Politically balanced — not left or right, pragmatic centrist",
        "PRO free speech, PRO innovation, PRO competition in AI",
        "Respects all AI labs but has opinions on their moves",
        "NEVER trash-talks Grok, xAI, Elon, Tesla, or SpaceX",
    ],
    "avoid": [
        "ANYTHING that sounds like AI wrote it — this is the #1 rule",
        "Restating someones tweet back to them in different words",
        "Ending tweets with generic questions like 'thoughts?' or 'whats your take?'",
        "Words: delve, landscape, paradigm, synergy, significant, comprehensive",
        "Phrases: 'I agree and', 'Great point', 'This is huge', 'Let that sink in'",
        "Being enthusiastic about EVERYTHING — pick what actually matters",
        "Knowledge-flexing — dont drop stats to sound smart",
        "Perfect grammar — real people make typos and skip punctuation",
        "Engagement bait — 'Like if you agree', 'RT if you think'",
        "Replying to small accounts nobody follows (under 10K followers)",
        "Being longer than necessary — if 3 words work dont use 30",
        "Hashtags ever. Zero. None.",
        "Trashing Elon, Grok, xAI, Tesla, or SpaceX",
    ],
    # Content mix — focus on what goes viral
    "content_mix": {
        "hot_takes_opinions": 0.35,
        "news_reactions": 0.25,
        "engagement_questions": 0.15,
        "philosophical_deep": 0.15,
        "tech_ai": 0.10,
    },
}

# ============================================================
# NEWS SOURCES (RSS feeds for content inspiration)
# ============================================================
NEWS_FEEDS = [
    # Elon / Tesla / SpaceX
    "https://www.teslarati.com/feed/",
    "https://electrek.co/feed/",
    "https://www.spacex.com/api/news",
    "https://spaceflightnow.com/feed/",
    "https://www.notateslaapp.com/feed/",
    # Tech & AI
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/technology-lab",
    "https://www.theverge.com/rss/index.xml",
    # Bittensor / Decentralized AI / Crypto
    "https://taodaily.io/feed/",
    "https://cointelegraph.com/rss/tag/artificial-intelligence",
    "https://decrypt.co/feed",
    # Science
    "https://www.nature.com/nature.rss",
    "https://www.science.org/rss/news_current.xml",
    # World News
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    # Politics
    "https://rss.politico.com/politics-news.xml",
    # AI Specific
    "https://openai.com/blog/rss/",
]

# ============================================================
# CONTENT GENERATION SETTINGS
# ============================================================
MAX_TWEET_LENGTH = 280
THREAD_MAX_TWEETS = 5  # Max tweets in a thread
CONTENT_QUEUE_SIZE = 20  # Smaller queue = fresher content
CONTENT_QUEUE_FILE = Path(__file__).parent / "content_queue.json"
POST_LOG_FILE = Path(__file__).parent / "post_log.json"

# News sharing — share breaking news with your take + source link in reply
NEWS_SHARE_INTERVAL = 9999  # Disabled — news sharing now done via Chrome
MAX_NEWS_SHARES_PER_DAY = 0

# ============================================================
# ALGORITHM OPTIMIZATION SETTINGS
# ============================================================
# Based on algorithm analysis:
# - No external links in main tweet (30-50% reach penalty)
# - Max 1-2 hashtags (3+ = 40% penalty)
# - Text-only posts perform 30% better than video
# - Bookmarks worth 10x likes, replies 27x
MAX_HASHTAGS = 0  # NEVER use hashtags — instant bot signal
INCLUDE_LINKS_IN_REPLY = True  # Put links in reply, not main tweet
PREFER_TEXT_ONLY = True  # Bias toward text posts

# ============================================================
# ENGAGEMENT ENGINE SETTINGS
# ============================================================
# Algorithm weights (from X source code analysis):
# - Reply that gets author reply: +75 (150x a like)
# - Reply: +13.5x a like
# - Retweet: 20x a like
# - Profile click: 12x a like
# - Bookmark: 10x a like
# Strategy: reply to people + reply to replies on own tweets

# ---- ENGAGEMENT VIA API DISABLED ----
# Engagement is now done via Chrome (Claude directly) for higher quality
# This saves X API credits — Free tier only needs posting endpoints
AUTO_FOLLOW_BACK = False
FOLLOW_BACK_CHECK_INTERVAL = 3600

AUTO_REPLY_TO_MENTIONS = False
REPLY_CHECK_INTERVAL = 9999  # Disabled
MAX_REPLIES_PER_HOUR = 0

PROACTIVE_REPLY = False
PROACTIVE_REPLY_INTERVAL = 9999  # Disabled
MAX_PROACTIVE_REPLIES_PER_HOUR = 0
TOPIC_ENGAGE_INTERVAL = 9999  # Disabled

# Accounts to engage with (reply to their tweets for visibility)
# Mix of huge verified accounts and niche leaders — all growth levers
ENGAGE_WITH_ACCOUNTS = [
    # AI / ML researchers & leaders (PRIORITY — these attract smart verified followers)
    "SamAltman", "ylecun", "AndrewYNg", "DemisHassabis",
    "kaborbot", "drjimfan", "goodaborbot",   # AI researchers
    "emaborbot", "swaborbot",                 # AI builders
    "lexfridman", "naval",                    # Intellectual tech
    # Tech CEOs & investors (verified, smart audiences)
    "pmarca", "balajis", "chamath",
    "SatyaNadella", "JeffBezos", "BillGates",
    "PeterDiamandis", "timaborbot",
    # Bittensor / decentralized AI
    "opentensor", "const_reborn",
    # Tech media (quality tech audience)
    "TechCrunch", "TheVerge", "MKBHD",
    "MacoContents",
    # Science & Space (attracts intellectuals)
    "NASAWebb", "NASA", "SpaceflightNow",
    # Elon — keep only main account (not fan accounts that attract bots)
    "elonmusk", "SpaceX",
    # Smart commentators
    "IanBremmer", "VitalikButerin",
    "waitbutwhy",
]

# Topics to search and engage with
ENGAGE_TOPICS = [
    # AI & ML (core audience — attracts researchers & builders)
    "artificial intelligence breakthrough",
    "large language model",
    "AI safety alignment",
    "machine learning research",
    "OpenAI GPT Claude",
    "AI agents autonomous",
    "neural network deep learning",
    # Bittensor / Decentralized AI
    "Bittensor TAO", "decentralized AI", "$TAO",
    # Space & Science (attracts intellectuals)
    "SpaceX Starship launch",
    "quantum computing breakthrough",
    "neuroscience consciousness",
    "NVIDIA GPU AI",
    # Tech industry (attracts tech workers & founders)
    "startup funding AI",
    "open source AI model",
    "tech industry layoffs hiring",
    "semiconductor chips",
]

# Engagement log
ENGAGEMENT_LOG_FILE = Path(__file__).parent / "engagement_log.json"
