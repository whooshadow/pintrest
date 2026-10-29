#!/usr/bin/env python3
"""Build landing pages, pin images and the Pinterest upload CSV.

You only edit links/*.txt (paste affiliate links). Then run:  ./go.sh

What this does, per topic (kitchen, bathroom, on-the-go):
  1. Reads your links from links/<topic>.txt and checks every one.
  2. If all 10 links are present and valid, it writes the landing page
     (site/index.html, site/bathroom/index.html, site/on-the-go/index.html)
     and 10 pin images (site/pins/<topic>/pin-01.png ...).
  3. Writes out/pinterest-upload.csv for Pinterest's bulk upload.

Nothing is deployed or posted by this script.
"""
import argparse
import csv
import datetime as dt
import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SITE = ROOT / "site"
OUT = ROOT / "out"
TAG = "ordinaryday20-20"
HANDLE = "@ordinarydayinyourlife"
BASE = "https://ordinarydayinyourlife.netlify.app"
TOPICS = ["kitchen", "bathroom", "on-the-go"]

# Pinterest bulk schedule: 3 pins/day at these UTC times (about 9am, 1pm, 7pm US Eastern-ish).
SLOTS_UTC = ["13:00:00", "17:00:00", "23:00:00"]

FONT_DIR = "/System/Library/Fonts/Supplemental/"
F_HEAD = FONT_DIR + "Georgia Bold.ttf"
F_BODY = FONT_DIR + "Trebuchet MS.ttf"
F_BODY_B = FONT_DIR + "Trebuchet MS Bold.ttf"
F_EMOJI = "/System/Library/Fonts/Apple Color Emoji.ttc"


# --------------------------------------------------------------------------
# Links
# --------------------------------------------------------------------------
ASIN_RE = re.compile(r"^[A-Z0-9]{10}$")
DP_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")
SHORT_HOSTS = {"link.amazon", "amzn.to", "a.co", "amzn.com"}
COM_HOSTS = {"www.amazon.com", "amazon.com", "smile.amazon.com"}


def normalize_link(raw):
    """Return (clean_url or None, error or None, note or None)."""
    raw = raw.strip()
    if not raw:
        return None, None, None
    if ASIN_RE.match(raw):
        return f"https://www.amazon.com/dp/{raw}?tag={TAG}", None, "built from ASIN"
    if not raw.lower().startswith("https://"):
        return None, "link must start with https:// (or be a 10-character ASIN)", None
    host = (urlparse(raw).hostname or "").lower()
    if host in SHORT_HOSTS:
        return raw, None, "short link (cannot check the tag offline)"
    if host in COM_HOSTS:
        if f"tag={TAG}" not in raw:
            return None, f"amazon.com link is missing tag={TAG}", None
        m = DP_RE.search(urlparse(raw).path)
        if m:
            return f"https://www.amazon.com/dp/{m.group(1)}?tag={TAG}", None, "cleaned to short form"
        return raw, None, None
    if host.startswith("www.amazon.") or host.startswith("amazon."):
        return None, (f"{host} is not the US store; your tag {TAG} only earns on amazon.com. "
                      "Open the product on amazon.com and make the link there"), None
    return None, f"{host} is not an Amazon link", None


def read_links(slug):
    path = ROOT / "links" / f"{slug}.txt"
    raw, current = {}, None
    for line in path.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^(\d+)\.\s", s)
        if m:
            current = int(m.group(1))
            continue
        m = re.match(r"^LINK:\s*(.*)$", s, re.I)
        if m and current is not None:
            raw[current] = m.group(1)
    return raw


