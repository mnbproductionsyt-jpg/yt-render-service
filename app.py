from flask import Flask, request, send_file
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, vfx
from PIL import Image
import numpy as np
import requests, io, tempfile

app = Flask(__name__)

def fetch_bytes(url):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content

def imageclip_from_url(url, duration, size):
    data = fetch_bytes(url)
    img = Image.open(io.BytesIO(data)).convert("RGB").resize(size)
    arr = np.array(img)
    clip = ImageClip(arr).set_duration(duration)
    return clip

def ken_burns(clip, mode="in"):
    if mode == "in":
        return clip.fx(vfx.resize, lambda t: 1.0 + 0.05 * (t/clip.duration))
    elif mode == "out":
        return clip.fx(vfx.resize, lambda t: 1.05 - 0.05 * (t/clip.duration))
    return clip

@app.post("/render")
def render():
    data = request.get_json()
    w = int(data.get("size", {}).get("w", 1920))
    h = int(data.get("size", {}).get("h", 1080))
    fps = int(data.get("fps", 30))
    scenes = data["scenes"]  # [{image_url, seconds, kenburns}]
    audio_url = data["audio_url"]

    clips = []
    for s in scenes:
        c = imageclip_from_url(s["image_url"], float(s["seconds"]), (w, h))
        kb = s.get("kenburns")
        if kb in ["in","out"]:
            c = ken_burns(c, kb)
        clips.append(c)

    video = concatenate_videoclips(clips, method="compose")

    audio_bytes = fetch_bytes(audio_url)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as af:
        af.write(audio_bytes)
        audio_path = af.name

    audio = AudioFileClip(audio_path)
    video = video.set_audio(audio).set_fps(fps)

    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    outpath = tmp.name
    tmp.close()
    video.write_videofile(outpath, codec="libx264", audio_codec="aac", fps=fps, preset="medium", threads=2)
    return send_file(outpath, mimetype="video/mp4", as_attachment=True, download_name="video.mp4")
