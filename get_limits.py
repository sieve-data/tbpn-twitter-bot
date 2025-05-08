import tweepy, requests, datetime as dt
import os

api_key = os.getenv("TW_API_KEY")
api_secret = os.getenv("TW_API_SECRET")
access_token = os.getenv("TW_ACCESS_TOKEN")
access_token_secret = os.getenv("TW_ACCESS_SECRET")


client = tweepy.Client(
    bearer_token=os.environ["TW_BEARER_TOKEN"],
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
    # Ask Tweepy to hand the raw requests.Response back
    return_type=requests.Response,  # 👈
    wait_on_rate_limit=False,
)

resp = client.create_tweet(text="Testing rate limit! 😊", user_auth=True)

headers = resp.headers
headers = resp.headers

print(
    "Limit (per window):", headers["x-rate-limit-limit"]
)  # 🔢 100, 17, 300 … depends on your plan
print("Remaining:        ", headers["x-rate-limit-remaining"])
print(
    "Window resets:    ", dt.datetime.fromtimestamp(int(headers["x-rate-limit-reset"]))
)
