"""Validate all content, render both languages, then write the static pages."""
from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
LANGUAGES = ('es', 'en')
GROUPS = ('featured', 'ongoing', 'other')
CATEGORIES = {'data', 'apps', 'ai'}
STATUSES = {'local', 'beta', 'demo', 'academic', 'research', 'private', 'code', 'notebook'}
RESERVED_IDS = {'top', 'main', 'projects', 'about', 'contact', 'intro-title', 'projects-title',
                'ongoing-title', 'other-title', 'about-title', 'contact-title', 'viewer-title'}


class ContentError(ValueError):
    """An editorial error that must be fixed before publishing."""


def require(condition, message):
    if not condition:
        raise ContentError(message)


def text(value, path):
    require(isinstance(value, str) and bool(value.strip()), f'{path}: expected non-empty text')


def translated(value, path):
    require(isinstance(value, dict) and set(value) == set(LANGUAGES), f'{path}: es and en are required')
    for language in LANGUAGES:
        text(value[language], f'{path}.{language}')


def local_file(value, root, path, images_only=False):
    text(value, path)
    require(not value.startswith('/') and '..' not in Path(value).parts, f'{path}: expected a relative asset path')
    target = (root / value).resolve()
    require(target.is_relative_to(root.resolve()) and target.is_file(), f'{path}: asset not found: {value}')
    if images_only:
        require(value.startswith('imgs/') and target.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.svg'}, f'{path}: expected an image in imgs/')


def https_link(value, path):
    text(value, path)
    url = urlsplit(value)
    require(url.scheme == 'https' and bool(url.hostname) and not url.username and not url.password
            and not any(c.isspace() for c in value), f'{path}: expected an absolute HTTPS link')


def same_shape(left, right, path='translations'):
    """Both independently written languages must cover the same interface."""
    require(type(left) is type(right), f'{path}: translation types differ')
    if isinstance(left, dict):
        require(left.keys() == right.keys(), f'{path}: translation keys differ')
        for key in left:
            same_shape(left[key], right[key], f'{path}.{key}')
    elif isinstance(left, list):
        require(len(left) == len(right) and bool(left), f'{path}: translation lists differ')
        for index, (a, b) in enumerate(zip(left, right)):
            same_shape(a, b, f'{path}[{index}]')
    else:
        text(left, f'{path}.es')
        text(right, f'{path}.en')


def validate_content(catalog, translations, root=ROOT):
    require(isinstance(catalog, dict) and isinstance(catalog.get('projects'), list) and catalog['projects'], 'projects: expected a non-empty list')
    require(set(translations) == set(LANGUAGES), 'both interface translations are required')
    same_shape(translations['es'], translations['en'])
    for language, ui in translations.items():
        require(set(ui.get('statuses', {})) == STATUSES, f'{language}: incomplete status labels')
    seen = set(RESERVED_IDS)
    for i, project in enumerate(catalog['projects']):
        where = f'projects[{i}]'
        require(isinstance(project, dict), f'{where}: expected an object')
        required = {'id','name','group','categories','status','stack','description','details','links','images'}
        require(required <= project.keys(), f'{where}: missing fields {required - project.keys()}')
        identifier = project['id']
        require(isinstance(identifier, str) and re.fullmatch(r'[a-z][a-z0-9-]*', identifier), f'{where}: invalid id')
        require(identifier not in seen, f'{where}: duplicate or reserved id {identifier}')
        seen.add(identifier)
        text(project['name'], f'{where}.name')
        require(project['group'] in GROUPS, f'{where}: unknown group')
        require(project['status'] in STATUSES, f'{where}: unknown status')
        categories = project['categories']
        require(isinstance(categories, list) and categories and all(isinstance(c,str) and c in CATEGORIES for c in categories), f'{where}: invalid categories')
        require(len(set(categories)) == len(categories), f'{where}: repeated category')
        require(isinstance(project['stack'], list) and project['stack'], f'{where}: missing stack')
        for item in project['stack']:
            text(item, f'{where}.stack')
        translated(project['description'], f'{where}.description')
        require(isinstance(project['details'],list) and project['details'], f'{where}: missing details')
        for detail in project['details']:
            require(isinstance(detail,dict) and {'heading','body'} <= detail.keys(), f'{where}: incomplete detail')
            translated(detail['heading'], f'{where}.detail.heading')
            translated(detail['body'], f'{where}.detail.body')
        require(isinstance(project['links'],list), f'{where}: links must be a list')
        for link in project['links']:
            require(isinstance(link,dict) and {'href','label'} <= link.keys(), f'{where}: incomplete link')
            https_link(link['href'], f'{where}.link')
            translated(link['label'], f'{where}.link.label')
        require(isinstance(project['images'],list), f'{where}: images must be a list')
        require(project['group'] != 'featured' or project['images'], f'{where}: featured projects need an image')
        for position, image in enumerate(project['images']):
            require(isinstance(image,dict) and {'src','alt','caption','width','height'} <= image.keys(), f'{where}: incomplete image')
            for field in ('src','alt','caption'):
                translated(image[field], f'{where}.image.{field}')
            if 'link' in image:
                # Only the large picture of a featured project is rendered as a link to its website.
                require(position == 0 and project['group'] == 'featured', f'{where}: only the main image of a featured project can link to a website')
                https_link(image['link'], f'{where}.image.link')
            for language in LANGUAGES:
                local_file(image['src'][language], root, f'{where}.image.src.{language}', images_only=True)
            for dimension in ('width','height'):
                require(type(image[dimension]) is int and image[dimension] > 0, f'{where}: invalid image {dimension}')
    require(any(p['group'] == 'featured' for p in catalog['projects']), 'at least one featured project is required')


class PageReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.urls = []
        self.image_alts = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        for key in ('href','src'):
            if key in attrs:
                self.urls.append(attrs[key])
        if tag == 'meta' and attrs.get('property') == 'og:image':
            self.urls.append(urlsplit(attrs.get('content', '')).path)
        if tag == 'img':
            self.image_alts.append(attrs.get('alt'))


def validate_pages(pages, root):
    """Catch broken local assets and anchors in the rendered result as well."""
    for name, page in pages.items():
        parser = PageReferences()
        parser.feed(page)
        require(len(parser.ids) == len(set(parser.ids)), f'{name}: duplicate HTML id')
        require(all(alt is not None for alt in parser.image_alts), f'{name}: an image has no alt attribute')
        for url in parser.urls:
            if url.startswith('#'):
                require(url[1:] in parser.ids, f'{name}: missing anchor {url}')
            elif url.startswith('/'):
                target = urlsplit(url).path.lstrip('/')
                if not target or target.endswith('/'):
                    target += 'index.html'
                if target not in pages:
                    local_file(target, root, f'{name}: {url}')


def render_site(catalog, translations, root=ROOT):
    validate_content(catalog, translations, root)
    env = Environment(loader=FileSystemLoader(root / '_portfolio/templates'),
                      autoescape=select_autoescape(['html']), undefined=StrictUndefined,
                      trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)
    groups = {group:[p for p in catalog['projects'] if p['group'] == group] for group in GROUPS}
    template = env.get_template('page.html')
    pages = {}
    for language in LANGUAGES:
        path = '/' if language == 'es' else '/en/'
        filename = 'index.html' if language == 'es' else 'en/index.html'
        pages[filename] = template.render(lang=language, t=translations[language], groups=groups,
                                         canonical='https://jandortiz.com'+path, locale_path=path)
    validate_pages(pages, root)
    return pages


def load_content(root=ROOT):
    directory = root / '_portfolio/content'
    catalog = json.loads((directory / 'projects.json').read_text(encoding='utf-8'))
    translations = {language:json.loads((directory / f'{language}.json').read_text(encoding='utf-8')) for language in LANGUAGES}
    return catalog, translations


def build(root=ROOT, check=False):
    pages = render_site(*load_content(root), root)
    if check:
        stale = [name for name, page in pages.items() if not (root/name).exists() or (root/name).read_text(encoding='utf-8') != page]
        require(not stale, 'Generated pages are out of date: '+', '.join(stale))
    else:
        # Validation and both renders finish before either output is touched.
        for name, page in pages.items():
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix('.html.tmp')
            temporary.write_text(page, encoding='utf-8')
            temporary.replace(destination)
    return pages


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify generated pages without writing')
    args = parser.parse_args()
    try:
        pages = build(check=args.check)
    except (ContentError, KeyError, TypeError, OSError, TemplateError, json.JSONDecodeError) as error:
        parser.exit(1, f'Content error: {error}\n')
    print(('Verified' if args.check else 'Generated') + ': ' + ', '.join(pages))
