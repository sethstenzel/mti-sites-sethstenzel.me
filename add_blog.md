# Adding a blog post

Posts are plain markdown files with a YAML frontmatter block. There is no database
and no build step — dropping a `.md` file into the blog folder publishes it, and the
running site picks it up on the next page refresh without a restart.

There are two ways to write one: the local editor (easier, and it fills in the
metadata for you) or by hand in your text editor of choice. Both produce the same
file, so you can start a post in the editor and finish it in Vim.

---

## Option 1 — the local editor

### Running it

```bash
# From anywhere, with the project venv active
python -m mti_sites_sethstenzel_me.blog_editor
```

Then open <http://127.0.0.1:18002>. A browser opens automatically.

The editor is a **local authoring tool and is not part of the public website.** It
binds to the loopback interface only, on port 18002 — a different port from the live
site's 18001, with no nginx vhost pointing at it. It is not reachable from another
machine, and importing the module does not register its routes on the deployed app.
Do not add it to `routes.py`.

Two environment variables adjust how it starts:

- `BLOG_EDITOR_PORT=18055` — run on a different port.
- `BLOG_EDITOR_NO_BROWSER=1` — don't open a browser window on startup.

### Finding and reopening posts

The left edge of the window is a list of every post, **newest first**, including
drafts. Click a row to open that post for editing — it loads the title, date, image,
tags, series and body back into the form. The post you're currently editing is
highlighted, drafts are badged, and a filter box at the top narrows the list by title,
slug, series, date or tag.

Collapse the list with the toggle when you want the room, and expand it again from the
same toggle (also available in the toolbar). The editor remembers whether you left it
collapsed.

The *Open* toolbar button does the same thing via a dialog, if you prefer it.

### Writing in it

The rest of the window is split: markdown source in the middle, live preview on the
right. Drag the divider to rebalance. The preview updates as you type (debounced
~300ms), and the source pane has browser spell checking turned on, so misspellings get
the usual squiggle and right-click corrections.

The fields above the editor map one-to-one onto the frontmatter:

| Field | Notes |
|---|---|
| **Title** | Required. The slug auto-derives from it (`My First Post` → `my-first-post`) until you edit the slug yourself, after which it stops overwriting your choice. |
| **Slug** | The URL: `/blog/<slug>`. Must be unique. |
| **Date** | Defaults to today automatically. You only touch it to backdate something. |
| **Header image** | Pick one already in the blog images folder, or upload a new one — the upload is saved and selected for you. Shown at the top of the post. |
| **Tags** | Pick from tags already in use or type a new one. Used by the filter on the blog list page. |
| **Series** | Optional. Pick an existing series or name a new one, then set **part** to order it. |
| **Draft** | On means the post is written but not published — it stays off the list and off its own URL. |

**Toolbar:** *New* starts a blank post dated today, *Save* writes it (`Ctrl+S` also
works), *Delete* removes it after a confirmation. Anything that would replace what
you're editing — *New*, *Open*, or clicking a row in the list — warns you first if you
have unsaved changes.

Renaming a post is safe: change the title or slug and save, and the old file is
removed rather than left behind as a duplicate.

---

## Option 2 — writing the file by hand

Create `src/mti_sites_sethstenzel_me/content/blog/<slug>.md`. The filename is the URL,
so `building-a-thing.md` serves at `/blog/building-a-thing`.

```markdown
---
title: Building a Blog With NiceGUI
date: 2026-08-07
image: /content/images/blog/nicegui-blog.png
tags: [python, nicegui, web]
series: Site Rebuild
series_part: 2
draft: false
---

Your markdown body starts here.

## Headings, lists, links and fenced code blocks all render

- like this
- and this

[Links work too](https://nicegui.io/)
```

Only `title` and `date` really matter. Everything else is optional:

- **`image`** — a URL path, not a disk path. Put the file in
  `src/mti_sites_sethstenzel_me/content/images/blog/` and reference it as
  `/content/images/blog/<filename>`. Omit the key for no header image. A referenced
  image that doesn't exist is skipped rather than rendering a broken-image icon.
- **`tags`** — either a YAML list (`[python, web]`) or a comma-separated string
  (`python, web`). Both work. Matching is case-insensitive.
- **`series`** — a free-text name. Any posts sharing it are linked together, ordered
  by **`series_part`**. Use this for multi-part write-ups.
- **`draft: true`** — hides the post from the list and its own URL. The editor still
  sees it under *Open*.

If you omit or mangle the date, the file's modification time is used instead and a
warning is logged — the post still renders. A malformed post is skipped with a
warning rather than taking down the whole blog.

---

## How it shows up on the site

**`/blog`** lists every non-draft post newest-first, with filter dropdowns for tag and
series at the top. Tag chips and series badges on each card are clickable and apply
that filter.

**`/blog/<slug>`** is the post itself: header image, title, date, series badge and
tags, then the rendered markdown. At the bottom are two navigation blocks — if the
post belongs to a series, *previous/next within that series* comes first, then
*previous (older) / next (newer)* across all posts. A side with no neighbour renders
dimmed rather than linking nowhere.

---

## Previewing and publishing

Run the site locally and visit <http://localhost:18001/blog>:

```bash
cd src/mti_sites_sethstenzel_me
python -m mti_sites_sethstenzel_me.site
```

The site must be started from that directory — the `/static` and `/content` mounts
use paths relative to the working directory.

Posts are loaded per request, so saving a file and refreshing the browser is enough to
see changes. You do not need to restart the server to add, edit or remove a post.

To publish, commit the markdown file (and any images) and push. Pushing to the
`release` branch triggers the deploy webhook, which pulls and restarts the service.

```bash
git add src/mti_sites_sethstenzel_me/content/blog src/mti_sites_sethstenzel_me/content/images/blog
git commit -m "post: building a blog with nicegui"
git push origin release
```

Because `deploy.sh update` runs `git reset --hard` and `git clean -fd` on the server,
**never write posts directly on the production box** — anything uncommitted there is
destroyed on the next deploy. Always author locally and push.
