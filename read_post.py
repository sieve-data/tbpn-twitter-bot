import os
import time, tweepy
from typing import List, Tuple
import dotenv
from write_script import Tweet

dotenv.load_dotenv()

TW_BEARER_TOKEN = os.getenv("TW_BEARER_TOKEN")
TW_API_KEY = os.getenv("TW_API_KEY")
TW_API_SECRET = os.getenv("TW_API_SECRET")
TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_SECRET = os.getenv("TW_ACCESS_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

client = tweepy.Client(
    bearer_token=TW_BEARER_TOKEN,
    consumer_key=TW_API_KEY,
    consumer_secret=TW_API_SECRET,
    access_token=TW_ACCESS_TOKEN,
    access_token_secret=TW_ACCESS_SECRET,
)


def _raw_get_tweet(tweet_id: int):
    while True:
        try:
            return client.get_tweet(
                tweet_id,
                tweet_fields=[
                    "author_id",
                    "created_at",
                    "public_metrics",
                    "entities",
                    "referenced_tweets",
                ],
                # these two expansions pull the *full* referenced tweet + its author
                expansions=[
                    "author_id",
                    "attachments.media_keys",
                    "referenced_tweets.id",
                    "referenced_tweets.id.author_id",
                ],
                media_fields=["url", "preview_image_url", "type"],
                user_fields=["username", "name", "verified"],
                user_auth=True,
            )
        except tweepy.TooManyRequests as e:
            reset = int(e.response.headers["x-rate-limit-reset"])
            sleep_for = max(reset - time.time(), 0) + 2
            print(f"Rate-limited. Sleeping {sleep_for:.0f}s …")
            time.sleep(sleep_for)


# ── 3.  Public function: returns a ready-to-use TweetData object ───────────────
def get_tweet(tweet_id: int) -> Tweet:
    resp = _raw_get_tweet(tweet_id)

    t = resp.data
    includes = resp.includes
    users_by_id = {u.id: u for u in includes.get("users", [])}
    media_by_id = {m.media_key: m for m in includes.get("media", [])}
    tweets_by_id = {tw.id: tw for tw in includes.get("tweets", [])}

    # main tweet
    author = users_by_id[t.author_id]
    main_image = None
    if "attachments" in t and t.attachments and t.attachments.get("media_keys"):
        key = t.attachments["media_keys"][0]
        main_image = media_by_id.get(key).url if key in media_by_id else None

    # defaults for “no reference”
    ref_type = None
    ref_user_at = ref_user_display_name = ref_content = ref_image = None
    ref_likes = ref_retweets = 0

    # pick the first referenced tweet (if any) – covers replies *and* quote-RTs
    if t.referenced_tweets:
        ref_info = t.referenced_tweets[0]  # object with .id and .type
        ref_type = ref_info.type  # "quoted" | "replied_to"
        ref_tweet = tweets_by_id.get(ref_info.id)

        if ref_tweet:  # should be present thanks to the expansion above
            ref_author = users_by_id[ref_tweet.author_id]

            if "attachments" in ref_tweet and ref_tweet.attachments:
                key = ref_tweet.attachments["media_keys"][0]
                ref_image = media_by_id.get(key).url if key in media_by_id else None

            ref_user_at = ref_author.username
            ref_user_display_name = ref_author.name
            ref_content = ref_tweet.text
            ref_likes = ref_tweet.public_metrics["like_count"]
            ref_retweets = ref_tweet.public_metrics["retweet_count"]

    return Tweet(
        id=t.id,
        user_at=author.username,
        user_display_name=author.name,
        content=t.text,
        image=main_image,
        likes=t.public_metrics["like_count"],
        retweets=t.public_metrics["retweet_count"],
        # reference block
        ref_type=ref_type,
        ref_user_at=ref_user_at,
        ref_user_display_name=ref_user_display_name,
        ref_content=ref_content,
        ref_image=ref_image,
        ref_likes=ref_likes,
        ref_retweets=ref_retweets,
    )


def get_replies(root_id: int):
    """Return a list of Tweepy Tweet objects that are *direct* replies to root_id."""
    replies = []
    query = f"conversation_id:{root_id} -is:retweet -is:quote"

    common_kwargs = dict(
        query=query,
        tweet_fields=[
            "author_id",
            "created_at",
            "in_reply_to_user_id",
            "referenced_tweets",
            "conversation_id",
            "public_metrics",
        ],
        expansions=["author_id"],
        max_results=100,  # highest allowed
        user_auth=True,
    )

    paginator = tweepy.Paginator(client.search_recent_tweets, **common_kwargs)
    try:
        tweets = []
        for tweet in paginator.flatten(limit=1000):
            if tweet.referenced_tweets and any(
                ref["id"] == root_id for ref in tweet.referenced_tweets
            ):
                tweets.append(
                    Tweet(
                        user_at=tweet.author_id,
                        content=tweet.text,
                        likes=tweet.public_metrics["like_count"],
                    )
                )

        # Sort by like count and take top 10
        sorted_tweets = sorted(tweets, key=lambda x: x.likes, reverse=True)
        return sorted_tweets[:10]

    except tweepy.TooManyRequests as e:
        reset = int(e.response.headers["x-rate-limit-reset"])
        sleep_for = max(reset - time.time(), 0) + 5  # 5 s safety buffer
        print(f"⚠️  Rate-limit hit — sleeping {sleep_for:.0f}s")
        time.sleep(sleep_for)
        return []


def get_tweet_and_replies(tweet_url: str) -> Tuple[Tweet, List[Tweet]]:
    # Extract the tweet ID from the URL
    tweet_id = int(tweet_url.split("/")[-1])
    tweet = get_tweet(tweet_id)
    # replies = get_replies(tweet_id)
    replies = []
    print(f"Tweet: {tweet}")
    # print(f"Replies: {replies}")

    return tweet, replies


if __name__ == "__main__":
    tweet_url = "https://x.com/tylercosg/status/1919764522505474278"
    tweet, replies = get_tweet_and_replies(tweet_url)
