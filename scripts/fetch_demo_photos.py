"""Fetch real crop demo photos from Wikimedia Commons and validate them by content.

Each crop gets two photos in frontend/public/demo-photos/:
  <crop>.jpg          — clearly diseased sample (lesions / chlorosis visible)
  <crop>-healthy.jpg  — clearly healthy leafy sample

Every download is feature-checked with the SAME computer-vision code that the
backend uses for inference (ml.inference.ImageArray), so a catalog cover, a
stamp, or a photo of people can never slip in as a "healthy leaf". Candidates
that fail the check are rejected and the next one is tried.

If no real photo on Commons passes for a crop, a clean SYNTHETIC leaf image is
generated instead (marked SYNTHETIC in CREDITS.txt) so the demo always works.

Run:  backend/.venv/Scripts/python scripts/fetch_demo_photos.py
(requires internet; photos are CC-licensed from Wikimedia Commons)
"""
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(ROOT, "frontend", "public", "demo-photos")
UA = {"User-Agent": "AgricureAcademicDemo/1.0 (educational project; contact: student)"}

# Make the ml/ feature extractor importable (backend venv provides numpy/Pillow)
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, ROOT)

# crop file stem -> ordered Commons search queries (representative disease symptom)
# Each crop ships two photos: a clearly diseased sample and a healthy one, so the
# app can demonstrate both outcomes ("diseased" detection and "healthy" detection).
CROPS = {
    "tomato": {
        "diseased": ["tomato late blight phytophthora infestans leaf",
                     "tomato early blight alternaria solani leaf",
                     "tomato leaf spot disease"],
        "healthy": ["tomato leaf closeup",
                    "tomato plant foliage field",
                    "tomato plants growing leaves",
                    "solanum lycopersicum foliage closeup",
                    "tomato greenhouse plants"],
    },
    "wheat": {
        "diseased": ["wheat yellow rust puccinia striiformis",
                     "wheat leaf rust puccinia recondita",
                     "wheat rust disease field"],
        "healthy": ["wheat field green healthy crop closeup",
                    "green wheat ears closeup",
                    "wheat crop healthy field"],
    },
    "cotton": {
        "diseased": ["cotton leaf curl virus",
                     "cotton leaf curl disease",
                     "cotton plant leaves gossypium",
                     "cotton crop field"],
        "healthy": ["cotton leaf closeup",
                    "cotton plant leaves closeup field",
                    "gossypium leaves",
                    "cotton crop field green"],
    },
    "rice": {
        "diseased": ["rice blast pyricularia oryzae leaf",
                     "rice leaf blast disease",
                     "rice blast disease symptoms"],
        "healthy": ["green rice paddy field closeup leaves",
                    "healthy rice plant leaves",
                    "rice paddy green closeup"],
    },
    "onion": {
        "diseased": ["onion purple blotch alternaria porri",
                     "onion leaf blight disease",
                     "onion plant leaf fungus disease",
                     "allium leaf spot", "onion disease symptoms leaf",
                     "allium crop disease leaf"],
        "healthy": ["green onion leaves field closeup",
                    "onion plant green leaves",
                    "allium cepa green leaves closeup"],
    },
}

# Book/journal scan artifacts — not useful as demo photos
BAD_TITLE = ("encyclopedia", "text-book", "textbook", "plate", "bulletin",
             "journal", "1917", "1918", "1897", "practical horticulture",
             "herbarium", "insects affecting", "report of", "annual report",
             "microform", "review", "catalog", "magazine", "advertis",
             "illustrated", "gardeners' chronicle", "stamp", "dress",
             "pelerine", "manual", "settlers", "map", "musicians",
             "tree near")

API = "https://commons.wikimedia.org/w/api.php"


def api(params):
    """Call the Commons API, politely retrying on rate-limit (429) responses."""
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 503) and attempt < 4:
                wait = 8 * (attempt + 1)
                print(f"  rate-limited, waiting {wait}s …")
                time.sleep(wait)
                continue
            raise
        except Exception:
            if attempt < 4:
                time.sleep(3)
                continue
            raise
    raise RuntimeError("unreachable")


def pick_candidates(queries):
    """Return ALL suitable bitmap candidates across the ordered queries (deduped,
    in search-rank order) so a feature validator can fall through bad images."""
    seen = set()
    candidates = []
    for query in queries:
        try:
            data = api({
                "action": "query",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}",
                "gsrnamespace": "6",
                "gsrlimit": "12",
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
                "iiurlwidth": "900",
            })
        except Exception as exc:
            print(f"  search failed for '{query}': {str(exc)[:80]}")
            continue
        pages = (data.get("query") or {}).get("pages") or {}
        for p in pages.values():
            title = (p.get("title") or "").lower()
            if any(bad in title for bad in BAD_TITLE):
                continue
            ii = (p.get("imageinfo") or [{}])[0]
            mime = ii.get("mime", "")
            w, h = ii.get("width", 0), ii.get("height", 0)
            if mime in ("image/jpeg", "image/png") and w >= 600 and h >= 350:
                meta = ii.get("extmetadata") or {}
                license_name = (meta.get("LicenseShortName") or {}).get("value", "?")
                full_title = p.get("title") or ""
                if full_title in seen:
                    continue
                seen.add(full_title)
                candidates.append((p.get("index", 99), {
                    "thumburl": ii.get("thumburl"),
                    "descriptionurl": ii.get("descriptionurl"),
                    "title": full_title,
                    "license": license_name,
                }))
        time.sleep(1.5)  # be polite between consecutive searches
    candidates.sort(key=lambda c: c[0])
    return [c[1] for c in candidates]


