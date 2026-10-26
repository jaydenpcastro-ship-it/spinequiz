"""Shared Blender helpers for the lumbosacral spine quiz renders.

All geometry comes from the ArtiSynth lumbosacral spine model
(Remus et al. 2021, BSD-3-Clause; Visible Human Project male).
Model frame (metres): +X anterior, +Y LEFT, +Z superior.
"""
import bpy, bmesh, os, math
import numpy as np
from mathutils import Vector, Matrix, kdtree

GEO = r"C:\Users\Jayden\Desktop\Tutorial\artisynth_lumbosacralSpineModel\hybrid_LSS_model\src\artisynth\models\passiveComponents_PlosOne\geometry"
RB = os.path.join(GEO, "RB")
FE = os.path.join(GEO, "FE", "LSS_20200529")
FAC = os.path.join(GEO, "FE", "LSS_Facets")

LEVELS = ["L1", "L2", "L3", "L4", "L5", "S1"]
DISCS = ["L12", "L23", "L34", "L45", "L51"]

# colours (linear RGB)
BONE = (0.80, 0.70, 0.54, 1)
BONE_CUT = (0.55, 0.40, 0.33, 1)
HL = (1.0, 0.22, 0.02, 1)          # vivid orange highlight
DISC_COL = (0.50, 0.62, 0.72, 1)   # bluish annulus
NP_COL = (0.62, 0.55, 0.78, 1)
LIG_COL = (0.75, 0.72, 0.62, 1)


# ------------------------------------------------------------------ scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    return sc


def read_obj(path):
    vs, fs = [], []
    with open(path) as f:
        for line in f:
            if line.startswith('v '):
                p = line.split()
                vs.append((float(p[1]), float(p[2]), float(p[3])))
            elif line.startswith('f '):
                p = line.split()[1:]
                fs.append(tuple(int(t.split('/')[0]) - 1 for t in p))
    return np.array(vs), fs


