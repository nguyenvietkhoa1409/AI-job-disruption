// Chart viewer: builds switch / dropdown controls from a JSON config and swaps the image.
//
// <div class="viewer" data-viewer>
//   <script type="application/json">{
//     "base": "img/",
//     "controls": [
//       {"type": "switch", "id": "metric", "label": "Metric", "default": "a",
//        "options": [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}]},
//       {"type": "select", "id": "country", "label": "Country", "default": "all",
//        "options": [{"value": "all", "label": "All"}, {"value": "us", "label": "United States"}]}
//     ],
//     "states": {
//       "metric=a&country=all": {"img": "chart__a.webp", "alt": "...", "note": "<b>HTML</b> allowed"}
//     }
//   }</script>
//   <figure class="viewer__frame"><img src="img/chart__a.webp" alt="..."></figure>
//   <div class="viewer__note"></div>
// </div>
//
// The state key is "id=value" for every control, in control order, joined with "&".
// A combination with no entry in "states" shows a "not captured yet" message.
(function () {
  function el(tag, attrs, text) {
    const n = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => n.setAttribute(k, v));
    if (text != null) n.textContent = text;
    return n;
  }

  document.querySelectorAll('[data-viewer]').forEach((root, vi) => {
    const cfg = JSON.parse(root.querySelector('script[type="application/json"]').textContent);
    const base = cfg.base || '';
    const img = root.querySelector('.viewer__frame img');
    const frame = root.querySelector('.viewer__frame');
    // The note lives inside the viewer, or in the text column of the same .chart block.
    const chart = root.closest('.chart');
    const note = root.querySelector('.viewer__note') || (chart && chart.querySelector('.viewer__note-target'));
    if (note) note.setAttribute('aria-live', 'polite');
    const value = {};
    const bar = el('div', { class: 'viewer__controls' });
    root.insertBefore(bar, frame);

    const missing = el('div', { class: 'viewer__missing', hidden: '' }, 'This combination has not been captured yet.');
    frame.appendChild(missing);

    cfg.controls.forEach((c, ci) => {
      value[c.id] = c.default || c.options[0].value;
      const group = el('div', { class: 'ctl ctl--' + c.type });
      const labelId = `v${vi}-c${ci}`;
      group.appendChild(el('span', { class: 'ctl__label', id: labelId }, c.label));

      if (c.type === 'select') {
        const sel = el('select', { 'aria-labelledby': labelId });
        c.options.forEach(o => {
          const opt = el('option', { value: o.value }, o.label);
          if (o.value === value[c.id]) opt.selected = true;
          sel.appendChild(opt);
        });
        sel.addEventListener('change', () => { value[c.id] = sel.value; render(); });
        group.appendChild(sel);
      } else {
        const seg = el('div', { class: 'seg', role: 'radiogroup', 'aria-labelledby': labelId });
        const btns = c.options.map(o => {
          const b = el('button', { type: 'button', role: 'radio', 'data-value': o.value }, o.label);
          b.addEventListener('click', () => { value[c.id] = o.value; sync(); render(); });
          b.addEventListener('keydown', e => {
            const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
            if (!d) return;
            e.preventDefault();
            const i = (c.options.findIndex(x => x.value === value[c.id]) + d + c.options.length) % c.options.length;
            value[c.id] = c.options[i].value; sync(); render(); btns[i].focus();
          });
          seg.appendChild(b);
          return b;
        });
        function sync() {
          btns.forEach(b => {
            const on = b.dataset.value === value[c.id];
            b.setAttribute('aria-checked', on);
            b.tabIndex = on ? 0 : -1;
          });
        }
        sync();
        group.appendChild(seg);
      }
      bar.appendChild(group);
    });

    function key() { return cfg.controls.map(c => `${c.id}=${value[c.id]}`).join('&'); }

    function render() {
      const s = cfg.states[key()];
      missing.hidden = !!s;
      img.style.visibility = s ? 'visible' : 'hidden';
      if (!s) { if (note) note.innerHTML = ''; return; }
      if (img.getAttribute('src') !== base + s.img) {
        img.classList.add('is-swapping');
        const next = new Image();
        next.onload = () => { img.src = next.src; img.alt = s.alt || ''; img.classList.remove('is-swapping'); };
        next.src = base + s.img;
      }
      if (note) note.innerHTML = s.note || '';
    }

    render();
    // Warm the cache so the first switch is instant.
    window.addEventListener('load', () => Object.values(cfg.states).forEach(s => { new Image().src = base + s.img; }));
  });
})();

// Page tabs: one web page per Power BI dashboard; its report pages are panels.
//
// <nav class="page-tabs"><div role="tablist">
//   <button role="tab" data-page="when-where" aria-controls="panel-when-where">...</button> ...
// </div></nav>
// <div class="page-panel" id="panel-when-where" data-page="when-where" data-lede="..." data-title="...">
// <button data-goto="who-cut-most">Next page</button>   (anywhere: jumps to that page)
//
// The URL hash (#who-cut-most) selects a page, so each page can be linked directly
// (the home page cards link to them). Without JS every panel stays visible.
(function () {
  const tabs = Array.from(document.querySelectorAll('.page-tabs [role="tab"]'));
  if (!tabs.length) return;
  const bar = document.querySelector('.page-tabs');
  const panels = Array.from(document.querySelectorAll('.page-panel'));
  const lede = document.querySelector('[data-page-lede]');
  const baseTitle = document.title;

  // Escape the lede text, then keep ISO dates (2026-09-08, 2025-01) on one line.
  function setLede(text) {
    const esc = text.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    lede.innerHTML = esc.replace(/\b\d{4}-\d{2}(?:-\d{2})?\b/g, '<span class="nw">$&</span>');
  }

  function select(name) {
    const tab = tabs.find(t => t.dataset.page === name) || tabs[0];
    tabs.forEach(t => {
      const on = t === tab;
      t.setAttribute('aria-selected', on);
      t.tabIndex = on ? 0 : -1;
    });
    panels.forEach(p => { p.hidden = p.dataset.page !== tab.dataset.page; });
    const panel = panels.find(p => !p.hidden);
    if (lede && panel && panel.dataset.lede) setLede(panel.dataset.lede);
    if (panel && panel.dataset.title) document.title = panel.dataset.title + ' · ' + baseTitle;
    return tab;
  }

  // After a switch from further down the page, bring the start of the new page into view.
  const sentinel = document.createElement('div');
  bar.parentNode.insertBefore(sentinel, bar);
  function toPageStart() {
    const top = sentinel.getBoundingClientRect().top + window.scrollY - 60;
    if (window.scrollY > top) window.scrollTo({ top, behavior: 'instant' });
  }

  function go(name, focus) {
    const tab = select(name);
    history.replaceState(null, '', '#' + tab.dataset.page);
    toPageStart();
    if (focus) tab.focus();
  }

  tabs.forEach((t, i) => {
    t.addEventListener('click', () => go(t.dataset.page));
    t.addEventListener('keydown', e => {
      const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (!d) return;
      e.preventDefault();
      go(tabs[(i + d + tabs.length) % tabs.length].dataset.page, true);
    });
  });
  document.querySelectorAll('[data-goto]').forEach(b => b.addEventListener('click', () => go(b.dataset.goto)));

  // Compact bar with a shadow once it sticks under the top bar.
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([e]) => bar.classList.toggle('is-stuck', !e.isIntersecting),
      { rootMargin: '-61px 0px 0px 0px' }).observe(sentinel);
  }

  select(location.hash.slice(1));
  window.addEventListener('hashchange', () => select(location.hash.slice(1)));
})();
