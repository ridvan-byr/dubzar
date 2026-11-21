/* shared by every page: a scroll progress line, and page-to-page transitions where the browser has no native ones */
(() => {
  const reduce = matchMedia("(prefers-reduced-motion:reduce)").matches;
  const bar = document.createElement("div");
  bar.className = "progress";
  bar.setAttribute("aria-hidden", "true");
  document.body.appendChild(bar);
  const update = () => {
    const h = document.documentElement.scrollHeight - innerHeight;
    bar.style.transform = `scaleX(${h > 0 ? Math.min(1, scrollY / h) : 0})`;
  };
  addEventListener("scroll", update, { passive: true });
  update();

  const native = "PageRevealEvent" in window;          // Chromium: the CSS @view-transition does the work
  if (native || reduce) return;
  document.body.classList.add("page-in");
  document.addEventListener("click", e => {
    const a = e.target.closest && e.target.closest("a[href]");
    if (!a || e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || a.target) return;
    const u = new URL(a.href, location.href);
    if (u.origin !== location.origin || (u.pathname === location.pathname && u.hash)) return;
    e.preventDefault();
    document.body.classList.add("page-out");
    setTimeout(() => { location.href = u.href; }, 230);
  });
})();
