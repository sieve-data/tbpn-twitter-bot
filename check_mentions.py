import tweepy
import os
import time
from dotenv import load_dotenv
import sieve
from datetime import datetime, timezone

load_dotenv()
# Load credentials from .env
api_key = os.getenv("TW_API_KEY")
api_secret = os.getenv("TW_API_SECRET")
access_token = os.getenv("TW_ACCESS_TOKEN")
access_token_secret = os.getenv("TW_ACCESS_SECRET")


client = tweepy.Client(
    bearer_token=os.getenv("TW_BEARER_TOKEN"),
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
)

BOT_USERNAME = "tbpnify"  # without @
BOT_USER_ID = 1919224688536059904


def get_likes(tweet_id: str) -> int:
    response = client.get_tweet(
        tweet_id, tweet_fields=["public_metrics"], user_auth=True
    )
    return response.data.public_metrics["like_count"]


def is_valid_summon(tweet) -> bool:
    txt = tweet.text.lower()

    # 1️⃣  Does the text actually contain @tbpnify?
    if (
        BOT_USERNAME not in txt
    ):  # shouldn’t happen given your query, but belt-and-suspenders
        return False

    # 2️⃣  Is it a reply at all?
    if tweet.in_reply_to_user_id is None:  # not a reply ⇒ ignore
        print("not a reply")
        return False

    print(str(tweet.in_reply_to_user_id))
    # 3️⃣  Is it replying **to the bot**?  If so, skip.
    if str(tweet.in_reply_to_user_id) == BOT_USER_ID:
        print("not reply to tbpnify")
        return False  # user’s just chatting with us

    return True


def check_mentions():
    utc_dt = datetime.now(timezone.utc)
    print("Local time {}".format(utc_dt.astimezone().isoformat()))

    query = f"@{BOT_USERNAME} -is:retweet"
    params = {
        "query": query,
        "tweet_fields": [
            "author_id",
            "created_at",
            "referenced_tweets",
            "in_reply_to_user_id",
            "public_metrics",
        ],
        "expansions": ["referenced_tweets.id.author_id"],
        "user_fields": ["username"],
        "max_results": 10,
        "user_auth": True,
    }

    response = client.search_recent_tweets(**params)
    tweets = response.data or []
    includes = response.includes

    # Build a map of tweet_id -> author username from the expansions
    tweet_author_map = {}
    if includes and "tweets" in includes and "users" in includes:
        tweet_map = {t.id: t for t in includes["tweets"]}
        user_map = {u.id: u.username for u in includes["users"]}
        for t in includes["tweets"]:
            if t.author_id in user_map:
                tweet_author_map[t.id] = user_map[t.author_id]

    for tweet in reversed(tweets):  # Oldest to newest
        print(f"New mention: {tweet.text}")

        # check if tweet is a reply
        if not tweet.referenced_tweets:
            continue

        for ref in tweet.referenced_tweets:
            if ref["type"] == "replied_to":
                replied_to_id = ref["id"]
                # if tweet doesn't have atleast 100 likes, skip
                # if get_likes(replied_to_id) < 100:
                #     print(f"Tweet {tweet.id} has less than 100 likes, skipping...")
                #     continue

                if is_valid_summon(tweet):
                    print("tweet is not original reply")
                    continue

                # Check if tweet has already been processed
                with open(
                    "/home/ubuntu/tbpn-twitter-bot/checked_posts.txt",
                    "r",
                ) as f:
                    checked_posts = f.read().splitlines()

                if str(replied_to_id) in checked_posts:
                    print(f"Already processed tweet {replied_to_id}, skipping...")
                    continue

                username = tweet_author_map.get(replied_to_id, "unknown")
                reply_url = f"https://twitter.com/{username}/status/{replied_to_id}"
                print(f"↪️ This tweet is a reply to: {reply_url}")
                create_tbpn_post = sieve.function.get("sieve-internal/create-tbpn-post")
                create_tbpn_post.push(reply_url, tweet.text, str(tweet.id))

                # Add to checked posts
                with open(
                    "/home/ubuntu/tbpn-twitter-bot/checked_posts.txt",
                    "a",
                ) as f:
                    f.write(f"{replied_to_id}\n")


check_mentions()
