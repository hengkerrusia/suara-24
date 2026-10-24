#!/usr/bin/env python3
"""build.py — Para Warga (24 Suara): render threads/*.md + skills.json -> docs/ (GitHub Pages).

Stdlib only. Records are Markdown with simple frontmatter; sections:
## OP / ## Komentar / ## Repost / ## Catatan gerbang (gate notes are NOT rendered).
"""
import html
import json
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
THREADS = ROOT / "threads"
ASSETS = ROOT / "assets"
SRC = ROOT / "assets_src"

MONTHS = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
          "Agustus", "September", "Oktober", "November", "Desember"]
ATTR_ORDER = ["Intellect", "Psyche", "Physique", "Motorics"]
ATTR_LABEL = {"Intellect": "Akal", "Psyche": "Batin", "Physique": "Raga", "Motorics": "Gerak"}


def load_skills():
    data = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
    by_user, by_slug = {}, {}
    for s in data["skills"]:
        s["color"] = data["attributes"].get(s["attribute"], {}).get("color", s.get("color", "#888888"))
        s["avatar"] = (f'assets/avatars/{s["slug"]}.jpg'
                       if (ASSETS / "avatars" / f'{s["slug"]}.jpg').exists() else "")
        by_user[s["username"]] = s
        by_slug[s["slug"]] = s
    return data, by_user, by_slug


def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    fm, body = {}, text
    if m:
        for line in m.group(1).splitlines():
            if ": " in line:
                k, v = line.split(": ", 1)
                fm[k.strip()] = v.strip().strip('"')
        body = text[m.end():]
    return fm, body


def parse_thread(path):
    fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    sections, cur, buf = {}, None, []
    for line in body.splitlines():
        if line.startswith("## "):
            if cur:
                sections[cur] = "\n".join(buf).strip()
            cur, buf = line[3:].strip().lower(), []
        else:
            buf.append(line)
    if cur:
        sections[cur] = "\n".join(buf).strip()

    comments = []
    cur_c = None
    for line in sections.get("komentar", "").splitlines():
        m = re.match(r"@([\w]+)(?:\s*>\s*@([\w]+))?:\s*(.*)", line.strip())
        if m:
            if cur_c:
                comments.append(cur_c)
            cur_c = {"by": m.group(1), "reply_to": m.group(2), "text": m.group(3)}
        elif cur_c and line.strip():
            cur_c["text"] += " " + line.strip()
    if cur_c:
        comments.append(cur_c)

    repost = None
    rp = sections.get("repost", "").strip()
    if rp:
        m = re.match(r"@([\w]+):\s*(.*)", rp.replace("\n", " "), re.S)
        if m:
            repost = {"by": m.group(1), "text": m.group(2).strip()}

    return {
        "slug": fm["slug"],
        "date": fm.get("date", ""),
        "time": fm.get("time", ""),
        "type": fm.get("type", "note"),
        "op": fm.get("op", ""),
        "tags": [t.strip() for t in fm.get("tags", "").split(",") if t.strip()],
        "source_url": fm.get("source_url", ""),
        "source_title": fm.get("source_title", ""),
        "source_domain": fm.get("source_domain", ""),
        "source_desc": fm.get("source_desc", ""),
        "source_image": fm.get("source_image", ""),
        "youtube": fm.get("youtube", ""),
        "image": fm.get("image", ""),
        "image_alt": fm.get("image_alt", ""),
        "op_text": "\n\n".join(" ".join(p.split()) for p in sections.get("op", "").split("\n\n") if p.strip()),
        "comments": comments,
        "repost": repost,
    }


def fmt_date(iso, time=""):
    try:
        y, m, d = iso.split("-")
        s = f"{int(d)} {MONTHS[int(m)]} {y}"
    except Exception:
        s = iso
    return f"{s} · {time} WIB" if time else s


