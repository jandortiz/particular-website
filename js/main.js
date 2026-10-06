import {initFilters} from './filters.js';
import {initGallery} from './gallery.js';

initFilters();
initGallery();

// Language links use a top anchor; stale section hashes must not carry across.
function openLinkedProject() {
  let id;
  try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
  const project = document.getElementById(id);
  if (!project?.matches('[data-project]')) return;
  const details = project.querySelector('details');
  if (details) details.open = true;
  project.scrollIntoView({block: 'start', behavior: 'instant'});
}
window.addEventListener('hashchange', openLinkedProject);
openLinkedProject();
