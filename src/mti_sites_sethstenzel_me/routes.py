def build_routes():
    # Because these page functions are decorated with the ui.page decorator
    # they need only be imported to register them.
    from mti_sites_sethstenzel_me.pages.index import build_index_page
    from mti_sites_sethstenzel_me.pages.portfolio import build_portfolio_page
    from mti_sites_sethstenzel_me.pages.articles import build_articles_page
    from mti_sites_sethstenzel_me.pages.contact import build_contact_page

