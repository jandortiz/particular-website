export function initFilters() {
  const controls = document.querySelector('[data-filters]');
  if (!controls) return;
  const buttons = [...controls.querySelectorAll('[data-filter]')];
  const projects = [...document.querySelectorAll('[data-project]')];
  const groups = [...document.querySelectorAll('[data-project-group]')];
  const archive = document.querySelector('[data-archive]');
  const pagination = document.querySelector('[data-pagination]');
  const previous = pagination.querySelector('[data-page-previous]');
  const next = pagination.querySelector('[data-page-next]');
  const pageSelect = pagination.querySelector('[data-page-select]');
  const pageStatus = pagination.querySelector('[data-page-status]');
  const pageSize = Number(pagination.dataset.pageSize);
  const result = document.querySelector('[data-result-count]');
  const empty = document.querySelector('[data-empty]');
  let category = 'all';
  let page = 1;
  const matches = project => category === 'all' || project.dataset.categories.split(' ').includes(category);
  const archiveMatches = () => projects.filter(project => project.hasAttribute('data-archive-project') && matches(project));

  function render() {
    const collection = archiveMatches();
    const pages = Math.max(1, Math.ceil(collection.length / pageSize));
    page = Math.max(1, Math.min(page, pages));
    const pageProjects = new Set(collection.slice((page - 1) * pageSize, page * pageSize));
    let count = 0;
    for (const project of projects) {
      const match = matches(project);
      if (match) count++;
      project.hidden = !match || (project.hasAttribute('data-archive-project') && !pageProjects.has(project));
    }
    for (const button of buttons) button.setAttribute('aria-pressed', String(button.dataset.filter === category));
    for (const group of groups) group.hidden = !group.querySelector('[data-project]:not([hidden])');
    result.textContent = `${count} ${count === 1 ? result.dataset.singular : result.dataset.plural}`;
    empty.hidden = count > 0;
    pagination.hidden = pages <= 1;
    previous.disabled = page === 1;
    next.disabled = page === pages;
    pageStatus.textContent = pagination.dataset.label.replace('{page}', page).replace('{pages}', pages);
    // Only the small page selector changes; project nodes and expanded details remain intact.
    pageSelect.replaceChildren(...Array.from({length: pages}, (_, index) => new Option(String(index + 1), String(index + 1))));
    pageSelect.value = String(page);
  }

  buttons.forEach(button => button.addEventListener('click', () => {
    category = button.dataset.filter;
    page = 1;
    render();
  }));
  function changePage(value) {
    page = value;
    render();
    archive.scrollIntoView({block: 'start', behavior: 'instant'});
    archive.querySelector('[data-project]:not([hidden]) summary')?.focus({preventScroll: true});
  }
  previous.addEventListener('click', () => changePage(page - 1));
  next.addEventListener('click', () => changePage(page + 1));
  pageSelect.addEventListener('change', () => changePage(Number(pageSelect.value)));
  function revealHash() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const project = document.getElementById(id)?.closest('[data-project]');
    if (!project) return;
    if (!matches(project)) category = 'all';
    if (project.hasAttribute('data-archive-project')) page = Math.floor(archiveMatches().indexOf(project) / pageSize) + 1;
    render();
  }
  window.addEventListener('hashchange', revealHash);
  controls.hidden = false;
  result.hidden = false;
  render();
  revealHash();
}
