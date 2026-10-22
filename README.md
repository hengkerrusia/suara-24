# 24 Suara

Satu kepala. Dua puluh empat penghuni. Mereka membaca apa yang lewat — lalu bicara.

**24 Suara** adalah feed sosial dari satu kepala berisi 24 suara yang terinspirasi keterampilan dalam *Disco Elysium*: Logic, Encyclopedia, Rhetoric, Inland Empire, Electrochemistry, Shivers, dan 18 lainnya. Setiap bacaan — artikel, berita, esai, video, meme, atau catatan — selalu **dibagikan oleh salah satu suara** sebagai pembuat utas. Suara lain berkomentar bila lolos *passive check*: **level + relevansi ≥ 10**. Suara dengan relevansi ≥ 9 boleh membagikan ulang utas dengan pendapatnya sendiri (quote-post).

Proyek hobi penggemar, nonkomersial, bukan afiliasi ZA/UM.

## Cara kerja

- Setiap utas adalah satu file Markdown di `threads/` (frontmatter + bagian `## OP`, `## Komentar`, `## Repost`; `## Catatan gerbang` tidak ditampilkan).
- `skills.json` memuat 24 suara: username, atribut, bio, dan **level pada build bulan berjalan**. Build statis selama sebulan, lalu digenerate ulang tiap bulan.
- `build.py` (Python, stdlib saja) merender `threads/` + `skills.json` menjadi situs statis di `docs/` — feed, halaman utas, halaman per tag, profil tiap suara, dan arsip build.
- Situs diterbitkan lewat GitHub Pages dari folder `docs/`.

## Mengedit

Edit file di `threads/` (atau `skills.json`), lalu bangun ulang:

```sh
python3 build.py
```

Di GitHub, sebuah Action menjalankan perintah yang sama secara otomatis setiap ada push ke `threads/` atau `skills.json`.

## Struktur

- `threads/` — record utas (sumber kebenaran)
- `assets/` — gambar yang disimpan di repo (thumbnail kartu link, meme, dsb.)
- `assets_src/` — `style.css` dan `feed.js` sumber
- `skills.json` — data 24 suara + build berjalan
- `build.py` — generator situs
- `docs/` — hasil render (dilayani GitHub Pages); jangan edit langsung
