"""5-second looping motion clips of the lumbopelvic model.
blender -b -P motion.py -- <flex|latflex|apt> [preview|final]
Renders frames/<name>/f####.png (RGBA) + frames/<name>/meta.json.

Each lumbar level pivots about the centre of the disc below it (nucleus centroid
from the FE mesh). Discs are skinned between the two neighbouring vertebrae.
Per-level ranges (one direction) follow typical in-vivo lumbar values
(White & Panjabi): flexion 8/10/12/13/9 deg (L1-2 ... L5-S1),
lateral flexion 6/6/8/6/3 deg. Anterior pelvic tilt: 15 deg about the hip axis
with the lumbar spine extending by the same total so the trunk stays upright."""
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import numpy as np
from mathutils import Vector, Matrix
import spine_lib as L

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NAME = argv[0] if argv else "flex"
QUAL = argv[1] if len(argv) > 1 else "preview"
FPS, SECS = 20, 5.0
NF = int(FPS * SECS)
W, H = (600, 600) if QUAL == "final" else (300, 300)
SAMPLES = 64 if QUAL == "final" else 12
ONLY = [int(a) for a in argv[2].split(",")] if len(argv) > 2 else None
OUT = os.path.join(HERE, "frames" if QUAL == "final" else "preview", NAME)
os.makedirs(OUT, exist_ok=True)

sc = L.reset()
L.setup_render(sc, W, H, SAMPLES)
M_BONE = L.mask_material("bone")
M_DISC = L.principled("disc", L.DISC_COL, rough=0.5)

SEG = [("L5", "L51"), ("L4", "L45"), ("L3", "L34"), ("L2", "L23"), ("L1", "L12")]  # vertebra, disc below
FLEX = {"L1": 8, "L2": 10, "L3": 12, "L4": 13, "L5": 9}      # deg at the disc below each vertebra
LATF = {"L1": 6, "L2": 6, "L3": 8, "L4": 6, "L5": 3}
APT = 15.0
APT_SHARE = {"L5": 0.30, "L4": 0.25, "L3": 0.20, "L2": 0.15, "L1": 0.10}


def hip_centre(pel):
    """Sphere fit to the left acetabulum, mirrored -> midpoint of both hip centres."""
    P = L.verts_np(pel); N = L.normals_np(pel)
    sel = (P[:, 1] > 0.055) & (P[:, 1] < 0.115) & (P[:, 2] > -0.13) & (P[:, 2] < -0.06) & \
          (P[:, 0] > -0.03) & (P[:, 0] < 0.055) & (N[:, 1] > 0.2)   # cup surface faces laterally
    Q = P[sel]
    A = np.c_[2 * Q, np.ones(len(Q))]
    b = (Q ** 2).sum(1)
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    c = sol[:3]; r = math.sqrt(sol[3] + c.dot(c))
    print("ACETABULUM fit: n=%d centre(mm)=%s r=%.1f mm" % (len(Q), np.round(c * 1000, 1), r * 1000))
    return Vector((c[0], 0.0, c[2])), r


# ---------------------------------------------------------------- scene
obs = {}
for lv in L.LEVELS:
    ob = L.load_vertebra(lv); L.assign(ob, M_BONE); L.set_mask(ob, np.zeros(len(ob.data.vertices)))
    obs[lv] = ob
pel = L.load_bone("Pelvis"); L.assign(pel, M_BONE); L.set_mask(pel, np.zeros(len(pel.data.vertices)))
hjc, hr = hip_centre(pel)
if not (0.018 < hr < 0.035):
    # Bell et al. regression from the ASIS as a fallback
    hjc = Vector((0.001, 0.0, -0.096))
    print("ACETABULUM fit rejected; using regression", hjc)
discs = {}
for d in L.DISCS:
    v, f, _ = L.fe_surface(L.disc_parts(d))
    ob = L.mesh_object(d, v, f, smooth=False); L.fix_normals(ob); L.assign(ob, M_DISC)
    discs[d] = ob

# ---------------------------------------------------------------- rig
arm_d = bpy.data.armatures.new("Rig")
arm = bpy.data.objects.new("Rig", arm_d)
sc.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
eb = arm_d.edit_bones
root = eb.new("pelvis"); root.head = hjc; root.tail = hjc + Vector((0, 0, 0.03)); root.roll = 0
prev = root
for lv, dz in SEG:
    b = eb.new(lv)
    b.head = L.disc_center(dz); b.tail = b.head + Vector((0, 0, 0.03)); b.roll = 0
    b.parent = prev; b.use_connect = False
    prev = b
bpy.ops.object.mode_set(mode='OBJECT')


