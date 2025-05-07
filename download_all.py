import requests
from video_clips import clips


def download_url(url: str, path: str):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url)
    response.raise_for_status()  # Raise an error if not 200 OK
    with open(path, "wb") as f:
        f.write(response.content)


for clip in clips:
    video = clip["url"]
    path = "vids/" + video.split("/")[-1]
    download_url(video, path)
