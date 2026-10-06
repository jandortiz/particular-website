/* Runs before CSS so a saved preference never flashes the other appearance. */
(() => {
  const key = 'jandortiz-theme';
  const root = document.documentElement;
  try {
    const saved = localStorage.getItem(key);
    if (saved === 'dark' || saved === 'light') root.dataset.theme = saved;
  } catch { /* Storage is optional; the initial appearance stays light. */ }

  document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.querySelector('[data-theme-toggle]');
    if (!toggle) return;
    const updateLabel = () => {
      const dark = root.dataset.theme === 'dark';
      const label = dark ? toggle.dataset.lightLabel : toggle.dataset.darkLabel;
      toggle.setAttribute('aria-label', label);
      toggle.title = label;
    };
    toggle.hidden = false;
    updateLabel();
    toggle.addEventListener('click', () => {
      root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(key, root.dataset.theme); } catch { /* Keep the in-memory choice. */ }
      updateLabel();
    });
  });
})();
