#!/usr/bin/env python3
"""build.py — 24 Suara: render threads/*.md + skills.json -> docs/ (GitHub Pages).

Stdlib only. Records are Markdown with simple frontmatter; sections:
## OP / ## Komentar / ## Repost / ## Catatan gerbang (gate notes are NOT rendered).
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
THREADS = ROOT / "threads"
ASSETS = ROOT / "assets"
SRC = ROOT / "assets_src"

MONTHS = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
          "Agustus", "September", "Oktober", "November", "Desember"]
ATTR_ORDER = ["Intellect", "Psyche", "Physique", "Motorics"]


def load_skills():
    data = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
    by_user, by_slug = {}, {}
    for s in data["skills"]:
        s["color"] = data["attributes"][s["attribute"]]["color"]
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
        "op_text": " ".join(sections.get("op", "").split()),
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
    cls = "avatar sm" if small else "avatar"
    return (f'<div class="{cls}" style="background:{skill["color"]};border-color:{skill["color"]}" '
            f'title="{html.escape(skill["name"])}">{html.escape(skill["name"][0])}</div>')


def post_head(skill, t, p):
    return f'''<div class="post-head">{avatar(skill, p)}
<div class="who"><div class="name">{html.escape(skill["name"].upper())}</div>
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
    if compact:
        n = len(t["comments"])
        rp = ""
        if t["repost"]:
            rp = f' · ↪ dibagikan ulang oleh @{html.escape(t["repost"]["by"])}'
        parts = ['<article class="post compact">',
                 f'<a class="card-link" href="{p}thread/{t["slug"]}.html" aria-label="Buka utas"></a>',
                 post_head(op, t, p),
                 f'<p class="post-text">{rich(t["op_text"])}</p>', media_html(t, p)]
        if t["tags"]:
            chips = " ".join(f'<a href="{p}tag/{html.escape(tag)}.html">#{html.escape(tag)}</a>' for tag in t["tags"])
            parts.append(f'<div class="tags">{chips}</div>')
        parts.append(f'<div class="thread-meta">💬 {n} komentar{rp} · Buka utas →</div>')
        parts.append('</article>')
        return "\n".join(parts)
    parts = ['<article class="post">', post_head(op, t, p),
             f'<p class="post-text">{rich(t["op_text"])}</p>', media_html(t, p)]
    if t["tags"]:
        chips = " ".join(f'<a href="{p}tag/{html.escape(tag)}.html">#{html.escape(tag)}</a>' for tag in t["tags"])
        parts.append(f'<div class="tags">{chips}</div>')
    if t["comments"]:
        parts.append('<div class="comments">')
        for c in t["comments"]:
            sk = by_user.get(c["by"])
            if not sk:
                continue
            reply = (f'<div class="reply-note">menanggapi @{html.escape(c["reply_to"])}</div>'
                     if c.get("reply_to") else "")
            parts.append(f'''<div class="comment">{avatar(sk, p, small=True)}
<div class="c-body"><div class="c-who">{html.escape(sk["name"].upper())} <span class="handle">@{html.escape(sk["username"])}</span></div>
{reply}<div class="c-text">{rich(c["text"])}</div></div></div>''')
        parts.append('</div>')
    if link_permalink:
        parts.append(f'<p><a class="permalink" href="{p}thread/{t["slug"]}.html">Buka utas →</a></p>')
    parts.append('</article>')
    return "\n".join(parts)


def repost_item(t, by_slug, by_user, p):
    rp = t["repost"]
    sk = by_user.get(rp["by"])
    if not sk:
        return ""
    return f'''<div class="repost-wrap"><p class="repost-note">{avatar(sk, p, small=True)}
<span><strong>{html.escape(sk["name"].upper())}</strong> <span class="handle">@{html.escape(sk["username"])}</span> membagikan ulang utas ini</span></p>
<p class="repost-text">{rich(rp["text"])}</p>
<div class="embedded">{thread_card(t, by_slug, by_user, p, compact=True)}</div></div>'''


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
DEFAULT_IMG = SITE + "/assets/esai-moral.jpg"


def make_excerpt(text, n=160):
    t = " ".join(text.replace("*", "").split())
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0] + "…"


def shell(title, p, body, desc=None, image=None, ogtype="website"):
    desc = desc or DEFAULT_DESC
    image = image or DEFAULT_IMG
    return f'''<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — 24 Suara</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="icon" type="image/svg+xml" href="{p}favicon.svg">
<meta property="og:site_name" content="24 Suara">
<meta property="og:type" content="{ogtype}">
<meta property="og:title" content="{html.escape(title)} — 24 Suara">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:image" content="{html.escape(image)}">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="{p}style.css"></head><body>
<div class="wrap">
<header class="site-head">
<p class="site-title"><span class="num">24</span> SUARA</p>
<p class="site-sub">Satu kepala. Dua puluh empat penghuni. Mereka membaca apa yang lewat — lalu bicara.</p>
<nav class="main"><a href="{p}index.html">Feed</a><a href="{p}skills.html">Para Suara</a><a href="{p}tags.html">Tag</a><a href="{p}build.html">Build</a><a href="{p}tentang.html">Tentang</a></nav>
</header>
{body}
<footer class="site">24 Suara adalah proyek hobi penggemar: 24 suara terinspirasi keterampilan dalam Disco Elysium (© ZA/UM) mengomentari bacaan, berita, video, dan meme dalam Bahasa Indonesia. Bukan afiliasi resmi. Utas ditulis sebagai Markdown di repositori ini — bisa diedit, lalu situs dibangun ulang.<br>Mesin gerbang: sebuah suara berkomentar bila level + relevansi ≥ 10. Level digenerate ulang tiap bulan.</footer>
</div>
<script src="{p}feed.js"></script>
</body></html>'''


def feed_item(t, by_slug, by_user, p):
    wrap = f'<div data-skills="{participants(t, by_slug, by_user)}">{thread_card(t, by_slug, by_user, p, compact=True)}</div>'
    if t["repost"]:
        wrap += f'\n<div data-skills="{participants(t, by_slug, by_user)}">{repost_item(t, by_slug, by_user, p)}</div>'
    return wrap


def build_site():
    data, by_user, by_slug = load_skills()
    skills = data["skills"]
    threads = [parse_thread(f) for f in sorted(THREADS.glob("*.md"))]
    threads.sort(key=lambda t: (t["date"], t["time"]), reverse=True)

    if DOCS.exists():
        shutil.rmtree(DOCS)
    for d in ["thread", "tag", "skill"]:
        (DOCS / d).mkdir(parents=True)
    shutil.copytree(ASSETS, DOCS / "assets")
    shutil.copy(SRC / "style.css", DOCS / "style.css")
    shutil.copy(SRC / "feed.js", DOCS / "feed.js")
    shutil.copy(SRC / "favicon.svg", DOCS / "favicon.svg")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    all_tags = sorted({tag for t in threads for tag in t["tags"]})

    # --- feed ---
    opts = "".join(f'<option value="{s["slug"]}">{html.escape(s["name"])} — @{html.escape(s["username"])}</option>' for s in skills)
    chips = " ".join(f'<a href="tag/{html.escape(tag)}.html">#{html.escape(tag)}</a>' for tag in all_tags)
    items = "\n".join(feed_item(t, by_slug, by_user, "") for t in threads)
    body = f'''<div class="intro"><strong>Baru di sini?</strong> Kepala ini dihuni 24 suara. Sang kurator menempelkan tautan — artikel, video, gambar — lalu suara-suara itu membacanya dan berbicara sesuai karakternya: memuji, membantah, menafsir. Yang tampil di feed adalah awal utas; klik untuk membaca percakapannya. <a href="tentang.html">Ini situs apa? →</a></div>
<div class="filterbar"><label for="skill-filter">Saring suara</label>
<select id="skill-filter"><option value="">Semua suara</option>{opts}</select></div>
<div class="tagchips">{chips}</div>
{items}'''
    (DOCS / "index.html").write_text(shell("Feed", "", body), encoding="utf-8")

    # --- thread pages ---
    for t in threads:
        b = thread_card(t, by_slug, by_user, "../", link_permalink=False)
        if t["repost"]:
            sk = by_user[t["repost"]["by"]]
            b += f'''<article class="post">{post_head(sk, t, "../")}
<p class="reply-note">membagikan ulang utas ini</p>
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
    lis = "".join(f'<p><a href="tag/{html.escape(tag)}.html">#{html.escape(tag)}</a> '
                  f'<span class="count-note">({sum(1 for t in threads if tag in t["tags"])} utas)</span></p>'
                  for tag in all_tags)
    (DOCS / "tags.html").write_text(shell("Tag", "", f'<h1 class="page">Semua Tag</h1>{lis}'), encoding="utf-8")

    # --- skill profiles ---
    for s in skills:
        acts = []
        for t in threads:
            roles = []
            if t["op"] == s["slug"]:
                roles.append(("Pembuat utas", t["op_text"]))
            for c in t["comments"]:
                if c["by"] == s["username"]:
                    roles.append(("Komentar" + (f' — menanggapi @{c["reply_to"]}' if c.get("reply_to") else ""), c["text"]))
            if t["repost"] and t["repost"]["by"] == s["username"]:
                roles.append(("Membagikan ulang", t["repost"]["text"]))
            for role, text in roles:
                plain = text.replace("*", "")
                excerpt = plain[:200] + ("…" if len(plain) > 200 else "")
                acts.append(f'''<div class="activity"><div class="role">{html.escape(role)} · {fmt_date(t["date"], t["time"])}</div>
<div class="excerpt">{html.escape(excerpt)}</div>
<a class="permalink" href="../thread/{t["slug"]}.html">Lihat utas →</a></div>''')
        b = f'''<div class="prof-head">{avatar(s, "../")}
<div><div class="name" style="font-size:16px;letter-spacing:.22em;font-weight:700">{html.escape(s["name"].upper())}<span class="level-badge">Level {s["level"]}</span></div>
<div class="handle">@{html.escape(s["username"])}</div>
<div class="attr-label" style="color:{s["color"]}">{html.escape(s["attribute"])}</div></div></div>
<p class="bio">{html.escape(s["bio"])}</p>
<h1 class="page">Aktivitas</h1>
{''.join(acts) if acts else '<p class="count-note">Belum bersuara pada periode ini. Kediaman juga data.</p>'}'''
        (DOCS / "skill" / f'{s["slug"]}.html').write_text(shell(s["name"], "../", b), encoding="utf-8")

    groups = []
    for attr in ATTR_ORDER:
        cards = "".join(
            f'<a class="skill-card" href="skill/{s["slug"]}.html">{avatar(s, "", small=True)}'
            f'<span><strong style="letter-spacing:.14em">{html.escape(s["name"].upper())}</strong><br>'
            f'<span class="handle">@{html.escape(s["username"])}</span> · Level {s["level"]}</span></a>'
            for s in skills if s["attribute"] == attr)
        groups.append(f'<h1 class="page" style="color:{data["attributes"][attr]["color"]}">{attr}</h1><div class="grid">{cards}</div>')
    (DOCS / "skills.html").write_text(shell("Para Suara", "", "\n".join(groups)), encoding="utf-8")

    # --- build page ---
    tables = []
    for attr in ATTR_ORDER:
        rows = "".join(
            f'<tr><td>{html.escape(s["name"])}</td><td>@{html.escape(s["username"])}</td>'
            f'<td class="lvl{" excess" if s["level"] >= 8 else ""}">{s["level"]}</td></tr>'
            for s in skills if s["attribute"] == attr)
        tables.append(f'<h1 class="page" style="color:{data["attributes"][attr]["color"]}">{attr}</h1>'
                      f'<table class="build"><tr><th>Suara</th><th>Username</th><th>Level</th></tr>{rows}</table>')
    b = f'''<h1 class="page">{html.escape(data["build_name"])}</h1>
<p>Kepala ini punya satu build: daftar level bagi 24 suaranya. Level menentukan siapa yang bicara — sebuah suara berkomentar bila <strong>level + relevansi konten ≥ 10</strong>. Level ≥ 8 masuk zona berlebihan: kuat, cerewet, dan mulai terdistorsi. Build bersifat statis selama sebulan, lalu <strong>digenerate ulang tiap bulan</strong> agar kepala ini berganti musim. Di bawah ini build yang sedang berjalan.</p>
{''.join(tables)}'''
    (DOCS / "build.html").write_text(shell("Build", "", b), encoding="utf-8")

    # --- tentang ---
    tb = '''<h1 class="page">Tentang 24 Suara</h1>
<p><strong>24 Suara</strong> adalah satu kepala dengan dua puluh empat penghuni. Para penghuninya terinspirasi dari keterampilan-keterampilan dalam permainan <em>Disco Elysium</em> — logika, empati, naluri, ketakutan, dan dua puluh lainnya — dan di situs ini mereka membaca internet dalam Bahasa Indonesia.</p>
<p><strong>Ini bukan situs berita.</strong> Yang kamu baca di sini adalah opini, kritik, dan tafsir para suara atas bahan yang ditautkan. Faktanya tetap milik sumbernya — setiap utas membawa kartu tautan ke bahan aslinya, jadi silakan selalu cek sendiri.</p>
<h1 class="page">Cara kerjanya</h1>
<p>Seorang kurator manusia menempelkan tautan: artikel, esai, video, gambar, meme. Setiap suara lalu dinilai seberapa relevan bahan itu baginya. Yang lolos gerbang — <strong>level suara + relevansi ≥ 10</strong> — boleh berbicara, dengan suara dan biasnya masing-masing. Antar-suara boleh tidak sepakat; bantahan dan selaan adalah bagian dari pertunjukannya. Sesekali, sebuah suara merasa bahan itu terlalu penting untuk sekadar dikomentari, lalu membagikannya ulang dengan pendapatnya sendiri.</p>
<p>Kekuatan tiap suara tidak tetap: susunannya — disebut <a href="build.html">build</a> — digenerate ulang setiap bulan. Suara yang cerewet bulan ini bisa pendiam bulan depan, dan sebaliknya.</p>
<h1 class="page">Siapa saja mereka</h1>
<p>Kenali ke-24 penghuni kepala ini di halaman <a href="skills.html">Para Suara</a> — lengkap dengan atasan warna atributnya: Intellect, Psyche, Physique, dan Motorics.</p>
<h1 class="page">Catatan</h1>
<p>Proyek hobi seorang penggemar; bukan afiliasi resmi ZA/UM. Seluruh utas situs ini adalah berkas Markdown terbuka di repositori GitHub-nya — bisa dibaca, diedit, dan dibangun ulang oleh siapa pun.</p>'''
    (DOCS / "tentang.html").write_text(shell("Tentang", "", tb), encoding="utf-8")

    # --- index.json ---
    payload = {"build_name": data["build_name"], "skills": skills, "threads": threads}
    (DOCS / "index.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"OK: {len(threads)} utas, {len(all_tags)} tag, {len(skills)} suara -> {DOCS}")


if __name__ == "__main__":
    build_site()
