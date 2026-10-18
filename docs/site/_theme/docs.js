/* planetai.fab.city/docs — search, the register switch, the menu on a phone, and "On this page".
   No framework, no network beyond search.json next to this file. */
(function () {
  'use strict';
  var d = document, root = d.documentElement;
  var assets = d.currentScript.src.replace(/[^/]*$/, '');
  var single = d.body.classList.contains('single');

  // ---- register (paper / dark) ----
  var themeBtn = d.querySelector('button.theme');
  function paint() { themeBtn.textContent = root.getAttribute('data-theme') === 'dark' ? 'Paper' : 'Dark'; }
  themeBtn.addEventListener('click', function () {
    var dark = root.getAttribute('data-theme') === 'dark';
    if (dark) root.removeAttribute('data-theme'); else root.setAttribute('data-theme', 'dark');
    try { localStorage.setItem('planetai_docs_theme', dark ? 'paper' : 'dark'); } catch (e) {}
    paint();
  });
  paint();

  // ---- menu on a phone ----
  var menu = d.querySelector('button.menu');
  menu.addEventListener('click', function () {
    var open = d.body.classList.toggle('side-open');
    menu.setAttribute('aria-expanded', String(open));
  });
  d.getElementById('side').addEventListener('click', function (e) {
    if (e.target.tagName === 'A') { d.body.classList.remove('side-open'); menu.setAttribute('aria-expanded', 'false'); }
  });

  // ---- "On this page": the heading in view is marked ----
  var toc = d.getElementById('toc');
  var tocLinks = toc ? Array.prototype.slice.call(toc.querySelectorAll('a')) : [];
  if (tocLinks.length && 'IntersectionObserver' in window) {
    var byId = {};
    tocLinks.forEach(function (a) { byId[a.getAttribute('href').slice(1)] = a; });
    var current = null, openL2 = null;
    function open(a) {
      var li = a.parentNode; if (li.classList.contains('l3')) li = li.parentNode.parentNode;
      if (openL2 && openL2 !== li) openL2.classList.remove('open');
      li.classList.add('open'); openL2 = li;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          if (current) current.classList.remove('here');
          current = byId[en.target.id]; if (current) { current.classList.add('here'); open(current); }
        }
      });
    }, { rootMargin: '-56px 0px -70% 0px' });
    if (tocLinks[0]) open(tocLinks[0]);
    Object.keys(byId).forEach(function (id) { var h = d.getElementById(id); if (h) io.observe(h); });
  }

  // ---- in the single-page build, the sidebar follows the article in view ----
  if (single && 'IntersectionObserver' in window) {
    var sideLinks = {};
    d.querySelectorAll('#side a[data-slug]').forEach(function (a) { sideLinks[a.dataset.slug] = a.parentNode; });
    var here = null;
    var io2 = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          if (here) here.classList.remove('here');
          here = sideLinks[en.target.dataset.slug]; if (here) here.classList.add('here');
        }
      });
    }, { rootMargin: '-56px 0px -60% 0px' });
    d.querySelectorAll('article.page').forEach(function (a) { io2.observe(a); });
  }

  // ---- search ----
  var q = d.getElementById('q'), box = d.getElementById('results'), index = null, sel = -1;
  function load(cb) {
    if (index) return cb();
    fetch(assets + 'search.json').then(function (r) { return r.json(); }).then(function (j) { index = j; cb(); })
      .catch(function () { index = []; cb(); });
  }
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function mark(text, terms) {
    var out = esc(text);
    terms.forEach(function (t) { if (t) out = out.replace(new RegExp('(' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig'), '<mark>$1</mark>'); });
    return out;
  }
  function snippet(t, terms) {
    var low = t.toLowerCase(), i = -1;
    terms.forEach(function (x) { var j = low.indexOf(x); if (j >= 0 && (i < 0 || j < i)) i = j; });
    var s = Math.max(0, i - 60), e = Math.min(t.length, (i < 0 ? 0 : i) + 120);
    return (s ? '… ' : '') + t.slice(s, e) + (e < t.length ? ' …' : '');
  }
  function search(str) {
    var terms = str.toLowerCase().split(/\s+/).filter(Boolean);
    if (!terms.length) { box.hidden = true; return; }
    var hits = [];
    index.forEach(function (p) {
      p.s.forEach(function (sec) {
        var hay = (p.title + ' ' + sec.h + ' ' + sec.t).toLowerCase();
        var score = 0;
        terms.forEach(function (t) {
          if (p.title.toLowerCase().indexOf(t) >= 0) score += 6;
          if (sec.h.toLowerCase().indexOf(t) >= 0) score += 4;
          if (hay.indexOf(t) >= 0) score += 1;
        });
        var all = terms.every(function (t) { return hay.indexOf(t) >= 0; });
        if (all) hits.push({ p: p, sec: sec, score: score });
      });
    });
    hits.sort(function (a, b) { return b.score - a.score; });
    hits = hits.slice(0, 12);
    if (!hits.length) { box.innerHTML = '<div class="none">Nothing on that. Try a setting, a command or an endpoint.</div>'; box.hidden = false; return; }
    box.innerHTML = hits.map(function (h) {
      var href = h.p.url + (h.sec.id ? (single ? '#' + h.sec.id : '#' + h.sec.id) : '');
      if (single && h.sec.id) href = '#' + h.sec.id;
      return '<a href="' + href + '"><div class="t">' + mark(h.p.title + (h.sec.h ? ' › ' + h.sec.h : ''), terms) +
        '<span class="k">' + esc(h.p.group) + '</span></div><div class="s">' + mark(snippet(h.sec.t, terms), terms) + '</div></a>';
    }).join('');
    box.hidden = false; sel = -1;
  }
  q.addEventListener('input', function () { var v = q.value; load(function () { search(v); }); });
  q.addEventListener('focus', function () { load(function () { if (q.value) search(q.value); }); });
  q.addEventListener('keydown', function (e) {
    var items = box.querySelectorAll('a');
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (!items.length) return;
      if (sel >= 0) items[sel].classList.remove('sel');
      sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      items[sel].classList.add('sel'); items[sel].scrollIntoView({ block: 'nearest' });
    } else if (e.key === 'Enter') {
      var a = sel >= 0 ? items[sel] : items[0];
      if (a) { location.href = a.getAttribute('href'); box.hidden = true; }
    } else if (e.key === 'Escape') { box.hidden = true; q.blur(); }
  });
  d.addEventListener('click', function (e) { if (!e.target.closest('.search')) box.hidden = true; });
  d.addEventListener('keydown', function (e) {
    if (e.key === '/' && !/INPUT|TEXTAREA/.test(d.activeElement.tagName)) { e.preventDefault(); q.focus(); q.select(); }
  });
})();
