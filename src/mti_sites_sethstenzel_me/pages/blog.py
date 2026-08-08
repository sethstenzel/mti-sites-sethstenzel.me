from nicegui import ui
from mti_sites_sethstenzel_me.utils import load_css, import_web_fonts
from mti_sites_sethstenzel_me.pages.templates.constants import DARK_BLUE
from mti_sites_sethstenzel_me.pages.templates.header import generate_header
from mti_sites_sethstenzel_me.pages.templates.footer import generate_footer
from mti_sites_sethstenzel_me.pages.templates.center_card import generate_center_card
from mti_sites_sethstenzel_me.blog_store import (
    BLOG_IMAGE_DIR,
    Post,
    all_series,
    all_tags,
    filter_posts,
    load_posts,
)
from pathlib import Path
import html
import re

page_url = '/blog'

# Roots used to check that a locally hosted image actually exists on disk before
# we ask the browser for it. Keeps missing header images from rendering as a
# broken-image icon.
_CONTENT_ROOT = BLOG_IMAGE_DIR.parent.parent
_STATIC_ROOT = Path(__file__).parent.parent / 'static'

_REMOTE_PREFIXES = ('http://', 'https://', '//', 'data:')

_EXCERPT_LENGTH = 180


# --------------------------------------------------------------------------- #
# Shared helpers (also used by pages/blog_post.py)
# --------------------------------------------------------------------------- #

def _local_image_path(url: str) -> Path | None:
    """Map a site-relative image URL onto its file on disk, or None if not ours."""
    path = url.split('?', 1)[0].split('#', 1)[0]
    for prefix, root in (('/content/', _CONTENT_ROOT), ('/static/', _STATIC_ROOT)):
        if path.startswith(prefix):
            candidate = root / path[len(prefix):]
            try:
                # Reject anything that escapes the root via '..' segments.
                candidate.resolve().relative_to(root.resolve())
            except (ValueError, OSError):
                return None
            return candidate
    return None


def image_is_available(url: str | None) -> bool:
    """Whether an image URL is worth rendering at all.

    Remote and unrecognised URLs are given the benefit of the doubt (the client
    side ``onerror`` hook cleans up if they fail); locally hosted ones are
    checked against the filesystem.
    """
    if not url:
        return False
    if url.startswith(_REMOTE_PREFIXES):
        return True
    local = _local_image_path(url)
    if local is None:
        return True
    try:
        return local.is_file()
    except OSError:
        return False


def render_image(url: str | None, alt: str, wrapper_classes: str, img_classes: str) -> None:
    """Render an image that removes itself if the file cannot be loaded.

    Missing files are skipped server side; anything that still fails in the
    browser hides its own wrapper via ``onerror`` so no broken-image icon or
    empty frame is ever shown.
    """
    if not image_is_available(url):
        return
    src = html.escape(url or '', quote=True)
    alt_text = html.escape(alt, quote=True)
    ui.html(
        f'<img src="{src}" alt="{alt_text}" class="{img_classes}" loading="lazy" '
        f'onerror="this.closest(\'.blog-img-wrap\').style.display=\'none\'">',
        sanitize=False,
    ).classes(f'blog-img-wrap {wrapper_classes}')


# Markdown constructs that should not leak into a plain-text excerpt.
_EXCERPT_STRIPPERS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'```.*?```', re.DOTALL), ' '),            # fenced code blocks
    (re.compile(r'~~~.*?~~~', re.DOTALL), ' '),            # alternative fences
    (re.compile(r'<[^>]+>'), ' '),                         # inline html
    (re.compile(r'!\[[^\]]*\]\([^)]*\)'), ' '),            # images
    (re.compile(r'\[([^\]]*)\]\([^)]*\)'), r'\1'),         # links -> link text
    (re.compile(r'^\s{0,3}#{1,6}\s*', re.MULTILINE), ''),  # heading markers
    (re.compile(r'^\s{0,3}>\s?', re.MULTILINE), ''),       # blockquote markers
    (re.compile(r'^\s{0,3}([-*+]|\d+\.)\s+', re.MULTILINE), ''),  # list markers
    (re.compile(r'^\s{0,3}([-*_])\s*(\1\s*){2,}$', re.MULTILINE), ' '),  # rules
    (re.compile(r'[`*_~]+'), ''),                          # leftover emphasis
)


def make_excerpt(body: str, length: int = _EXCERPT_LENGTH) -> str:
    """Turn a markdown body into a short plain-text excerpt.

    Strips headings, fences, links and emphasis, collapses whitespace and cuts on
    a word boundary, appending an ellipsis when the text was truncated.
    """
    text = body or ''
    for pattern, replacement in _EXCERPT_STRIPPERS:
        text = pattern.sub(replacement, text)
    text = re.sub(r'\s+', ' ', text).strip()

    if len(text) <= length:
        return text
    clipped = text[:length].rstrip()
    if ' ' in clipped:
        clipped = clipped[:clipped.rfind(' ')].rstrip()
    return clipped.rstrip('.,;:!?-') + '…'


