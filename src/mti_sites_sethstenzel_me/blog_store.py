"""Data layer for the blog: parsing, loading, filtering and saving markdown posts.

Posts live as markdown files with YAML frontmatter in ``content/blog/<slug>.md``.
This module is deliberately free of any NiceGUI imports so it can be used by the
public pages, the editor and by tests alike.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence
import datetime
import re
import unicodedata

import yaml
from loguru import logger

BLOG_DIR: Path = Path(__file__).parent / 'content' / 'blog'
BLOG_IMAGE_DIR: Path = Path(__file__).parent / 'content' / 'images' / 'blog'
BLOG_IMAGE_URL_PREFIX: str = '/content/images/blog'


class _FlowList(list):
    """A list that ``yaml.safe_dump`` renders inline, e.g. ``[python, web]``."""


yaml.SafeDumper.add_representer(
    _FlowList,
    lambda dumper, data: dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=True),
)

# Matches a leading YAML frontmatter block delimited by '---' lines.
_FRONTMATTER_RE = re.compile(r'^﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)', re.DOTALL)


@dataclass(frozen=True)
class Post:
    """A single blog post parsed from a markdown file."""

    slug: str
    title: str
    date: datetime.date
    image: str | None
    tags: tuple[str, ...]
    series: str | None
    series_part: int | None
    draft: bool
    body: str
    path: Path

    @property
    def url(self) -> str:
        """Site-relative URL for this post's detail page."""
        return f'/blog/{self.slug}'

    @property
    def date_display(self) -> str:
        """Human readable publication date, e.g. 'August 7, 2026'."""
        return f'{self.date.strftime("%B")} {self.date.day}, {self.date.year}'


# --------------------------------------------------------------------------- #
# Normalization helpers
# --------------------------------------------------------------------------- #

def slugify(title: str) -> str:
    """Convert a post title into a URL-safe slug.

    Lowercases, strips accents and punctuation, collapses whitespace and runs of
    hyphens into single hyphens and trims leading/trailing hyphens. Falls back to
    'untitled' when nothing usable remains.

    Args:
        title: Free-form post title.

    Returns:
        A lowercase hyphen-separated slug, never empty.
    """
    text = unicodedata.normalize('NFKD', str(title or ''))
    text = ''.join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    text = re.sub(r'-{2,}', '-', text).strip('-')
    return text or 'untitled'


