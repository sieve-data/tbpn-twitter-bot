import os
import random
from typing import Dict, Literal, TypedDict
import uuid
import elevenlabs
import sieve
from mutagen.mp3 import MP3
import io
from video_clips import clips
from dotenv import load_dotenv

load_dotenv()

eleven_labs_api_key = os.getenv("ELEVEN_LABS_API_KEY")
jordi_voice_id = "Tw6MHQ70AkrkqFDf75BN"
john_voice_id = "qMH3IpwT6hc2977abay7"


class Dialogue(TypedDict):
    dialogue: str
    speaker: Literal["jordi", "john"]


def gen_audio(idx: int, seg: Dialogue):
    """Text→speech → duration → S3 → return audio metadata."""
    local_client = elevenlabs.ElevenLabs(api_key=eleven_labs_api_key)  # thread-local
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
    audio_path = file_name
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # Return the result
    return {
        "idx": idx,
        "speaker": seg["speaker"],
        "audio_path": audio_path,
        "duration": duration,
    }


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
    lipsync_fn = sieve.function.get("sieve/lipsync")
    clip = find_clip(meta["speaker"], meta["duration"], clip_idx)
    base_clip = sieve.File(url=clip["url"])
    audio_file = sieve.File(path=meta["audio_path"])
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
