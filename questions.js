/* Lumbar Spine Live: lumbosacral spine and pelvis review.
   Three question types: identify the highlighted structure, name the muscle that originates on the
   highlighted bony aspect, and name the motion in a 5-second looping animation.
   Every image is rendered from the meshes of the ArtiSynth lumbosacral spine model
   (github.com/RemusR9/artisynth_lumbosacralSpineModel; Remus et al., PLoS ONE 2021, BSD-3-Clause).
   The highlight in each picture is computed from that geometry (facet surfaces, FE disc parts and
   ligament attachment data come straight from the model files). See spine_render/ for the scripts.
   correct = 0-based index into options. */
window.MQ_QUESTIONS = [
  {
    q: "Identify the highlighted part of the L3 vertebra.",
    img: "img/sp.jpg", cap: "L2–L4, seen from behind and slightly to the left",
    alt: "Three lumbar vertebrae seen from behind; the midline bony projection pointing backward from L3 is orange.",
    options: ["Transverse process", "Spinous process", "Pedicle", "Superior articular process"],
    correct: 1
  },
  {
    q: "Which muscle originates from the highlighted landmark?",
    img: "img/asis.jpg", cap: "Pelvis and lower lumbar spine · left side highlighted",
    alt: "Front view of the pelvis; the front tip of the left iliac crest is orange.",
    options: ["Rectus femoris", "Iliacus", "Sartorius", "Gluteus medius"],
    correct: 2
  },
  {
    q: "What motion is occurring at the lumbar spine?",
    img: "img/flex.gif", cap: "5-second loop · faint outline = starting position",
    alt: "Animation, left side view: the lumbar vertebrae tip forward and the lumbar curve flattens and reverses, then return.",
    options: ["Flexion", "Extension", "Right lateral flexion", "Left rotation"],
    correct: 0
  },
  {
    q: "Identify the highlighted joints between L4 and L5.",
    img: "img/facet.jpg", cap: "L3–S1, seen from behind",
    alt: "Back view of the lower lumbar spine; the paired joints between the articular processes of L4 and L5 are orange on both sides.",
    options: ["Intervertebral disc joints", "Uncovertebral joints", "Sacroiliac joints", "Zygapophyseal (facet) joints"],
    correct: 3
  },
  {
    q: "Which muscle originates from the highlighted surfaces?",
    img: "img/psoas.jpg", cap: "L1–L5 and pelvis, seen from the front-left",
    alt: "Lumbar spine from the front-left; the left sides of the L1–L5 vertebral bodies and the discs between them are orange.",
    options: ["Quadratus lumborum", "Psoas major", "Rectus abdominis", "Iliacus"],
    correct: 1
  },
  {
    q: "What motion is occurring at the lumbar spine?",
    img: "img/latflex.gif", cap: "5-second loop · faint outline = starting position",
    alt: "Animation, back view: the lumbar spine bends sideways toward the patient's right (viewer's right), then returns.",
    options: ["Left lateral flexion", "Right rotation", "Right lateral flexion", "Extension"],
    correct: 2
  },
  {
    q: "Identify the highlighted part of the L4–L5 intervertebral disc.",
    img: "img/np.jpg", cap: "L4–L5 disc resting on L5, front-left quarter cut away",
    alt: "An intervertebral disc on top of L5 with a quarter cut away; the soft central core is orange, surrounded by blue concentric rings.",
    options: ["Nucleus pulposus", "Annulus fibrosus", "Vertebral endplate", "Posterior longitudinal ligament"],
    correct: 0
  },
  {
    q: "Which muscle group originates from the highlighted landmark?",
    img: "img/isch.jpg", cap: "Pelvis, seen from behind and below · left side highlighted",
    alt: "Back view of the pelvis from slightly below; the lowest, rearmost part of the left ischium is orange.",
    options: ["Rectus femoris", "Gluteus medius", "Piriformis", "Hamstrings"],
    correct: 3
  },
  {
    q: "Identify the highlighted ligament (orange fibres).",
    img: "img/lf.jpg", cap: "L2–L5 cut down the midline · ligament fibres from the model",
    alt: "Midline section of the lumbar spine seen from the left; orange fibres run between the laminae at the back of the spinal canal; other ligaments are cream.",
    options: ["Posterior longitudinal ligament", "Ligamentum flavum", "Interspinous ligament", "Supraspinous ligament"],
    correct: 1
  },
  {
    q: "What motion is occurring at the pelvis?",
    img: "img/apt.gif", cap: "5-second loop · faint outline = starting position",
    alt: "Animation, left side view: the pelvis rotates forward about the hips while the lumbar curve deepens and the top of the spine stays upright, then returns.",
    options: ["Posterior pelvic tilt", "Lateral pelvic tilt (hip hike)", "Anterior pelvic tilt", "Pelvic rotation"],
    correct: 2
  }
];
