// Light scroll reveal: blocks fade up 12px once as they enter the viewport.
// Charts and figures are deliberately excluded: they stay still.
// Content is never hidden without JS, and blocks already on screen at load are left alone.
(function () {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return;
  const sel = '.card, .callout, .schema__col, .chart__text, .story';
  const io = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!e.isIntersecting) return;
      e.target.classList.add('is-in');
      io.unobserve(e.target);
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll(sel).forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.top < window.innerHeight && r.bottom > 0) return; // already visible: no animation
    el.classList.add('reveal');
    io.observe(el);
  });
})();