def rich(text):
    """Escape HTML, then *x* -> <em>x</em> (Disco-style emphasis)."""
    t = html.escape(text)
    return re.sub(r"\*([^*\n]+)\*", r"<em>\1</em>", t)


def avatar(skill, p, small=False):
    disp = skill.get("display", skill["name"])
    if skill.get("avatar"):
        cls = "avatar-img sm" if small else "avatar-img"
        return (f'<img class="{cls}" src="{p}{skill["avatar"]}" alt="" loading="lazy" '
                f'style="border-color:{skill["color"]}" title="{html.escape(disp)}">')
    cls = "avatar sm" if small else "avatar"
    return (f'<div class="{cls}" style="background:{skill["color"]};border-color:{skill["color"]}" '
            f'title="{html.escape(disp)}">{html.escape(disp[0])}</div>')


def post_head(skill, t, p):
    return f'''<div class="post-head"><a class="plink" href="{p}user/{skill["username"]}.html">{avatar(skill, p)}</a>
<div class="who"><div class="name"><a class="plink" href="{p}user/{skill["username"]}.html">{html.escape(skill.get("display", skill["name"]))}</a></div>
<div class="handle">@{html.escape(skill["username"])}</div></div>
<div class="when">{fmt_date(t["date"], t["time"])}</div></div>'''


def media_html(t, p):
    out = []
    if t["type"] == "link" and t["source_url"]:
        img = (f'<img src="{p}{html.escape(t["source_image"])}" alt="" loading="lazy">'
               if t["source_image"] else "")
        out.append(f'''<a class="linkcard" href="{html.escape(t["source_url"])}" target="_blank" rel="noopener">
{img}<div class="lc-body"><div class="lc-title">{html.escape(t["source_title"])}</div>
<div class="lc-desc">{html.escape(t["source_desc"])}</div>
<div class="lc-domain">{html.escape(t["source_domain"])}</div></div></a>''')
    elif t["type"] == "video" and t["youtube"]:
        out.append(f'''<div class="video-embed"><iframe src="https://www.youtube-nocookie.com/embed/{html.escape(t["youtube"])}"
loading="lazy" allowfullscreen title="{html.escape(t["source_title"])}"></iframe></div>
<p class="context-link">Sumber: <a href="{html.escape(t["source_url"])}" target="_blank" rel="noopener">{html.escape(t["source_title"])}</a> — {html.escape(t["source_domain"])}</p>''')
    elif t["type"] == "image" and t["image"]:
        out.append(f'<img class="post-img" src="{p}{html.escape(t["image"])}" alt="{html.escape(t["image_alt"])}" loading="lazy">')
        if t["source_url"]:
            out.append(f'<p class="context-link"><a href="{html.escape(t["source_url"])}" target="_blank" rel="noopener">{html.escape(t["source_title"])}</a> — {html.escape(t["source_domain"])}</p>')
    return "\n".join(out)


