from src.primespiders.utils.operators import Q, Rules
from src.primespiders.utils.urls import URL


def url_empty(url: URL):
    """Check if the URL is empty."""
    return Q(Rules.EMPTY)(url)


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


def ignore_social_media(url: URL):
    """Check if the URL belongs to a social media domain."""
    social_media_domains = [
        "facebook",
        "twitter",
        "instagram",
        "linkedin",
        "tiktok",
        "youtube",
        "spotify",
        "pinterest",
        "snapchat",
    ]
    return any(domain in url for domain in social_media_domains)
