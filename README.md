# Terminal Video Factory

Turns a small JSON file into a finished, captioned, narrated vertical video of a **real terminal
session** — no screen recorder, no microphone, no video editor.

```bash
python factory.py scenes/invoice.json
# → out/invoice-short-01.mp4   (1080x1920, ~25s)
```

I built it because I wanted to publish a daily technical short without ever filming anything, and
because the interesting part of a demo is the terminal, not a face.

## How it works

```
scene.json
   ├── demo_commands ──► asciinema records a REAL shell session (the commands actually run)
   │                        └── agg renders the cast to video
   ├── narration ──────► piper (local neural TTS) synthesises the voice track, line by line
   │                        └── per-line audio durations become the caption timings
   └── title / hook ───► ffmpeg composes: title card, hook, terminal, burned-in captions, audio
```

The commands genuinely execute — the output on screen is real program output, not a mockup. If the
demo breaks, the video breaks, which is the correct failure mode for a technical demo.

Captions are timed from the *measured* duration of each synthesised audio line rather than a
speech-recognition pass over the finished track, so they can't drift out of sync and there's no
transcription step to get wrong.

Everything runs locally and costs nothing per video: piper is an offline Apache-2.0 TTS model, and
ffmpeg does the rest.

## A scene file

```json
{
  "slug": "invoice-short-01",
  "title": "AI does invoice data entry",
  "hook": "10 min per invoice → 4 seconds",
  "narration": ["This business typed invoice data by hand.", "..."],
  "demo_dir": "/path/to/your/demo",
  "demo_commands": ["ls invoices/", "./invoice2csv.sh invoices output.csv"]
}
```

## Setup

```bash
python3 -m venv .venv && .venv/bin/pip install asciinema piper-tts
# agg (terminal→video renderer)
curl -sL https://github.com/asciinema/agg/releases/latest/download/agg-x86_64-unknown-linux-gnu -o agg && chmod +x agg
# a piper voice
mkdir voices && curl -sL https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx -o voices/en_US-lessac-medium.onnx
curl -sL https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json -o voices/en_US-lessac-medium.onnx.json
```

Also needs `ffmpeg` and a DejaVu Sans font on the system.

## Note on publishing

If you post the output anywhere with synthetic-media disclosure rules (YouTube, for one), tick the
altered/synthetic content box — the narration is a TTS model.

## Licence

MIT — see [LICENSE](LICENSE).

---
Built by [Susheel Pandey](https://github.com/susheel7860).