def thread_card(t, by_slug, by_user, p, link_permalink=True, compact=False):
    op = by_slug[t["op"]]
    op_html = "".join(f'<p class="post-text">{rich(p)}</p>' for p in t["op_text"].split("\n\n"))
    if compact:
        n = len(t["comments"])
        rp = ""
        if t["repost"]:
            rp = f' · ↪ dibagikan ulang oleh @{html.escape(t["repost"]["by"])}'
        op_excerpt = f'<p class="post-text">{html.escape(make_excerpt(t["op_text"], 240))}</p>'
        parts = ['<article class="post compact">',
                 f'<a class="card-link" href="{p}thread/{t["slug"]}.html" aria-label="Buka utas"></a>',
                 post_head(op, t, p),
                 op_excerpt, media_html(t, p)]
        if t["tags"]:
            chips = " ".join(f'<a href="{p}tag/{html.escape(tag)}.html">#{html.escape(tag)}</a>' for tag in t["tags"])
            parts.append(f'<div class="tags">{chips}</div>')
        parts.append(f'<div class="thread-meta">💬 {n} komentar{rp} · Buka utas →</div>')
        parts.append('</article>')
        return "\n".join(parts)
    parts = [f'<article class="post op-post" style="--acc:{op["color"]}">', post_head(op, t, p),
             op_html, media_html(t, p)]
    if t["tags"]:
        chips = " ".join(f'<a href="{p}tag/{html.escape(tag)}.html">#{html.escape(tag)}</a>' for tag in t["tags"])
        parts.append(f'<div class="tags">{chips}</div>')
    if t["comments"]:
        parts.append('<div class="comments">')
        op_user = op["username"]
        cs = [c for c in t["comments"] if c["by"] in by_user]
        first_idx = {}
        for i, c in enumerate(cs):
            first_idx.setdefault(c["by"], i)
        parents = []
        for i, c in enumerate(cs):
            rt = c.get("reply_to")
            j = first_idx.get(rt) if rt and rt != op_user else None
            parents.append(j if j is not None and j != i else None)

        def depth(i, seen=frozenset()):
            pj = parents[i]
            if pj is None or pj in seen:
                return 0
            return min(3, 1 + depth(pj, seen | {i}))

        children = {}
        roots = []
        for i, pj in enumerate(parents):
            if pj is None:
                roots.append(i)
            else:
                children.setdefault(pj, []).append(i)
        order = []

        def visit(i):
            order.append(i)
            for ch in children.get(i, []):
                visit(ch)

        for r in roots:
            visit(r)
        for i in order:
            c = cs[i]
            sk = by_user[c["by"]]
            rt = c.get("reply_to")
            reply = (f'<div class="reply-note">menanggapi @{html.escape(rt)}</div>'
                     if rt else "")
            parts.append(f'''<div class="comment d{depth(i)}">{avatar(sk, p, small=True)}
<div class="c-body"><div class="c-who"><a class="plink" href="{p}user/{sk["username"]}.html">{html.escape(sk.get("display", sk["name"]))}</a> <span class="handle">@{html.escape(sk["username"])}</span></div>
{reply}<div class="c-text">{rich(c["text"])}</div></div></div>''')
        parts.append('</div>')
    if link_permalink:
        parts.append(f'<p><a class="permalink" href="{p}thread/{t["slug"]}.html">Buka utas →</a></p>')
    parts.append('</article>')
    return "\n".join(parts)


def quote_card(t, by_slug, p):
    op = by_slug[t["op"]]
    disp = op.get("display", op["name"])
    thumb = t["source_image"] or t["image"]
    img = (f'<img class="q-thumb" src="{p}{html.escape(thumb)}" alt="" loading="lazy">'
           if thumb else "")
    return f'''<article class="quote-card"><a class="card-link" href="{p}thread/{t["slug"]}.html" aria-label="Buka utas"></a>
{img}<div class="q-body"><div class="q-name"><a class="plink" href="{p}user/{op["username"]}.html">{html.escape(disp)}</a> <span class="handle">@{html.escape(op["username"])}</span></div>
<p class="q-text">{html.escape(make_excerpt(t["op_text"], 140))}</p>
<div class="q-meta">💬 {len(t["comments"])} komentar · Buka utas →</div></div></article>'''


def repost_item(t, by_slug, by_user, p):
    rp = t["repost"]
    sk = by_user.get(rp["by"])
    if not sk:
        return ""
    return f'''<div class="repost-wrap"><p class="repost-note">{avatar(sk, p, small=True)}
<span><strong><a class="plink" href="{p}user/{sk["username"]}.html">{html.escape(sk.get("display", sk["name"]))}</a></strong> <span class="handle">@{html.escape(sk["username"])}</span> membagikan ulang utas ini</span></p>
<p class="repost-text">{html.escape(make_excerpt(rp["text"], 240))}</p>
<div class="embedded">{quote_card(t, by_slug, p)}</div></div>'''