def matches_variant(path, variant):
    """Feature-check the downloaded photo with the same CV used at inference.

    healthy  -> must really be leafy green (rejects catalog covers, people, soil)
    diseased -> must show visible symptom pixels or lesion clusters
    """
    try:
        from ml.inference import ImageArray

        with open(path, "rb") as fh:
            f = ImageArray.from_bytes(fh.read()).features()
        symptom = f["yellow_frac"] + f["brown_frac"] + f["dark_frac"]
        if variant == "healthy":
            return f["green_frac"] >= 0.22 and symptom <= 0.12
        return symptom >= 0.04 or f["dark_spots"] >= 3
    except Exception as exc:
        print(f"    feature check failed: {str(exc)[:60]}")
        return variant == "diseased"  # don't block diseased on tooling issues


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def normalize_jpeg(path):
    """Re-encode as JPEG via Pillow (from the backend venv) if available."""
    try:
        from PIL import Image
    except ImportError:
        return
    img = Image.open(path).convert("RGB")
    img.save(path, "JPEG", quality=86)


def synthetic_leaf(path, healthy=True, crop=""):
    """Generate a clean synthetic leaf image (fallback when no real photo passes).

    Marked SYNTHETIC in CREDITS.txt — never presented as a real photograph.
    """
    from PIL import Image, ImageDraw

    w = h = 480
    img = Image.new("RGB", (w, h), (74, 124, 62))
    draw = ImageDraw.Draw(img)
    # Leaf veins
    for k in range(-6, 7):
        draw.line([(w // 2, h // 2), (w // 2 + k * 60, 0)], fill=(96, 148, 80), width=3)
        draw.line([(w // 2, h // 2), (w // 2 + k * 60, h)], fill=(96, 148, 80), width=3)
    draw.line([(w // 2, 0), (w // 2, h)], fill=(88, 140, 74), width=6)
    if not healthy:
        # Brown lesion blobs + yellow chlorotic halos
        for k in range(16):
            cx, cy = (k * 97 + 31) % (w - 40) + 20, (k * 61 + 17) % (h - 40) + 20
            r = 14 + (k % 3) * 6
            draw.ellipse([cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8],
                         fill=(186, 172, 72))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(108, 70, 38))
    img.save(path, "JPEG", quality=88)


def main():
    os.makedirs(DEST, exist_ok=True)
    credits = ["Demo photos sourced from Wikimedia Commons (CC-licensed).",
               "Files marked SYNTHETIC are generated leaf images, not photographs.", ""]
    ok, failed = [], []
    for stem, variants in CROPS.items():
        for variant, queries in variants.items():
            name = f"{stem}.jpg" if variant == "diseased" else f"{stem}-healthy.jpg"
            dest = os.path.join(DEST, name)
            if os.path.exists(dest) and os.path.getsize(dest) > 15000 and \
                    matches_variant(dest, variant):
                print(f"SKIP {name:22s} already present & valid")
                ok.append(name)
                continue
            kept = None
            try:
                candidates = pick_candidates(queries)
                for attempt, info in enumerate(candidates[:6]):
                    if not info.get("thumburl"):
                        continue
                    download(info["thumburl"], dest)
                    normalize_jpeg(dest)
                    if os.path.getsize(dest) < 15000:
                        continue
                    if not matches_variant(dest, variant):
                        safe_title = info["title"].encode("ascii", "replace").decode()
                        print(f"  reject #{attempt} {safe_title[:60]}")
                        continue
                    kept = info
                    break
            except Exception as exc:
                print(f"  error: {str(exc)[:100]}")
            if kept is None:
                # Fall back to a clearly-labelled synthetic leaf so demos always work
                synthetic_leaf(dest, healthy=(variant == "healthy"), crop=stem)
                credits += [
                    f"{name}  (SYNTHETIC — no suitable CC photo found)",
                    "  source:   generated locally by scripts/fetch_demo_photos.py",
                    "  license:  n/a",
                    "",
                ]
                ok.append(name)
                print(f"SYN  {name:22s} {os.path.getsize(dest) // 1024} KB  (synthetic leaf)")
                continue
            ok.append(name)
            credits += [
                f"{name}",
                f"  file:     {kept['title']}",
                f"  source:   {kept['descriptionurl']}",
                f"  license:  {kept['license']}",
                "",
            ]
            safe_title = kept["title"].encode("ascii", "replace").decode()
            print(f"OK   {name:22s} {os.path.getsize(dest) // 1024} KB  {safe_title}")

    if ok:
        with open(os.path.join(DEST, "CREDITS.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(credits))
    print(f"\nDone. {len(ok)} prepared, {len(failed)} failed.")
    for stem, why in failed:
        print(f"FAIL {stem}: {why}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
