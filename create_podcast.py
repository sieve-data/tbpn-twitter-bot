import io
import os
import random
import subprocess
import tempfile
from typing import List, Dict, Literal, TypedDict
import boto3
import requests
import sieve
import elevenlabs
from video_clips import clips
from mutagen.mp3 import MP3
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import dotenv

dotenv.load_dotenv()


class Dialogue(TypedDict):
    dialogue: str
    speaker: Literal["jordi", "john"]


eleven_labs_api_key = os.getenv("ELEVEN_LABS_API_KEY")

jordi_voice_id = "Tw6MHQ70AkrkqFDf75BN"
john_voice_id = "qMH3IpwT6hc2977abay7"

aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
region_name = os.getenv("AWS_REGION_NAME")
bucket_name = os.getenv("AWS_BUCKET_NAME")

session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name=region_name,
)
s3 = session.client("s3")


def escape_for_drawtext(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace(":", "\\:")
    text = text.replace("'", "\\'")
    text = text.replace('"', "")  # remove double quotes entirely if not essential
    return text


def download_url(url: str, path: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if not 200 OK
    with open(path, "wb") as f:
        f.write(response.content)


def upload_s3_bytes(
    key: str, file_name: str, data: bytes, type: Literal["video", "audio"] = "video"
) -> str:
    object_name = f"{key}/{file_name}"
    try:
        headers = {
            "ContentType": "video/mp4" if type == "video" else "audio/mpeg",
        }
        s3.upload_fileobj(io.BytesIO(data), bucket_name, object_name, ExtraArgs=headers)
        # print(f"File uploaded successfully to {bucket_name}/{object_name}")
        url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{object_name}"
        print(url)
        return url
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return None


@sieve.function(
    name="generate-podcast",
    python_packages=["boto3", "elevenlabs", "mutagen", "requests", "python-dotenv"],
    system_packages=["ffmpeg"],
)
def make_podcast(script: List, title: str):
    script: List[Dialogue] = script
    lipsync_fn = sieve.function.get("sieve/lipsync")

    # ---------- phase 1: AUDIO (5-way concurrency) ----------
    def gen_audio(idx: int, seg: Dialogue):
        """Text→speech → duration → S3 → return audio metadata."""
        local_client = elevenlabs.ElevenLabs(
            api_key=eleven_labs_api_key
        )  # thread-local
        tts = local_client.text_to_speech.convert(
            text=seg["dialogue"],
            voice_id=john_voice_id if seg["speaker"] == "john" else jordi_voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
            voice_settings={
                "stability": 0.1,
                "similarity_boost": 0.8,
            },
        )
        audio_bytes = b"".join(tts)
        duration = MP3(io.BytesIO(audio_bytes)).info.length
        file_name = f"{uuid.uuid4()}.mp3"
        url = upload_s3_bytes("podcast-audios", file_name, audio_bytes)
        return {
            "idx": idx,
            "speaker": seg["speaker"],
            "audio_url": url,
            "duration": duration,
        }

    audio_meta: List[Dict] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = [pool.submit(gen_audio, i, seg) for i, seg in enumerate(script)]
        for f in as_completed(futs):
            audio_meta.append(f.result())

    audio_meta.sort(key=lambda x: x["idx"])  # restore original order
    print(audio_meta)

    # ---------- phase 2: VIDEO / LIPSYNC (10-way concurrency) ----------
    def find_clip(speaker: str, dur: float, clip_idx: int) -> Dict:
        """Pick a clip long enough for the given speaker."""
        visited: set[int] = set()
        while True:
            idx = random.randrange(len(clips))
            clip = clips[idx]
            if (
                idx not in visited
                and clip["speaker"] == speaker
                and clip["duration"] >= dur
            ):
                return clip
            visited.add(idx)
            if len(visited) == len(clips):
                raise RuntimeError("No suitable clip found")

    def gen_video(meta: Dict, clip_idx: int):
        """Lipsync chosen clip with uploaded audio."""
        clip = find_clip(meta["speaker"], meta["duration"], clip_idx)
        base_clip = sieve.File(url=clip["url"])
        audio_file = sieve.File(url=meta["audio_url"])
        out: sieve.File = lipsync_fn.run(
            base_clip,
            audio_file,
            backend="sync-2.0",
            # backend="musetalk",
            enable_multispeaker=False,
            enhance="default",
            check_quality=False,
            downsample=False,
            cut_by="audio",
        )
        print("generating: ", meta)
        return {"idx": meta["idx"], "path": out.path}

    video_meta: List[Dict] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = [pool.submit(gen_video, m, i) for i, m in enumerate(audio_meta)]
        for f in as_completed(futs):
            video_meta.append(f.result())

    video_meta.sort(key=lambda x: x["idx"])  # restore original order
    result_videos = [v["path"] for v in video_meta]

    # ---------- phase 3: CONCATENATE ----------
    with tempfile.TemporaryDirectory() as td:
        # Download the overlay image into the temporary directory
        overlay_image_path = os.path.join(td, "overlay.png")
        print(f"Downloading overlay to: {overlay_image_path}")
        download_url(
            "https://inpaint-results.s3.us-east-2.amazonaws.com/tbpncover3.png",
            overlay_image_path,
        )  # Placeholder

        # First concatenate the videos
        concat_txt_path = os.path.join(td, "concat.txt")
        with open(concat_txt_path, "w") as fp:
            for (
                video_path
            ) in result_videos:  # Assuming result_videos contains accessible paths
                fp.write(
                    f"file '{os.path.abspath(video_path)}'\n"
                )  # Use abspath for clarity with -safe 0

        temp_stitched_path = os.path.join(td, "temp_stitched.mp4")
        print(f"Concatenating videos to: {temp_stitched_path}")
        subprocess.run(
            [
                "ffmpeg",
                "-y",  # Overwrite output files without asking
                "-f",
                "concat",
                "-safe",
                "0",  # Allows absolute paths in concat_txt
                "-i",
                concat_txt_path,
                "-c",
                "copy",  # Assumes compatible codecs in result_videos
                temp_stitched_path,
            ],
            check=True,  # Raises CalledProcessError on failure
            capture_output=True,
            text=True,  # For better debugging
        )

        # Now add the overlay
        final_stitched_path = os.path.join(td, "stitched_output.mp4")
        print(f"Adding overlay, outputting to: {final_stitched_path}")

        text = escape_for_drawtext(title)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                temp_stitched_path,
                "-i",
                overlay_image_path,
                "-filter_complex",
                f"[0:v][1:v]overlay=0:0:format=auto,drawtext=text='{text}':fontcolor=black:fontsize=48:x=185:y=H-th-180,format=yuv420p[out]",
                "-map",
                "[out]",
                "-map",
                "0:a?",
                "-c:a",
                "aac",
                "-shortest",
                final_stitched_path,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        # Upload to S3 using file path for better memory management
        with open(final_stitched_path, "rb") as f:
            video_bytes = f.read()

        # Upload to S3 from bytes
        s3_bucket = "podcast-audios"
        s3_key = f"{uuid.uuid4()}.mp4"
        print(f"Uploading to S3 bucket {s3_bucket} as {s3_key}")
        final_url = upload_s3_bytes(s3_bucket, s3_key, video_bytes)
        print(f"Final URL: {final_url}")
        return {"segments": result_videos, "stitched_video": final_url}