# --------------------------------------------------------------------------
# Landing page
# --------------------------------------------------------------------------
PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{h1}</title>
  <meta name="description" content="{meta}" />
  <style>
    :root {{
      --bg: {bg};
      --card: #ffffff;
      --ink: {ink};
      --muted: {muted};
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.45;
      padding: 24px 16px 60px;
    }}
    .wrap {{ max-width: 540px; margin: 0 auto; }}
    header {{ text-align: center; margin-bottom: 8px; }}
    h1 {{ font-size: 1.5rem; line-height: 1.25; margin-bottom: 8px; }}
    .sub {{ color: var(--muted); font-size: 0.95rem; margin-bottom: 14px; }}
    .disclosure {{
      background: {soft};
      border: 1px solid {softborder};
      color: var(--muted);
      font-size: 0.8rem;
      padding: 8px 12px;
      border-radius: 10px;
      text-align: center;
      margin: 0 auto 22px;
    }}
    a.link {{
      display: flex;
      align-items: center;
      gap: 14px;
      background: var(--card);
      border: 1px solid {cardborder};
      border-radius: 14px;
      padding: 12px 14px;
      margin-bottom: 12px;
      text-decoration: none;
      color: var(--ink);
      transition: transform .08s ease, box-shadow .15s ease;
      box-shadow: 0 1px 2px rgba(0,0,0,.04);
    }}
    a.link:hover {{ transform: translateY(-1px); box-shadow: 0 4px 14px rgba(0,0,0,.08); }}
    .thumb {{
      flex: 0 0 56px;
      width: 56px;
      height: 56px;
      border-radius: 10px;
      background: {soft};
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.8rem;
      overflow: hidden;
    }}
    .thumb img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
    .meta {{ min-width: 0; }}
    .meta .title {{ font-weight: 600; font-size: 1rem; }}
    .meta .tag {{ display: block; font-weight: 400; font-size: 0.85rem; color: var(--muted); margin-top: 2px; }}
    footer {{ text-align: center; color: var(--muted); font-size: 0.78rem; margin-top: 26px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>{h1}</h1>
      <p class="sub">{sub}</p>
    </header>

    <p class="disclosure">As an Amazon Associate I earn from qualifying purchases. #ad</p>

    <!-- GENERATED by build.py from data/{slug}.json and links/{slug}.txt. Edit those, not this file.
         Thumbnails: put your own photo (NOT an Amazon product image) at site/img/{slug}/NN.jpg
         (NN = product number, 01-10) and the build uses it instead of the emoji. -->

{rows}
    <footer>
      {footer}<br />
      As an Amazon Associate I earn from qualifying purchases.
    </footer>
  </div>
</body>
</html>
"""

ROW = """    <a class="link" href="{href}" target="_blank" rel="nofollow sponsored noopener">
      <span class="thumb">{thumb}</span>
      <span class="meta"><span class="title">{title}</span><span class="tag">{tag}</span></span>
    </a>
"""


def build_page(t, links):
    rows = []
    for p in t["products"]:
        thumb = html.escape(p["emoji"])
        for ext in ("jpg", "jpeg", "png", "webp"):
            if (SITE / "img" / t["slug"] / f"{p['n']:02d}.{ext}").exists():
                thumb = f'<img src="/img/{t["slug"]}/{p["n"]:02d}.{ext}" alt="{html.escape(p["title"])}" />'
                break
        rows.append(ROW.format(href=html.escape(links[p["n"]], quote=True), thumb=thumb,
                               title=html.escape(p["title"]), tag=html.escape(p["tag"])))
    th = t["theme"]
    out = PAGE.format(h1=html.escape(t["h1"]), meta=html.escape(t["meta"], quote=True),
                      sub=html.escape(t["sub"]), footer=html.escape(t["footer"]),
                      slug=t["slug"], rows="\n".join(rows), **th)
    dest = SITE / t["page_path"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out)
    return dest


# --------------------------------------------------------------------------
# Pin images
# --------------------------------------------------------------------------
W, H = 1000, 1500

# (background, big circle, text, pill background, pill text)
PALETTES = {
    "kitchen": [
        ("#f4f1ea", "#e3ecd9", "#2f3b30", "#2f3b30", "#f4f1ea"),
        ("#2f3b30", "#3d4d3e", "#f4f1ea", "#f4f1ea", "#2f3b30"),
        ("#dfe9d3", "#cbdcb9", "#26402b", "#26402b", "#dfe9d3"),
        ("#f6e9d2", "#efdcbb", "#4a3a22", "#4a3a22", "#f6e9d2"),
        ("#7a9a78", "#8cab8a", "#fdfbf5", "#fdfbf5", "#35503a"),
        ("#fbf6ec", "#f0e5cf", "#3b4a2f", "#7a9a78", "#ffffff"),
        ("#264f3d", "#31614b", "#f1f6ec", "#e6d9a6", "#264f3d"),
        ("#eaeadf", "#d9dcc7", "#323d2a", "#323d2a", "#eaeadf"),
        ("#c9d8c5", "#b8cab3", "#243326", "#243326", "#c9d8c5"),
        ("#fffaf0", "#f3e6c8", "#4d3b1f", "#4d3b1f", "#fffaf0"),
    ],
    "bathroom": [
        ("#eef4f6", "#d8e8ee", "#1f3a44", "#1f3a44", "#eef4f6"),
        ("#1f3a44", "#2a4b58", "#eef4f6", "#eef4f6", "#1f3a44"),
        ("#d6e8ec", "#c0dbe2", "#17424d", "#17424d", "#d6e8ec"),
        ("#f3e8e4", "#ead6cf", "#4a2f2a", "#4a2f2a", "#f3e8e4"),
        ("#6fa3ad", "#82b2bb", "#ffffff", "#ffffff", "#1f4650"),
        ("#f7fbfc", "#e2eff3", "#28505c", "#4f8c99", "#ffffff"),
        ("#234e5a", "#2d616f", "#eaf5f7", "#f0dcc4", "#234e5a"),
        ("#e9eeea", "#d5dfd8", "#2d3f38", "#2d3f38", "#e9eeea"),
        ("#bcd9de", "#a9cbd2", "#14363f", "#14363f", "#bcd9de"),
        ("#fdf8f3", "#f1e4d6", "#3f3128", "#3f3128", "#fdf8f3"),
    ],
    "on-the-go": [
        ("#f7f0e8", "#efdfcb", "#4a2a18", "#4a2a18", "#f7f0e8"),
        ("#4a2a18", "#5d3924", "#f7f0e8", "#f7f0e8", "#4a2a18"),
        ("#f1d9c4", "#e8c7aa", "#5a2d17", "#5a2d17", "#f1d9c4"),
        ("#e9ecdf", "#d8ddc6", "#36401f", "#36401f", "#e9ecdf"),
        ("#c8704a", "#d68360", "#fffaf4", "#fffaf4", "#6b2f17"),
        ("#fbf4e6", "#f1e4c4", "#5b3b14", "#c8704a", "#ffffff"),
        ("#2f4a52", "#3b5b64", "#f4efe6", "#f2c9a6", "#2f4a52"),
        ("#f4e6dd", "#ead3c5", "#55281c", "#55281c", "#f4e6dd"),
        ("#dbe6e0", "#c7d6ce", "#213b33", "#213b33", "#dbe6e0"),
        ("#fff7ec", "#f6e3c8", "#50361d", "#50361d", "#fff7ec"),
    ],
}
EMOJIS = {
    "kitchen": ["🌿", "🐝", "🧽", "🥬", "🍋", "♻️", "🧼", "🥣", "🌱", "☕"],
    "bathroom": ["🛁", "🍃", "🫧", "🧼", "🌸", "🌿", "🪒", "💧", "🌱", "✨"],
    "on-the-go": ["💧", "🥤", "☕", "🍴", "🥪", "🎒", "🌍", "🧳", "🥡", "♻️"],
}


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, f):
    return tuple(int(a[i] * (1 - f) + b[i] * f) for i in range(3))


def fnt(path, size):
    return ImageFont.truetype(path, size)


def fit_font(draw, lines, path, max_w, start, stop):
    for size in range(start, stop - 1, -4):
        f = fnt(path, size)
        if max(draw.textlength(l, font=f) for l in lines) <= max_w:
            return f, size
    return fnt(path, stop), stop


def spaced(draw, xy, text, font, fill, spacing):
    """Draw centered text with letter spacing around xy=(cx, y)."""
    widths = [draw.textlength(c, font=font) for c in text]
    total = sum(widths) + spacing * (len(text) - 1)
    x = xy[0] - total / 2
    for c, w in zip(text, widths):
        draw.text((x, xy[1]), c, font=font, fill=fill)
        x += w + spacing


def emoji_image(char, size):
    try:
        f = ImageFont.truetype(F_EMOJI, 160)
        im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((20, 10), char, font=f, embedded_color=True)
        bbox = im.getbbox()
        if not bbox:
            return None
        im = im.crop(bbox)
        scale = size / max(im.size)
        return im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    except Exception:
        return None


def cover(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l, tp = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((l, tp, l + w, tp + h))


def render_pin(t, pin, dest):
    slug = t["slug"]
    pal = PALETTES[slug][(pin["n"] - 1) % 10]
    bg, circ, ink, pill_bg, pill_ink = (rgb(c) for c in pal)

    photo = None
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = ROOT / "photos" / slug / f"pin-{pin['n']:02d}.{ext}"
        if p.exists():
            photo = Image.open(p).convert("RGB")
            break
    if photo:  # white text over a darkened photo
        ink, pill_bg, pill_ink = (255, 255, 255), (255, 255, 255), (30, 30, 30)

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    main = pin["main"]
    f_main, size = fit_font(probe, main, F_HEAD, 840, 150, 70)
    lh = int(size * 1.14)
    main_h = lh * len(main)
    f_sub, _ = fit_font(probe, [pin["sub"]], F_BODY_B, 780, 42, 28)
    sub_w = probe.textlength(pin["sub"], font=f_sub)
    pill_h, pill_w = 96, int(sub_w + 90)

    emoji_size = 230
    gap1, gap2, gap3 = 70, 56, 72
    total = emoji_size + gap1 + main_h + gap2 + 6 + gap3 + pill_h
    y0 = (H - total) // 2 + 10
    y_emoji = y0
    y_main = y_emoji + emoji_size + gap1
    y_rule = y_main + main_h + gap2
    y_pill = y_rule + 6 + gap3

    # shapes are drawn at 2x and scaled down so edges are smooth
    S = 2
    if photo:
        base = cover(photo, W, H).convert("RGBA")
        base = Image.alpha_composite(base, Image.new("RGBA", (W, H), (0, 0, 0, 120)))
    else:
        bl = Image.new("RGB", (W * S, H * S), bg)
        d = ImageDraw.Draw(bl)
        for cx, cy, r in ((860, 230, 400), (90, 1380, 340)):
            d.ellipse(((cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S), fill=circ)
        base = bl.resize((W, H), Image.LANCZOS).convert("RGBA")

    ov = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle((W // 2 * S - 60 * S, y_rule * S, W // 2 * S + 60 * S, (y_rule + 6) * S),
                        radius=3 * S, fill=pill_bg)
    d.rounded_rectangle(((W - pill_w) // 2 * S, y_pill * S, (W + pill_w) // 2 * S, (y_pill + pill_h) * S),
                        radius=(pill_h // 2) * S, fill=pill_bg)
    img = Image.alpha_composite(base, ov.resize((W, H), Image.LANCZOS)).convert("RGB")

    dr = ImageDraw.Draw(img)
    label_color = mix(ink, bg, 0.35) if not photo else (235, 235, 235)
    spaced(dr, (W / 2, 96), t["label"], fnt(F_BODY_B, 28), label_color, 6)

    em = emoji_image(pin.get("emoji") or EMOJIS[slug][(pin["n"] - 1) % 10], emoji_size)
    if em:
        img.paste(em, ((W - em.width) // 2, y_emoji + (emoji_size - em.height) // 2), em)

    for i, line in enumerate(main):
        w = dr.textlength(line, font=f_main)
        dr.text(((W - w) / 2, y_main + i * lh), line, font=f_main, fill=ink)

    dr.text((W / 2, y_pill + pill_h / 2 + 1), pin["sub"], font=f_sub, fill=pill_ink, anchor="mm")
    dr.text((W / 2, H - 80), HANDLE, font=fnt(F_BODY, 30), fill=label_color, anchor="mm")

    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG", optimize=True)


# --------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------
def keywords(desc):
    tags = [w.lstrip("#") for w in re.findall(r"#\w+", desc)]
    return ", ".join(t for t in tags if t.lower() != "ad")


def write_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["Title", "Media URL", "Pinterest board", "Thumbnail", "Description",
            "Link", "Publish date", "Keywords"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def schedule(start, count):
    out = []
    for i in range(count):
        day = start + dt.timedelta(days=i // len(SLOTS_UTC))
        out.append(f"{day.isoformat()}T{SLOTS_UTC[i % len(SLOTS_UTC)]}")
    return out


def check_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", str(e))


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", action="append", choices=TOPICS, help="build just this topic")
    ap.add_argument("--start", help="first publish date YYYY-MM-DD (default: tomorrow)")
    ap.add_argument("--preview", action="store_true",
                    help="also render pin images for unfinished topics into out/preview/")
    ap.add_argument("--include-posted", action="store_true", help="include pins marked as already posted")
    ap.add_argument("--verify-urls", action="store_true",
                    help="after deploying: check that every image + page URL in the CSV is live")
    a = ap.parse_args()

    topics = a.only or TOPICS
    start = dt.date.fromisoformat(a.start) if a.start else dt.date.today() + dt.timedelta(days=1)
    problems, csv_rows, summary = 0, [], []

    for slug in topics:
        t = json.loads((ROOT / "data" / f"{slug}.json").read_text())
        raw = read_links(slug)
        links, errors, missing = {}, [], []
        for p in t["products"]:
            url, err, note = normalize_link(raw.get(p["n"], ""))
            if err:
                errors.append(f"  #{p['n']} {p['title']}: {err}")
            elif url is None:
                missing.append(p["n"])
            else:
                links[p["n"]] = url
        dupes = {u for u in links.values() if list(links.values()).count(u) > 1}
        for u in dupes:
            errors.append(f"  the same link is used more than once: {u}")

        print(f"\n== {slug}: {len(links)}/10 links ready")
        for e in errors:
            print("  ERROR" + e[1:])
        if missing:
            print("  still missing: " + ", ".join(
                f"#{n} {t['products'][n-1]['title']}" for n in missing))
        problems += len(errors)

        ready = len(links) == 10 and not errors
        if ready:
            page = build_page(t, links)
            print(f"  page   -> {page.relative_to(ROOT)}")
            for pin in t["pins"]:
                render_pin(t, pin, SITE / "pins" / slug / f"pin-{pin['n']:02d}.png")
            print(f"  pins   -> site/pins/{slug}/ (10 images)")
            todo = [p for p in t["pins"] if a.include_posted or not p.get("posted")]
            for p in todo:
                csv_rows.append({
                    "Title": p["title"],
                    "Media URL": f"{BASE}/pins/{slug}/pin-{p['n']:02d}.png",
                    "Pinterest board": t["board"], "Thumbnail": "",
                    "Description": p["description"], "Link": t["url"],
                    "Publish date": "", "Keywords": keywords(p["description"]),
                })
            summary.append((slug, len(todo)))
        else:
            print("  -> page and pins NOT built yet (need all 10 valid links)")
            if a.preview:
                for pin in t["pins"]:
                    render_pin(t, pin, OUT / "preview" / slug / f"pin-{pin['n']:02d}.png")
                print(f"  preview pins -> out/preview/{slug}/")

    if csv_rows:
        for row, when in zip(csv_rows, schedule(start, len(csv_rows))):
            row["Publish date"] = when
        last = dt.date.fromisoformat(csv_rows[-1]["Publish date"][:10])
        if (last - dt.date.today()).days > 30:
            print("\nWARNING: Pinterest only accepts dates up to 30 days ahead; split with --only / --start")
        write_csv(csv_rows, OUT / "pinterest-upload.csv")
        print(f"\nCSV -> out/pinterest-upload.csv  ({len(csv_rows)} pins, "
              f"{csv_rows[0]['Publish date'][:10]} to {csv_rows[-1]['Publish date'][:10]})")
        for slug, n in summary:
            print(f"   {slug}: {n} pins")
    else:
        print("\nNo CSV written (no topic is complete yet).")

    if a.verify_urls:
        bad = 0
        urls = [r["Media URL"] for r in csv_rows] + [
            json.loads((ROOT / "data" / f"{s}.json").read_text())["url"] for s, _ in summary]
        for u in urls:
            code = check_url(u)
            if code != 200:
                bad += 1
                print(f"  NOT LIVE ({code}): {u}")
        print(f"\nverify: {len(urls) - bad}/{len(urls)} URLs live")
        problems += bad

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
