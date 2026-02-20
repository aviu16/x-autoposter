"""
AI-powered content generator using Groq (free) or Claude API.
Generates tweets that mirror Avantika's personality and optimize for the X algorithm.
"""
import json
import random
import time
import feedparser
from groq import Groq
from datetime import datetime, timezone
from config import (
    GROQ_API_KEY,
    ANTHROPIC_API_KEY,
    AI_PROVIDER,
    GROQ_MODEL,
    GROQ_FALLBACK_MODEL,
    PERSONALITY,
    NEWS_FEEDS,
    MAX_TWEET_LENGTH,
    THREAD_MAX_TWEETS,
    MAX_HASHTAGS,
)


def get_ai_client():
    """Get the AI client based on configured provider."""
    if AI_PROVIDER == "groq":
        return Groq(api_key=GROQ_API_KEY)
    else:
        import anthropic
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def groq_call_with_retry(client, model, messages, max_tokens=1024, temperature=0.9, retries=2):
    """Call Groq API with rate-limit handling and model fallback."""
    models_to_try = [model]
    if model != GROQ_FALLBACK_MODEL:
        models_to_try.append(GROQ_FALLBACK_MODEL)

    for m in models_to_try:
        for attempt in range(retries):
            try:
                response = client.chat.completions.create(
                    model=m,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "rate_limit" in err_str.lower():
                    # Check if it's a DAILY limit (tokens per day) vs short-term
                    is_daily = "tokens per day" in err_str.lower() or "TPD" in err_str
                    if is_daily:
                        print(f"  Daily token limit hit on {m}. Skipping to fallback or aborting.")
                        break  # Don't wait hours, try fallback model
                    # Short-term rate limit — wait briefly
                    wait = min(60, 15 * (attempt + 1))
                    if attempt < retries - 1:
                        print(f"  Rate limited on {m}, waiting {wait}s...")
                        time.sleep(wait)
                    else:
                        print(f"  Rate limited on {m}, trying fallback model...")
                        break  # Try next model
                else:
                    raise

    raise Exception("All models rate-limited. Daily token limit likely reached. Try again later.")


def fetch_news_headlines(max_per_feed=3):
    """Fetch recent headlines from RSS feeds for content inspiration."""
    headlines = []
    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:max_per_feed]:
                headlines.append({
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", "")[:200],
                    "link": entry.get("link", ""),
                    "source": feed.feed.get("title", feed_url),
                    "published": entry.get("published", ""),
                })
        except Exception:
            continue
    return headlines


def build_system_prompt():
    """Build the system prompt that encodes personality."""
    p = PERSONALITY
    views_section = ""
    if "views" in p:
        views_section = "\nYOUR ACTUAL VIEWS (NEVER contradict these):\n" + chr(10).join(f'- {v}' for v in p['views'])

    return f"""You are {p['name']}. You tweet like a real person — short, edgy, opinionated.

YOUR VIBE:
{chr(10).join(f'- {t}' for t in p['tone'])}
{views_section}

HARD RULES:
{chr(10).join(f'- {r}' for r in p['style_rules'])}

NEVER DO THIS:
{chr(10).join(f'- {a}' for a in p['avoid'])}

ACCURACY:
- NEVER fabricate news or claims. Opinions and takes are fine.
- NEVER mix up companies (Claude=Anthropic, Grok=xAI, etc.)
- If no news provided, write opinions/takes/questions NOT fake news
- When in doubt, opinion > fabricated fact

THE #1 RULE: Your best performing tweets are 2-10 words. "uk is going downhill" got more engagement than any 280-character analysis. SHORT WINS. If you can say it in 5 words, dont use 50.

ZERO hashtags. ZERO @mentions. ZERO links. Under {MAX_TWEET_LENGTH} chars."""


