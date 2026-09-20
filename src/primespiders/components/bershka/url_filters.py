from src.primespiders.utils.operators import Or, Q, Rules
from src.primespiders.utils.urls import URL


def remove_static_page(url: URL):
    """Remove Bershka static and privacy-related pages from the URL."""
    return Or(
        url,
        Q(Rules.CONTAINS, "static.bershka.net")(url),
        Q(Rules.CONTAINS, "integration/privacy")(url),
        Q(Rules.CONTAINS, "static.inditex.com")(url),
        Q(Rules.CONTAINS, "cart")(url),
        Q(Rules.CONTAINS, "packaging")(url),
        Q(Rules.CONTAINS, "shopping-guide")(url),
        Q(Rules.CONTAINS, "member-content")(url),
    )
