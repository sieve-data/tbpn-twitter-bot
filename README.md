# How to Create an AI Video Influencer Agent for X/Twitter Using Sieve AI

With the rise of virtual influencers and AI agents, finding good solutions for lipsync and clip processing is super important. Fortunately, with Sieve's APIs, you can easily and rapidly build an AI influencer agent within a matter of minutes. These virtual influencers can be used for a variety of use cases like:

- Automated AI UGC Ad Campaigns
- AI Crypto Virtual Agents
- Educational Content Creation
- Virtual Brand Ambassadors
- AI News Anchors
- Social Media Influencer Content
- Product Demonstrations
- Virtual Event Hosts

Recently, we worked on a [fun project](https://x.com/tbpnify) based on the TBPN podcast, mimicking the style of the show, where the hosts Jordi Hays and John Coogan reply to viral tweets and break them down.

1. Monitor for users pinging our bot with the @tbpnify call in response to a tweet.
2. Generate contextual podcast-style scripts based on those tweets.
3. Create AI-generated videos featuring virtual hosts discussing the content.
4. Post the video as a quote retweet to X, creating an automated content creation pipeline.

We'll demonstrate using the "TBPN" (Tech Bro Podcast Network) format with hosts "John" and "Jordi," who discuss tech tweets in a distinctive style.

### Finding Base Clips for Your Influencer

First, collect video clips of the person(s) you want your AI influencer to mimic. Here's the process we went through for collecting clips for our influencer:

- Download YouTube videos featuring your target personality.

  - We found a [TBPN episode](https://www.youtube.com/watch?v=o--23bDDk1c) that focused on the two hosts chatting with each other — perfect for this use case.
  - Using ([Sieve's YouTube downloader](https://www.sievedata.com/functions/sieve/youtube-downloader)), we were able to retrieve the raw video from the podcast.

```python
import sieve

url = "https://www.youtube.com/watch?v=o--23bDDk1c"
download_type = "video"
resolution = "highest-available"
include_audio = True
start_time = 0
end_time = -1
include_metadata = False
metadata_fields = title,thumbnail,description,tags,duration
include_subtitles = False
subtitle_languages = en
video_format = "mp4"
audio_format = "mp3"

youtube_downloader = sieve.function.get("sieve/youtube-downloader")
output = youtube_downloader.run(url, download_type, resolution, include_audio, start_time, end_time, include_metadata, metadata_fields, include_subtitles, subtitle_languages, video_format, audio_format)
```

- Use scene detection to segment videos into usable clips.

  - Sieve comes in clutch again! Simply drop the video into the scene detection function to segment your video into clips.
  - [Sieve Scene Detection](https://www.sievedata.com/functions/sieve/scene-detection)
  - You can use `return_scenes` to get the individual segments.

```python
import sieve

video = sieve.File(path="video.mp4")
backend = "base"
start_time = 0
end_time = -1
return_scenes = True
min_scene_duration = 0.1
threshold = 1
transition_merge_gap = 0.1
scene_detection = sieve.function.get("sieve/scene-detection")
output = scene_detection.run(video, backend, start_time, end_time, return_scenes, min_scene_duration, threshold, transition_merge_gap)

for output_object in output:
    print(output_object)
```

- Classify clips by person/speaker.

  - This may not be necessary for your use case, but since we had two hosts, we needed to identify clips by speaker.
  - We used CLIP to classify the scenes into two buckets by comparing similarity to two reference images.

```python
DEVICE = "cuda" if torch.cuda.is_available() else "CPU"
REF_IMAGES = {"jordi": "jordi_scene.png", "john": "john_scene.png"}
model, preprocess = clip.load("ViT-B/32", device=DEVICE)

ref_embs = {k: embed(Image.open(v)) for k, v in REF_IMAGES.items()}

def tag_clip(clip_obj: dict) -> dict:
    try:
        frame = first_frame(clip_obj["url"])
        clip_emb = embed(frame)

        sims = {
            k: torch.nn.functional.cosine_similarity(clip_emb, v).item()
            for k, v in ref_embs.items()
        }

        best_speaker, best_score = max(sims.items(), key=lambda kv: kv[1])
        clip_obj["speaker"] = best_speaker if best_score > 0.75 else "wide"
    except Exception as e:
        clip_obj["speaker"] = "unknown"
        clip_obj["error"] = str(e)
    return clip_obj
```

### Responding to Pings to Our Bot

Using the X Developer API, we can periodically search for tweets that contain a mention of our bot. We built our bot in Python using the `tweepy` library, which provides helpful wrappers for working with the X API. Using `search_recent_tweets` with the `referenced_tweets.id.author_id` expansion, we can grab the 10 most recent pings.

To set up Tweepy, grab your API keys from the X Developer Portal:

```python
client_v2 = tweepy.Client(
    bearer_token=bearer_token,
    consumer_key=api_key,
    consumer_secret=api_secret,
    access_token=access_token,
    access_token_secret=access_token_secret,
)
```

```python
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
if last_seen_id:
    params["since_id"] = last_seen_id

response = client.search_recent_tweets(**params)
```

Once we have the tweets, we parse them to determine if they've already been processed or if they meet our threshold (in our case, tweets with more than 100 likes).

```python
if get_likes(replied_to_id) < 100:
    print(f"Tweet {tweet.id} has less than 100 likes, skipping...")
    continue

with open("/Users/adipanda/codingProjects/tbpn-twitter-bot/checked_posts.txt", "r") as f:
    checked_posts = f.read().splitlines()

if str(replied_to_id) in checked_posts:
    print(f"Already processed tweet {replied_to_id}, skipping...")
    continue

username = tweet_author_map.get(replied_to_id, "unknown")
reply_url = f"https://twitter.com/{username}/status/{replied_to_id}"
print(f"↩️ This tweet is a reply to: {reply_url}")
create_tbpn_post = sieve.function.get("sieve-internal/create-tbpn-post")
create_tbpn_post.push(reply_url, str(tweet.id))

with open("/Users/adipanda/codingProjects/tbpn-twitter-bot/checked_posts.txt", "a") as f:
    f.write(f"{replied_to_id}\n")
```

You can set this script to run periodically using a cron job. Just add the following with `crontab -e`:

```bash
0 * * * * /path/to/project/venv/bin/python3 /path/to/project/check_mentions.py >> /path/to/project/cron.log 2>&1
```

### Grabbing Information from the Tweet

Once we've selected the tweet, we grab key information like content, media, and engagement metrics:

```python
result = client.get_tweet(
    id_,
    tweet_fields=["author_id", "created_at", "public_metrics", "entities"],
    expansions=["author_id", "attachments.media_keys"],
    media_fields=["url", "preview_image_url", "type"],
    user_fields=["username", "name", "verified"],
    user_auth=True,
)
```

If the tweet has an image, we use GPT-4o to describe it:

```python
def describe_image(image: str) -> str:
    completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_IMAGE},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {"type": "image_url", "image_url": {"url": image}},
                ],
            },
        ],
    )
    return completion.choices[0].message.content
```

### Enriching Tweets with Context

To add valuable background or references, we use Perplexity AI:

```python
def enrich_tweet(tweet: Tweet) -> Tweet:
    user_prompt = f"""
    Enrich the following tweet with any background, news, or other information
    needed to understand what the tweet refers to.

    Tweet author: {tweet.user_at}
    Tweet content: {tweet.content}
    {f'Tweet image: {tweet.image_content}' if tweet.image_content else ''}"""

    completion = perplexity_client.chat.completions.create(
        model="sonar-pro",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_RESEARCH},
            {"role": "user", "content": user_prompt},
        ],
    )
    tweet.context = completion.choices[0].message.content.strip()
    return tweet
```

### Making the Video Script

Once we have all the tweet metadata, we generate a script in the "TBPN" style:

```
You are an AI podcast writer that is writing a custom podcast about a tweet in the user's timeline.
Your goal is to break down that tweet and explain what's happening and why it's important.
You will be given a tweet as well as the likes, replies, and the retweet count.
Generate a podcast script between two hosts "jordi" and "john". The podcast should have a tech-bro,
energetic tone with dry sarcastic humour. The hosts are pro-technology and innovation, and the
podcast is called "TBPN". Go straight to the tweet, no introduction is needed.
Keep the script not too long, around a minute or so. (less than 140 words)

Here's the vibe of the show:
- Very online, hyper-conversational, meme-speak.
- Frequent self-aware jabs at VC clichés
- Segues that start serious and crash-land into dad-jokes or mutual roasting.
- not too cheesy, funny/sarcastic but still analytical/informative
- Make it authentic, like this is a clip from a podcast, like two real dudes chatting
about tech news
- Don't make all just memes, also include some genuine analysis/insights on the tweet

Here are some inside jokes that you COULD include in the script
- "Low TAM Banger" - banger for small audience
- "Hit the size gong" - when something big happens you hit the size gong
- Rapid-fire callbacks: “Founder Mode”, “10-year Overnight Success”

There will also be a user prompt giving an additional prompt for the script

Talk about specific tweets and elaborate on their details. 'john' always goes first.

Return **only** JSON in the form:
{
  "script": [
    { "speaker": "john" | "jordi", "dialogue": "…" },
    …
  ]
}
```

### Generating the Video

Using ElevenLabs, we generate audio for each segment:

```python
tts = local_client.text_to_speech.convert(
    text=seg["dialogue"],
    voice_id=john_voice_id if seg["speaker"] == "john" else jordi_voice_id,
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
    voice_settings={"stability": 0.1, "similarity_boost": 0.5},
)
```

Then we generate lipsynced video clips using the [Sieve Lipsync](https://www.sievedata.com/functions/sieve/lipsync) function
using the audio and base clip.

```python
def gen_video(meta: Dict):
    clip = find_clip(meta["speaker"], meta["duration"])
    base_clip = sieve.File(url=clip["url"])
    audio_file = sieve.File(url=meta["audio_url"])
    out: sieve.File = lipsync_fn.run(
        base_clip,
        audio_file,
        backend="sync-2.0",
        enable_multispeaker=False,
        enhance="default",
        check_quality=False,
        downsample=False,
        cut_by="audio",
    )
    return {"idx": meta["idx"], "path": out.path}
```

### Stitching It All Together

We combine the generated video segments into one using FFmpeg:

```python
with open(concat_txt, "w") as fp:
    for p in result_videos:
        fp.write(f"file '{p}'\n")

stitched_path = os.path.join(td, "stitched_output.mp4")
subprocess.run([
    "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", stitched_path
], check=True)
```

### Posting to X

Use the X API to quote tweet the video:

```python
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
```

### Conclusion

You're done! By combining GPT-4o for script generation, Perplexity AI for research, and Sieve AI for video synthesis, we've created an autonomous AI video influencer that can:

1. Monitor for users pinging our bot with the @tbpnify call.
2. Generate contextual podcast-style scripts based on tweets.
3. Create AI-generated videos with virtual hosts discussing the content.
4. Post the video as a quote retweet to X.

This approach allows for scalable content creation without manual intervention — perfect for maintaining a stream of engaging, topical content.