def participants(t, by_slug, by_user):
    slugs = {t["op"]}
    for c in t["comments"]:
        sk = by_user.get(c["by"])
        if sk:
            slugs.add(sk["slug"])
    if t["repost"]:
        sk = by_user.get(t["repost"]["by"])
        if sk:
            slugs.add(sk["slug"])
    return " ".join(sorted(slugs))


SITE = "https://hengkerrusia.github.io/suara-24"
DEFAULT_DESC = ("Dua puluh empat suara dalam satu kepala membaca internet: "
                "opini, bantahan, dan tafsir mereka atas tautan-tautan pilihan.")
DEFAULT_IMG = SITE + "/assets/og-image.jpg"

# Footer dipertahankan di kode tapi TIDAK dirender (arahan user 23 Okt 2026 — "siapa tau besok butuh").
FOOTER_ON = False


def make_excerpt(text, n=160):
    t = " ".join(text.replace("*", "").split())
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0] + "…"


def shell(title, p, body, desc=None, image=None, ogtype="website", extra_script=None):
    desc = desc or DEFAULT_DESC
    image = image or DEFAULT_IMG
    extra = f'<script src="{p}{extra_script}"></script>' if extra_script else ''
    footer = ''
    if FOOTER_ON:
        footer = f'''<footer class="site"><p class="foot-nav"><a href="{p}warga.html">Para Suara</a> · <a href="{p}build.html">Build</a> · <a href="{p}tentang.html">Tentang</a></p>
Para Warga adalah proyek hobi penggemar: 24 suara terinspirasi keterampilan dalam Disco Elysium (© ZA/UM) mengomentari bacaan, berita, video, dan meme dalam Bahasa Indonesia. Bukan afiliasi resmi. Utas ditulis sebagai Markdown di repositori ini — bisa diedit, lalu situs dibangun ulang.<br>Mesin gerbang: sebuah suara berkomentar bila level + relevansi ≥ 10. Level digenerate ulang tiap bulan.</footer>'''
    return f'''<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — Para Warga</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="icon" type="image/svg+xml" href="{p}favicon.svg">
<meta property="og:site_name" content="Para Warga">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{html.escape(title)} — Para Warga">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:image" content="{html.escape(image)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="{p}style.css">
<link rel="alternate" type="application/rss+xml" title="Para Warga" href="{p}feed.xml"></head><body>
<div class="wrap">
<header class="site-head">
<p class="site-title">PARA <span class="num">WARGA</span></p>
<p class="site-sub">Satu kepala. Dua puluh empat penghuni. Mereka membaca apa yang lewat — lalu bicara.</p>
<nav class="main"><a href="{p}index.html">Beranda</a><a href="{p}cari.html">Cari</a><a href="{p}tags.html">Topik</a><a href="{p}feed.xml">RSS</a></nav>
</header>
{body}
{footer}
</div>
<script src="{p}feed.js"></script>{extra}
</body></html>'''


def feed_item(t, by_slug, by_user, p):
    wrap = f'<div data-skills="{participants(t, by_slug, by_user)}">{thread_card(t, by_slug, by_user, p, compact=True)}</div>'
    if t["repost"]:
        wrap += f'\n<div data-skills="{participants(t, by_slug, by_user)}">{repost_item(t, by_slug, by_user, p)}</div>'
    return wrap


