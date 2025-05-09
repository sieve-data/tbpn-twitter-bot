# helper code to check x api limits
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

print("User daily limit : ", headers.get("x-user-limit-24hour-limit"))
print("User remaining   : ", headers.get("x-user-limit-24hour-remaining"))
print(
    "User resets      : ",
    (
        dt.datetime.fromtimestamp(int(headers["x-user-limit-24hour-reset"]))
        if "x-user-limit-24hour-reset" in headers
        else "—"
    ),
)

print("App daily limit  : ", headers.get("x-app-limit-24hour-limit"))
print("App remaining    : ", headers.get("x-app-limit-24hour-remaining"))