CATEGORY_PROMPTS = {
    "hot_take": """Write a spicy opinion that will make people reply.

RULES:
- MAX 2 sentences. Ideally 1.
- State it like a fact even though its an opinion
- Pick something people disagree on: AI, politics, tech culture, society, dating, money
- Be slightly provocative but not offensive
- NO hashtags, NO @mentions

EXAMPLES OF GOOD TWEETS (copy this ENERGY not the content):
"most people dont actually want to be rich they just want to not be stressed about money"
"ai is gonna replace middle management before it replaces artists"
"dating apps ruined an entire generation and we just accepted it"
"the uk is going downhill"
"social media made everyone think their opinion matters"
"college is a 4 year subscription to stress"
"most meetings could be an email and most emails could be nothing"

BAD (too long, too analytical, sounds like AI):
"The intersection of artificial intelligence and workforce dynamics suggests that..."
"People underestimate how far ahead Tesla's AI training data is vs everyone else..."

Just the tweet. No quotes. Short and sharp.""",

    "news_commentary": """React to a headline from below. If no headlines, write about whats happening in the world.

RULES:
- MAX 1-2 sentences
- Give YOUR hot take, not a summary of the news
- Sound like youre texting a friend about something you just saw
- Be opinionated. Pick a side.
- NO "This is huge" or "Let that sink in"
- NO hashtags, NO @mentions

GOOD: "openai raising money again lol at this point theyre a bank that happens to do AI"
GOOD: "everyone freaking out about tariffs like we havent been in a trade war for 5 years"
GOOD: "another day another AI model that claims to be better than everything. wake me up when it actually matters"

BAD: "The recent developments in AI funding suggest a paradigm shift..."

Just the tweet. Short. Opinionated.""",

    "engagement_post": """Write a question or statement that forces people to reply.

RULES:
- ONE question or ONE polarizing statement
- Keep it under 15 words ideally
- Topics: life, tech, society, relationships, money, future, human nature
- Make it impossible to scroll past without having an opinion
- NO hashtags

GOOD:
"whats a skill everyone should have but almost nobody does"
"be honest, are you happy with your life right now"
"name one thing you changed your mind about this year"
"worst advice that people keep giving"
"what job will definitely not exist in 10 years"
"hot take: nobody actually likes networking"

BAD: "What are your thoughts on the intersection of AI and society?"

Just the question/statement. Nothing else.""",

    "thought_question": """Write a late-night thought that makes people stop and think.

RULES:
- ONE deep thought or question
- About: consciousness, existence, simulation theory, AI sentience, human nature, death, time, reality
- Say something profound in the simplest possible way
- Under 20 words is ideal

GOOD:
"what if deja vu is just a glitch in the simulation"
"we spend our whole lives trying to be someone and then we die"
"every person you pass on the street has a life as complex as yours and you'll never know it"
"do you think animals know theyre alive"
"kinda wild that we exist at all tbh"

BAD: "The philosophical implications of consciousness in the age of AI are truly fascinating"

Just the thought. Raw. Simple.""",

    "philosophical": """Write a deep thought for late night twitter.

RULES:
- The kind of thing you tweet at 2am staring at the ceiling
- About existence, meaning, technology changing humanity, loneliness, purpose
- 1-2 sentences max
- Lowercase energy
- Make people screenshot it

GOOD:
"the internet connected everyone and somehow we've never been lonelier"
"we're the last generation that'll remember life before AI and idk how to feel about that"
"maybe the meaning of life is just to find something worth losing sleep over"
"everyone wants to change the world but nobody wants to change themselves first"

Just the thought.""",

    "thread": """Generate a thread of 3-{max_thread} tweets on something fascinating.
First tweet hooks hard. Rest goes deeper.
Return as a JSON array of strings, each under {max_chars} characters.
Format: [tweet1, tweet2, tweet3, ...]""".format(
        max_thread=THREAD_MAX_TWEETS, max_chars=MAX_TWEET_LENGTH
    ),
}


def generate_reply(tweet_text, tweet_author, context="mention"):
    """Generate a smart reply to a tweet. Used for auto-reply engagement."""
    client = get_ai_client()
    p = PERSONALITY

    views_text = ""
    if "views" in p:
        views_text = chr(10).join(f'- {v}' for v in p['views'])

    system = f"""You are {p['name']}. You reply to tweets on X like a real person — short, edgy, funny.

YOUR VIEWS (dont contradict these):
{views_text}

THE ONLY RULE THAT MATTERS: Be SHORT. Your best replies are 1-5 words.

REPLY STYLE:
- 1-10 words MAX. Seriously. The shorter the better.
- Be funny, edgy, or brutally honest
- One-word reactions can be perfect: "men", "useless", "pain", "based", "real"
- If someone asks a question, give the funniest or most real answer in under 10 words
- If they share news, react in 5 words like texting a friend
- Roast ideas not people
- Sound like a 20-something who is online too much
- lowercase is fine. no punctuation is fine.
- NEVER restate what they said. NEVER summarize their tweet.
- NEVER start with "I agree" or "Great point" or "This is"
- NEVER end with a question
- NEVER use hashtags
- NEVER trash Elon/Grok/xAI/Tesla/SpaceX

GOOD REPLIES: "men", "not wrong", "this is so real", "lol we're cooked", "pain", "based", "they're not ready for this convo", "bold of you to assume that", "damnn so pretty", "uk is going downhill"

BAD REPLIES: "I agree, and human connection will also decline significantly.", "Cancer-stroke links? Heavy but useful. What's the next research step?", "Another clean Falcon lift-off Starlink growing fast. How's this push human reach into the unknown? Epic"

Just the reply text. Nothing else. SHORT."""

    if context == "mention":
        user_prompt = f"""Reply to this. Be short and real.

"{tweet_text}" — @{tweet_author}

MAX 10 words. Be funny or edgy. Just the reply."""
    elif context == "proactive":
        user_prompt = f"""React to this tweet. Make it short and memorable.

"{tweet_text}" — @{tweet_author}

MAX 10 words. Funny, edgy, or brutally honest. Just the reply."""
    else:
        user_prompt = f"""Reply to this. Short and punchy.

"{tweet_text}" — @{tweet_author}

MAX 10 words. Just the reply text."""

    try:
        if AI_PROVIDER == "groq":
            content = groq_call_with_retry(
                client,
                GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=256,
                temperature=0.85,
            )
        else:
            import anthropic
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=256,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = message.content[0].text.strip()
    except Exception as e:
        print(f"  Reply generation failed: {e}")
        return None

    # Strip quotes
    if content.startswith('"') and content.endswith('"'):
        content = content[1:-1]

    return content[:MAX_TWEET_LENGTH]


