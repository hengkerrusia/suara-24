document.addEventListener('DOMContentLoaded', function () {
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.feedtab'));
  var views = {};
  document.querySelectorAll('[data-view]').forEach(function (el) { views[el.getAttribute('data-view')] = el; });
  var sel = document.getElementById('skill-filter');
  var cur = 'ronda';
  function apply() {
    Object.keys(views).forEach(function (k) { views[k].style.display = (k === cur) ? '' : 'none'; });
    tabs.forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-tab') === cur); });
    if (!sel) return;
    var v = sel.value, box = views[cur];
    if (!box) return;
    var hidden = 0;
    box.querySelectorAll('[data-skills]').forEach(function (el) {
      var hide = !!v && (el.getAttribute('data-skills') || '').split(/\s+/).indexOf(v) === -1;
      el.classList.toggle('hidden-by-filter', hide);
      if (hide) hidden++;
    });
    var note = box.querySelector('.filternote');
    if (note) note.textContent = (v && hidden) ? hidden + ' utas disembunyikan oleh saringan.' : '';
  }
  tabs.forEach(function (b) { b.addEventListener('click', function () { cur = b.getAttribute('data-tab'); apply(); }); });
  if (sel) sel.addEventListener('change', apply);
  if (tabs.length) apply();
});
