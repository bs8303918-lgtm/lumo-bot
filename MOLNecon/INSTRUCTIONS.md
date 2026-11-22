# MOLNecon Shorts: production instructions

Channel: **MOLNecon** (@MOLNecon), "for everyone learning economics on their own".
One short per day. Every short is approved by Nursultan before upload.
The look is defined in [STYLE.md](STYLE.md); this file is the process.

Method source: the measured study in "How to Make Viral Animated Shorts Using Claude"
([transcript](MOLNecon_Reference_Transcript.md), github.com/mromidev/claude-animated-shorts, MIT).
We copy its **numbers**, never its stories or characters.

## What the reference video teaches

- **Script:** first line is a strange fact, no intro. Then 3-5 beats that escalate, one
  "Wait, why...?" question, then "You see," and an everyday example that explains it.
  Ends on a short twist line. ~3.7 words/s, almost no pauses.
- **Picture:** never fully still. The camera slowly pushes in all the time; moves glide over
  ~1 s (≈23 frames), never jump. Almost no hard cuts. Strong colour, no pure black, warm light,
  blue shadows. Every sentence is shown literally on screen.
- **Method:** measure the videos with numbers instead of opinions. When several agents work in
  parallel, split the files, not just the jobs.

## Pipeline (per short)

1. **Topic and facts.** One surprising, TRUE economics story with visible cause and effect
   (year, place, named person, numbers). Web-check every fact; list facts + sources at the top
   of `shorts/NN_<topic>/SCRIPT.md`. Check [LOG.md](LOG.md) so no topic repeats.
2. **Script.** 45-60 s, 170-220 words: hook (paradox, 10-16 words) → setting → 3-5 escalation
   beats → mystery question → "You see," + everyday analogy → optional "Luckily / Unluckily" →
   ironic payoff. Video ends on the last word. Write 3 hook options and pick the strongest.
   **Nursultan approves the script before anything is built.**
3. **Voice.** Kokoro TTS (kokoro-onnx), voice `am_michael`, 3.5-4 words/s, total gaps < 1 s.
   Word timings → `words.json`. Every visual change lands 0-3 frames before its word.
4. **Picture.** Rotate styles A / B / C (see STYLE.md). 1080×1920, 30 fps.
5. **Sound.** Voice untouched, music 5-10 dB under and ducked, SFX on impacts. Original or
   licensed audio only. Final loudness -14 LUFS (`loudnorm I=-14:TP=-1.5:LRA=7`).
6. **Render.** One file per scene (rawvideo → libx264 -crf 18), concat with `-c copy`, then mux
   audio. Contact sheet of the busiest still of each scene before the full render.
7. **QA (measure).** No frozen span ≥ 12 frames, no black/white frames, captions in sync,
   loudness on target, end lands on the last word. Look at the end frame + 6 mid frames.
8. **Deliver.** `MOLNecon_Short_NN_<Topic>.mp4` + title (< 60 chars, "Day N: ..." + #shorts),
   description (one line + 3-5 hashtags + Follow MOLNecon), Public, Made for kids: No,
   "altered or synthetic content" ON (AI voice). Upload only after Nursultan says yes.
9. **Log** the short in [LOG.md](LOG.md).

## Open decisions (from the planning notes)

1. **Style C runs on Nursultan's PC.** three.js + Remotion is too slow on the 2-CPU cloud
   machine (hours vs ~10 min). Styles A and B are made in the cloud.
2. **Topics:** send 5-10 economics topics, or Claude picks true stories with real numbers
   (e.g. the 10,000-bitcoin pizza, Zimbabwe hyperinflation, why tenge prices change).
3. **Captions: ON**, one word at a time (helps sound-off viewers).
4. **Upload access:** connect the Downloads folder in the Claude desktop app so the file can be
   picked in YouTube Studio.
