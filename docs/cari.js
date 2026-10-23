document.addEventListener('DOMContentLoaded', function () {
  var inp = document.getElementById('q');
  var out = document.getElementById('results');
  if (!inp || !out) return;
  var data = null;
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function render() {
    var q = inp.value.trim().toLowerCase();
    if (!data) { out.innerHTML = ''; return; }
    if (q.length < 2) {
      out.innerHTML = '<p class="count-note">Ketik minimal 2 huruf — pencarian menelusuri judul, isi utas, komentar, tag, dan nama suara.</p>';
      return;
    }
    var byUser = {}, bySlug = {};
    data.skills.forEach(function (s) { byUser[s.username] = s; bySlug[s.slug] = s; });
    var h = '';
    data.skills.forEach(function (s) {
      var hay = (s.display + ' ' + s.name + ' @' + s.username).toLowerCase();
      if (hay.indexOf(q) > -1) {
        h += '<p><a href="skill/' + s.slug + '.html">' + esc(s.display) + '</a> ' +
             '<span class="handle">@' + esc(s.username) + '</span>' + (s.level ? ' · Level ' + s.level : '') + '</p>';
      }
    });
    var hits = 0;
    data.threads.forEach(function (t) {
      var op = bySlug[t.op] || {};
      var hay = (t.source_title + ' ' + t.op_text + ' ' + t.tags.join(' ') + ' ' +
                 (op.display || '') + ' ' + (op.name || '') + ' @' + (op.username || '')).toLowerCase();
      t.comments.forEach(function (c) {
        var cs = byUser[c.by] || {};
        hay += ' ' + c.text.toLowerCase() + ' ' + (cs.display || '').toLowerCase();
      });
      if (hay.indexOf(q) === -1) return;
      hits++;
      var plain = t.op_text.replace(/\*/g, '');
      var ex = plain.length > 180 ? plain.slice(0, 180) + '…' : plain;
      h += '<article class="post compact"><p style="margin:0 0 4px"><strong>' + esc(op.display || '') +
           '</strong> <span class="handle">@' + esc(op.username || '') + '</span></p>' +
           '<p class="post-text">' + esc(ex) + '</p>' +
           '<div class="thread-meta">💬 ' + t.comments.length + ' komentar · ' +
           '<a href="thread/' + t.slug + '.html">Buka utas →</a></div></article>';
    });
    out.innerHTML = h || ('<p class="count-note">Tidak ada hasil untuk "' + esc(q) + '".</p>');
  }
  fetch('index.json').then(function (r) { return r.json(); }).then(function (d) { data = d; render(); });
  inp.addEventListener('input', render);
  render();
});