def mesh_object(name, verts, faces, smooth=True, coll=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.validate(clean_customdata=False)
    me.update()
    if smooth:
        me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def load_bone(fname, name=None):
    v, f = read_obj(os.path.join(RB, fname + ".obj"))
    return mesh_object(name or fname, v, f)


def load_vertebra(lv):
    """Whole vertebra (shrink-wrapped surface)."""
    return load_bone(f"{lv}_Schrumpfverpacken", lv)


def body_points(lv):
    v, _ = read_obj(os.path.join(RB, f"{lv}_body.obj"))
    return v


# ------------------------------------------------------------------ FE discs
def read_nodes(path):
    ids, xyz = [], []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 4:
                ids.append(int(p[0])); xyz.append((float(p[1]), float(p[2]), float(p[3])))
    return dict(zip(ids, range(len(ids)))), np.array(xyz)


def read_hex(path):
    els = []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 8:
                els.append([int(t) for t in p[:8]])
    return els


# ANSYS hex8 node order: 0-3 bottom, 4-7 top
HEX_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def fe_surface(parts, keep=None):
    """Boundary surface of the union of FE parts (e.g. ['L45_AN_R1', 'L45_NP']).
    keep(centroid)->bool drops elements (for cut-aways). Returns verts, faces, part index per face."""
    allv, faces, fpart = [], [], []
    keyed = {}
    vmap = {}

    def vid(p):
        k = tuple(np.round(p, 6))
        if k not in vmap:
            vmap[k] = len(allv); allv.append(p)
        return vmap[k]

    for pi, part in enumerate(parts):
        idmap, xyz = read_nodes(os.path.join(FE, part + ".node"))
        for e in read_hex(os.path.join(FE, part + ".elem")):
            try:
                pts = [xyz[idmap[n]] for n in e]
            except KeyError:
                continue
            c = np.mean(pts, axis=0)
            if keep is not None and not keep(c):
                continue
            ids = [vid(p) for p in pts]
            for hf in HEX_FACES:
                q = tuple(ids[i] for i in hf)
                if len(set(q)) < 3:
                    continue
                k = tuple(sorted(set(q)))
                if k in keyed:
                    keyed[k] = None  # shared -> interior
                else:
                    keyed[k] = (q, pi)
    for k, val in keyed.items():
        if val is None:
            continue
        q, pi = val
        q = tuple(dict.fromkeys(q))
        faces.append(q); fpart.append(pi)
    return np.array(allv), faces, fpart


def disc_parts(lvl, np_=True):
    p = [f"{lvl}_AN_R{i}" for i in range(1, 5)]
    if np_:
        p.append(f"{lvl}_NP")
    return p


def disc_center(lvl):
    _, xyz = read_nodes(os.path.join(FE, f"{lvl}_NP.node"))
    return Vector(xyz.mean(0))


def fix_normals(ob, inside_point=None):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()


# ------------------------------------------------------------------ ligaments
def read_lig_as(lvl):
    """Axial-spring ligaments: name -> list of (p_upper, p_lower)."""
    out = {}
    with open(os.path.join(GEO, f"{lvl}_Ligs_AS.lig")) as f:
        lines = [l.strip() for l in f if l.strip()]
    i = 1
    while i < len(lines):
        head = [t.strip() for t in lines[i].split(',')]
        name, n = head[0], int(head[1])
        fib = []
        for j in range(n):
            v = [float(t) for t in lines[i + 1 + j].replace(',', ' ').split()]
            fib.append((Vector(v[0:3]), Vector(v[3:6])))
        out[name] = fib
        i += 1 + n
    return out


def read_lig_mp(lvl):
    """Multi-point ligaments (ALL/PLL): name -> list of polylines."""
    out = {}
    with open(os.path.join(GEO, f"{lvl}_Ligs_MP.lig")) as f:
        lines = [l.strip() for l in f if l.strip()]
    i = 1
    while i < len(lines):
        head = [t.strip() for t in lines[i].split(',')]
        name, n, m = head[0], int(head[1]), int(head[2])
        polys = []
        for j in range(n):
            v = [float(t) for t in lines[i + 1 + j].replace(',', ' ').split()]
            polys.append([Vector(v[3 * k:3 * k + 3]) for k in range(m)])
        out[name] = polys
        i += 1 + n
    return out


def tubes(name, polylines, radius, mat, coll=None):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.use_fill_caps = True
    for pl in polylines:
        sp = cu.splines.new('POLY')
        sp.points.add(len(pl) - 1)
        for k, p in enumerate(pl):
            sp.points[k].co = (p.x, p.y, p.z, 1)
    ob = bpy.data.objects.new(name, cu)
    (coll or bpy.context.scene.collection).objects.link(ob)
    ob.data.materials.append(mat)
    return ob


# ------------------------------------------------------------------ materials
def principled(name, col, rough=0.55, emit=0.0, sss=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = rough
    if emit > 0:
        b.inputs["Emission Color"].default_value = col
        b.inputs["Emission Strength"].default_value = emit
    if sss > 0:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (0.004, 0.002, 0.001)
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    return m


def mask_material(name, base=BONE, hl=HL, attr="hl", emit=0.6, rough=0.55):
    """Bone material whose colour switches to the highlight where point attribute `attr` ~ 1."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    a = nt.nodes.new("ShaderNodeAttribute"); a.attribute_name = attr; a.attribute_type = 'GEOMETRY'
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = 0.35
    mr.inputs["From Max"].default_value = 0.65
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = 'RGBA'
    mix.inputs[6].default_value = base
    mix.inputs[7].default_value = hl
    nt.links.new(a.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], mix.inputs["Factor"])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    b.inputs["Emission Color"].default_value = hl
    em = nt.nodes.new("ShaderNodeMath"); em.operation = 'MULTIPLY'; em.inputs[1].default_value = emit
    nt.links.new(mr.outputs["Result"], em.inputs[0])
    nt.links.new(em.outputs[0], b.inputs["Emission Strength"])
    return m


def set_mask(ob, values, attr="hl"):
    me = ob.data
    if attr in me.attributes:
        me.attributes.remove(me.attributes[attr])
    at = me.attributes.new(attr, 'FLOAT', 'POINT')
    at.data.foreach_set("value", np.asarray(values, dtype=np.float32))


def verts_np(ob):
    me = ob.data
    a = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", a)
    return a.reshape(-1, 3)


def normals_np(ob):
    me = ob.data
    a = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("normal", a)
    return a.reshape(-1, 3)


def smooth_mask(ob, mask, iters=2):
    """Average a 0/1 vertex mask with its neighbours to soften the boundary."""
    me = ob.data
    e = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    m = np.asarray(mask, dtype=np.float64)
    deg = np.bincount(e.ravel(), minlength=len(m)).astype(np.float64) + 1
    for _ in range(iters):
        s = m.copy()
        np.add.at(s, e[:, 0], m[e[:, 1]])
        np.add.at(s, e[:, 1], m[e[:, 0]])
        m = s / deg
    return m


def kd_from(points):
    kd = kdtree.KDTree(len(points))
    for i, p in enumerate(points):
        kd.insert(Vector(p), i)
    kd.balance()
    return kd


def dist_to(points_a, points_b):
    kd = kd_from(points_b)
    return np.array([kd.find(Vector(p))[2] for p in points_a])


def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


# ------------------------------------------------------------------ look
def setup_render(sc, w, h, samples=64, engine='CYCLES'):
    sc.render.engine = engine
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    if engine == 'CYCLES':
        prefs = bpy.context.preferences.addons['cycles'].preferences
        try:
            prefs.compute_device_type = 'OPTIX'
            prefs.get_devices()
            for d in prefs.devices:
                d.use = True
            sc.cycles.device = 'GPU'
        except Exception as ex:
            print("GPU setup failed:", ex)
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 6
    w_ = bpy.data.worlds.new("W"); sc.world = w_
    w_.use_nodes = True
    w_.node_tree.nodes["Background"].inputs[0].default_value = (0.20, 0.22, 0.27, 1)
    w_.node_tree.nodes["Background"].inputs[1].default_value = 0.25


def area_light(name, loc, target, power, size, col=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = power; ld.size = size; ld.color = col
    ob = bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def three_point(center, view_dir, up=(0, 0, 1), dist=1.2, scale=1.0):
    """Key/fill/rim lights arranged around the camera direction (view_dir points camera->subject)."""
    c = Vector(center); v = Vector(view_dir).normalized(); u = Vector(up).normalized()
    r = v.cross(u).normalized()
    cam_side = -v
    key = c + (cam_side * 0.8 + r * -0.7 + u * 0.8).normalized() * dist
    fill = c + (cam_side * 0.9 + r * 0.9 + u * 0.1).normalized() * dist
    rim = c + (v * 0.9 + u * 0.6 + r * 0.3).normalized() * dist
    # irradiance ~ P / d^2, so scale power with d^2 for a constant exposure
    k = dist * dist * scale
    area_light("Key", key, c, 13 * k, dist * 0.5)
    area_light("Fill", fill, c, 5 * k, dist * 0.8)
    area_light("Rim", rim, c, 12 * k, dist * 0.4)


def camera(view_dir, up, target, ortho_scale, dist=2.0):
    cd = bpy.data.cameras.new("Cam"); cd.type = 'ORTHO'; cd.ortho_scale = ortho_scale
    cd.clip_start = 0.01; cd.clip_end = 20
    ob = bpy.data.objects.new("Cam", cd); bpy.context.scene.collection.objects.link(ob)
    ob.matrix_world = look_matrix(view_dir, up, Vector(target) - Vector(view_dir).normalized() * dist)
    bpy.context.scene.camera = ob
    return ob


def look_matrix(view_dir, up, loc):
    """Camera/light matrix looking along view_dir with `up` on screen (local -Z forward, +Y up)."""
    z = -Vector(view_dir).normalized()
    y = Vector(up) - z * Vector(up).dot(z)
    y.normalize()
    x = y.cross(z)
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(loc)
    return m


def fit_camera(cam, points, aspect, margin=0.08):
    """Centre an ortho camera on `points` (Nx3) and set ortho_scale to fit."""
    m = cam.matrix_world.to_3x3()
    right = m @ Vector((1, 0, 0)); up = m @ Vector((0, 1, 0)); fwd = m @ Vector((0, 0, -1))
    P = np.asarray(points)
    xs = P @ np.array(right); ys = P @ np.array(up); zs = P @ np.array(fwd)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    w, h = xs.max() - xs.min(), ys.max() - ys.min()
    # ortho_scale spans the longer image side
    scale = (max(w, h * aspect) if aspect >= 1 else max(h, w / aspect)) * (1 + 2 * margin)
    cam.data.ortho_scale = scale
    centre = right * cx + up * cy + fwd * ((zs.min() + zs.max()) / 2)
    cam.location = centre - fwd * 3.0
    return centre


def world_to_px(cam, p, w, h):
    from bpy_extras.object_utils import world_to_camera_view
    co = world_to_camera_view(bpy.context.scene, cam, Vector(p))
    return (co.x * w, (1 - co.y) * h)
