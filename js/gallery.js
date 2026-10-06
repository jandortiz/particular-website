export function initGallery() {
  const dialog = document.querySelector('[data-viewer]');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const image = dialog.querySelector('[data-viewer-image]');
  const caption = dialog.querySelector('[data-viewer-caption]');
  const title = dialog.querySelector('[data-viewer-title]');
  const counter = dialog.querySelector('[data-viewer-counter]');
  const navigation = dialog.querySelector('[data-viewer-navigation]');
  const previous = dialog.querySelector('[data-previous]');
  const next = dialog.querySelector('[data-next]');
  const close = dialog.querySelector('[data-close]');
  let slides = [];
  let index = 0;
  let opener;
  let touchStart;

  function show(offset = 0) {
    index = (index + offset + slides.length) % slides.length;
    const slide = slides[index];
    image.src = slide.href;
    image.alt = slide.dataset.alt;
    caption.textContent = slide.dataset.caption;
    counter.textContent = `${index + 1} / ${slides.length}`;
    navigation.hidden = slides.length < 2;
  }

  for (const link of document.querySelectorAll('[data-gallery]')) {
    link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
      event.preventDefault();
      opener = link;
      const project = link.closest('[data-project]');
      slides = [...project.querySelectorAll('[data-gallery]')];
      index = slides.indexOf(link);
      title.textContent = (project.querySelector('[data-project-name]') || project.querySelector('h3')).textContent;
      show();
      dialog.showModal();
      document.body.classList.add('viewer-open');
      close.focus({preventScroll: true});
    });
  }
  close.addEventListener('click', () => dialog.close());
  previous.addEventListener('click', () => show(-1));
  next.addEventListener('click', () => show(1));
  dialog.addEventListener('keydown', event => {
    if (event.key === 'Tab') {
      const first = close;
      const last = navigation.hidden ? close : next;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
      return;
    }
    if (slides.length < 2) return;
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      show(event.key === 'ArrowRight' ? 1 : -1);
    }
  });
  dialog.addEventListener('click', event => {
    const bounds = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => {
    document.body.classList.remove('viewer-open');
    touchStart = null;
    opener?.focus({preventScroll: true});
  });
  image.addEventListener('touchstart', event => {
    touchStart = event.touches.length === 1 ? {x: event.touches[0].clientX, y: event.touches[0].clientY} : null;
  }, {passive: true});
  image.addEventListener('touchend', event => {
    if (!touchStart || !event.changedTouches.length || slides.length < 2) return;
    const dx = event.changedTouches[0].clientX - touchStart.x;
    const dy = event.changedTouches[0].clientY - touchStart.y;
    touchStart = null;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) show(dx < 0 ? 1 : -1);
  }, {passive: true});
  image.addEventListener('touchcancel', () => { touchStart = null; }, {passive: true});
}
