import re
import subprocess
import json, os, tempfile, urllib.request, cv2
import numpy as np
import requests
import torch, clip
from PIL import Image
import video_clips_raw

# ---------- config ----------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
REF_IMAGES = {"jordi": "jordi_scene.png", "john": "john_scene.png"}
OUTFILE = "clips_with_speaker.json"
# ----------------------------

# ---- 1. load CLIP once -----
model, preprocess = clip.load(
    "ViT-B/32", device=DEVICE
)  # assumes you fixed the pip package issue


@torch.no_grad()
def embed(img: Image.Image):
    return model.encode_image(preprocess(img).unsqueeze(0).to(DEVICE)).float()


ref_embs = {k: embed(Image.open(v)) for k, v in REF_IMAGES.items()}


# ---- 2. util: fetch first frame quickly ----
MOOV = re.compile(b"moov")
CHUNK = 256_000  # 256 KB
MAX = 20_000_000  # 20 MB safety cap


def first_frame(url: str) -> Image.Image:
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        url,  # remote input
        "-frames:v",
        "1",  # only the very first frame
        "-f",
        "image2pipe",
        "-pix_fmt",
        "rgb24",
        "-vcodec",
        "rawvideo",
        "-",
    ]  # raw bytes to stdout
    out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    # width/height? we can query ffprobe first, but easier:
    # read as JPEG instead to let Pillow decode size automatically:
    # cmd = ["ffmpeg","-v","error","-i",url,"-frames:v","1","-f","image2pipe","-vcodec","mjpeg","-"]
    # then return Image.open(BytesIO(out))
    w, h = 1920, 1080  # hard-code if you know it, otherwise probe
    frame = np.frombuffer(out, np.uint8).reshape((h, w, 3))

    result = Image.fromarray(frame)
    return result


# ---- 3. main loop ----
def tag_clip(clip_obj: dict) -> dict:
    try:
        print("getting frame")
        frame = first_frame(clip_obj["url"])
        print("embedding")
        clip_emb = embed(frame)
        # cosine similarity to each reference speaker
        sims = {
            k: torch.nn.functional.cosine_similarity(clip_emb, v).item()
            for k, v in ref_embs.items()
        }
        # print(clip_obj.url)
        print(sims)
        best_speaker, best_score = max(sims.items(), key=lambda kv: kv[1])
        clip_obj["speaker"] = best_speaker if best_score > 0.75 else "wide"
        # clip_obj["similarity"] = {k: round(v, 4) for k, v in sims.items()}
    except Exception as e:
        clip_obj["speaker"] = "unknown"
        clip_obj["error"] = str(e)
    return clip_obj


# your original list


annotated = [tag_clip(c) for c in video_clips_raw.clips_raw]

with open(OUTFILE, "w") as f:
    json.dump(annotated, f, indent=2)

print(f"Wrote {OUTFILE}")
