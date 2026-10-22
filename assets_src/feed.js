document.addEventListener('DOMContentLoaded', function () {
  var sel = document.getElementById('skill-filter');
  if (!sel) return;
  sel.addEventListener('change', function () {
    var v = sel.value;
    document.querySelectorAll('[data-skills]').forEach(function (el) {
      if (!v) { el.classList.remove('hidden-by-filter'); return; }
      var list = (el.getAttribute('data-skills') || '').split(/\s+/);
      el.classList.toggle('hidden-by-filter', list.indexOf(v) === -1);
    });
  });
});
