// Dashboard tabs (with arrow-key navigation)
(function () {
  const tabs = Array.from(document.querySelectorAll('.tabs [role="tab"]'));
  function select(tab) {
    tabs.forEach(t => {
      const on = t === tab;
      t.setAttribute('aria-selected', on);
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
    });
  }
  tabs.forEach((t, i) => {
    t.tabIndex = i === 0 ? 0 : -1;
    t.addEventListener('click', () => select(t));
    t.addEventListener('keydown', e => {
      const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!d) return;
      const next = tabs[(i + d + tabs.length) % tabs.length];
      select(next); next.focus();
    });
  });
})();

// Click-to-zoom lightbox
(function () {
  const box = document.getElementById('lightbox');
  if (!box) return;
  const big = box.querySelector('img');
  function close() { box.hidden = true; big.src = ''; }
  document.querySelectorAll('.zoomable img').forEach(img => {
    img.addEventListener('click', () => { big.src = img.src; big.alt = img.alt; box.hidden = false; });
  });
  box.addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && !box.hidden) close(); });
})();

// Highlight the nav link of the section in view
(function () {
  const links = Array.from(document.querySelectorAll('.nav a[href^="#"]'));
  const byId = new Map(links.map(a => [a.getAttribute('href').slice(1), a]));
  const io = new IntersectionObserver(entries => {
    entries.forEach(en => {
      if (!en.isIntersecting) return;
      links.forEach(a => a.classList.remove('is-active'));
      const a = byId.get(en.target.id);
      if (a) a.classList.add('is-active');
    });
  }, { rootMargin: '-40% 0px -55% 0px' });
  byId.forEach((_, id) => { const s = document.getElementById(id); if (s) io.observe(s); });
})();
