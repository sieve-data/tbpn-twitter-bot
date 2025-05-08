import json
import io
import os
from typing import Literal
import dotenv
import requests
import boto3
from video_clips_raw import video_clips_raw
from tqdm import tqdm
from create_podcast import upload_s3_bytes


# upload video clips to s3
def process_clips(
    video_clips, s3_key_prefix="podcast-videos", output_path="clips_output.json"
):
    results = []

    for clip in tqdm(video_clips):
        try:
            url = clip["data"][0]["url"]
            duration = clip["data"][1]["duration"]

            response = requests.get(url)
            if response.status_code != 200:
                print(f"Failed to download video: {url}")
                continue

            file_name = url.split("/")[-1].split("?")[0]
            s3_url = upload_s3_bytes(
                s3_key_prefix, file_name, response.content, "video"
            )

            if s3_url:
                results.append({"url": s3_url, "duration": duration})

        except Exception as e:
            print(f"Error processing clip: {e}")

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Output saved to {output_path}")


# Example usage
process_clips(video_clips_raw)
