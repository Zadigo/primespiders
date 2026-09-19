from urllib.parse import urlparse


class URL:
    def __init__(self, url: str | bytes | None, domain: str | None = None):
        self.raw_url = url.decode() if isinstance(url, bytes) else (url or "")
        self.parsed_url = urlparse(self.raw_url)
        self._domain = domain

    def __repr__(self):
        return f"URL(raw_url='{self.raw_url}', domain='{self._domain}')"

    def __str__(self):
        return self.raw_url

    def __eq__(self, other: str | URL):
        if not isinstance(other, URL):
            return self.raw_url == str(other)
        return self.raw_url == other.raw_url and self._domain == other._domain

    def __hash__(self):
        return hash((self.raw_url, self._domain))

    def __contains__(self, value: str):
        return str(value) in self.raw_url

    @property
    def is_valid(self):
        return all(
            [
                self.raw_url != "",
                self.parsed_url.scheme in ("http", "https"),
                bool(self.parsed_url.netloc)
            ]
        )

    @property
    def is_path(self):
        return bool(self.parsed_url.path) and not self.parsed_url.netloc

    @property
    def is_absolute(self):
        return bool(self.parsed_url.netloc)

    @property
    def domain(self):
        return URL(self.parsed_url.netloc)

    @property
    def full_url(self):
        if self.is_absolute:
            return self.raw_url

        if self._domain:
            return f"{self._domain}{self.raw_url}"

        return self.raw_url
