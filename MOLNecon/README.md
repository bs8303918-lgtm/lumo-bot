# MOLNecon: YouTube Shorts workspace

Daily economics shorts for **@MOLNecon**, series "Economics in 60s".

| File | What it is |
|---|---|
| [STYLE.md](STYLE.md) | The house style: colours, type, layout, motion, sound |
| [INSTRUCTIONS.md](INSTRUCTIONS.md) | The production process, step by step |
| [MOLNecon_Reference_Transcript.md](MOLNecon_Reference_Transcript.md) | Transcript of the reference video the method comes from |
| [LOG.md](LOG.md) | Every short posted (no topic repeats, numbering never breaks) |
| `style/molnstyle.py` | Style tokens + drawing helpers every short imports |
| `style/make_style_frames.py` | Renders the style board and motion test |
| `style/frames/` | Sample stills, style board, `motion_test.mp4` |
| `shorts/NN_<topic>/` | One folder per short (script, facts, voice, render) |

Rebuild the style board:

```bash
python3 MOLNecon/style/make_style_frames.py --motion
```

Needs Python 3 with Pillow and numpy, ffmpeg, and the Inter, JetBrains Mono and Noto Color Emoji
fonts.
