"""Local-only markdown blog editor for sethstenzel.me.

This is a **local authoring tool**, not part of the public website.

Hard rules, deliberately enforced by this module:

* It binds to the loopback interface only (``host='127.0.0.1'``) on a port that is
  distinct from the live site (default ``18002``, override with the
  ``BLOG_EDITOR_PORT`` environment variable). nginx proxies the site on 18001 and
  has no vhost for this port, so the editor is not reachable off-box.
* It is a standalone ``__main__``-runnable module::

      python -m mti_sites_sethstenzel_me.blog_editor

* It **must never** be imported by ``routes.py`` / ``site.py`` and must never be
  added to the production route table. Importing this module is intentionally
  inert: every ``@ui.page`` registration happens inside :func:`_register_pages`,
  which is only ever called from :func:`main`. A stray
  ``import mti_sites_sethstenzel_me.blog_editor`` therefore cannot leak editor
  routes (or the delete/save endpoints they drive) onto the deployed app.

The editor reads and writes posts exclusively through
:mod:`mti_sites_sethstenzel_me.blog_store`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import datetime
import os
import re
import sys

from loguru import logger
from nicegui import app, events, ui

from mti_sites_sethstenzel_me.blog_store import (
    BLOG_IMAGE_DIR,
    BLOG_IMAGE_URL_PREFIX,
    Post,
    all_series,
    all_tags,
    delete_post,
    get_post,
    load_posts,
    save_post,
    slugify,
)

# --------------------------------------------------------------------------- #
# Constants -- every path is absolute and derived from __file__ so the editor can
# be launched from any working directory.
# --------------------------------------------------------------------------- #

PACKAGE_DIR: Path = Path(__file__).resolve().parent
STATIC_DIR: Path = PACKAGE_DIR / 'static'
CONTENT_DIR: Path = PACKAGE_DIR / 'content'

DEFAULT_PORT: int = 18002
LOOPBACK_HOST: str = '127.0.0.1'
ACCENT: str = '#1d6096'

# Only ever used to sign a loopback-only session cookie holding UI preferences.
STORAGE_SECRET: str = 'blog-editor-local-only'
SIDEBAR_STORAGE_KEY: str = 'blog_editor_sidebar_collapsed'

IMAGE_SUFFIXES: frozenset[str] = frozenset(
    {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif', '.svg'}
)

MARKDOWN_EXTRAS: list[str] = ['fenced-code-blocks', 'tables']

STARTER_BODY: str = 'Start writing...\n'

# Forces browser-native spell checking onto the inner ``<textarea>`` Quasar renders.
# The Quasar ``spellcheck`` prop normally passes straight through to the native
# element, but this observer guarantees it regardless of Quasar/NiceGUI internals.
# It also swallows the browser's Ctrl+S "save page" dialog so ui.keyboard can own it.
_HEAD_SCRIPT: str = '''
<script>
(function () {
    const forceSpellcheck = function () {
        document.querySelectorAll('.blog-editor-source textarea').forEach(function (node) {
            if (node.getAttribute('spellcheck') !== 'true') {
                node.setAttribute('spellcheck', 'true');
                node.dataset.spellcheckForced = 'js';
            }
            node.spellcheck = true;
        });
    };
    const start = function () {
        forceSpellcheck();
        new MutationObserver(forceSpellcheck).observe(
            document.body, {childList: true, subtree: true});
    };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
    document.addEventListener('keydown', function (event) {
        if ((event.ctrlKey || event.metaKey) && (event.key === 's' || event.key === 'S')) {
            event.preventDefault();
        }
    }, true);
})();
</script>
'''


@dataclass
class EditorState:
    """Mutable per-client state for one editor session."""

    #: Slug of the post currently open on disk, or None for an unsaved new post.
    loaded_slug: str | None = None
    #: True when the form has edits that have not been written to disk.
    dirty: bool = False
    #: True once the user has typed in the slug field, which stops auto-derivation.
    slug_overridden: bool = False
    #: Guard so programmatic form updates do not count as user edits.
    loading: bool = False
    #: Whether the post-list sidebar is collapsed to its narrow rail.
    sidebar_collapsed: bool = False


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def available_images() -> list[str]:
    """Return URL paths for every image already sitting in ``content/images/blog``.

    Returns:
        Sorted ``/content/images/blog/<file>`` URL paths; empty when the directory
        is missing.
    """
    if not BLOG_IMAGE_DIR.is_dir():
        return []
    names = sorted(
        path.name
        for path in BLOG_IMAGE_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    return [f'{BLOG_IMAGE_URL_PREFIX}/{name}' for name in names]


def safe_image_name(name: str) -> str:
    """Sanitize an uploaded filename down to something safe to put on disk.

    Args:
        name: The client supplied filename.

    Returns:
        A filename containing only ``[A-Za-z0-9._-]``, never empty.
    """
    stem = Path(name).name
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '-', stem).strip('-.')
    return cleaned or 'upload.png'


def parse_iso_date(text: str) -> datetime.date | None:
    """Parse a ``YYYY-MM-DD`` string, returning None when it is not a valid date."""
    try:
        return datetime.date.fromisoformat(str(text or '').strip())
    except ValueError:
        return None


def _post_label(post: Post) -> str:
    """Return a one-line description of a post for the open dialog."""
    bits = [post.date.isoformat(), post.title]
    if post.series:
        part = f' #{post.series_part}' if post.series_part is not None else ''
        bits.append(f'[{post.series}{part}]')
    if post.draft:
        bits.append('(draft)')
    return '  '.join(bits)


def _series_label(post: Post) -> str:
    """Return ``Series #part`` for a post in a series, else an empty string."""
    if not post.series:
        return ''
    if post.series_part is None:
        return post.series
    return f'{post.series} #{post.series_part}'


