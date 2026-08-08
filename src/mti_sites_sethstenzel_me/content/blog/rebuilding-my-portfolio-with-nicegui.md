---
title: Rebuilding My Portfolio With NiceGUI
date: 2026-02-18
image: /content/images/blog/nicegui-portfolio.png
tags: [python, nicegui, web, design]
series: Site Rebuild
series_part: 1
draft: false
---

My old portfolio was a static site I hand-edited every time a project shipped. It
worked, but every update meant touching HTML, and every visual tweak meant hunting
through a stylesheet I had not read in a year. When I started sketching a rebuild I
had one hard requirement: the whole thing should be Python, top to bottom, so that
adding a page felt like writing a function rather than editing a template.

## Why NiceGUI

NiceGUI sits on top of FastAPI and Vue, and it hides almost all of that from you.
You describe the page with nested context managers, it keeps the browser in sync
over a websocket, and you never write a line of JavaScript unless you want to. For
a portfolio site that is mostly layout and content, that trade is close to free.

The parts that sold me:

- Pages are plain functions decorated with `@ui.page`, so routing is just imports.
- Tailwind classes are available on every element via `.classes()`, which means I
  can lean on a design system instead of inventing one.
- The same toolkit scales down to the little desktop utilities I write for work.

## The shape of the site

Everything lives under a `pages` package, and a single `routes.py` imports each
module for its side effect of registering a route. A shared card template wraps the
header, the body, and the footer so every page inherits the same frame:

```python
from nicegui import ui

page_url = '/portfolio'

@ui.page(page_url)
def build_portfolio_page():
    ui.add_head_html('<link rel="stylesheet" href="/static/css/styles.css">')

    def main_content():
        with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 gap-4'):
            for project in load_projects():
                create_project_card(project)

    generate_center_card(generate_header, main_content, generate_footer, url=page_url)
```

Content itself is data, not code. The project cards read from a JSON file, which
means adding a project is a five-line diff and no Python changes at all.

## What I would do differently

I front-loaded the styling and back-loaded the content model, which is exactly
backwards. The layout was pixel-perfect weeks before I had decided how a project
entry should be structured, and I ended up reshaping the CSS anyway once real
content went in. Next time the data model goes first.

If you want to poke at the framework yourself, the
[NiceGUI documentation](https://nicegui.io/documentation) is unusually good — every
component page has a runnable example embedded in it.

Next in this series: adding a blog, which turned out to be far more interesting
than I expected.
