"""Composite renders for the quiz: background, orientation labels, neutral-pose ghost, GIF encoding.
usage: python post.py <quiz img dir>"""
import os, sys, json, glob, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "final")
os.makedirs(DEST, exist_ok=True)
BG = (22, 27, 43)
CHIP_TXT = (205, 214, 236)
FONT_B = r"C:\Windows\Fonts\seguisb.ttf"
FONT_X = r"C:\Windows\Fonts\segoeuib.ttf"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def layer(im):
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
    return ov, ImageDraw.Draw(ov)


def chip(im, text, scale):
    ov, d = layer(im)
    f = font(FONT_B, int(22 * scale))
    pad = int(9 * scale)
    x0, y0 = int(14 * scale), int(14 * scale)
    tw = d.textlength(text, font=f)
    th = int(22 * scale * 1.25)
    d.rounded_rectangle([x0, y0, x0 + tw + 2 * pad, y0 + th + pad], radius=int(10 * scale), fill=(255, 255, 255, 30))
    d.text((x0 + pad, y0 + pad * 0.45), text, font=f, fill=CHIP_TXT + (255,))
    im.alpha_composite(ov)


def side_letters(im, left, right, scale):
    """Radiograph-style side markers at mid-height on the left and right edges."""
    ov, d = layer(im)
    f = font(FONT_X, int(44 * scale))
    w, h = im.size
    for txt, x in ((left, int(22 * scale)), (right, w - int(22 * scale))):
        tw = d.textlength(txt, font=f)
        xx = x if x < w / 2 else x - tw
        d.text((xx, h / 2 - 28 * scale), txt, font=f, fill=(255, 255, 255, 150))
    im.alpha_composite(ov)


def corner_words(im, left, right, scale):
    ov, d = layer(im)
    f = font(FONT_B, int(23 * scale))
    w, h = im.size
    y = h - int(40 * scale)
    if left:
        d.text((int(16 * scale), y), "\u2190 " + left, font=f, fill=(255, 255, 255, 140))
    if right:
        tw = d.textlength(right + " \u2192", font=f)
        d.text((w - tw - int(16 * scale), y), right + " \u2192", font=f, fill=(255, 255, 255, 140))
    im.alpha_composite(ov)


def place(im, scale, valign):
    """Render scaled down on the background so the label chip has room (valign: 'bottom' or 'center')."""
    w, h = im.size
    sm = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    out = Image.new("RGBA", im.size, BG + (255,))
    x = (w - sm.size[0]) // 2
    y = (h - sm.size[1]) - int(h * 0.015) if valign == "bottom" else (h - sm.size[1]) // 2
    out.alpha_composite(sm, (x, y))
    return out


STILLS = {
    # name: (chip text, side letters (screen-left, screen-right) or None, corner words or None)
    "sp": ("Posterior oblique view", ("L", "R"), None),
    "facet": ("Posterior view", ("L", "R"), None),
    "np": ("Front-left view, from above", None, None),
    "lf": ("Midline cut, seen from the left", None, ("Anterior", "Posterior")),
    "asis": ("Anterior view", ("R", "L"), None),
    "isch": ("Posterior view", ("L", "R"), None),
    "psoas": ("Anterior-left oblique view", None, None),
}

for name, (txt, sides, words) in STILLS.items():
    src = os.path.join(HERE, "out", name + ".png")
    if not os.path.exists(src):
        print("missing", src); continue
    im = Image.open(src).convert("RGBA")
    s = im.size[0] / 600
    out = place(im, 0.86 if words else 0.90, "center" if words else "bottom")
    chip(out, txt, s)
    if sides:
        side_letters(out, sides[0], sides[1], s)
    if words:
        corner_words(out, words[0], words[1], s)
    out = out.convert("RGB").resize((im.size[0] // 3 * 2, im.size[1] // 3 * 2), Image.LANCZOS)
    out.save(os.path.join(DEST, name + ".jpg"), quality=88, optimize=True)
    print("still", name, out.size)


MOTIONS = {
    "flex": ("Left side view", None, ("Anterior", "Posterior")),
    "latflex": ("Posterior view", ("L", "R"), None),
    "apt": ("Left side view", None, ("Anterior", "Posterior")),
}
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
for name, (txt, sides, words) in MOTIONS.items():
    fdir = os.path.join(HERE, "frames", name)
    files = sorted(glob.glob(os.path.join(fdir, "f*.png")))
    if not files:
        print("no frames", name); continue
    meta = json.load(open(os.path.join(fdir, "meta.json")))
    first = Image.open(files[0]).convert("RGBA")
    s = first.size[0] / 600
    # ghost of the neutral pose: faint fill + thin outline
    a0 = first.split()[3].point(lambda v: 255 if v > 128 else 0)
    edge = ImageChops.subtract(a0.filter(ImageFilter.MaxFilter(3)), a0.filter(ImageFilter.MinFilter(3)))
    ghost = Image.new("RGBA", first.size, (0, 0, 0, 0))
    ghost.paste((150, 168, 205, 30), mask=a0)
    ghost.paste((150, 168, 205, 120), mask=edge)
    cdir = os.path.join(fdir, "comp")
    shutil.rmtree(cdir, ignore_errors=True); os.makedirs(cdir)
    for i, f in enumerate(files):
        im = Image.open(f).convert("RGBA")
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0))
        lay.alpha_composite(ghost)
        lay.alpha_composite(im)
        out = place(lay, 0.88 if words else 0.90, "center" if words else "bottom")
        chip(out, txt, s)
        if sides:
            side_letters(out, sides[0], sides[1], s)
        if words:
            corner_words(out, words[0], words[1], s)
        out.convert("RGB").save(os.path.join(cdir, "c%04d.png" % i))
    gif = os.path.join(DEST, name + ".gif")
    vf = "split[a][b];[a]palettegen=max_colors=160:stats_mode=full[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-framerate", str(meta["fps"]),
                    "-i", os.path.join(cdir, "c%04d.png"), "-vf", vf, "-loop", "0", gif], check=True)
    print("gif", name, len(files), "frames", "%.1f MB" % (os.path.getsize(gif) / 1e6))
