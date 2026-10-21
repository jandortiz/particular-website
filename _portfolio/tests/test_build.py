import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('portfolio_build', ROOT/'_portfolio/build.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

class BuildTests(unittest.TestCase):
    def setUp(self):
        self.catalog, self.ui = build.load_content(ROOT)

    def validate(self):
        build.validate_content(self.catalog,self.ui,ROOT)

    def test_real_catalog_and_both_static_languages(self):
        pages=build.render_site(self.catalog,self.ui,ROOT)
        self.assertEqual(set(pages),{'index.html','en/index.html'})
        self.assertIn('<html lang="en"',pages['en/index.html'])
        self.assertIn('Una selección de mi trabajo',pages['index.html'])
        for html in pages.values():
            for project in self.catalog['projects']:
                self.assertIn(f'id="{project["id"]}"',html)
                self.assertIn(project['name'],html)
            self.assertNotIn('fetch(',html)

    def test_deterministic(self):
        self.assertEqual(build.render_site(self.catalog,self.ui,ROOT),build.render_site(self.catalog,self.ui,ROOT))

    def test_editorial_order_is_preserved(self):
        featured=[p for p in self.catalog['projects'] if p['group']=='featured']
        self.catalog['projects'][:3]=list(reversed(featured))
        html=build.render_site(self.catalog,self.ui,ROOT)['index.html']
        self.assertLess(html.index('id="tikeo"'),html.index('id="aplica"'))

    def test_content_is_escaped_in_text_and_attributes(self):
        attack='"><script>alert(1)</script>'
        self.catalog['projects'][0]['description']['es']=attack
        self.catalog['projects'][0]['images'][0]['caption']['es']=attack
        html=build.render_site(self.catalog,self.ui,ROOT)['index.html']
        self.assertNotIn(attack,html)
        self.assertIn('&lt;script&gt;',html)

    def test_duplicate_id_rejected(self):
        self.catalog['projects'][1]['id']='aplica'
        with self.assertRaises(build.ContentError): self.validate()

    def test_reserved_id_rejected(self):
        self.catalog['projects'][0]['id']='projects'
        with self.assertRaises(build.ContentError): self.validate()

    def test_missing_project_translation_rejected(self):
        del self.catalog['projects'][0]['description']['en']
        with self.assertRaises(build.ContentError): self.validate()

    def test_missing_ui_translation_rejected(self):
        del self.ui['en']['next']
        with self.assertRaises(build.ContentError): self.validate()

    def test_unknown_status_and_category_rejected(self):
        for field,value in [('status','finished-maybe'),('categories',['unknown'])]:
            with self.subTest(field=field):
                catalog=copy.deepcopy(self.catalog)
                catalog['projects'][0][field]=value
                with self.assertRaises(build.ContentError): build.validate_content(catalog,self.ui,ROOT)

    def test_image_missing_or_outside_project_rejected(self):
        for path in ['imgs/missing.jpg','../secret.jpg','/etc/passwd','README.md']:
            with self.subTest(path=path):
                self.catalog['projects'][0]['images'][0]['src']['es']=path
                with self.assertRaises(build.ContentError): self.validate()

    def test_empty_alt_rejected(self):
        self.catalog['projects'][0]['images'][0]['alt']['en']=''
        with self.assertRaises(build.ContentError): self.validate()

    def test_unsafe_links_rejected(self):
        for url in ['javascript:alert(1)','https://user:pass@example.com','https:///no-host','https://example.com/a b']:
            with self.subTest(url=url):
                self.catalog['projects'][1]['links'][0]['href']=url
                with self.assertRaises(build.ContentError): self.validate()

    def test_main_image_link_opens_website_and_keeps_captures_in_viewer(self):
        pages=build.render_site(self.catalog,self.ui,ROOT)
        for name,label in [('index.html','Ir a la web de Aplica Jobs (abre aparte)'),('en/index.html','Visit the Aplica Jobs website (opens separately)')]:
            with self.subTest(page=name):
                html=pages[name]
                aplica=html[html.index('id="aplica"'):html.index('id="renfe"')]
                self.assertIn(f'<a class="project-image" href="https://aplicajobs.es" target="_blank" rel="noopener noreferrer" aria-label="{label}">',aplica)
                self.assertEqual(aplica.count('data-gallery'),2)
                renfe=html[html.index('id="renfe"'):html.index('id="tikeo"')]
                self.assertIn('class="project-image" href="/imgs/projects/renfe.jpg" data-gallery',renfe)

    def test_image_link_only_on_main_image_of_featured_project(self):
        uam=next(i for i,p in enumerate(self.catalog['projects']) if p['id']=='uam-rag')
        cases=[(0,1,'https://aplicajobs.es'),(uam,0,'https://example.com'),(0,0,'http://aplicajobs.es'),(0,0,'javascript:alert(1)')]
        for project,image,url in cases:
            with self.subTest(project=project,image=image,url=url):
                catalog=copy.deepcopy(self.catalog)
                catalog['projects'][0]['images'][0].pop('link',None)
                catalog['projects'][project]['images'][image]['link']=url
                with self.assertRaises(build.ContentError): build.validate_content(catalog,self.ui,ROOT)

    def test_broken_anchor_and_local_asset_rejected(self):
        for html in ['<a href="#missing">Test</a>','<script src="/js/missing.js"></script>']:
            with self.subTest(html=html):
                with self.assertRaises(build.ContentError): build.validate_pages({'index.html':html},ROOT)

    def test_invalid_build_preserves_both_existing_pages(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'_portfolio/content').mkdir(parents=True)
            (root/'en').mkdir()
            (root/'index.html').write_text('previous spanish')
            (root/'en/index.html').write_text('previous english')
            self.catalog['projects'][0]['id']='projects'
            (root/'_portfolio/content/projects.json').write_text(json.dumps(self.catalog))
            for lang in ('es','en'):
                (root/f'_portfolio/content/{lang}.json').write_text(json.dumps(self.ui[lang]))
            with self.assertRaises(build.ContentError): build.build(root)
            self.assertEqual((root/'index.html').read_text(),'previous spanish')
            self.assertEqual((root/'en/index.html').read_text(),'previous english')

    def test_required_template_field_missing_fails_before_output(self):
        from jinja2 import UndefinedError
        for lang in ('es','en'): del self.ui[lang]['intro']
        with self.assertRaises(UndefinedError): build.render_site(self.catalog,self.ui,ROOT)

if __name__ == '__main__': unittest.main()
