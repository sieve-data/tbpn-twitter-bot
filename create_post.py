import requests
from create_podcast import make_podcast
from read_post import get_tweet_and_replies

from write_script import (
    describe_image,
    enrich_tweet,
    generate_title,
    generate_tweet,
    write_script,
)
import tweepy
import os
import sieve
from dotenv import load_dotenv

load_dotenv()

# Load credentials from .env
api_key = os.getenv("TW_API_KEY")
api_secret = os.getenv("TW_API_SECRET")
access_token = os.getenv("TW_ACCESS_TOKEN")
access_token_secret = os.getenv("TW_ACCESS_SECRET")
bearer_token = os.getenv("TW_BEARER_TOKEN")


# Authenticate with OAuth 1.0a
auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
api = tweepy.API(auth)


client_v2 = tweepy.Client(
    bearer_token=bearer_token,
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
)


def post_quote(tweet_url: int, video_path: str, tweet_text: str):
    tweet_id = tweet_url.split("/")[-1]
    print(tweet_id)
    upload_result = api.media_upload(video_path)
    tweet_response = client_v2.create_tweet(
        text=tweet_text,
        media_ids=[upload_result.media_id],
        quote_tweet_id=tweet_id,
    )
    return f"https://x.com/tbpnify/status/{tweet_response.data['id']}"


def post_reply(quote_url: str, tweet_reply_id: str):
    client_v2.create_tweet(
        text=f"{quote_url}",
        in_reply_to_tweet_id=tweet_reply_id,
    )
    print("Tweeted reply successfully!")


@sieve.function(
    name="create-tbpn-post",
    python_packages=[
        "tweepy",
        "elevenlabs",
        "mutagen",
        "requests",
        "python-dotenv",
        "openai",
    ],
    system_packages=["ffmpeg"],
)
def create_tbpn_post(
    tweet_url: str, user_prompt: str, reply_id: str, tweet_video: bool = True
):
    load_dotenv()
    print(api_key)

    tweet, replies = get_tweet_and_replies(tweet_url)
    if tweet.image:
        image_content = describe_image(tweet.image)
        tweet.image_content = image_content
    if tweet.ref_image:
        ref_image_content = describe_image(tweet.ref_image)
        tweet.ref_image_content = ref_image_content

    tweet = enrich_tweet(tweet)
    script = write_script(tweet, replies, user_prompt)
    title = generate_title(script)
    tweet_text = generate_tweet(script)
    print(script)
    podcast_video_path = make_podcast(script, title)
    if tweet_video:
        quote_url = post_quote(tweet_url, podcast_video_path, tweet_text)
        post_reply(
            quote_url,
            reply_id,
        )
        return quote_url
    else:
        return sieve.File(path=podcast_video_path)


# create_tbpn_post("https://x.com/realDonaldTrump/status/1919395973802897676")

# client_v2.create_tweet(text="Hello, world!")
