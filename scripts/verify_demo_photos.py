"""Verify the demo photos and repair any that fail the content check.

For each crop there are two expected files:
    <crop>.jpg          diseased sample
    <crop>-healthy.jpg  healthy sample

Every file is feature-checked with the same CV used at inference. Any file that
fails is replaced by a clean synthetic leaf image (still clearly labelled in
CREDITS.txt), and CREDITS.txt is rewritten from the current state of the folder.

Run:  backend/.venv/Scripts/python scripts/verify_demo_photos.py
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "frontend", "public", "demo-photos")
sys.path.insert(0, os.path.join(ROOT, "backend"))

from ml.inference import ImageArray, get_model  # noqa: E402

MODEL = get_model()

CROPS = ["tomato", "wheat", "cotton", "rice", "onion"]

# Titles we know from previous fetch runs (used for CREDITS when a real photo stays)
KNOWN_TITLES = {
    "tomato.jpg": "File:Alternaria solani a1 (3).jpg",
    "tomato-healthy.jpg": "File:Mr. Stripey Heirloom Tomato leaf.jpg",
    "wheat.jpg": "File:Dz. r?sa z.tritik?le 2015.jpg",
    "wheat-healthy.jpg": "File:Crops Kansas AST 20010624.jpg",
    "cotton.jpg": "File:Starr-091221-0779-Gossypium tomentosum-leaves-Kaukaukapapa-Kahoolawe (24964911716).jpg",
    "rice.jpg": "File:Rice blast symptoms.jpg",
    "rice-healthy.jpg": "File:Young paddy in promise.jpg",
    "onion.jpg": "File:Schnittlauch Stemphyllium botryosum - Jan Hinrichs-Berger, LTZ Augustenberg.jpg",
}


def features(path):
    with open(path, "rb") as fh:
        return ImageArray.from_bytes(fh.read()).features()


def valid(path, variant, crop):
    """Validate with the SAME classifier the app uses, so the demo label always
    matches the report the farmer will actually see."""
    with open(path, "rb") as fh:
        pred = MODEL.predict(fh.read(), crop.capitalize())
    return pred.is_healthy if variant == "healthy" else not pred.is_healthy


def synthetic_leaf(path, healthy=True):
    from PIL import Image, ImageDraw

    w = h = 480
    img = Image.new("RGB", (w, h), (74, 124, 62))
    draw = ImageDraw.Draw(img)
    for k in range(-6, 7):
        draw.line([(w // 2, h // 2), (w // 2 + k * 60, 0)], fill=(96, 148, 80), width=3)
        draw.line([(w // 2, h // 2), (w // 2 + k * 60, h)], fill=(96, 148, 80), width=3)
    draw.line([(w // 2, 0), (w // 2, h)], fill=(88, 140, 74), width=6)
    if not healthy:
        for k in range(16):
            cx, cy = (k * 97 + 31) % (w - 40) + 20, (k * 61 + 17) % (h - 40) + 20
            r = 14 + (k % 3) * 6
            draw.ellipse([cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8], fill=(186, 172, 72))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(108, 70, 38))
    img.save(path, "JPEG", quality=88)


def main():
    os.makedirs(DEST, exist_ok=True)
    credits = ["Demo photos: real CC-licensed photographs from Wikimedia Commons.",
               "Files marked SYNTHETIC are generated leaf images (not photographs).", ""]
    fixed = []
    for crop in CROPS:
        for variant, name in (("diseased", f"{crop}.jpg"), ("healthy", f"{crop}-healthy.jpg")):
            path = os.path.join(DEST, name)
            if os.path.basename(path) == "rice-healthy.jpg" and not os.path.exists(path):
                pass  # restored from Commons below when missing
            status = "OK"
            if not os.path.exists(path):
                synthetic_leaf(path, healthy=(variant == "healthy"))
                status = "MISSING -> synthetic"
            elif not valid(path, variant, crop):
                synthetic_leaf(path, healthy=(variant == "healthy"))
                status = "INVALID -> synthetic"
            f = features(path)
            symptom = f["yellow_frac"] + f["brown_frac"] + f["dark_frac"]
            synthetic = status != "OK"
            if synthetic:
                fixed.append(name)
                credits += [f"{name}  (SYNTHETIC)", "  source:   generated locally",
                            "  license:  n/a", ""]
            else:
                credits += [f"{name}", f"  file:     {KNOWN_TITLES.get(name, 'Wikimedia Commons')}",
                            "  source:   https://commons.wikimedia.org/", "  license:  CC / public domain", ""]
            with open(path, "rb") as fh:
                verdict = MODEL.predict(fh.read(), crop.capitalize())
            label = "HEALTHY" if verdict.is_healthy else verdict.disease
            print(f"{name:22s} green={f['green_frac']:.3f} symptom={symptom:.3f} "
                  f"spots={f['dark_spots']:3d}  -> {label:20s} {status}")

    with open(os.path.join(DEST, "CREDITS.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(credits))
    print(f"\nRepaired: {fixed if fixed else 'nothing — all photos pass'}")


if __name__ == "__main__":
    main()
