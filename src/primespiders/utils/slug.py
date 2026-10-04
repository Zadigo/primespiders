import base64

import unidecode


def create_reference(text: str | None) -> str:
    if text is None:
        return ''
    return base64.urlsafe_b64encode(text)


def create_slug(text: str | None) -> str:
    if text is None:
        return ''
    str_title = text.lower().replace("'", "-").replace(' ', '-')
    return unidecode.unidecode(str_title)
