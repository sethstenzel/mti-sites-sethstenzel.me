---
title: Building a Blog With NiceGUI
date: 2026-08-07
image: /content/images/blog/nicegui-blog.png
tags: [python, nicegui, web, markdown]
series: Site Rebuild
series_part: 2
draft: false
---

A blog is the classic "I'll just add a database" moment. I did not want a database.
This site gets a few hundred visitors a week, the posts are written by exactly one
person, and the content already lives happily in git. So the blog is a folder of
markdown files with YAML frontmatter, and the entire data layer is one module.

## The file format

Every post is `content/blog/<slug>.md`, and the slug is the URL. The frontmatter
carries the metadata that the listing page needs without having to render the body:

```
---
title: Building a Blog With NiceGUI
date: 2026-08-07
tags: [python, nicegui, web]
series: Site Rebuild
series_part: 2
draft: false
---
```

Only `title` and `date` are required. Everything else degrades gracefully — a post
with no image just renders without one, and a post with no series simply has no
series navigation at the bottom.

## Being generous about input

The one rule I set for the parser was that it should never throw because I typed
something slightly wrong at 1am. That means:

- `tags` accepts a YAML list, a comma-separated string, or nothing at all.
- `date` accepts whatever PyYAML hands back, and falls back to the file's mtime.
- A file with no frontmatter block still parses, using a title-cased slug.
- One broken file logs a warning and gets skipped instead of taking down the
  whole listing page.

That last point matters more than it sounds. The listing page is the front door of
the blog, and a single unbalanced quote in a draft should not 500 it.

## Caching without a cache

Re-reading and re-parsing every post on every request is wasteful, but a real cache
layer would be absurd for a folder of a dozen files. The compromise is a fingerprint:
take the sorted tuple of `(path, mtime_ns)` for the directory, use it as a dict key,
and rebuild only when it changes. Editing a post invalidates it automatically because
the mtime moves. Deleting one invalidates it because the tuple shrinks.

```python
def _directory_fingerprint() -> tuple[tuple[str, int], ...]:
    return tuple(sorted(
        (str(p), p.stat().st_mtime_ns) for p in BLOG_DIR.glob('*.md')
    ))
```

Twelve lines, no invalidation bugs, and it survives an editor writing files behind
the app's back.

## Rendering

Markdown goes through [markdown2](https://github.com/trentm/python-markdown2) with
the fenced-code-blocks and tables extras enabled, and the resulting HTML is dropped
into a `ui.html` element. Syntax highlighting is handled by a stylesheet rather than
a JavaScript pass, which keeps the page weight down.

The whole data layer came in under 400 lines. Sometimes the boring answer really is
the right one.
