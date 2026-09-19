from src.primespiders.utils.operators import Or, PartTest, Q, Rules
from src.primespiders.utils.urls import URL


def remove_static_page(url: URL):
    return Or(
        url,
        Q(Rules.CONTAINS, "static.bershka.net")(url),
        Q(Rules.CONTAINS, "integration/privacy")(url),
        Q(Rules.CONTAINS, "static.inditex.com")(url),
    )


def remove_privacy_pages(url: URL):
    return PartTest(url, "privacy", part='path')