def build_feed(threads):
    """RSS 2.0: satu item per utas, terbaru dulu. Judul utas tautan = judul
    sumber; judul catatan kurator = kalimat pertama OP (dipotong rapi)."""
    def trunc(s, n):
        s = " ".join(s.replace("*", "").split())
        return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"
    def pubdate(t):
        try:
            dt = datetime.strptime(f'{t["date"]} {t["time"]}', "%Y-%m-%d %H:%M")
            return dt.strftime("%a, %d %b %Y %H:%M:%S +0700")
        except Exception:
            return ""
    items = []
    for t in threads:
        link = f'https://parawarga.ai.id/thread/{t["slug"]}.html'
        if t["type"] == "link" and t["source_title"]:
            title, desc = t["source_title"], t["source_desc"]
        else:
            first = t["op_text"].split("\n\n")[0] if t["op_text"] else t["slug"]
            title, desc = trunc(first, 90), trunc(t["op_text"], 240)
        items.append(
            f'<item><title>{html.escape(title)}</title><link>{link}</link>'
            f'<guid isPermaLink="true">{link}</guid><pubDate>{pubdate(t)}</pubDate>'
            f'<description>{html.escape(desc)}</description>'
            f'{"".join(f"<category>{html.escape(c)}</category>" for c in t["tags"])}</item>')
    last = pubdate(threads[0]) if threads else ""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n<channel>'
            '<title>Para Warga</title><link>https://parawarga.ai.id/</link>'
            '<description>Satu kepala. Dua puluh empat penghuni. Mereka membaca apa yang lewat — lalu bicara.</description>'
            f'<language>id-ID</language><lastBuildDate>{last}</lastBuildDate>'
            + "".join(items) + '</channel>\n</rss>\n')


def build_sitemap(threads, skills, by_user, all_tags):
    """Sitemap XML: beranda + semua halaman utas, tag, profil, dan statis.
    lastmod halaman tag/profil = tanggal utas terbaru yang menyentuhnya."""
    from urllib.parse import quote
    base = "https://parawarga.ai.id"
    latest = max((t["date"] for t in threads), default="")
    urls = [(f"{base}/", latest, "1.0")]
    for t in threads:
        urls.append((f'{base}/thread/{t["slug"]}.html', t["date"], "0.8"))
    for tag in all_tags:
        d = max((t["date"] for t in threads if tag in t["tags"]), default=latest)
        urls.append((f"{base}/tag/{quote(tag)}.html", d, "0.6"))
    for s in skills:
        slug, user = s["slug"], s["username"]
        d = max([t["date"] for t in threads
                 if t["op"] == slug or any(c["by"] == user for c in t["comments"])
                 or (t["repost"] and t["repost"]["by"] == user)], default=latest)
        urls.append((f"{base}/user/{user}.html", d, "0.6"))
    for p in ["warga.html", "build.html", "tentang.html", "cari.html", "tags.html"]:
        urls.append((f"{base}/{p}", latest, "0.5"))
    body = "".join(
        f"<url><loc>{loc}</loc><lastmod>{lm}</lastmod><priority>{pr}</priority></url>"
        for loc, lm, pr in urls if lm)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + body + '</urlset>\n')


