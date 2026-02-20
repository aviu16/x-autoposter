# X Algorithm Deep Dive & Revenue Sharing Strategy

## Revenue Sharing Requirements (Updated 2026)

| Requirement | Details |
|------------|---------|
| Subscription | X Premium or Verified Organization |
| Followers | **2,000 verified/premium followers** (increased from 500) |
| Impressions | **5M organic impressions** in last 3 months |
| Account age | 3+ months |
| Payout | Stripe, min $30, bi-weekly |
| Revenue source | Ads in reply threads under your posts |
| What counts | Only engagements from Premium subscribers count toward revenue |

---

## Algorithm Ranking Signals (From Open-Source Code)

### Engagement Weights (Confirmed from X's codebase)

| Signal | Weight | Multiplier vs Like |
|--------|--------|--------------------|
| Reply that author engages with | **+75** | **150x** |
| Reply | +13.5 | 27x |
| Profile click + engagement | +12.0 | 24x |
| Conversation click + engagement | +11.0 | 22x |
| Dwell time (2+ min) | +10.0 | 20x |
| Bookmark | +10.0 | 20x |
| Retweet | +1.0 | 2x |
| Like | +0.5 | 1x (baseline) |

### Key Insight
**A reply that gets a reply from the author is worth 150x more than a like.**
Conversation depth dominates everything. One genuine reply chain is worth more than hundreds of likes.

### Negative Signals

| Signal | Impact |
|--------|--------|
| Block | Strong penalty, hurts TweepCred |
| Report | -15 to -35 reputation |
| Mute | Significant negative |
| Unfollow | Negative relationship score |
| External links | **30-50% reach reduction** |
| 3+ hashtags | **40% penalty** |

### TweepCred Reputation Score
- Range: 0-100
- Critical threshold: **65** (below = only 3 tweets distributed)
- Premium boost: +4 to +16 points
- Factors: Account age, follower quality, engagement patterns, report history

### Content Format Performance
- **Text-only: Best** (30% more engagement than video)
- Video: 5.4% more than images
- Images: 12% more than links
- **Links: DEAD** (Zero median engagement for free accounts since March 2025)

### Premium Account Boost
- In-network: **4x visibility multiplier**
- Out-of-network: **2x visibility multiplier**
- Overall: ~**10x more impressions** per post vs free accounts

### 2026 Algorithm Update (Grok-Powered)
- January 2026: xAI replaced legacy algorithm with Grok-based transformer
- Reads every post and watches every video for content matching
- "Small account boost" — actively promotes emerging voices
- Non-Premium link posts get ZERO distribution

---

## Growth Strategy: 0 to 2,000 Premium Followers

### Phase 1: Foundation (Week 1-2)
1. **Get X Premium** ($8/mo) — mandatory for 4x visibility boost
2. **Optimize profile**: Clear bio (science/tech/world affairs), professional photo, pinned thread
3. **Join X Communities**: "Build in Public", "Science & Tech", "World News"
4. **Post 8-15x/day** — high volume is essential early on

### Phase 2: Content Machine (Week 2-6)
Content mix formula:
- **40% Thought-provoking** (questions, hot takes, contrarian views)
- **30% Educational** (science explainers, tech breakdowns, data)
- **20% News commentary** (world events + your unique analysis)
- **10% Personal/stories** (lab life, research, authentic moments)

### Phase 3: Engagement Farming (Ongoing)
- **Reply to EVERY reply** on your posts (75x weight!)
- **Quote tweet** viral posts with your analysis (not just RT)
- **Reply to big accounts** in your niche with substantive takes
- **Post in Communities** — 100% of content when under 5K followers
- **Never post bare links** — put URL in first reply instead

### Phase 4: Viral Triggers
- **Threads**: 3x more engagement than single tweets
- **Controversial but factual takes**: drives replies
- **"Most people don't know..." format**: curiosity gap
- **Data visualizations**: highly bookmarked (10x like weight)
- **Time-sensitive news + analysis**: rides trending wave

### Optimal Posting Schedule
| Time (EST) | Content Type |
|-----------|-------------|
| 6:00 AM | Morning news take / overnight world events |
| 8:00 AM | Science/tech explainer |
| 9:30 AM | Thought-provoking question |
| 11:00 AM | Thread (deep dive on topic) |
| 12:30 PM | News commentary |
| 2:00 PM | Hot take / contrarian view |
| 4:00 PM | Tech/AI update |
| 6:00 PM | Evening engagement post (poll/question) |
| 8:00 PM | Global politics / world affairs |
| 10:00 PM | Late night thought / philosophical question |

### Impression Targets
- Need: 5M impressions in 3 months = ~55,500/day
- With Premium + 10 posts/day + good engagement = achievable at ~2K followers
- DogeDesigner model: 16.5 posts/day = 313M views/month

---

## Automation Rules (What's Allowed)

### ALLOWED
- Scheduling tweets in advance
- Posting from RSS feeds
- Using analytics tools
- Automated posting of original content at set times
- AI-generated content (if original, not spam)

### PROHIBITED (Will get you banned)
- Automated replies based on keywords
- Mass following/unfollowing
- Bulk liking or retweeting
- Posting about trending topics automatically
- Posting duplicate/identical content across accounts
- Spam DMs

### Safe Approach
Our script will: pre-generate content using AI, schedule posts at optimal times, and post original content. This is within TOS — it's equivalent to using Buffer/Hootsuite/Typefully.

---

## X API Details

### Pricing
| Tier | Cost | Write Limit | Read Limit |
|------|------|-------------|------------|
| Free | $0 | 1,500 tweets/mo | None |
| Basic | $200/mo | 50,000 tweets/mo | 15,000/mo |
| Pro | $5,000/mo | Unlimited | High |

### For Our Use Case
- **Free tier is sufficient**: 1,500 tweets/month = ~50/day (we only need 10-15)
- Use OAuth 2.0 with PKCE for user context authentication
- Library: **tweepy** (most maintained, best docs)
