from functools import cached_property
from urllib.parse import urlparse, urlunparse

from PIL import Image


class URL:
    """Represents a URL and provides utility methods for URL manipulation.

    Args:
        url (str | bytes | None): The raw URL string or bytes.
        root_domain (str | None): The root domain to be used for relative URLs.

    Attributes:
        raw_url (str): The raw URL string.
        parsed_url (ParseResult): The parsed URL object from urlparse.
        root_domain (str | None): The root domain for relative URLs.
    
    """
    def __init__(self, url: str | bytes | None, root_domain: str | None = None):
        self.raw_url = url.decode() if isinstance(url, bytes) else (url or "")
        self.parsed_url = urlparse(self.raw_url)

        self.root_domain: str | None = None
        if root_domain is not None: 
            # Must have a scheme otherwise urlparse will not correctly parse the netloc.
            _root_domain = 'https://' + root_domain if not root_domain.startswith("http") else root_domain
            self.root_domain = urlparse(_root_domain or "").netloc

    def __repr__(self):
        return f"URL(raw_url='{self.raw_url}', domain='{self.domain}')"

    def __str__(self):
        return self.raw_url
    
    def __eq__(self, other: str | URL):
        if not isinstance(other, URL):
            return self.raw_url == str(other)
        return self.raw_url == other.raw_url and self.domain == other.domain

    def __hash__(self):
        return hash((self.raw_url, self.domain))

    def __contains__(self, value: str):
        return str(value) in self.raw_url

    @cached_property
    def extensions(self):
        return list(Image._EXTENSION_PLUGIN.keys())

    @property
    def is_valid(self):
        """Check if the URL is valid based on its 
        scheme, netloc, and root domain."""
        logic = [
            self.is_not_none,
            self.parsed_url.scheme in ("http", "https"),
            bool(self.parsed_url.netloc)
        ]

        # If a root domain is specified, ensure 
        # the URL's domain matches it.
        if self.root_domain is not None:
            logic.append(self.domain == self.root_domain)
    
        return all(logic)

    @property
    def is_not_none(self):
        """Check if the URL is None or empty."""
        return bool(self.raw_url)

    @property
    def is_path(self):
        return bool(self.parsed_url.path) and not self.parsed_url.netloc

    @property
    def domain(self):
        """Return the domain part of the URL as a URL object."""
        return self.parsed_url.netloc

    @property
    def full_url(self):
        """Return the full URL, including the 
        root domain if the URL is relative."""
        if self.parsed_url.netloc != "" and self.parsed_url.path != "":
            return URL(self.raw_url, root_domain=self.root_domain)

        if self.root_domain is not None:
            result = urlunparse((
                'https',  # scheme
                self.root_domain,  # netloc
                self.parsed_url.path,  # path
                self.parsed_url.params,  # params
                self.parsed_url.query,  # query
                self.parsed_url.fragment  # fragment
            ))

            return URL(result, root_domain=self.root_domain)

    @property
    def parts(self):
        """Return the parts of the URL path as a list of strings."""
        return self.parsed_url.path.strip("/").split("/")

    def check_domain(self, url: str) -> bool:
        return self.domain == url