def bind(ob, weights):
    """weights: {bone: array or 1.0}"""
    n = len(ob.data.vertices)
    for bone, w in weights.items():
        vg = ob.vertex_groups.new(name=bone)
        w = np.full(n, w) if np.isscalar(w) else w
        for val in np.unique(np.round(w, 3)):
            if val <= 0:
                continue
            idx = np.nonzero(np.round(w, 3) == val)[0].tolist()
            vg.add(idx, float(val), 'REPLACE')
    md = ob.modifiers.new("arm", 'ARMATURE'); md.object = arm


for lv in ["L1", "L2", "L3", "L4", "L5"]:
    bind(obs[lv], {lv: 1.0})
bind(obs["S1"], {"pelvis": 1.0})
bind(pel, {"pelvis": 1.0})
upper_of = {"L12": "L1", "L23": "L2", "L34": "L3", "L45": "L4", "L51": "L5"}
lower_of = {"L12": "L2", "L23": "L3", "L34": "L4", "L45": "L5", "L51": "pelvis"}
for d, ob in discs.items():
    P = L.verts_np(ob)
    _, xyz = L.read_nodes(os.path.join(L.FE, f"{d}_NP.node"))
    c = xyz.mean(0)
    w_, V = np.linalg.eigh(np.cov((xyz - c).T)); n = V[:, 0] * np.sign(V[2, 0])
    h = (P - c) @ n
    t = np.clip((h - h.min()) / (h.max() - h.min()), 0, 1)
    t = t * t * (3 - 2 * t)
    bind(ob, {upper_of[d]: t, lower_of[d]: 1 - t})

pb = arm.pose.bones
for b in pb:
    b.rotation_mode = 'AXIS_ANGLE'


def set_rot(bone, axis_world, deg):
    rest = arm_d.bones[bone].matrix_local.to_3x3()
    ax = (rest.inverted() @ Vector(axis_world)).normalized()
    pb[bone].rotation_axis_angle = (math.radians(deg), ax.x, ax.y, ax.z)


def pose(s):
    """s in [0,1] = fraction of the end-range position."""
    for b in pb:
        b.rotation_axis_angle = (0, 0, 1, 0)
    if NAME == "flex":
        for lv, a in FLEX.items():
            set_rot(lv, (0, 1, 0), a * s)          # +Y rotation tips the top anteriorly
    elif NAME == "latflex":
        for lv, a in LATF.items():
            set_rot(lv, (1, 0, 0), a * s)          # +X rotation tips the top to the right (-Y)
    elif NAME == "apt":
        set_rot("pelvis", (0, 1, 0), APT * s)      # pelvis tips forward about the hip axis
        for lv, k in APT_SHARE.items():
            set_rot(lv, (0, 1, 0), -APT * k * s)   # lumbar extension keeps the trunk upright
    bpy.context.view_layer.update()


def ease(t):
    """0 -> 1 -> 0 over SECS with short holds at neutral and end range."""
    a, b, c, d = 0.35, 2.15, 2.85, 4.65
    if t < a or t >= d:
        return 0.0
    if t < b:
        x = (t - a) / (b - a)
    elif t < c:
        return 1.0
    else:
        x = 1 - (t - c) / (d - c)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def eval_points(stride=3):
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for ob in list(obs.values()) + [pel] + list(discs.values()):
        e = ob.evaluated_get(dg)
        me = e.to_mesh()
        a = np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", a)
        pts.append((np.array(e.matrix_world) [:3, :3] @ a.reshape(-1, 3)[::stride].T).T)
        e.to_mesh_clear()
    return np.vstack(pts)


# ---------------------------------------------------------------- camera
VIEWS = {"flex": ((0, -1, 0), "Left side view"),
         "apt": ((0, -1, 0), "Left side view"),
         "latflex": ((1, 0, -0.05), "Posterior view")}
vd, vname = VIEWS[NAME]
pose(0.0); p0 = eval_points()
pose(1.0); p1 = eval_points()
pose(0.0)
cam = L.camera(vd, (0, 0, 1), (0, 0, 0), 1.0)
bpy.context.view_layer.update()
centre = L.fit_camera(cam, np.vstack([p0, p1]), W / H, 0.05)
bpy.context.view_layer.update()
L.three_point(centre, vd, (0, 0, 1), dist=cam.data.ortho_scale * 2.2)

meta = {"w": W, "h": H, "fps": FPS, "frames": NF, "view": vname, "labels": {}}
if NAME == "latflex":
    meta["labels"]["L"] = L.world_to_px(cam, centre + Vector((0, 1, 0)) * cam.data.ortho_scale * 0.45, W, H)
    meta["labels"]["R"] = L.world_to_px(cam, centre + Vector((0, -1, 0)) * cam.data.ortho_scale * 0.45, W, H)
json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)

frames = ONLY if ONLY is not None else range(NF)
for f in frames:
    pose(ease(f / FPS))
    sc.render.filepath = os.path.join(OUT, "f%04d.png" % f)
    bpy.ops.render.render(write_still=True)
    print("FRAME", f, "s=%.3f" % ease(f / FPS))
