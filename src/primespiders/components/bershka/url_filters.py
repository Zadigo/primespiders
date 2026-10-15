from primespiders.utils.operators import Or, Q, Rules
from primespiders.utils.urls import URL


def remove_static_page(url: URL):
    """Remove Bershka static and privacy-related pages from the URL."""

    rules = [
        Q(Rules.CONTAINS, "static.bershka.net"),
        Q(Rules.CONTAINS, "integration/privacy"),
        Q(Rules.CONTAINS, "static.inditex.com"),
        Q(Rules.CONTAINS, "cart"),
        Q(Rules.CONTAINS, "packaging"),
        Q(Rules.CONTAINS, "shopping-guide"),
        Q(Rules.CONTAINS, "member-content"),
        Q(Rules.CONTAINS, "wish-list"),
        Q(Rules.CONTAINS, "store-locator"),
        Q(Rules.CONTAINS, "mmbrs"),
        Q(Rules.CONTAINS, "faq"),
        Q(Rules.CONTAINS, "gift-card"),
        Q(Rules.CONTAINS, "company"),
        Q(Rules.CONTAINS, "guest-orders-validation"),
        Q(Rules.CONTAINS, "openwifi"),
    ]
    
    # return Or(url, *[rule(url) for rule in rules])
    return Or(url, *rules)
