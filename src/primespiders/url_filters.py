from primespiders.utils.operators import Q, Rules
from primespiders.utils.urls import URL


def url_empty(value: URL):
    """Check if the URL is empty."""
    return Q(Rules.EMPTY, value)


def has_fragment(value: URL):
    """Check if the URL has a fragment (e.g., #section)"""
    return value.parsed_url.fragment != ""


def has_query(value: URL):
    """Check if the URL has a query string (e.g., ?key=value)"""
    return value.parsed_url.query != ""


def is_file(value: URL):
    """Check if the URL points to a file (e.g., ends with a file extension)"""
    path = value.parsed_url.path
    return '.' in path.split('/')[-1]
