# tbpn_ai.py
from __future__ import annotations
import openai
import json
import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

openai_client = openai.OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://api.openai.com/v1",
)

perplexity_client = openai.OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai",  # Perplexity's Chat API
)

grok_client = openai.OpenAI(
    api_key=os.getenv("GROK_API_KEY"),
    base_url="https://api.x.ai/v1",
)


SYSTEM_PROMPT_SCRIPT = """\
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
"""

SYSTEM_PROMPT_RESEARCH = """\
You are a researcher trying to figure out the context of a given tweet.
You will be given a tweet and must return any background, news, or other information
needed to understand what the tweet refers to.
"""

SYSTEM_PROMPT_IMAGE = """\
You are an image description expert.
You will be given an image and must return a description of the image.
"""


@dataclass
class Tweet:
    id: int
    user_display_name: str
    user_at: str
    content: str
    likes: int
    retweets: int
    ref_type: Optional[str]  # "quoted" | "replied_to" | None
    ref_user_at: Optional[str]
    ref_user_display_name: Optional[str]
    ref_content: Optional[str]
    ref_image: Optional[str]
    ref_likes: int
    ref_retweets: int
    image: Optional[str] = None
    image_content: Optional[str] = None
    ref_image_content: Optional[str] = None
    context: str = field(default_factory=str)
    ref_context: str = field(default_factory=str)


def enrich_tweet(tweet: Tweet) -> Tweet:
    user_prompt = f"""
    Enrich the following tweet with any background, news, or other information
    needed to understand what the tweet refers to.

    Tweet author: {tweet.user_at}
    Tweet content: {tweet.content} 
    {f'Tweet image: {tweet.image_content}' if tweet.image_content else ''}
    {f'Reference tweet author: {tweet.ref_user_at}' if tweet.ref_user_at else ''}
    {f'Reference tweet content: {tweet.ref_content}' if tweet.ref_content else ''}
    {f'Reference tweet image: {tweet.ref_image}' if tweet.ref_image else ''}
    {f'Reference tweet image content: {tweet.ref_image_content}' if tweet.ref_image_content else ''}"""

    completion = perplexity_client.chat.completions.create(
        model="sonar-pro",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_RESEARCH},
            {"role": "user", "content": user_prompt},
        ],
    )
    tweet.context = completion.choices[0].message.content.strip()

    return tweet


def describe_image(image: str) -> str:
    completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_IMAGE},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image,
                        },
                    },
                ],
            },
        ],
    )

    return completion.choices[0].message.content


def generate_title(script: List) -> str:
    completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are a title generator for a script. 
                Make the title like a clickworthy headline, but don't use any special characters/punctionation, just return a normal text title.
                Also keep it short, ideally under 5 words.""",
            },
            {
                "role": "user",
                "content": f"Please a headline title based on this script {script}",
            },
        ],
    )

    return completion.choices[0].message.content


def generate_tweet(script: List) -> str:
    completion = openai_client.chat.completions.create(
        model="gpt-4.5-preview",
        messages=[
            {
                "role": "system",
                "content": """You are a tweet generator based on a script.
                Make the tweet is interesting and engagement bate worthy. The tweet
                should hook people in to the video. But keep it realistic and not 
                overexaggerated, don't use any emojis or hastags. Simple and 
                straight to the point.
                """,
            },
            {
                "role": "user",
                "content": f"Please generate a tweet based on this script {script}",
            },
        ],
    )

    return completion.choices[0].message.content


def write_script(tweet: Tweet, replies: List[Tweet], prompt: str) -> List[dict]:
    replies_text = ""
    for t in replies:
        replies_text += f"Tweet author: {t.user_at}\n"
        replies_text += f"Tweet content: {t.content}\n"
        replies_text += f"Likes: {t.likes}\n\n"

    tweets_blob = f"""
Tweet user display name: {tweet.user_display_name}
Tweet user at: {tweet.user_at}
Tweet content: {tweet.content}
Likes: {tweet.likes}
Retweets: {tweet.retweets}
Additional context: {tweet.context}

{f'Reference tweet author: {tweet.ref_user_display_name}' if tweet.ref_user_display_name else ''}
{f'Reference tweet user at: {tweet.ref_user_at}' if tweet.ref_user_at else ''}
{f'Reference tweet content: {tweet.ref_content}' if tweet.ref_content else ''}
{f'Reference tweet image: {tweet.ref_image}' if tweet.ref_image else ''}
{f'Reference tweet image content: {tweet.ref_image_content}' if tweet.ref_image_content else ''}

---------

Replies:
{replies_text}

#User Prompt:
{prompt}
"""

    user_prompt = (
        f"Please generate a script based on the following tweets:\n\n{tweets_blob}"
    )

    completion = openai_client.chat.completions.create(
        model="gpt-4.5-preview",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_SCRIPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        max_tokens=500,
    )

    parsed = json.loads(completion.choices[0].message.content)
    return parsed["script"]