def _normalize_tags(value: Any) -> tuple[str, ...]:
    """Normalize a frontmatter ``tags`` value into a tuple of clean strings.

    Accepts a YAML list, a comma-separated string, a bare scalar or None.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        parts: list[Any] = value.split(',')
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        parts = [value]
    tags: list[str] = []
    for part in parts:
        tag = str(part).strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tuple(tags)


def _normalize_date(value: Any, fallback_path: Path | None = None) -> datetime.date:
    """Normalize a frontmatter ``date`` value into a ``datetime.date``.

    PyYAML natively yields ``date``/``datetime`` objects for ISO dates; anything
    else is parsed from its string form. On failure the file's mtime date is used
    so a malformed date never breaks a post.
    """
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if value is not None:
        text = str(value).strip()
        if text:
            for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%B %d, %Y', '%b %d, %Y'):
                try:
                    return datetime.datetime.strptime(text, fmt).date()
                except ValueError:
                    continue
            try:
                return datetime.date.fromisoformat(text[:10])
            except ValueError:
                logger.warning(f'Unparseable blog post date {value!r}; falling back to file mtime')
    if fallback_path is not None:
        try:
            return datetime.date.fromtimestamp(fallback_path.stat().st_mtime)
        except OSError:
            pass
    return datetime.date.today()


def _normalize_series_part(value: Any) -> int | None:
    """Normalize a frontmatter ``series_part`` value into an int or None."""
    if value is None or value == '':
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        logger.warning(f'Unparseable blog post series_part {value!r}; ignoring')
        return None


def _normalize_optional_str(value: Any) -> str | None:
    """Return a stripped string, or None for missing/blank values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Split raw file text into a frontmatter mapping and the markdown body."""
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw.lstrip('﻿')
    block = match.group(1)
    body = raw[match.end():]
    data = yaml.safe_load(block)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f'Frontmatter must be a mapping, got {type(data).__name__}')
    return data, body


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #

def parse_post(path: Path) -> Post:
    """Parse a single markdown file into a :class:`Post`.

    Tolerant by design: a file with no frontmatter block still yields a Post whose
    title falls back to a title-cased version of the slug.

    Args:
        path: Path to the ``.md`` file.

    Returns:
        The parsed Post.

    Raises:
        OSError: If the file cannot be read.
        ValueError: If the frontmatter block exists but is not a YAML mapping.
        yaml.YAMLError: If the frontmatter block is not valid YAML.
    """
    path = Path(path)
    raw = path.read_text(encoding='utf-8')
    data, body = _split_frontmatter(raw)

    slug = path.stem
    title = _normalize_optional_str(data.get('title')) or slug.replace('-', ' ').title()

    return Post(
        slug=slug,
        title=title,
        date=_normalize_date(data.get('date'), fallback_path=path),
        image=_normalize_optional_str(data.get('image')),
        tags=_normalize_tags(data.get('tags')),
        series=_normalize_optional_str(data.get('series')),
        series_part=_normalize_series_part(data.get('series_part')),
        draft=bool(data.get('draft', False)),
        body=body.strip('\n'),
        path=path,
    )


# Simple mtime-based cache: maps the directory fingerprint to the parsed posts.
_POSTS_CACHE: dict[tuple[tuple[str, int], ...], list[Post]] = {}


def _directory_fingerprint() -> tuple[tuple[str, int], ...]:
    """Return a sorted (path, mtime_ns) fingerprint of the blog directory."""
    if not BLOG_DIR.is_dir():
        return ()
    entries: list[tuple[str, int]] = []
    for path in BLOG_DIR.glob('*.md'):
        try:
            entries.append((str(path), path.stat().st_mtime_ns))
        except OSError:  # pragma: no cover - file vanished mid-listing
            continue
    return tuple(sorted(entries))


def load_posts(include_drafts: bool = False) -> list[Post]:
    """Load every post in :data:`BLOG_DIR`, newest first.

    Results are cached against the directory's (path, mtime_ns) fingerprint so the
    live site does not re-parse files on every request. Malformed files are logged
    and skipped rather than breaking the whole listing.

    Args:
        include_drafts: When True, posts marked ``draft: true`` are included.

    Returns:
        Posts sorted by date descending, with a stable tiebreak on slug ascending.
    """
    fingerprint = _directory_fingerprint()
    posts = _POSTS_CACHE.get(fingerprint)

    if posts is None:
        posts = []
        for path_str, _mtime in fingerprint:
            path = Path(path_str)
            try:
                posts.append(parse_post(path))
            except Exception as e:
                logger.warning(f'Skipping malformed blog post {path}: {e}')
        posts.sort(key=lambda post: (-post.date.toordinal(), post.slug))
        _POSTS_CACHE.clear()
        _POSTS_CACHE[fingerprint] = posts
        logger.debug(f'Loaded {len(posts)} blog post(s) from {BLOG_DIR}')

    if include_drafts:
        return list(posts)
    return [post for post in posts if not post.draft]


def get_post(slug: str, include_drafts: bool = False) -> Post | None:
    """Return the post with the given slug, or None if it does not exist."""
    for post in load_posts(include_drafts=include_drafts):
        if post.slug == slug:
            return post
    return None


# --------------------------------------------------------------------------- #
# Aggregation / filtering
# --------------------------------------------------------------------------- #

def all_tags(posts: Sequence[Post]) -> list[str]:
    """Return the unique tags across ``posts``, sorted case-insensitively."""
    seen: dict[str, str] = {}
    for post in posts:
        for tag in post.tags:
            seen.setdefault(tag.casefold(), tag)
    return [seen[key] for key in sorted(seen)]


def all_series(posts: Sequence[Post]) -> list[str]:
    """Return the unique series names across ``posts``, sorted."""
    seen: dict[str, str] = {}
    for post in posts:
        if post.series:
            seen.setdefault(post.series.casefold(), post.series)
    return [seen[key] for key in sorted(seen)]


def filter_posts(
    posts: Sequence[Post],
    tag: str | None = None,
    series: str | None = None,
) -> list[Post]:
    """Filter ``posts`` by tag and/or series, preserving the incoming order.

    Both comparisons are case-insensitive. A None filter is ignored.
    """
    result = list(posts)
    if tag:
        needle = tag.casefold()
        result = [p for p in result if any(t.casefold() == needle for t in p.tags)]
    if series:
        needle = series.casefold()
        result = [p for p in result if p.series and p.series.casefold() == needle]
    return result


def chronological_neighbors(posts: Sequence[Post], post: Post) -> tuple[Post | None, Post | None]:
    """Return ``(previous, next)`` around ``post`` in chronological order.

    ``previous`` is the older post and ``next`` is the newer post. Either may be
    None when ``post`` sits at an end of the range (or is not in ``posts``).
    """
    ordered = sorted(posts, key=lambda p: (p.date.toordinal(), p.slug))
    try:
        index = next(i for i, p in enumerate(ordered) if p.slug == post.slug)
    except StopIteration:
        return None, None
    previous = ordered[index - 1] if index > 0 else None
    following = ordered[index + 1] if index + 1 < len(ordered) else None
    return previous, following


def series_neighbors(posts: Sequence[Post], post: Post) -> tuple[Post | None, Post | None]:
    """Return ``(previous, next)`` around ``post`` within its series.

    Ordering is by ``series_part`` ascending, with posts lacking a part sorted last
    by date ascending. Returns ``(None, None)`` when the post has no series.
    """
    if not post.series:
        return None, None
    members = filter_posts(posts, series=post.series)
    ordered = sorted(
        members,
        key=lambda p: (
            p.series_part is None,
            p.series_part if p.series_part is not None else 0,
            p.date.toordinal(),
            p.slug,
        ),
    )
    try:
        index = next(i for i, p in enumerate(ordered) if p.slug == post.slug)
    except StopIteration:
        return None, None
    previous = ordered[index - 1] if index > 0 else None
    following = ordered[index + 1] if index + 1 < len(ordered) else None
    return previous, following


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #

def save_post(
    *,
    slug: str,
    title: str,
    date: datetime.date,
    body: str,
    image: str | None = None,
    tags: Sequence[str] = (),
    series: str | None = None,
    series_part: int | None = None,
    draft: bool = False,
    old_slug: str | None = None,
) -> Path:
    """Write a post to disk as YAML frontmatter plus a markdown body.

    When ``old_slug`` is supplied and differs from ``slug`` the post is renamed:
    the new file is written and the old one removed.

    Args:
        slug: Target slug; also the filename stem.
        title: Post title.
        date: Publication date (a datetime is narrowed to its date).
        body: Markdown body without frontmatter.
        image: Optional hero image URL.
        tags: Tags as a sequence or a comma-separated string.
        series: Optional series name.
        series_part: Optional 1-based position within the series.
        draft: Whether the post is a draft.
        old_slug: Previous slug when renaming an existing post.

    Returns:
        The path the post was written to.

    Raises:
        ValueError: If the slug is empty, or the target file already exists and
            belongs to a different post.
    """
    slug = slugify(slug) if slug else ''
    if not slug:
        raise ValueError('save_post requires a non-empty slug')

    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    target = BLOG_DIR / f'{slug}.md'
    old_path = BLOG_DIR / f'{old_slug}.md' if old_slug else None

    if target.exists() and (old_path is None or target.resolve() != old_path.resolve()):
        raise ValueError(f'A different post already exists at {target.name}')

    if isinstance(date, datetime.datetime):
        date = date.date()
    elif not isinstance(date, datetime.date):
        date = _normalize_date(date)

    frontmatter: dict[str, Any] = {
        'title': title,
        'date': date,
        'image': image or None,
        'tags': _FlowList(_normalize_tags(tags)),
        'series': series or None,
        'series_part': _normalize_series_part(series_part),
        'draft': bool(draft),
    }

    dumped = yaml.safe_dump(
        frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    content = f'---\n{dumped}---\n\n{body.strip()}\n'
    target.write_text(content, encoding='utf-8')
    logger.info(f'Saved blog post: {target}')

    if old_path is not None and old_path.resolve() != target.resolve() and old_path.exists():
        try:
            old_path.unlink()
            logger.info(f'Removed renamed blog post: {old_path}')
        except OSError as e:
            logger.error(f'Could not remove old blog post {old_path}: {e}')

    _POSTS_CACHE.clear()
    return target


def delete_post(slug: str) -> bool:
    """Delete the post file for ``slug``.

    Returns:
        True if a file was deleted, False if there was nothing to delete.
    """
    target = BLOG_DIR / f'{slug}.md'
    if not target.exists():
        logger.warning(f'Cannot delete missing blog post: {target}')
        return False
    try:
        target.unlink()
    except OSError as e:
        logger.error(f'Could not delete blog post {target}: {e}')
        return False
    _POSTS_CACHE.clear()
    logger.info(f'Deleted blog post: {target}')
    return True