def _matches_query(post: Post, query: str) -> bool:
    """Case-insensitive match of ``query`` against a post's searchable text."""
    if not query:
        return True
    haystack = ' '.join(
        [post.title, post.slug, post.series or '', post.date.isoformat(), *post.tags]
    ).casefold()
    return all(word in haystack for word in query.split())


def _read_sidebar_collapsed() -> bool:
    """Read the persisted sidebar state, defaulting to expanded."""
    try:
        return bool(app.storage.user.get(SIDEBAR_STORAGE_KEY, False))
    except Exception as error:  # noqa: BLE001 - storage is a nicety, never fatal
        logger.debug(f'Could not read sidebar state from storage: {error}')
        return False


def _write_sidebar_collapsed(collapsed: bool) -> None:
    """Persist the sidebar state so it survives a reload."""
    try:
        app.storage.user[SIDEBAR_STORAGE_KEY] = bool(collapsed)
    except Exception as error:  # noqa: BLE001 - storage is a nicety, never fatal
        logger.debug(f'Could not persist sidebar state: {error}')


# --------------------------------------------------------------------------- #
# Page
# --------------------------------------------------------------------------- #

def build_editor_page() -> None:  # noqa: PLR0915 - one cohesive UI builder
    """Build the markdown editor for the current client.

    Three columns: a collapsible sidebar listing every post newest-first, the post
    metadata plus markdown source, and a live debounced preview. The last two live
    in a resizable ``ui.splitter``.
    """
    state = EditorState()

    # Versioned like utils.site_stylesheet(): without the query a returning browser
    # keeps a heuristically-cached old stylesheet and the layout silently breaks.
    try:
        css_version = (STATIC_DIR / 'css' / 'blog_editor.css').stat().st_mtime_ns
    except OSError:
        css_version = 0
    ui.add_head_html(
        f'<link rel="stylesheet" href="/static/css/blog_editor.css?v={css_version}">'
    )
    ui.add_head_html(_HEAD_SCRIPT)

    # ----------------------------------------------------------------- helpers
    def mark_dirty() -> None:
        """Flag unsaved changes unless the form is being populated programmatically."""
        if state.loading:
            return
        if not state.dirty:
            state.dirty = True
            refresh_status()

    def refresh_status() -> None:
        """Update the toolbar status label from the current state."""
        if state.loaded_slug:
            text = f'Editing: {state.loaded_slug}.md'
        else:
            text = 'New post (unsaved)'
        status_label.text = f'{text}{"  *" if state.dirty else ""}'

    def refresh_preview() -> None:
        """Push the markdown source into the existing preview element."""
        preview.content = source.value or ''
        image_url = (image_select.value or '').strip()
        preview_image.set_source(image_url or '')
        preview_image.set_visibility(bool(image_url))
        preview_title.text = (title_input.value or '').strip() or 'Untitled'
        date_text = (date_input.value or '').strip()
        preview_meta.text = date_text

    async def confirm(message: str, ok_text: str = 'Discard', color: str = 'negative') -> bool:
        """Show a modal yes/no dialog and await the answer.

        Args:
            message: Question to show the user.
            ok_text: Label for the affirmative button.
            color: Quasar color for the affirmative button.

        Returns:
            True when the user confirmed.
        """
        with ui.dialog() as dialog, ui.card().classes('gap-4 p-4'):
            ui.label(message).classes('text-base')
            with ui.row().classes('w-full justify-end gap-2'):
                ui.button('Cancel', on_click=lambda: dialog.submit(False)).props('flat')
                ui.button(ok_text, on_click=lambda: dialog.submit(True)).props(f'color={color}')
        try:
            return bool(await dialog)
        finally:
            dialog.delete()

    async def confirm_discard() -> bool:
        """Return True when it is safe to throw away the current form contents."""
        if not state.dirty:
            return True
        return await confirm('This post has unsaved changes. Discard them?')

    def refresh_image_options(select_value: str | None = None) -> None:
        """Reload the header-image dropdown from disk, optionally selecting a value."""
        options = available_images()
        if select_value and select_value not in options:
            options.append(select_value)
        image_select.options = options
        if select_value is not None:
            image_select.value = select_value
        image_select.update()

    def refresh_vocabulary(extra_tags: tuple[str, ...] = (), extra_series: str | None = None) -> None:
        """Reseed the tag/series dropdowns from the posts currently on disk."""
        posts = load_posts(include_drafts=True)
        tags = all_tags(posts)
        for tag in extra_tags:
            if tag not in tags:
                tags.append(tag)
        series = all_series(posts)
        if extra_series and extra_series not in series:
            series.append(extra_series)
        tags_select.options = tags
        tags_select.update()
        series_select.options = series
        series_select.update()

    def load_blank() -> None:
        """Reset the whole form to an empty post dated today."""
        state.loading = True
        try:
            title_input.value = ''
            slug_input.value = ''
            date_input.value = datetime.date.today().isoformat()
            refresh_image_options('')
            tags_select.value = []
            series_select.value = None
            series_part_input.value = None
            draft_switch.value = True
            source.value = STARTER_BODY
            refresh_vocabulary()
        finally:
            state.loading = False
        state.loaded_slug = None
        state.slug_overridden = False
        state.dirty = False
        refresh_status()
        refresh_preview()
        refresh_post_list()

    def load_post(post: Post) -> None:
        """Populate the form from an existing post."""
        state.loading = True
        try:
            title_input.value = post.title
            slug_input.value = post.slug
            date_input.value = post.date.isoformat()
            refresh_image_options(post.image or '')
            refresh_vocabulary(extra_tags=post.tags, extra_series=post.series)
            tags_select.value = list(post.tags)
            series_select.value = post.series
            series_part_input.value = post.series_part
            draft_switch.value = bool(post.draft)
            source.value = post.body
        finally:
            state.loading = False
        state.loaded_slug = post.slug
        state.slug_overridden = True
        state.dirty = False
        refresh_status()
        refresh_preview()
        refresh_post_list()
        logger.info(f'Opened blog post in editor: {post.path}')

    # ----------------------------------------------------------- post sidebar
    def refresh_post_list() -> None:
        """Rebuild the sidebar list from disk, newest post first.

        ``load_posts`` is cached against the blog directory's mtime fingerprint and
        ``save_post``/``delete_post`` clear that cache, so calling this after any
        write is enough to keep the list truthful across saves, renames and deletes.
        """
        posts = load_posts(include_drafts=True)  # already sorted newest first
        query = (search_input.value or '').strip().casefold()
        visible = [post for post in posts if _matches_query(post, query)]

        post_count_label.text = (
            f'{len(posts)}' if len(visible) == len(posts) else f'{len(visible)}/{len(posts)}'
        )

        post_list.clear()
        with post_list:
            if not posts:
                ui.label('No posts yet.').classes('blog-editor-post-empty')
                return
            if not visible:
                ui.label('No posts match that filter.').classes('blog-editor-post-empty')
                return
            for post in visible:
                current = post.slug == state.loaded_slug
                classes = 'blog-editor-post-row' + (' is-current' if current else '')
                row = ui.element('div').classes(classes)
                row.on('click', lambda _=None, slug=post.slug: open_slug(slug))
                with row:
                    ui.label(post.title).classes('blog-editor-post-title')
                    with ui.element('div').classes('blog-editor-post-meta'):
                        ui.label(post.date.isoformat()).classes('blog-editor-post-date')
                        if post.series:
                            ui.label(_series_label(post)).classes('blog-editor-post-series')
                        if post.draft:
                            ui.label('draft').classes('blog-editor-post-draft')

    def load_slug(slug: str) -> None:
        """Load ``slug`` into the editor without asking about unsaved changes."""
        post = get_post(slug, include_drafts=True)
        if post is None:
            ui.notify(f'Post "{slug}" could not be loaded.', type='negative')
            refresh_post_list()
            return
        load_post(post)

    async def open_slug(slug: str) -> None:
        """Open a post from the sidebar, guarding any unsaved changes first.

        Clicking the row of the post already open is a no-op unless the buffer is
        dirty, in which case reloading it from disk still needs confirmation.
        """
        if slug == state.loaded_slug and not state.dirty:
            return
        if not await confirm_discard():
            return
        load_slug(slug)

    def apply_sidebar_state() -> None:
        """Sync the sidebar's CSS class and toggle icons to ``state``."""
        collapsed = state.sidebar_collapsed
        sidebar.classes(add='collapsed') if collapsed else sidebar.classes(remove='collapsed')
        icon = 'chevron_right' if collapsed else 'chevron_left'
        sidebar_toggle.props(f'icon={icon}')

    def toggle_sidebar() -> None:
        """Collapse or expand the post list and remember the choice."""
        state.sidebar_collapsed = not state.sidebar_collapsed
        apply_sidebar_state()
        _write_sidebar_collapsed(state.sidebar_collapsed)

    # ------------------------------------------------------------- event hooks
    def on_title_change() -> None:
        """Auto-derive the slug while the user has not taken it over manually."""
        if not state.loading and not state.slug_overridden:
            derived = slugify(title_input.value or '')
            if (title_input.value or '').strip():
                state.loading = True
                try:
                    slug_input.value = derived
                finally:
                    state.loading = False
        mark_dirty()
        refresh_preview()

    def on_slug_change() -> None:
        """A user edit to the slug field permanently stops auto-derivation."""
        if not state.loading:
            state.slug_overridden = True
        mark_dirty()

    def on_body_change() -> None:
        """Re-render the preview (already debounced client side) and flag edits."""
        mark_dirty()
        refresh_preview()

    def on_image_change() -> None:
        """Refresh the thumbnail and preview header when the image selection changes."""
        mark_dirty()
        url = (image_select.value or '').strip()
        thumbnail.set_source(url or '')
        thumbnail.set_visibility(bool(url))
        refresh_preview()

    def on_date_change() -> None:
        """Flag edits and refresh the preview byline."""
        mark_dirty()
        refresh_preview()

    async def handle_upload(event: events.UploadEventArguments) -> None:
        """Save an uploaded image into ``content/images/blog`` and select it.

        NiceGUI 3.x hands over a ``FileUpload`` on ``event.file`` exposing ``name``
        and an awaitable ``save()``; existing filenames are never clobbered.
        """
        try:
            BLOG_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
            name = safe_image_name(event.file.name)
            target = BLOG_IMAGE_DIR / name
            counter = 1
            while target.exists():
                target = BLOG_IMAGE_DIR / f'{Path(name).stem}-{counter}{Path(name).suffix}'
                counter += 1
            await event.file.save(target)
        except Exception as error:  # noqa: BLE001 - surface, never crash the editor
            logger.exception(f'Image upload failed: {error}')
            ui.notify(f'Upload failed: {error}', type='negative')
            return
        logger.info(f'Uploaded blog image: {target}')
        upload.reset()
        refresh_image_options(f'{BLOG_IMAGE_URL_PREFIX}/{target.name}')
        on_image_change()
        ui.notify(f'Uploaded {target.name}', type='positive')

    def collect() -> dict | None:
        """Validate the form and return kwargs for :func:`save_post`, or None.

        Errors are surfaced with a negative ``ui.notify`` instead of raising.
        """
        title = (title_input.value or '').strip()
        if not title:
            ui.notify('A title is required.', type='negative')
            return None

        # An emptied slug field falls back to the title, matching the auto-derivation.
        raw_slug = (slug_input.value or '').strip() or title
        slug = slugify(raw_slug)
        if not slug:
            ui.notify('A slug is required.', type='negative')
            return None

        clash = get_post(slug, include_drafts=True)
        if clash is not None and clash.slug != state.loaded_slug:
            ui.notify(f'The slug "{slug}" is already used by another post.', type='negative')
            return None

        date = parse_iso_date(date_input.value or '')
        if date is None:
            ui.notify('Date must be a valid YYYY-MM-DD date.', type='negative')
            return None

        part_value = series_part_input.value
        series_part = int(part_value) if part_value not in (None, '') else None

        return {
            'slug': slug,
            'title': title,
            'date': date,
            'body': source.value or '',
            'image': (image_select.value or '').strip() or None,
            'tags': tuple(tags_select.value or ()),
            'series': (series_select.value or '').strip() or None,
            'series_part': series_part,
            'draft': bool(draft_switch.value),
            'old_slug': state.loaded_slug,
        }

    def do_save() -> None:
        """Validate and persist the current post."""
        payload = collect()
        if payload is None:
            return
        try:
            written = save_post(**payload)
        except Exception as error:  # noqa: BLE001 - blog_store raises ValueError/OSError
            logger.exception(f'Saving blog post failed: {error}')
            ui.notify(f'Save failed: {error}', type='negative')
            return
        state.loading = True
        try:
            slug_input.value = payload['slug']
        finally:
            state.loading = False
        state.loaded_slug = payload['slug']
        state.slug_overridden = True
        state.dirty = False
        refresh_vocabulary()
        refresh_status()
        # Picks up new posts, retitled posts and the file move behind a slug rename.
        refresh_post_list()
        ui.notify(f'Saved {written}', type='positive')

    async def do_new() -> None:
        """Clear the form after confirming any unsaved changes."""
        if await confirm_discard():
            load_blank()
            ui.notify('Started a new post.')

    async def do_open() -> None:
        """Pick an existing post (drafts included) and load it into the editor."""
        if not await confirm_discard():
            return
        posts = load_posts(include_drafts=True)
        if not posts:
            ui.notify('There are no posts to open yet.', type='warning')
            return
        with ui.dialog() as dialog, ui.card().classes('w-[36rem] max-w-full gap-2 p-4'):
            ui.label('Open a post').classes('text-lg font-medium')
            with ui.column().classes('w-full gap-1 max-h-96 overflow-auto'):
                for post in posts:
                    ui.button(
                        _post_label(post),
                        on_click=lambda _=None, p=post: dialog.submit(p.slug),
                    ).props('flat no-caps align=left').classes('w-full')
            with ui.row().classes('w-full justify-end'):
                ui.button('Cancel', on_click=lambda: dialog.submit(None)).props('flat')
        try:
            chosen = await dialog
        finally:
            dialog.delete()
        if not chosen:
            return
        load_slug(chosen)

    async def do_delete() -> None:
        """Delete the post currently open, after an explicit confirmation."""
        if not state.loaded_slug:
            ui.notify('This post has not been saved yet, so there is nothing to delete.',
                      type='warning')
            return
        slug = state.loaded_slug
        if not await confirm(f'Permanently delete "{slug}.md"? This cannot be undone.',
                             ok_text='Delete'):
            return
        if delete_post(slug):
            ui.notify(f'Deleted {slug}.md', type='positive')
            load_blank()
        else:
            ui.notify(f'Could not delete {slug}.md', type='negative')

    def on_key(event: events.KeyEventArguments) -> None:
        """Handle Ctrl+S / Cmd+S as save."""
        if event.action.keydown and event.key == 's' and (
            event.modifiers.ctrl or event.modifiers.meta
        ):
            do_save()

    # ----------------------------------------------------------------- toolbar
    with ui.row().classes('blog-editor-toolbar w-full items-center gap-2 px-3 py-2'):
        ui.button(icon='menu_open', on_click=toggle_sidebar).props('flat dense round') \
            .tooltip('Show or hide the post list')
        ui.icon('edit_note').classes('text-2xl').style(f'color: {ACCENT}')
        ui.label('Blog Editor').classes('text-lg font-medium mr-2')
        ui.button('New', icon='note_add', on_click=do_new).props('flat no-caps')
        ui.button('Open', icon='folder_open', on_click=do_open).props('flat no-caps')
        ui.button('Save', icon='save', on_click=do_save).props('unelevated no-caps') \
            .style(f'background-color: {ACCENT}; color: white')
        ui.button('Delete', icon='delete', on_click=do_delete).props('flat no-caps color=negative')
        ui.space()
        status_label = ui.label('').classes('blog-editor-status text-sm')
        ui.label(f'127.0.0.1:{editor_port()}').classes('text-xs opacity-60 ml-3')

    # -------------------------------------------------------------------- body
    # Layout: [post list] | [markdown source | preview]. The sidebar is a plain
    # flex column rather than ui.left_drawer so it cannot contend with the
    # full-viewport splitter's own height/scroll handling.
    with ui.row().classes('blog-editor-body w-full no-wrap'):
        with ui.column().classes('blog-editor-sidebar') as sidebar:
            with ui.row().classes('blog-editor-sidebar-head no-wrap items-center'):
                sidebar_toggle = ui.button(icon='chevron_left', on_click=toggle_sidebar) \
                    .props('flat dense round').classes('blog-editor-sidebar-toggle')
                sidebar_toggle.tooltip('Show or hide the post list')
                ui.label('Posts').classes('blog-editor-sidebar-title')
                post_count_label = ui.label('').classes('blog-editor-sidebar-count')
            with ui.column().classes('blog-editor-sidebar-body'):
                search_input = ui.input(
                    placeholder='Filter posts...', on_change=lambda: refresh_post_list(),
                ).props('outlined dense clearable debounce=200 spellcheck="false"') \
                    .classes('blog-editor-search')
                post_list = ui.column().classes('blog-editor-post-list')

        with ui.splitter(value=50, limits=(0, 100)).classes('blog-editor-splitter') as splitter:
            with splitter.before:
                with ui.column().classes('blog-editor-pane blog-editor-left'):
                    with ui.element('div').classes('blog-editor-meta'):
                        with ui.row().classes('w-full gap-3 items-start no-wrap'):
                            title_input = ui.input('Title', on_change=on_title_change) \
                                .props('outlined dense spellcheck="true"').classes('grow')
                            date_input = ui.input('Date', on_change=on_date_change) \
                                .props('outlined dense mask="####-##-##"').classes('w-40')
                            with date_input.add_slot('append'):
                                ui.icon('event').classes('cursor-pointer') \
                                    .on('click', lambda: date_menu.open())
                            with ui.menu().props('no-parent-event') as date_menu:
                                ui.date().bind_value(date_input).props('color=primary')

                        with ui.row().classes('w-full gap-3 items-start no-wrap'):
                            slug_input = ui.input('Slug', on_change=on_slug_change) \
                                .props('outlined dense spellcheck="false"').classes('grow')
                            draft_switch = ui.switch('Draft', on_change=lambda: mark_dirty()) \
                                .classes('mt-1')

                        with ui.row().classes('w-full gap-3 items-start no-wrap'):
                            tags_select = ui.select(
                                [], label='Tags', multiple=True, with_input=True,
                                new_value_mode='add-unique', on_change=lambda: mark_dirty(),
                            ).props('outlined dense use-chips').classes('grow')
                            series_select = ui.select(
                                [], label='Series', with_input=True, clearable=True,
                                new_value_mode='add-unique', on_change=lambda: mark_dirty(),
                            ).props('outlined dense').classes('grow')
                            series_part_input = ui.number(
                                'Part', min=1, precision=0, step=1,
                                on_change=lambda: mark_dirty(),
                            ).props('outlined dense').classes('w-24')

                        with ui.row().classes('w-full gap-3 items-center no-wrap'):
                            image_select = ui.select(
                                [], label='Header image', clearable=True,
                                on_change=on_image_change,
                            ).props('outlined dense').classes('grow')
                            upload = ui.upload(
                                on_upload=handle_upload, auto_upload=True,
                                max_file_size=20 * 1024 * 1024, label='Upload image',
                            ).props('flat dense accept="image/*"') \
                                .classes('blog-editor-upload w-64')
                            thumbnail = ui.image('').classes('blog-editor-thumb')
                            thumbnail.set_visibility(False)

                    source = ui.textarea(
                        placeholder='# Write your post in markdown...',
                        on_change=on_body_change,
                    ).props(
                        'outlined dense debounce=300 spellcheck="true" autogrow=false '
                        'input-class="blog-editor-textarea"'
                    ).classes('blog-editor-source w-full')

            with splitter.after:
                with ui.column().classes('blog-editor-pane blog-editor-preview'):
                    preview_image = ui.image('').classes('blog-editor-preview-image')
                    preview_image.set_visibility(False)
                    preview_title = ui.label('Untitled').classes('blog-editor-preview-title')
                    preview_meta = ui.label('').classes('blog-editor-preview-meta')
                    preview = ui.markdown('', extras=MARKDOWN_EXTRAS) \
                        .classes('blog-editor-markdown w-full')

    ui.keyboard(on_key=on_key, ignore=[], repeating=False)

    state.sidebar_collapsed = _read_sidebar_collapsed()
    apply_sidebar_state()
    load_blank()


