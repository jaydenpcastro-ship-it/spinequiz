"""Quiz stills: one function per question. Run:
blender -b -P stills.py -- <name> [preview|final]
Writes out/<name>.png (RGBA) + out/<name>.json (label anchors in pixels)."""
import sys, os, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
import numpy as np
from mathutils import Vector, Matrix
import spine_lib as L

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NAME = argv[0] if argv else "sp"
QUAL = argv[1] if len(argv) > 1 else "preview"
W, H = (1200, 900) if QUAL == "final" else (600, 450)
SAMPLES = 96 if QUAL == "final" else 16
OUT = os.path.join(HERE, "out" if QUAL == "final" else "preview")
os.makedirs(OUT, exist_ok=True)

sc = L.reset()
L.setup_render(sc, W, H, SAMPLES)
M_BONE = L.mask_material("bone")
M_DISC = L.principled("disc", L.DISC_COL, rough=0.5)
M_DISC2 = L.principled("disc2", (0.40, 0.52, 0.63, 1), rough=0.5)
M_NP = L.principled("np", L.NP_COL, rough=0.45)
M_HL = L.principled("hl", L.HL, rough=0.45, emit=0.6)
M_LIG = L.principled("lig", L.LIG_COL, rough=0.6)
M_CUT = L.principled("cut", L.BONE_CUT, rough=0.8)
labels = {}


# ---------------------------------------------------------------- helpers
def disc_normal(lvl):
    _, xyz = L.read_nodes(os.path.join(L.FE, f"{lvl}_NP.node"))
    c = xyz.mean(0)
    w, V = np.linalg.eigh(np.cov((xyz - c).T))
    n = V[:, 0]
    return n if n[2] > 0 else -n


def vert_frame(lv):
    """Local frame of a vertebra: origin = body centroid, axes (ant, left, sup)."""
    B = L.body_points(lv)
    c = B.mean(0)
    i = L.LEVELS.index(lv)
    ns = []
    if i > 0:
        ns.append(disc_normal(L.DISCS[i - 1]))
    if i < 5:
        ns.append(disc_normal(L.DISCS[i]))
    sup = np.mean(ns, axis=0); sup /= np.linalg.norm(sup)
    ant = np.array([1.0, 0, 0]); ant -= sup * ant.dot(sup); ant /= np.linalg.norm(ant)
    left = np.cross(sup, ant)
    return c, ant, left, sup


def local(ob, lv):
    c, a, l, s = vert_frame(lv)
    P = L.verts_np(ob) - c
    return P @ a, P @ l, P @ s


def add_vertebrae(levels, mask=None):
    obs = {}
    for lv in levels:
        ob = L.load_vertebra(lv)
        L.assign(ob, M_BONE)
        L.set_mask(ob, np.zeros(len(ob.data.vertices)))
        obs[lv] = ob
    return obs


def add_disc(lvl, keep=None, mat=None, hl_np=False):
    v, f, fp = L.fe_surface(L.disc_parts(lvl), keep)
    ob = L.mesh_object(lvl + "_disc", v, f, smooth=False)
    L.fix_normals(ob)
    for m in (M_DISC, M_DISC2, M_NP, M_HL):
        ob.data.materials.append(m)
    idx = []
    for p in fp:
        if p == 4:
            idx.append(3 if hl_np else 2)
        else:
            idx.append(p % 2)
    ob.data.polygons.foreach_set("material_index", idx)
    if mat is not None:
        ob.data.materials.clear(); ob.data.materials.append(mat)
    return ob


def view(vd, up, pts, margin=0.06, light_scale=1.0):
    cam = L.camera(vd, up, (0, 0, 0), 1.0)
    bpy.context.view_layer.update()
    centre = L.fit_camera(cam, pts, W / H, margin)
    bpy.context.view_layer.update()
    span = cam.data.ortho_scale
    L.three_point(centre, vd, up, dist=span * 2.2, scale=light_scale)
    return cam


def label(key, p, cam):
    labels[key] = L.world_to_px(cam, p, W, H)


def finish(extra=None):
    sc.render.filepath = os.path.join(OUT, NAME + ".png")
    bpy.ops.render.render(write_still=True)
    meta = {"w": W, "h": H, "labels": labels}
    if extra:
        meta.update(extra)
    json.dump(meta, open(os.path.join(OUT, NAME + ".json"), "w"), indent=1)


def all_pts(obs):
    return np.vstack([L.verts_np(o) for o in obs])


