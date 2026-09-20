import pytest

from src.primespiders.utils.urls import URL


async def test_url_instance():
    url = URL("https://example.com")
    assert url.is_valid
    assert url.domain == "example.com"
    assert url == 'https://example.com'


@pytest.mark.parametrize(
    "raw_url,expected_domain",
    [
        ("https://example.com", "example.com"),
        ("http://sub.example.com", "sub.example.com"),
        ("/relative/path", ""),
    ]
)
async def test_url_domains(raw_url, expected_domain):
    url = URL(raw_url)
    assert url.domain == expected_domain


@pytest.mark.parametrize(
    "raw_url,expected_parts",
    [
        ("https://example.com/path/to/resource", ["path", "to", "resource"]),
        ("http://sub.example.com/", [""]),
        ("/relative/path", ["relative", "path"]),
    ]
)
async def test_url_parts(raw_url, expected_parts):
    url = URL(raw_url)
    assert url.parts == expected_parts


async def test_url_extensions():
    url = URL("https://example.com/image.jpg")
    assert ".jpg" in url.extensions
    assert ".png" in url.extensions


@pytest.mark.parametrize(
    "raw_url,expected_validity,rootdomain",
    [
        ("https://example.com", True, None),
        ("http://sub.example.com", True, None),
        ("/relative/path", False, None),
        ("", False, None),
        ("ftp://example.com", False, None),
        ("https://example.com", True, "example.com"),
        ("https://example.com", False, "sub.example.com"),
    ]
)
async def test_validity(raw_url, expected_validity, rootdomain):
    url = URL(raw_url, root_domain=rootdomain)
    assert url.is_valid == expected_validity
    if rootdomain is not None:
        assert url.root_domain == rootdomain


@pytest.mark.parametrize(
    "raw_url,expected_full_url",
    [
        ("https://example.com/path/to/resource", "https://example.com/path/to/resource"),
        ("/path/to/resource", "https://example.com/path/to/resource"),
    ]
)
def test_full_url(raw_url, expected_full_url):
    if raw_url.startswith("/"):
        url = URL(raw_url, root_domain="https://example.com")
    else:
        url = URL(raw_url)
        
    assert url.full_url is not None
    assert isinstance(url.full_url, URL)
    assert str(url.full_url) == expected_full_url