def series_label(post: Post) -> str:
    """Human readable series badge text, e.g. 'Site Rebuild · Part 2'."""
    if not post.series:
        return ''
    if post.series_part is None:
        return post.series
    return f'{post.series} · Part {post.series_part}'


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #

@ui.page(page_url)
def build_blog_page():
    ui.add_head_html(import_web_fonts())
    ui.add_head_html('<link rel="stylesheet" href="/static/css/styles.css">')

    def main_content():
        # Reloaded per request so newly published posts show up on a refresh.
        available_posts = load_posts()
        tag_options = {'': 'All tags'}
        tag_options.update({tag: tag for tag in all_tags(available_posts)})
        series_options = {'': 'All series'}
        series_options.update({name: name for name in all_series(available_posts)})

        with ui.element('div').classes('card-inner-row-content w-full px-4'):
            # ui.column carries an inline 'gap: unset' default style site-wide, so
            # blog containers use plain divs and lay themselves out from CSS.
            with ui.element('div').classes('blog-page w-full'):
                ui.label('Blog').classes('blog-page-title')
                ui.label(
                    'Build logs, teardowns, and the occasional opinion about tooling.'
                ).classes('blog-page-subtitle')

                with ui.row().classes('blog-filter-row w-full items-center gap-3'):
                    tag_select = ui.select(
                        options=tag_options,
                        value='',
                        label='Tag',
                        clearable=True,
                        on_change=lambda: post_list.refresh(),
                    ).props('outlined dense options-dense').classes('blog-filter-select')

                    series_select = ui.select(
                        options=series_options,
                        value='',
                        label='Series',
                        clearable=True,
                        on_change=lambda: post_list.refresh(),
                    ).props('outlined dense options-dense').classes('blog-filter-select')

                    ui.button('Clear filters', on_click=lambda: clear_filters()) \
                        .props('flat dense no-caps').classes('blog-clear-button')

                def selected(select: ui.select) -> str | None:
                    """Normalize a select's value: '' and None both mean 'no filter'."""
                    return select.value or None

                def clear_filters() -> None:
                    """Reset both selects; each assignment triggers a list refresh."""
                    tag_select.value = ''
                    series_select.value = ''
                    post_list.refresh()

                def set_filter(tag: str | None = None, series: str | None = None) -> None:
                    """Apply a filter from a clicked tag chip or series badge."""
                    if tag is not None:
                        tag_select.value = tag if tag in tag_options else ''
                    if series is not None:
                        series_select.value = series if series in series_options else ''
                    post_list.refresh()

                @ui.refreshable
                def post_list() -> None:
                    posts = filter_posts(
                        load_posts(),
                        tag=selected(tag_select),
                        series=selected(series_select),
                    )

                    if not posts:
                        render_empty_state(bool(available_posts), clear_filters)
                        return

                    with ui.element('div').classes('blog-post-list w-full'):
                        # load_posts() is already newest-first and filter_posts
                        # preserves that order.
                        for post in posts:
                            render_post_summary(post, set_filter)

                with ui.element('div').classes('w-full'):
                    post_list()

        with ui.row().classes("card-inner-row-footer"):
            ui.label('In search of the fantastic, hidden in the everyday.')

    generate_center_card(generate_header, main_content, generate_footer, url=page_url)


def render_empty_state(has_any_posts: bool, on_clear) -> None:
    """Message shown when the list is empty, with an escape hatch if filtered."""
    with ui.element('div').classes('blog-empty-state w-full'):
        if has_any_posts:
            ui.label('Nothing matches those filters.').classes('blog-empty-title')
            ui.label(
                'Try a different tag or series, or clear the filters to see everything.'
            ).classes('blog-empty-text')
            ui.button('Clear filters', on_click=lambda: on_clear()) \
                .props('unelevated no-caps').classes('blog-empty-button')
        else:
            ui.label('No posts yet.').classes('blog-empty-title')
            ui.label(
                'The first one is being written. Check back soon.'
            ).classes('blog-empty-text')


def render_post_summary(post: Post, set_filter) -> None:
    """Render one entry in the blog listing."""
    with ui.element('article').classes('blog-card w-full'):
        with ui.row().classes('blog-card-row w-full items-start gap-4'):
            render_image(
                post.image,
                alt=post.title,
                wrapper_classes='blog-card-thumb',
                img_classes='blog-card-thumb-img',
            )

            with ui.element('div').classes('blog-card-body'):
                ui.link(post.title, post.url).classes('blog-card-title')

                with ui.row().classes('blog-card-meta items-center gap-2'):
                    ui.label(post.date_display).classes('blog-card-date')
                    if post.series:
                        ui.label(series_label(post)) \
                            .classes('blog-series-badge blog-clickable') \
                            .on('click', lambda s=post.series: set_filter(series=s))

                excerpt = make_excerpt(post.body)
                if excerpt:
                    ui.label(excerpt).classes('blog-card-excerpt')

                if post.tags:
                    with ui.row().classes('blog-tag-row gap-2'):
                        for tag in post.tags:
                            ui.label(tag) \
                                .classes('blog-tag-chip blog-clickable') \
                                .on('click', lambda t=tag: set_filter(tag=t))

                ui.link('Read post →', post.url).classes('blog-card-more')
