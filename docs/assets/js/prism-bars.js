// Prism bars: turns a plain data table into faceted horizontal bars (SVG).
//
// <table class="prism-source" data-prism data-of="of answers" data-count-label="answers">
//   <caption>Answers per topic</caption>
//   <thead><tr><th>Topic</th><th>Share</th><th>Answers</th></tr></thead>
//   <tbody><tr><td>Business / domain understanding</td><td data-value="14.7">14.7%</td><td>2,301</td></tr>...</tbody>
// </table>
//
// - Bar LENGTH encodes the value from a shared baseline; the facets are decoration with the
//   same slant on every bar, so lengths stay comparable.
// - The table stays in the page as the accessible / no-JS view (visually hidden once enhanced).
// - Optional: data-color="cut|create|feel" picks the palette; <tr data-muted> draws a row grey
//   (catch-all groups such as "Other").
(function () {
  const SVGNS = 'http://www.w3.org/2000/svg';
  const H = 34;            // bar height (px)
  const O = Math.round(H * 0.38); // facet slant
  const NARROW = 560;      // below this width the label moves above the bar

  function svg(tag, attrs) {
    const n = document.createElementNS(SVGNS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    return n;
  }

  function points(L) {
    const m = H / 2;
    return {
      top: `0,${m} ${O},0 ${O + L},0 ${L},${m}`,
      bottom: `0,${m} ${L},${m} ${O + L},${H} ${O},${H}`,
      cap: `${O + L},0 ${2 * O + L},${m} ${O + L},${H} ${L},${m}`,
    };
  }

  function enhance(table) {
    const rows = Array.from(table.tBodies[0].rows).map(r => {
      const c = r.cells;
      const v = parseFloat(c[1].dataset.value != null ? c[1].dataset.value : c[1].textContent);
      return { muted: r.hasAttribute('data-muted'), label: c[0].textContent.trim(), value: v, text: c[1].textContent.trim(), count: c[2] ? c[2].textContent.trim() : '' };
    });
    const max = Math.max(...rows.map(r => r.value));
    const of = table.dataset.of || '';
    const countLabel = table.dataset.countLabel || '';

    const wrap = document.createElement('div');
    wrap.className = 'prism prism--' + (table.dataset.color || 'feel');
    wrap.setAttribute('aria-hidden', 'true'); // the table is the accessible view
    const tip = document.createElement('div');
    tip.className = 'prism__tip';
    tip.hidden = true;

    const items = rows.map(r => {
      const row = document.createElement('div');
      row.className = 'prism__row' + (r.muted ? ' prism__row--muted' : '');
      row.tabIndex = 0;
      const name = document.createElement('div');
      name.className = 'prism__name';
      name.textContent = r.label;
      const s = svg('svg', { class: 'prism__bar', height: H });
      const top = svg('polygon', { class: 'prism__top' });
      const bottom = svg('polygon', { class: 'prism__bottom' });
      const cap = svg('polygon', { class: 'prism__cap' });
      s.append(top, bottom, cap);
      const lab = document.createElement('div');
      lab.className = 'prism__label';
      lab.innerHTML = `<b>${r.text}</b><span>${r.label}</span>`;
      row.append(name, s, lab);
      wrap.appendChild(row);
      return { r, row, s, top, bottom, cap, lab, L: 0, target: 0 };
    });
    wrap.appendChild(tip);
    table.classList.add('prism-source--enhanced');
    table.insertAdjacentElement('afterend', wrap);

    function draw(it) {
      const p = points(it.L);
      it.top.setAttribute('points', p.top);
      it.bottom.setAttribute('points', p.bottom);
      it.cap.setAttribute('points', p.cap);
      it.s.setAttribute('width', it.L + 2 * O + 1);
      it.s.style.visibility = it.L > 0.5 ? 'visible' : 'hidden';
      it.lab.style.left = (it.L + 2 * O + 14) + 'px';
    }

    function layout() {
      const w = wrap.clientWidth;
      const narrow = w < NARROW;
      wrap.classList.toggle('is-narrow', narrow);
      const reserve = narrow ? 64 : Math.min(300, Math.max(200, w * 0.34));
      const track = Math.max(40, w - reserve - 2 * O);
      items.forEach(it => {
        it.target = (it.r.value / max) * track;
        it.L = it.target; draw(it);
      });
    }

    // Tooltip
    function showTip(it, x) {
      const r = it.r;
      tip.innerHTML = `<span class="prism__tip-name">${r.label}</span>` +
        `<span class="prism__tip-val"><i></i><b>${r.text}</b> ${of}</span>` +
        (r.count ? `<span class="prism__tip-count">${r.count} ${countLabel}</span>` : '');
      tip.style.setProperty('--tip-swatch', getComputedStyle(it.row).getPropertyValue('--prism-top'));
      tip.hidden = false;
      const wr = wrap.getBoundingClientRect();
      const rr = it.s.getBoundingClientRect();
      const tw = tip.offsetWidth;
      const left = Math.min(Math.max(0, (x != null ? x : rr.left + rr.width / 2) - wr.left - tw / 2), wr.width - tw);
      tip.style.left = left + 'px';
      tip.style.top = (rr.top - wr.top - tip.offsetHeight - 8) + 'px';
    }
    items.forEach(it => {
      it.row.addEventListener('pointermove', e => showTip(it, e.clientX));
      it.row.addEventListener('pointerleave', () => { tip.hidden = true; });
      it.row.addEventListener('focus', () => showTip(it));
      it.row.addEventListener('blur', () => { tip.hidden = true; });
    });

    layout();
    if ('ResizeObserver' in window) new ResizeObserver(layout).observe(wrap);
    else window.addEventListener('resize', layout);
  }

  document.querySelectorAll('table[data-prism]').forEach(enhance);
})();
