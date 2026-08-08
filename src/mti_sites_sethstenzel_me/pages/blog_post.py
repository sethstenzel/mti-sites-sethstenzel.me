from nicegui import ui
from mti_sites_sethstenzel_me.utils import load_css, import_web_fonts
from mti_sites_sethstenzel_me.pages.templates.constants import DARK_BLUE
from mti_sites_sethstenzel_me.pages.templates.header import generate_header
from mti_sites_sethstenzel_me.pages.templates.footer import generate_footer
from mti_sites_sethstenzel_me.pages.templates.center_card import generate_center_card
from mti_sites_sethstenzel_me.pages.blog import render_image, series_label
from mti_sites_sethstenzel_me.blog_store import (
    Post,
    chronological_neighbors,
    get_post,
    load_posts,
    series_neighbors,
)

# The nav bar highlights on an exact path match, so a post page reports itself as
# the blog section rather than its own URL.
page_url = '/blog'


@ui.page('/blog/{slug}')
def build_blog_post_page(slug: str):
    ui.add_head_html(import_web_fonts())
    ui.add_head_html('<link rel="stylesheet" href="/static/css/styles.css">')

    def main_content():
        # Reloaded per request so edits show up without restarting the server.
        post = get_post(slug)

        with ui.element('div').classes('card-inner-row-content w-full px-4'):
            if post is None:
                render_not_found(slug)
            else:
                render_post(post)

        with ui.row().classes("card-inner-row-footer"):
            ui.label('In search of the fantastic, hidden in the everyday.')

    generate_center_card(generate_header, main_content, generate_footer, url=page_url)


def render_not_found(slug: str) -> None:
    """Friendly in-chrome 404 for a slug that does not resolve to a post."""
    with ui.element('div').classes('blog-empty-state w-full'):
        ui.label('Post not found').classes('blog-empty-title')
        ui.label(
            f'There is no post at /blog/{slug}. It may have been renamed or unpublished.'
        ).classes('blog-empty-text')
        ui.link('← Back to the blog', '/blog').classes('blog-empty-link')


def render_post(post: Post) -> None:
    """Render a single post: header image, metadata, body and bottom navigation."""
    posts = load_posts()

    # ui.column carries an inline 'gap: unset' default style site-wide, so blog
    # containers use plain divs and lay themselves out from CSS.
    with ui.element('div').classes('blog-post w-full'):
        render_image(
            post.image,
            alt=post.title,
            wrapper_classes='blog-post-hero',
            img_classes='blog-post-hero-img',
        )

        with ui.element('div').classes('blog-post-head w-full'):
            ui.label(post.title).classes('blog-post-title')
            with ui.row().classes('blog-post-meta items-center gap-2'):
                ui.label(post.date_display).classes('blog-post-date')
                if post.series:
                    ui.label(series_label(post)).classes('blog-series-badge')
            if post.tags:
                with ui.row().classes('blog-tag-row gap-2'):
                    for tag in post.tags:
                        ui.label(tag).classes('blog-tag-chip')

        ui.markdown(post.body).classes('blog-prose')

        # 1. Series navigation, closest to the body it continues.
        if post.series:
            render_series_nav(post, *series_neighbors(posts, post))

        # 2. General chronological navigation, at the very bottom.
        render_chronological_nav(*chronological_neighbors(posts, post))


def render_series_nav(post: Post, previous: Post | None, following: Post | None) -> None:
    """Previous/next within the post's series, ordered by series part."""
    if previous is None and following is None:
        # A one-part series has nothing to navigate to.
        return
    with ui.element('nav').classes('blog-nav blog-nav-series w-full'):
        ui.label(f'More in {post.series}').classes('blog-nav-heading')
        with ui.row().classes('blog-nav-row w-full items-stretch gap-3'):
            render_nav_slot('Previous in series', previous)
            render_nav_slot('Next in series', following, align_right=True)


def render_chronological_nav(previous: Post | None, following: Post | None) -> None:
    """Site-wide previous (older) / next (newer) navigation."""
    if previous is None and following is None:
        return
    with ui.element('nav').classes('blog-nav blog-nav-chrono w-full'):
        ui.label('All posts').classes('blog-nav-heading')
        with ui.row().classes('blog-nav-row w-full items-stretch gap-3'):
            render_nav_slot('Previous post', previous)
            render_nav_slot('Next post', following, align_right=True)


def render_nav_slot(caption: str, post: Post | None, align_right: bool = False) -> None:
    """One side of a navigation pair; renders disabled when there is no neighbour."""
    side = 'blog-nav-slot-right' if align_right else 'blog-nav-slot-left'
    if post is None:
        with ui.element('div').classes(f'blog-nav-slot blog-nav-slot-empty {side}'):
            ui.label(caption).classes('blog-nav-caption')
            ui.label('—').classes('blog-nav-title')
        return
    with ui.link(target=post.url).classes(f'blog-nav-slot {side}'):
        ui.label(caption).classes('blog-nav-caption')
        ui.label(post.title).classes('blog-nav-title')