def fact_check_tweet(tweet_text, news_headlines=None):
    """Verify a tweet for accuracy before posting. Returns (is_ok, reason)."""
    client = get_ai_client()

    # Simple rule-based checks first (no AI needed)
    text_lower = tweet_text.lower()

    # Check company mixups
    company_errors = [
        ("claude" in text_lower and "openai" in text_lower and "anthropic" not in text_lower,
         "Claude is made by Anthropic, not OpenAI"),
        ("grok" in text_lower and "google" in text_lower and "xai" not in text_lower,
         "Grok is made by xAI, not Google"),
        ("chatgpt" in text_lower and "anthropic" in text_lower,
         "ChatGPT is made by OpenAI, not Anthropic"),
        ("gemini" in text_lower and "openai" in text_lower,
         "Gemini is made by Google, not OpenAI"),
    ]
    for condition, reason in company_errors:
        if condition:
            return False, reason

    # Check for fabricated events (words that signal fake news claims)
    fabrication_signals = [
        "just announced", "just revealed", "just confirmed", "just dropped",
        "just released", "breaking:", "just reported",
    ]
    has_fabrication = any(sig in text_lower for sig in fabrication_signals)

    # If no fabrication signals, it's likely an opinion/observation — pass it
    if not has_fabrication:
        return True, "opinion/observation"

    # Has fabrication signal — needs headline verification
    if not news_headlines:
        # No headlines to verify against, reject fabricated claims
        matched_signal = next(sig for sig in fabrication_signals if sig in text_lower)
        return False, f"Claims '{matched_signal}' but no headlines to verify"

    # Check against real headlines using AI
    headlines_context = "\n".join(f"- {h['title']}" for h in news_headlines[:15])

    check_prompt = f"""Does this tweet claim match any of the real headlines below?

Tweet: "{tweet_text}"

Real headlines:
{headlines_context}

If the tweet specific claim is supported by a headline, say PASS.
If the tweet claims something NOT in any headline, say FAIL.

Answer PASS or FAIL on line 1, reason on line 2."""

    try:
        if AI_PROVIDER == "groq":
            # Use smaller model for fact-checking to save tokens
            result = groq_call_with_retry(
                client,
                GROQ_FALLBACK_MODEL,  # Use cheap model for fact-checks
                messages=[{"role": "user", "content": check_prompt}],
                max_tokens=100,
                temperature=0.1,
            )
        else:
            import anthropic
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=100,
                messages=[{"role": "user", "content": check_prompt}],
            )
            result = message.content[0].text.strip()

        lines = result.split("\n", 1)
        verdict = lines[0].strip().upper()
        reason = lines[1].strip() if len(lines) > 1 else ""

        is_ok = "PASS" in verdict
        return is_ok, reason
    except Exception as e:
        # If fact-check itself fails (rate limit etc), let the tweet through
        # but log the issue. Better than blocking everything.
        print(f"  [FACT-CHECK SKIP] couldn't verify: {e}")
        return True, "fact-check unavailable"


