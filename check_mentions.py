import tweepy
import os
import time
from dotenv import load_dotenv
import sieve
from datetime import datetime, timezone

load_dotenv()

# Load credentials
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

BOT_USERNAME = "tbpnify"
BOT_USER_ID = 101354595
# check_log_path = "/home/ubuntu/tbpn-twitter-bot/checked_posts.txt"
check_log_path = "/Users/adipanda/codingProjects/tbpn-twitter-bot/checked_posts.txt"


def get_likes(tweet_id: str) -> int:
    response = client.get_tweet(
        tweet_id, tweet_fields=["public_metrics"], user_auth=True
    )
    return response.data.public_metrics["like_count"]


def is_valid_summon(tweet) -> bool:
    txt = tweet.text.lower()
    if BOT_USERNAME not in txt:
        return False
    if tweet.in_reply_to_user_id is None:
        return False
    if str(tweet.in_reply_to_user_id) == str(BOT_USER_ID):
        return False
    return True


def run_scheduled_posts(tweet_data):
    total = len(tweet_data)
    if total == 0:
        print("No new valid mentions to process.")
        return

    interval = 3600 // total  # seconds between each post

    for idx, (reply_url, tweet_text, tweet_id) in enumerate(tweet_data):
        print(f"Posting #{idx + 1}/{total}: {reply_url}")
        create_tbpn_post = sieve.function.get("sieve-internal/create-tbpn-post")
        create_tbpn_post.push(reply_url, tweet_text, tweet_id)

        # Save to checked posts
        with open(check_log_path, "a") as f:
            f.write(f"{reply_url.split('/')[-1]}\n")

        if idx < total - 1:
            print(f"Sleeping {interval} seconds before next post…")
            time.sleep(interval)


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
        "expansions": ["referenced_tweets.id.author_id", "in_reply_to_user_id"],
        "user_fields": ["username"],
        "max_results": 10,
        "user_auth": True,
    }

    response = client.search_recent_tweets(**params)
    tweets = response.data or []
    includes = response.includes

    tweet_author_map = {}
    user_map = {u.id: u.username for u in response.includes.get("users", [])}

    if includes and "tweets" in includes and "users" in includes:
        tweet_map = {t.id: t for t in includes["tweets"]}
        user_map.update({u.id: u.username for u in includes["users"]})
        for t in includes["tweets"]:
            if t.author_id in user_map:
                tweet_author_map[t.id] = user_map[t.author_id]

    with open(check_log_path, "r") as f:
        checked_posts = set(f.read().split())

    scheduled_tweets = []
    print(checked_posts)

    for tweet in reversed(tweets):  # Oldest to newest
        print(f"New mention: {tweet.text}")
        if not is_valid_summon(tweet):
            continue

        for ref in tweet.referenced_tweets:
            if ref["type"] == "replied_to":
                replied_to_id = ref["id"]
                print(replied_to_id)
                if str(replied_to_id) in checked_posts:
                    print(f"Already processed tweet {replied_to_id}, skipping...")
                    continue

                username = tweet_author_map.get(replied_to_id, "unknown")
                reply_url = f"https://twitter.com/{username}/status/{replied_to_id}"
                print(f"↪️ Valid reply to: {reply_url}")

                scheduled_tweets.append((reply_url, tweet.text, str(tweet.id)))

    run_scheduled_posts(scheduled_tweets)


check_mentions()
