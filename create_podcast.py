import os
import subprocess
import tempfile
from typing import List, Dict, Literal, TypedDict
import requests
from podcast_utils import gen_audio, gen_video
from concurrent.futures import ThreadPoolExecutor, as_completed
import dotenv

dotenv.load_dotenv()


class Dialogue(TypedDict):
    dialogue: str
    speaker: Literal["jordi", "john"]


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


def make_podcast(script: List, title: str):
    script: List[Dialogue] = script
    audio_meta: List[Dict] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futs = [pool.submit(gen_audio, i, seg) for i, seg in enumerate(script)]
        for f in as_completed(futs):
            audio_meta.append(f.result())

    audio_meta.sort(key=lambda x: x["idx"])  # restore original order
    print(audio_meta)

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
        final_stitched_path = "final_stitched_output.mp4"
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

        return final_stitched_path
