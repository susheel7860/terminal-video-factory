#!/usr/bin/env python3
"""video factory — scene JSON in, finished vertical Short out. No human recording.

Usage: .venv/bin/python factory.py scenes/invoice.json
Output: out/<slug>.mp4  (1080x1920, AI narration, burned captions)
"""
import json, math, os, shlex, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.join(HERE, ".venv", "bin")
VOICE = os.path.join(HERE, "voices", "en_US-lessac-medium.onnx")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
BG = "0x0e1311"          # dark green-black, matches brand
ACCENT = "0x6fd3a8"      # emerald

def run(cmd, **kw):
    subprocess.run(cmd, check=True, **kw)

def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())

def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"

def main(scene_path):
    scene = json.load(open(scene_path))
    slug = scene["slug"]
    work = tempfile.mkdtemp(prefix=f"{slug}-")
    outdir = os.path.join(HERE, "out"); os.makedirs(outdir, exist_ok=True)

    # 1) narration: one wav per line -> exact caption timings, then concat
    segs, t = [], 0.0
    for i, line in enumerate(scene["narration"]):
        wav = os.path.join(work, f"seg{i}.wav")
        run([os.path.join(VENV, "piper"), "-m", VOICE, "-f", wav],
            input=line.encode(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        d = dur(wav)
        segs.append((line, t, t + d, wav))
        t += d + 0.35                       # breath between lines
    narration = os.path.join(work, "narration.wav")
    concat = os.path.join(work, "concat.txt")
    with open(concat, "w") as f:
        for _, a, b, wav in segs:
            f.write(f"file '{wav}'\n")
            f.write(f"duration {b - a + 0.35:.3f}\n")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", concat,
         "-af", "apad=pad_dur=0.6", narration])
    total = dur(narration)

    subs = os.path.join(work, "subs.srt")
    with open(subs, "w") as f:
        for i, (line, a, b, _) in enumerate(segs, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(min(b + 0.3, total))}\n{line}\n\n")

    # 2) terminal demo: typed + executed inside asciinema, rendered by agg
    play = os.path.join(work, "play.sh")
    with open(play, "w") as f:
        f.write("#!/usr/bin/env bash\nset -e\n")
        f.write(f"cd {shlex.quote(scene['demo_dir'])}\n")
        f.write("type_cmd() { printf '\\033[1;32m$\\033[0m '; "
                "python3 -c \"import sys,time\nfor c in sys.argv[1]:\n print(c,end='',flush=True); time.sleep(0.035)\nprint()\" \"$1\"; }\n")
        for cmd in scene["demo_commands"]:
            f.write(f"type_cmd {shlex.quote(cmd)}\nsleep 0.4\n{cmd}\nsleep 0.9\n")
    cast = os.path.join(work, "demo.cast")
    run([os.path.join(VENV, "asciinema"), "rec", "-q", "--overwrite",
         "-c", f"bash {play}", cast],
        env={**os.environ, "COLUMNS": "64", "LINES": "24"})
    gif = os.path.join(work, "demo.gif")
    run([os.path.join(HERE, "agg"), "--cols", "64", "--rows", "24", "--font-size", "28",
         "--theme", "asciinema", cast, gif], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    termvid = os.path.join(work, "term.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-i", gif, "-movflags", "faststart",
         "-pix_fmt", "yuv420p", "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", termvid])

    # 3) compose: stretch terminal video across narration, title + hook + captions
    stretch = total / max(dur(termvid), 0.1)
    title = scene["title"].replace(":", r"\:").replace("'", r"\'")
    hook = scene["hook"].replace(":", r"\:").replace("'", r"\'")
    final = os.path.join(outdir, f"{slug}.mp4")
    vf = (
        f"[1:v]setpts={stretch:.4f}*PTS,scale=1020:-2[term];"
        f"[0:v][term]overlay=(W-w)/2:430:shortest=0[base];"
        f"[base]drawtext=fontfile={FONT}:text='{title}':fontsize=58:fontcolor=white:"
        f"x=(w-text_w)/2:y=170:line_spacing=12,"
        f"drawtext=fontfile={FONT}:text='{hook}':fontsize=44:fontcolor={ACCENT}:"
        f"x=(w-text_w)/2:y=300,"
        f"subtitles={subs}:force_style='FontName=DejaVu Sans,FontSize=15,Bold=1,"
        f"PrimaryColour=&HFFFFFF&,OutlineColour=&H80000000&,BorderStyle=1,Outline=2,"
        f"Alignment=2,MarginV=55'[v]"
    )
    run(["ffmpeg", "-y", "-v", "error",
         "-f", "lavfi", "-i", f"color=c={BG}:s=1080x1920:d={total:.2f}:r=30",
         "-i", termvid, "-i", narration,
         "-filter_complex", vf, "-map", "[v]", "-map", "2:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "192k", "-shortest", final])
    print(f"DONE {final}  ({dur(final):.1f}s)")

if __name__ == "__main__":
    main(sys.argv[1])
