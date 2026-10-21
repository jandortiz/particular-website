// A real DOM harness, with no test framework or production dependencies.
const frame = document.getElementById('site');
const results = document.getElementById('results');
let passed = 0;
let failed = 0;
let loadNumber = 0;
function check(name, condition) {
  const line = document.createElement('li');
  line.className = condition ? 'pass' : 'fail';
  line.textContent = `${condition ? 'PASS' : 'FAIL'} — ${name}`;
  results.append(line);
  condition ? passed++ : failed++;
}
async function load(path) {
  const ready = new Promise(resolve => frame.addEventListener('load',resolve,{once:true}));
  const url=new URL(path,location.origin);
  url.searchParams.set("test-load",String(++loadNumber));
  frame.src=url.href;
  await ready;
  return frame.contentDocument;
}
const select = (doc, category) => doc.querySelector(`[data-filter="${category}"]`).click();
const visible = doc => [...doc.querySelectorAll('[data-project]:not([hidden])')].map(p=>p.id);
try {
  let doc = await load('/__test__/fresh/');
  check('first visit starts light',doc.documentElement.dataset.theme==='light');
  check('all 12 projects are in the initial HTML',doc.querySelectorAll('[data-project]').length===12);
  check('archive initially shows six compact entries',doc.querySelectorAll('[data-archive-project]:not([hidden])').length===6);
  await doc.fonts.ready;
  const pair=['aplica','renfe'].map(id=>doc.getElementById(id));
  check('paired images and detail controls align',Math.abs(pair[0].querySelector('img').getBoundingClientRect().height-pair[1].querySelector('img').getBoundingClientRect().height)<1 && Math.abs(pair[0].querySelector('summary').getBoundingClientRect().top-pair[1].querySelector('summary').getBoundingClientRect().top)<1);

  select(doc,'data');
  check('data filter has the expected projects',visible(doc).join(',')==='renfe,flight-delay,uam-rag,emt-madrid,mascotas-madrid,california-housing');
  check('filter count is announced',doc.querySelector('[data-result-count]').textContent==='6 proyectos');
  select(doc,'apps');
  check('group with no matches is hidden',doc.querySelector('[aria-labelledby="ongoing-title"]').hidden);
  const details=doc.querySelector('#aplica details');
  details.open=true;
  doc.querySelector('[data-theme-toggle]').click();
  check('theme toggle preserves filter and expanded content',details.open && visible(doc).length===8 && doc.querySelector('[data-filter="apps"]').getAttribute('aria-pressed')==='true');
  doc = await load('/en/');
  check('saved dark preference survives language navigation',doc.documentElement.dataset.theme==='dark');
  check('English labels and counter',doc.querySelector('[data-theme-toggle]').getAttribute('aria-label')==='Switch to light mode' && doc.querySelector('[data-result-count]').textContent==='12 projects');
  check('language links reset to the top',doc.querySelector('[data-language]').getAttribute('href')==='/#top');
  doc=await load('/en/#contact');
  const languageNavigation=new Promise(resolve=>frame.addEventListener('load',resolve,{once:true}));
  doc.querySelector('[data-language]').click();
  await languageNavigation;
  doc=frame.contentDocument;
  check('switching language from contact opens the top',doc.documentElement.lang==='es' && frame.contentWindow.location.hash==='#top' && frame.contentWindow.scrollY===0);
  doc=await load('/en/');

  select(doc,'ai');
  check('AI category supports shared membership',visible(doc).join(',')==='aplica,tikeo,flight-delay,uam-rag,jeff-chef');
  select(doc,'all');
  check('all restores original editorial order',visible(doc).slice(0,4).join(',')==='aplica,renfe,tikeo,flight-delay' && visible(doc).length===10);
  doc.querySelector('[data-page-next]').click();
  check('archive page two exposes remaining projects',visible(doc).slice(4).join(',')==='california-housing,jalt' && doc.querySelector('[data-page-next]').disabled);
  check('page changes keep the full result count',doc.querySelector('[data-result-count]').textContent==='12 projects');
  check('pagination moves focus into the archive',doc.activeElement===doc.querySelector('#california-housing summary'));
  doc.querySelector('#jalt details').open=true;
  doc.querySelector('[data-theme-toggle]').click();
  check('theme preserves archive page and expanded entry',doc.querySelector('[data-page-select]').value==='2' && doc.querySelector('#jalt details').open && !doc.querySelector('#jalt').hidden);
  doc.querySelector('[data-theme-toggle]').click();

  select(doc,'data');
  check('filter resets archive page and removes unnecessary controls',!doc.querySelector('#uam-rag').hidden && doc.querySelector('[data-pagination]').hidden);
  select(doc,'all');
  const contacts=[...doc.querySelectorAll('.contact-links a')];
  check('contact links open separately and isolate the opener',contacts.length===3 && contacts.every(a=>a.target==='_blank' && a.rel.includes('noopener')));
  const site=doc.querySelector('#aplica .project-image');
  check('Aplica main image opens its website separately',site.href==='https://aplicajobs.es/' && site.target==='_blank' && site.rel.includes('noopener') && !site.hasAttribute('data-gallery'));
  doc.querySelector('#aplica details').open=true;
  const opener=doc.querySelector('#aplica details [data-gallery]');
  opener.click();
  const dialog=doc.querySelector('[data-viewer]');
  check('multi-image viewer opens with focus on close',dialog.open && doc.activeElement===dialog.querySelector('[data-close]'));
  dialog.querySelector('[data-close]').dispatchEvent(new frame.contentWindow.KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}));
  check('Shift+Tab wraps to the last viewer control',doc.activeElement===dialog.querySelector('[data-next]'));
  dialog.querySelector('[data-next]').dispatchEvent(new frame.contentWindow.KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));
  check('Tab wraps to the first viewer control',doc.activeElement===dialog.querySelector('[data-close]'));

  dialog.querySelector('[data-next]').click();
  check('next image updates caption and counter',dialog.querySelector('[data-viewer-counter]').textContent==='2 / 2' && dialog.querySelector('[data-viewer-image]').src.endsWith('aplica-live-process.jpg'));
  const image=dialog.querySelector('[data-viewer-image]');
  const win=frame.contentWindow;
  const touch=(type,x,y)=>{
    const event=new win.Event(type,{bubbles:true});
    Object.defineProperty(event,'touches',{value:type==='touchstart'?[{clientX:x,clientY:y}]:[]});
    Object.defineProperty(event,'changedTouches',{value:[{clientX:x,clientY:y}]});
    image.dispatchEvent(event);
  };
  touch('touchstart',200,100);touch('touchend',50,105);
  check('horizontal swipe advances the viewer',dialog.querySelector('[data-viewer-counter]').textContent==='1 / 2');
  touch('touchstart',100,100);touch('touchend',105,250);
  check('vertical gesture does not change the image',dialog.querySelector('[data-viewer-counter]').textContent==='1 / 2');
  const closed=new Promise(resolve=>dialog.addEventListener('close',resolve,{once:true}));
  dialog.querySelector('[data-close]').click();
  await closed;
  check('closing returns focus to the opener',!dialog.open && doc.activeElement===opener && !doc.body.classList.contains('viewer-open'));
  doc.querySelector('#renfe [data-gallery]').click();
  check('single-image viewer hides navigation',dialog.open && dialog.querySelector('[data-viewer-navigation]').hidden);
  dialog.querySelector('[data-close]').click();

  doc.querySelector('#uam-rag details').open=true;
  doc.querySelector('#uam-rag [data-gallery]').click();
  check('archive images retain a clean viewer title',dialog.open && dialog.querySelector('[data-viewer-title]').textContent==='UAM RAG Agent');
  dialog.querySelector('[data-close]').click();
  doc=await load('/__test__/blocked-storage/');
  check('blocked storage keeps a usable light default',doc.documentElement.dataset.theme==='light');
  doc.querySelector('[data-theme-toggle]').click();
  check('theme still changes when storage is blocked',doc.documentElement.dataset.theme==='dark');
  for (const language of ['es','en']) {
    doc=await load('/__test__/no-js/'+language+'/');
    check(`${language}: no JS still shows every project`,visible(doc).length===12 && doc.querySelector('[data-theme-toggle]').hidden && doc.querySelector('[data-filters]').hidden);
    check(`${language}: native details remain available`,doc.querySelectorAll('details').length===12);
  }
  doc=await load('/#jalt');
  check('direct links reveal the correct archive page and details',!doc.querySelector('#jalt').hidden && doc.querySelector('#jalt details').open && doc.querySelector('[data-page-select]').value==='2');
  doc=await load('/__test__/large/');
  check('100-project fixture keeps only six archive rows visible',doc.querySelectorAll('[data-project]').length===100 && doc.querySelectorAll('[data-archive-project]:not([hidden])').length===6);
  check('100 projects have 16 archive pages and an accurate total',doc.querySelector('[data-page-select]').options.length===16 && doc.querySelector('[data-result-count]').textContent==='100 proyectos');
  const lastPage=doc.querySelector('[data-page-select]');
  lastPage.value='16';lastPage.dispatchEvent(new frame.contentWindow.Event('change',{bubbles:true}));
  check('last page remains reachable with bounded rows',!doc.querySelector('#fixture-100').hidden && doc.querySelectorAll('[data-archive-project]:not([hidden])').length===6 && doc.querySelector('[data-page-next]').disabled);
  doc=await load('/__test__/motion/');
  check('reduced-motion CSS removes smooth scroll and transitions',frame.contentWindow.getComputedStyle(doc.documentElement).scrollBehavior==='auto' && frame.contentWindow.getComputedStyle(doc.querySelector('.project-image img')).transitionDuration==='0s');
} catch(error) {
  check(error.message,false);
} finally {
  try {localStorage.removeItem('jandortiz-theme')} catch {}
  document.getElementById('status').textContent=`${passed} passed, ${failed} failed`;
}