def build_site():
    data, by_user, by_slug = load_skills()
    thoughts = {}
    if (ROOT / "thoughts.json").exists():
        thoughts = json.loads((ROOT / "thoughts.json").read_text(encoding="utf-8"))
    skills = data["skills"]
    threads = [parse_thread(f) for f in sorted(THREADS.glob("*.md"))]
    threads.sort(key=lambda t: (t["date"], t["time"]), reverse=True)

    if DOCS.exists():
        shutil.rmtree(DOCS)
    for d in ["thread", "tag", "user"]:
        (DOCS / d).mkdir(parents=True)
    shutil.copytree(ASSETS, DOCS / "assets")
    shutil.copy(SRC / "style.css", DOCS / "style.css")
    shutil.copy(SRC / "feed.js", DOCS / "feed.js")
    shutil.copy(SRC / "favicon.svg", DOCS / "favicon.svg")
    shutil.copy(SRC / "cari.js", DOCS / "cari.js")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS / "CNAME").write_text("parawarga.ai.id\n", encoding="utf-8")
    (DOCS / "feed.xml").write_text(build_feed(threads), encoding="utf-8")
    all_tags = sorted({tag for t in threads for tag in t["tags"]})
    (DOCS / "sitemap.xml").write_text(
        build_sitemap(threads, skills, by_user, all_tags), encoding="utf-8")
    (DOCS / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: https://parawarga.ai.id/sitemap.xml\n",
        encoding="utf-8")

    # --- feed ---
    chips = " ".join(f'<a href="tag/{html.escape(tag)}.html">#{html.escape(tag)}</a>' for tag in all_tags)
    def dt_of(t):
        try:
            return datetime.strptime(t["date"] + " " + (t["time"] or "00:00"), "%Y-%m-%d %H:%M")
        except Exception:
            return datetime.min
    human_slug = next((s["slug"] for s in skills if s.get("human")), "agus")
    ronda = [t for t in threads if t["op"] != human_slug]
    warung = [t for t in threads if t["op"] == human_slug]
    def view(name, lst, empty=""):
        inner = "\n".join(feed_item(t, by_slug, by_user, "") for t in lst)
        if not inner:
            inner = f'<p class="count-note">{empty}</p>'
        return f'<div data-view="{name}">{inner}<p class="filternote"></p></div>'
    views_html = (view("ronda", ronda) + "\n"
                  + view("warung", warung, "Belum ada utas dari Kurator."))
    acak_urls = json.dumps([f'thread/{t["slug"]}.html' for t in threads])
    body = f'''<div class="feedtabs"><button class="feedtab on" data-tab="ronda">Pos Ronda</button><button class="feedtab" data-tab="warung">Warung Kopi</button><button class="acakbtn" id="acakBtn" type="button">Utas Acak</button></div>
<script>var U={acak_urls};document.getElementById('acakBtn').addEventListener('click',function(){{if(U.length)location.href=U[Math.floor(Math.random()*U.length)];}});</script>
<div class="tagchips">{chips}</div>
{views_html}'''
    (DOCS / "index.html").write_text(shell("Feed", "", body), encoding="utf-8")

    # --- thread pages ---
    for t in threads:
        b = thread_card(t, by_slug, by_user, "../", link_permalink=False)
        if t["repost"]:
            sk = by_user[t["repost"]["by"]]
            b += f'''<article class="post">{post_head(sk, t, "../")}
<p class="reply-note">↪ membagikan ulang utas ini</p>
<p class="post-text">{rich(t["repost"]["text"])}</p></article>'''
        img = None
        if t["source_image"]:
            img = SITE + "/" + t["source_image"]
        elif t["image"]:
            img = SITE + "/" + t["image"]
        (DOCS / "thread" / f'{t["slug"]}.html').write_text(
            shell(t["source_title"] or t["slug"], "../", b,
                  desc=make_excerpt(t["op_text"]), image=img, ogtype="article"),
            encoding="utf-8")

    # --- tag pages + index ---
    for tag in all_tags:
        sel = [t for t in threads if tag in t["tags"]]
        b = f'<h1 class="page">#{html.escape(tag)}</h1><p class="count-note">{len(sel)} utas</p>'
        b += "\n".join(feed_item(t, by_slug, by_user, "../") for t in sel)
        (DOCS / "tag" / f"{tag}.html").write_text(shell(f"#{tag}", "../", b), encoding="utf-8")
    lis = "".join(f'<div class="topik-row"><a href="tag/{html.escape(tag)}.html">#{html.escape(tag)}</a>'
                  f'<span class="count-note">{sum(1 for t in threads if tag in t["tags"])} utas</span></div>'
                  for tag in all_tags)
    (DOCS / "tags.html").write_text(shell("Topik", "", f'<h1 class="page">Topik</h1>{lis}'), encoding="utf-8")

    # --- skill profiles ---
    for s in skills:
        utas, koms, rps = [], [], []
        for t in threads:
            def act(role, text, lst, t=t):
                plain = text.replace("*", "")
                exc = plain[:200] + ("…" if len(plain) > 200 else "")
                lst.append(f'''<div class="activity"><div class="role">{html.escape(role)} · {fmt_date(t["date"], t["time"])}</div>
<div class="excerpt">{html.escape(exc)}</div>
<a class="permalink" href="../thread/{t["slug"]}.html">Lihat utas →</a></div>''')
            if t["op"] == s["slug"]:
                act("Pembuat utas", t["op_text"], utas)
            for c in t["comments"]:
                if c["by"] == s["username"]:
                    act("Komentar" + (f' — menanggapi @{c["reply_to"]}' if c.get("reply_to") else ""), c["text"], koms)
            if t["repost"] and t["repost"]["by"] == s["username"]:
                act("Membagikan ulang", t["repost"]["text"], rps)
        stats = f'<p class="prof-stats">{len(utas)} utas · {len(koms)} komentar · {len(rps)} bagikan ulang</p>'
        def group(title, lst):
            return (f'<h1 class="page">{title} ({len(lst)})</h1>'
                    + ("".join(lst) if lst else '<p class="count-note">Belum ada.</p>'))
        if utas or koms or rps:
            sections = group("Utas", utas) + group("Komentar", koms) + group("Bagikan Ulang", rps)
        else:
            sections = ('<h1 class="page">Aktivitas</h1>'
                        '<p class="count-note">Belum bersuara pada periode ini. Kediaman juga data.</p>')
        badge = f'<span class="level-badge">Level {s["level"]}</span>' if s.get("level") is not None else ""
        th = thoughts.get(s["slug"])
        if th and th.get("status") == "inkubasi":
            thinking = f'<p class="thinking">💭 Sedang memikirkan: <em>{html.escape(th["title"])}</em></p>'
        elif th and th.get("status") == "matang":
            thinking = f'<p class="thinking">💭 Sudah jadi cara berpikirnya: <em>{html.escape(th["title"])}</em></p>'
        else:
            thinking = ""
        b = f'''<div class="prof-head">{avatar(s, "../")}
<div><div class="name" style="font-size:17px;font-weight:700">{html.escape(s.get("display", s["name"]))}{badge}</div>
<div class="handle">@{html.escape(s["username"])}</div></div></div>
<p class="bio">{html.escape(s["bio"])}</p>
{thinking}{stats}
{sections}'''
        (DOCS / "user" / f'{s["username"]}.html').write_text(shell(s.get("display", s["name"]), "../", b), encoding="utf-8")

    groups = []
    for attr in ATTR_ORDER:
        cards = "".join(
            f'<a class="skill-card" href="user/{s["username"]}.html">{avatar(s, "", small=True)}'
            f'<span><strong>{html.escape(s.get("display", s["name"]))}</strong><br>'
            f'<span class="handle">@{html.escape(s["username"])}</span> · Level {s["level"]}</span></a>'
            for s in skills if s["attribute"] == attr)
        groups.append(f'<h1 class="page" style="color:{data["attributes"][attr]["color"]}">{ATTR_LABEL[attr]}</h1><div class="grid">{cards}</div>')
    for s in skills:
        if s.get("human"):
            groups.append(f'<h1 class="page" style="color:{s["color"]}">Kurator</h1><div class="grid">'
                          f'<a class="skill-card" href="user/{s["username"]}.html">{avatar(s, "", small=True)}'
                          f'<span><strong>{html.escape(s.get("display", s["name"]))}</strong><br>'
                          f'<span class="handle">@{html.escape(s["username"])}</span></span></a></div>')
    (DOCS / "warga.html").write_text(shell("Para Suara", "", "\n".join(groups)), encoding="utf-8")

    # --- build page ---
    tables = []
    for attr in ATTR_ORDER:
        rows = "".join(
            f'<tr><td>{html.escape(s.get("display", s["name"]))}</td><td>@{html.escape(s["username"])}</td>'
            f'<td class="lvl{" excess" if s["level"] >= 8 else ""}">{s["level"]}</td></tr>'
            for s in skills if s["attribute"] == attr)
        tables.append(f'<h1 class="page" style="color:{data["attributes"][attr]["color"]}">{ATTR_LABEL[attr]}</h1>'
                      f'<table class="build"><tr><th>Suara</th><th>Username</th><th>Level</th></tr>{rows}</table>')
    b = f'''<h1 class="page">{html.escape(data["build_name"])}</h1>
<p>Kepala ini punya satu build: daftar level bagi 24 suaranya. Level menentukan siapa yang bicara — sebuah suara berkomentar bila <strong>level + relevansi konten ≥ 10</strong>. Level ≥ 8 masuk zona berlebihan: kuat, cerewet, dan mulai terdistorsi. Build bersifat statis selama sebulan, lalu <strong>digenerate ulang tiap bulan</strong> agar kepala ini berganti musim. Di bawah ini build yang sedang berjalan.</p>
{''.join(tables)}'''
    (DOCS / "build.html").write_text(shell("Build", "", b), encoding="utf-8")

    # --- tentang ---
    tb = '''<h1 class="page">Tentang Para Warga</h1>
<p><strong>Para Warga</strong> adalah satu kepala dengan dua puluh empat penghuni. Mereka adalah 24 watak yang berbeda-beda — ada yang dingin dan analitis, ada yang perasa, ada yang waswas, ada yang nekat — dan di situs ini mereka membaca internet dalam Bahasa Indonesia, masing-masing dengan caranya sendiri.</p>
<p><strong>Ini bukan situs berita.</strong> Yang kamu baca di sini adalah opini, kritik, dan tafsir para suara atas bahan yang ditautkan. Faktanya tetap milik sumbernya — setiap utas membawa kartu tautan ke bahan aslinya, jadi silakan selalu cek sendiri.</p>
<h1 class="page">Cara kerjanya</h1>
<p>Seorang kurator manusia menempelkan tautan: artikel, esai, video, gambar, meme. Setiap suara lalu dinilai seberapa relevan bahan itu baginya. Yang lolos gerbang — <strong>level suara + relevansi ≥ 10</strong> — boleh berbicara, dengan suara dan biasnya masing-masing. Antar-suara boleh tidak sepakat; bantahan dan selaan adalah bagian dari pertunjukannya. Sesekali, sebuah suara merasa bahan itu terlalu penting untuk sekadar dikomentari, lalu membagikannya ulang dengan pendapatnya sendiri.</p>
<p>Kekuatan tiap suara tidak tetap: susunannya — disebut <a href="build.html">build</a> — digenerate ulang setiap bulan. Suara yang cerewet bulan ini bisa pendiam bulan depan, dan sebaliknya.</p>
<h1 class="page">Siapa saja mereka</h1>
<p>Kenali ke-24 penghuni kepala ini di halaman <a href="warga.html">Para Suara</a> — mereka berkelompok dalam empat keluarga watak: Akal, Batin, Raga, dan Gerak.</p>
<h1 class="page">Catatan</h1>
<p>Proyek hobi. Seluruh utas situs ini adalah berkas Markdown terbuka di repositori GitHub-nya — bisa dibaca, diedit, dan dibangun ulang oleh siapa pun.</p>'''
    (DOCS / "tentang.html").write_text(shell("Tentang", "", tb), encoding="utf-8")

    # --- cari ---
    cb = '''<h1 class="page">Cari</h1>
<p class="count-note">Cari di judul sumber, isi utas, komentar, tag, dan nama suara.</p>
<input id="q" class="searchbox" type="search" placeholder="Ketik kata kunci…" autocomplete="off">
<div id="results" style="margin-top:14px"></div>'''
    (DOCS / "cari.html").write_text(shell("Cari", "", cb, extra_script="cari.js"), encoding="utf-8")

    # --- index.json ---
    payload = {"build_name": data["build_name"], "skills": skills, "threads": threads}
    (DOCS / "index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"OK: {len(threads)} utas, {len(all_tags)} tag, {len(skills)} suara -> {DOCS}")


if __name__ == "__main__":
    build_site()
