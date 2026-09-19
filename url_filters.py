from utils.operators import Q, Rules
from utils.urls import URL


def is_fragment(value: URL):
    return Q(Rules.EMPTY, value)


def has_fragment(value: URL):
    return value.parsed_url.fragment != ""


def has_query(value: URL):
    return value.parsed_url.query != ""