# ---------------------------------------------------------------- questions
def q_sp():
    """L3 spinous process, posterior-left oblique view of L2-L4."""
    obs = add_vertebrae(["L2", "L3", "L4"])
    discs = [add_disc("L23"), add_disc("L34")]
    u, s, w = local(obs["L3"], "L3")
    m = ((u < -0.044) & (np.abs(s) < 0.014)).astype(float)
    L.set_mask(obs["L3"], L.smooth_mask(obs["L3"], m, 2))
    vd = Vector((0.90, -0.36, -0.24))
    cam = view(vd, (0, 0, 1), all_pts(list(obs.values())))
    finish({"view": "Posterior oblique view"})


def q_facet():
    """Both L4-L5 zygapophyseal joints, posterior view of L3-S1."""
    obs = add_vertebrae(["L3", "L4", "L5", "S1"])
    discs = [add_disc(d) for d in ("L34", "L45", "L51")]
    masks = {"L4": np.zeros(len(obs["L4"].data.vertices)), "L5": np.zeros(len(obs["L5"].data.vertices))}
    for side in ("l", "r"):
        fac_inf = L.read_obj(os.path.join(L.FAC, f"L45FacL4{side}_i.obj"))[0]
        fac_sup = L.read_obj(os.path.join(L.RB, f"L5_PD{side}_a.obj"))[0]
        jc = np.vstack([fac_inf, fac_sup]).mean(0)
        for lv, fac in (("L4", fac_inf), ("L5", fac_sup)):
            P = L.verts_np(obs[lv])
            d = L.dist_to(P, fac)
            # articular process surface around the joint line
            masks[lv] = np.maximum(masks[lv], ((d < 0.0045) & (np.linalg.norm(P - jc, axis=1) < 0.015)).astype(float))
        # capsular ligament fibres
        cl = L.read_lig_as("L45")["L45_CL_" + side.upper()]
        L.tubes("CL" + side, [[a, b] for a, b in cl], 0.0009, M_HL)
    for lv in ("L4", "L5"):
        L.set_mask(obs[lv], L.smooth_mask(obs[lv], masks[lv], 2))
    pts = all_pts([obs["L3"], obs["L4"], obs["L5"]])
    pts = np.vstack([pts, L.verts_np(obs["S1"])[L.verts_np(obs["S1"])[:, 2] > 0.0]])
    vd = Vector((1.0, 0.0, -0.10))
    cam = view(vd, (0, 0, 1), pts, margin=0.04)
    finish({"view": "Posterior view"})


def q_np():
    """L4-L5 disc cut-away on L5, nucleus highlighted."""
    obs = add_vertebrae(["L5"])
    c = np.array(L.disc_center("L45"))
    keep = lambda p: not (p[0] - c[0] > -0.002 and p[1] - c[1] > -0.002)
    d = add_disc("L45", keep=keep, hl_np=True)
    vd = Vector((-0.62, -0.55, -0.56))
    pts = all_pts([obs["L5"], d])
    cam = view(vd, (0, 0, 1), pts, margin=0.05)
    finish({"view": "Anterior-left oblique view from above"})