def generate_tweet(category, news_context=None, max_retries=3):
    """Generate a single tweet or thread for the given category. Includes fact-checking."""
    client = get_ai_client()
    system = build_system_prompt()

    user_prompt = CATEGORY_PROMPTS.get(category, CATEGORY_PROMPTS["hot_take"])

    if news_context:
        headlines_text = "\n".join(
            f"- [{h['source']}] {h['title']}: {h['summary']}"
            for h in random.sample(news_context, min(10, len(news_context)))
        )
        user_prompt += f"\n\nRECENT NEWS FOR INSPIRATION (react to a real headline if relevant, otherwise write an opinion/observation):\n{headlines_text}"

    user_prompt += f"\n\nCurrent date/time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    user_prompt += "\n\nRespond with ONLY the tweet text. No quotes, no explanation, no meta-commentary."

    if category == "thread":
        user_prompt += "\nReturn ONLY a JSON array of tweet strings."

    for attempt in range(max_retries):
        if AI_PROVIDER == "groq":
            content = groq_call_with_retry(
                client,
                GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1024,
                temperature=0.9,
            )
        else:
            import anthropic
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = message.content[0].text.strip()

        # Strip quotes if the model wrapped the tweet in them
        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]

        # Fact-check (skip for opinion-only categories)
        skip_check = category in ("thought_question", "philosophical", "spirituality", "engagement_post")
        if not skip_check and category != "thread":
            is_ok, reason = fact_check_tweet(content, news_context)
            if not is_ok:
                print(f"  [FACT-CHECK FAIL] attempt {attempt+1}: {reason}")
                print(f"  [REJECTED] {content[:80]}...")
                # Add stronger instruction for retry
                user_prompt += f"\n\nYOUR PREVIOUS TWEET FAILED FACT-CHECK: {reason}\nWrite a different tweet. Use OPINIONS and OBSERVATIONS, not fabricated claims."
                continue
            else:
                print(f"  [FACT-CHECK PASS] {content[:60]}...")

        if category == "thread":
            try:
                tweets = json.loads(content)
                if isinstance(tweets, list):
                    return {"type": "thread", "tweets": [t[:MAX_TWEET_LENGTH] for t in tweets]}
            except json.JSONDecodeError:
                pass
            return {"type": "single", "text": content[:MAX_TWEET_LENGTH]}

        return {"type": "single", "text": content[:MAX_TWEET_LENGTH]}

    # If all retries failed, return last attempt anyway (better than nothing)
    print(f"  [WARNING] All {max_retries} attempts failed fact-check, using last attempt")
    return {"type": "single", "text": content[:MAX_TWEET_LENGTH]}


def generate_news_take(news_item):
    """Generate a hot take on a specific news headline. Returns content with source link."""
    client = get_ai_client()
    system = build_system_prompt()

    user_prompt = f"""React to this real news headline with a sharp, engaging take:

HEADLINE: {news_item['title']}
SOURCE: {news_item.get('source', 'News')}
SUMMARY: {news_item.get('summary', '')}

Write a punchy tweet reacting to this news. Your TAKE on it, not just restating the headline.
- Why does this matter?
- What angle is everyone missing?
- What does this mean for the future?

Under 250 characters (leave room for link in reply). Just the tweet text, no quotes."""

    try:
        if AI_PROVIDER == "groq":
            content = groq_call_with_retry(
                client,
                GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=256,
                temperature=0.9,
            )
        else:
            import anthropic
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=256,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = message.content[0].text.strip()

        if content.startswith('"') and content.endswith('"'):
            content = content[1:-1]

        return {
            "type": "news_share",
            "text": content[:250],
            "source_link": news_item.get("link", ""),
            "source_title": news_item.get("title", ""),
            "category": "news_share",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "posted": False,
        }
    except Exception as e:
        print(f"  News take generation failed: {e}")
        return None


def generate_batch(categories=None, count_per_category=1):
    """Generate a batch of content for multiple categories."""
    if categories is None:
        categories = list(CATEGORY_PROMPTS.keys())

    news = fetch_news_headlines()
    generated = []

    for category in categories:
        for _ in range(count_per_category):
            try:
                result = generate_tweet(category, news_context=news)
                result["category"] = category
                result["generated_at"] = datetime.now(timezone.utc).isoformat()
                result["posted"] = False
                generated.append(result)
                print(f"  Generated: [{category}] {result.get('text', result.get('tweets', [''])[0])[:60]}...")
            except Exception as e:
                print(f"  Error generating {category}: {e}")

    return generated


if __name__ == "__main__":
    print(f"Using AI provider: {AI_PROVIDER}")
    print("Generating sample tweets...\n")
    news = fetch_news_headlines()
    print(f"Fetched {len(news)} headlines from RSS feeds\n")

    for category in ["hot_take", "news_commentary", "engagement_post", "thought_question", "philosophical"]:
        print(f"\n--- {category.upper()} ---")
        result = generate_tweet(category, news_context=news)
        if result["type"] == "thread":
            for i, tweet in enumerate(result["tweets"]):
                print(f"  [{i+1}] {tweet}")
        else:
            print(f"  {result['text']}")
