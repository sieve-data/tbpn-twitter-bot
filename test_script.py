import requests
from read_post import get_tweet_and_replies

from write_script import describe_image, enrich_tweet, generate_title, write_script
import tweepy
import os
import sieve
from dotenv import load_dotenv
import dotenv


# Load credentials from .env
api_key = "LsPQTzNAjgUMQ2drMsMReBOl1"
api_secret = "PlDxIL0f9VAFadl3X971Lt9BWqlfqZcfhtOAnocG0IudHyXu2g"
access_token = "1919224688536059904-9ito9bvipHVrAQMeswURsKWob3zfSo"
access_token_secret = "hWYwTkD206m0bIVJ5nUCnDn7vBoE8YFo16GPFwbGw76sT"
bearer_token = "AAAAAAAAAAAAAAAAAAAAADxAswEAAAAA%2Fua1DhpB6MdtwdXr7PGB34LXsls%3DYhJ2fPT8czLrRRZs8qVuz2wgy4tqAnt7snxqJpWKVCB9Lj0lEJ"


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


def download_url(url: str, path: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if not 200 OK
    with open(path, "wb") as f:
        f.write(response.content)


def post_quote(tweet_url: str, video_path: str, tweet_reply_id: str):
    upload_result = api.media_upload(video_path)
    tweet_response = client_v2.create_tweet(
        text=f"{tweet_url} Here's the breakdown: ",
        media_ids=[upload_result.media_id],
    )
    return f"https://x.com/tbpnify/status/{tweet_response.data['id']}"


def post_reply(quote_url: str, tweet_reply_id: str):
    client_v2.create_tweet(
        text=f"{quote_url}",
        in_reply_to_tweet_id=tweet_reply_id,
    )
    print("Tweeted reply successfully!")


def create_tbpn_post(
    tweet_url: str, user_prompt: str, reply_id: str, tweet_video: bool = True
):
    tweet, replies = get_tweet_and_replies(tweet_url)
    if tweet.image:
        image_content = describe_image(tweet.image)
        tweet.image_content = image_content
    if tweet.ref_image:
        ref_image_content = describe_image(tweet.ref_image)
        tweet.ref_image_content = ref_image_content

    tweet = enrich_tweet(tweet)
    print("enriched", tweet)
    script = write_script(tweet, replies, user_prompt)
    title = generate_title(script)
    print("---------")
    print(script)
    print(title)
    # generate_podcast = sieve.function.get("sieve-internal/generate-podcast")
    # output = generate_podcast.run(script, title)
    # print(output)
    # video_path = "video.mp4"
    # result_video_url = output["stitched_video"]
    # if tweet_video:
    #     download_url(result_video_url, video_path)
    #     quote_url = post_quote(tweet_url, video_path, reply_id)
    #     post_reply(
    #         quote_url,
    #         reply_id,
    #     )
    #     return quote_url
    # else:
    #     return result_video_url


create_tbpn_post(
    "https://x.com/_trish_xD/status/1919686021287157823", "is this really true??", ""
)
