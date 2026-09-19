from utils.urls import URL

from primespiders.utils.operators import PartTest, Q, Rules


def remove_static_page(url: URL):
    instance = Q(Rules.CONTAINS, "static.bershka.net")
    return instance(url)


def remove_privacy_pages(url: URL):
    return PartTest(url, "privacy", part='path')