# --------------------------------------------------------------------------- #
# Wiring -- deliberately NOT executed at import time
# --------------------------------------------------------------------------- #

def editor_port() -> int:
    """Return the port the editor listens on (``BLOG_EDITOR_PORT`` or 18002)."""
    raw = os.environ.get('BLOG_EDITOR_PORT', '')
    try:
        return int(raw) if raw.strip() else DEFAULT_PORT
    except ValueError:
        logger.warning(f'Invalid BLOG_EDITOR_PORT={raw!r}; falling back to {DEFAULT_PORT}')
        return DEFAULT_PORT


def _register_pages() -> None:
    """Register the editor's ``@ui.page`` routes.

    Called only from :func:`main`. Keeping registration out of module scope is what
    makes ``import mti_sites_sethstenzel_me.blog_editor`` inert, so the editor can
    never end up in the production route table by accident.
    """
    ui.page('/')(build_editor_page)
    logger.debug('Blog editor page registered at /')


def _mount_static_files() -> None:
    """Mount ``/static`` and ``/content`` using absolute paths.

    The main site mounts these relative to its working directory; the editor uses
    ``__file__``-derived absolute paths so it can be launched from anywhere and
    still resolve stylesheets and header-image previews.
    """
    app.add_static_files('/static', STATIC_DIR)
    app.add_static_files('/content', CONTENT_DIR)
    logger.debug(f'Static mounts: /static -> {STATIC_DIR}, /content -> {CONTENT_DIR}')


def main() -> None:
    """Run the editor on loopback only.

    Never change ``host`` away from ``127.0.0.1``: this tool has no authentication
    and can delete post files, so it must stay unreachable from the network.
    """
    logger.remove()
    logger.add(
        sys.stdout,
        format=('<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | '
                '<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>'),
        level='INFO',
    )

    port = editor_port()
    show = os.environ.get('BLOG_EDITOR_NO_BROWSER', '') == ''

    _mount_static_files()
    _register_pages()

    logger.info('Starting the LOCAL-ONLY blog editor')
    logger.info(f'Host: {LOOPBACK_HOST} (loopback only - never expose this)')
    logger.info(f'Port: {port}')
    logger.info(f'Blog directory: {PACKAGE_DIR / "content" / "blog"}')

    ui.run(
        host=LOOPBACK_HOST,
        port=port,
        reload=False,
        show=show,
        title='Blog Editor (local)',
        favicon='📝',
        dark=False,
        storage_secret=STORAGE_SECRET,  # only signs the sidebar collapse preference
    )


if __name__ in {'__main__', '__mp_main__'}:
    main()
