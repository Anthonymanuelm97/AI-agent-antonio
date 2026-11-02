import re

MAX_NAME = 80
MAX_DETAIL = 300

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def clean_text(text: object, maximum: int) -> str:
    cleaned = _CONTROL_CHARS.sub(
        lambda match: " " if match.group().isspace() else "",
        str(text),
    )
    cleaned = " ".join(cleaned.split()).lstrip()

    while cleaned and cleaned[0] in "=+-@":
        cleaned = cleaned[1:].lstrip()

    return cleaned[:maximum]