def bool_cut(ob, keep_neg_y=True, plane_y=0.0):
    """Keep the right half (y < plane) of a closed mesh; cut face gets M_CUT."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    cu = bpy.context.active_object
    cu.scale = (1.0, 1.0, 1.0)
    cu.location = (0, plane_y + 0.5, 0) if keep_neg_y else (0, plane_y - 0.5, 0)
    cu.data.materials.append(M_CUT)
    if M_CUT.name not in [m.name for m in ob.data.materials]:
        ob.data.materials.append(M_CUT)
    md = ob.modifiers.new("cut", 'BOOLEAN')
    md.operation = 'DIFFERENCE'; md.object = cu
    md.solver = 'EXACT'
    md.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.data.objects.remove(cu)
    return ob


def q_lf():
    """Mid-sagittal section L2-L5, ligamentum flavum highlighted (left view of the right half)."""
    lvls = ["L2", "L3", "L4", "L5"]
    obs = add_vertebrae(lvls)
    for ob in obs.values():
        bool_cut(ob)
    discs = [add_disc(d, keep=lambda p: p[1] < 0) for d in ("L23", "L34", "L45")]
    for lvl in ("L23", "L34", "L45"):
        AS = L.read_lig_as(lvl)
        for name, fib in AS.items():
            kind = name.split("_", 1)[1]
            if kind.startswith(("CL", "ITL")):
                continue
            keepf = [[a, b] for a, b in fib if (a.y + b.y) / 2 < 0.0005]
            if not keepf:
                continue
            mat = M_HL if kind == "LF" else M_LIG
            L.tubes(name, keepf, 0.0011 if kind == "LF" else 0.0006, mat)
        MP = L.read_lig_mp(lvl)
        for name, polys in MP.items():
            keepp = [pl for pl in polys if np.mean([p.y for p in pl]) < 0.0005]
            L.tubes(name, keepp, 0.0006, M_LIG)
    vd = Vector((0, -1, 0))
    pts = all_pts(list(obs.values()))
    cam = view(vd, (0, 0, 1), pts, margin=0.05)
    finish({"view": "Mid-sagittal section, viewed from the left"})


def pelvis_scene(extra_levels=("L4", "L5", "S1")):
    obs = add_vertebrae(list(extra_levels))
    pel = L.load_bone("Pelvis")
    L.assign(pel, M_BONE)
    L.set_mask(pel, np.zeros(len(pel.data.vertices)))
    return obs, pel


def q_asis():
    obs, pel = pelvis_scene()
    for d in ("L45", "L51"):
        add_disc(d)
    P = L.verts_np(pel)
    band = (P[:, 1] > 0.09) & (P[:, 2] > -0.035) & (P[:, 2] < 0.0)
    asis = P[band][P[band][:, 0].argmax()]
    m = (np.linalg.norm(P - asis, axis=1) < 0.014).astype(float)
    L.set_mask(pel, L.smooth_mask(pel, m, 2))
    vd = Vector((-0.88, -0.45, -0.02))
    cam = view(vd, (0, 0, 1), all_pts([pel] + list(obs.values())), margin=0.04)
    label("asis", asis, cam)
    finish({"view": "Anterior-left oblique view", "asis_mm": (asis * 1000).round(1).tolist()})


def q_isch():
    obs, pel = pelvis_scene()
    for d in ("L45", "L51"):
        add_disc(d)
    P = L.verts_np(pel)
    N = L.normals_np(pel)
    left = P[:, 1] > 0.02
    low = P[left][P[left][:, 2].argmin()]
    # rough posteroinferior surface of the ischium near its lowest point
    near = np.linalg.norm(P - (low + np.array([-0.008, 0.004, 0.014])), axis=1) < 0.026
    facing = (-N[:, 0] * 0.6 - N[:, 2] * 0.8 + N[:, 1] * 0.2) > 0.05
    m = (left & near & facing).astype(float)
    L.set_mask(pel, L.smooth_mask(pel, m, 2))
    vd = Vector((0.90, -0.30, 0.22))
    cam = view(vd, (0, 0, 1), all_pts([pel] + list(obs.values())), margin=0.04)
    label("isch", low, cam)
    finish({"view": "Posterior view from below", "low_mm": (low * 1000).round(1).tolist()})


def q_psoas():
    lv = ["L1", "L2", "L3", "L4", "L5", "S1"]
    obs = add_vertebrae(lv)
    pel = L.load_bone("Pelvis"); L.assign(pel, M_BONE); L.set_mask(pel, np.zeros(len(pel.data.vertices)))
    discs = {}
    for d in L.DISCS:
        discs[d] = add_disc(d)
    # lateral (left) surfaces of the L1-L5 bodies
    for k in ["L1", "L2", "L3", "L4", "L5"]:
        ob = obs[k]
        P = L.verts_np(ob); N = L.normals_np(ob)
        c, a, l, s = vert_frame(k)
        body = L.body_points(k)
        dB = L.dist_to(P, body)
        u = (P - c) @ a
        nl = N @ l
        m = (dB < 0.0015) & (nl > 0.35) & (u > -0.012)
        if k == "L5":
            # attachment runs only to the upper border of L5
            m &= ((P - c) @ s) > -0.002
        m = m.astype(float)
        L.set_mask(ob, L.smooth_mask(ob, m, 2))
    # left side of each disc -> highlight faces (material swap)
    for d, ob in discs.items():
        if d == "L51":
            continue
        me = ob.data
        idx = np.zeros(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("material_index", idx)
        nrm = np.empty(len(me.polygons) * 3); me.polygons.foreach_get("normal", nrm); nrm = nrm.reshape(-1, 3)
        cen = np.empty(len(me.polygons) * 3); me.polygons.foreach_get("center", cen); cen = cen.reshape(-1, 3)
        dc = np.array(L.disc_center(d))
        sel = (nrm[:, 1] > 0.35) & (cen[:, 0] - dc[0] > -0.012) & (idx != 2)
        idx[sel] = 3
        me.polygons.foreach_set("material_index", idx)
    vd = Vector((-0.62, -0.72, -0.12))
    PP = L.verts_np(pel)
    cam = view(vd, (0, 0, 1), np.vstack([all_pts([obs[k] for k in lv]), PP[PP[:, 2] > -0.03]]), margin=0.04)
    finish({"view": "Anterior-left oblique view"})


{"sp": q_sp, "facet": q_facet, "np": q_np, "lf": q_lf, "asis": q_asis, "isch": q_isch, "psoas": q_psoas}[NAME]()
