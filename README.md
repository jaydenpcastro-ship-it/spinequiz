# Lumbar Spine Live

*Spot the structure, name the muscle, call the motion: a lumbosacral spine and pelvis review*

A live, Kahoot-style multiplayer quiz. Students join from their own phones
(no account, no sign-in, no app): open the link or scan the host's QR code, type a name, and answer.

Every picture comes from the 3D bone, disc and ligament geometry of the
[ArtiSynth lumbosacral spine model](https://github.com/RemusR9/artisynth_lumbosacralSpineModel)
(Remus et al., *PLoS ONE* 2021, built from the Visible Human Project male), rendered in Blender.
The orange highlight in each picture is computed from the model geometry: the facet joints use the
model's own facet surfaces and capsular ligament fibres, the nucleus pulposus is the model's FE nucleus,
and the ligament fibres come from the model's ligament attachment files.

## The 10 questions

| # | Type | Picture | Answer |
|---|------|---------|--------|
| 1 | Identify the region | L2–L4, posterior oblique | Spinous process (L3) |
| 2 | Muscle origin | Pelvis, anterior view | Sartorius (ASIS) |
| 3 | Motion (5 s GIF) | Lumbopelvic model, left side view | Lumbar flexion |
| 4 | Identify the joints | L3–S1, posterior view | Zygapophyseal (facet) joints, L4–L5 |
| 5 | Muscle origin | L1–L5, anterior-left oblique | Psoas major (sides of the vertebral bodies and discs) |
| 6 | Motion (5 s GIF) | Posterior view | Right lateral flexion |
| 7 | Identify the disc part | L4–L5 disc, quarter cut away | Nucleus pulposus |
| 8 | Muscle origin | Pelvis, posterior view from below | Hamstrings (ischial tuberosity) |
| 9 | Identify the ligament | L2–L5 mid-sagittal section | Ligamentum flavum |
| 10 | Motion (5 s GIF) | Left side view | Anterior pelvic tilt |

- Motion GIFs loop every 5.0 s (100 frames at 20 fps). A faint outline shows the starting position.
  Each lumbar level rotates about the centre of the disc below it, with typical per-level ranges
  (White & Panjabi): flexion 8/10/12/13/9° from L1–2 to L5–S1, lateral flexion 6/6/8/6/3°.
  Anterior pelvic tilt is 15° about the hip axis (acetabulum sphere fit), and the lumbar spine extends
  by the same amount so the trunk stays upright.
- Side markers: **L/R** on front and back views, **Anterior/Posterior** arrows on side views.
- 5-second reading window on each question, then a 20-second answer timer (configurable, 10-60 s);
  speed-weighted scoring counts from when answers open.
- Host-only Pause / Resume (button, or Space / P). Every 5th wrong answer: jump scare plus error buzzer.
- Host lobby music: "Back at It" by Dyalla (Epidemic Sound), played through YouTube's official embedded
  player on the host screen only.
- Live leaderboard, final podium, automatic winner.

Live site: <https://spinequiz.vercel.app>

## Files

- `index.html`: the whole app (host + player screens)
- `questions.js`: the question set (`q`, `img`, `cap`, `alt`, `options`, `correct` = 0-based index)
- `img/`: renders (`.jpg`) and motion loops (`.gif`)
- `render/`: the Blender/Python scripts that made `img/` (`stills.py`, `motion.py`, `post.py`, `spine_lib.py`)
- `config.js`: Supabase project URL + publishable key
- `schema.sql`: database tables and policies (run once in the Supabase SQL Editor)

Built from the same template as `gaitquiz` / `hipquiz`, on the same Supabase project (games are kept
apart by their 4-letter room codes). Browser storage prefix: `lsl_`.

## Model credit and licence

Bone, disc and ligament geometry: ArtiSynth lumbosacral spine model,
Remus R, Lipphaus A, Neumann M, Bender B (2021) *Calibration and validation of a novel hybrid model of the
lumbosacral spine in ArtiSynth – The passive structures.* PLoS ONE 16(4): e0250456.
<https://doi.org/10.1371/journal.pone.0250456>

Copyright (c) 2021, Robin Remus. All rights reserved. Used under the BSD 3-Clause License; the full licence
text is in [`render/LICENSE-artisynth-model.txt`](render/LICENSE-artisynth-model.txt). The model's authors
have not reviewed or endorsed this quiz.
