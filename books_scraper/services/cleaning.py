import re

_WHITESPACE = re.compile(r"\s+")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


def normalize_text(value: object) -> str | None:
    """Strip and collapse internal whitespace; return ``None`` if empty."""
    if value is None:
        return None
    text = _WHITESPACE.sub(" ", str(value)).strip()
    return text or None


def parse_price(value: object) -> float | None:
    """Remove currency symbols (and garbled ones like ``Â£``), return a float."""
    text = normalize_text(value)
    if text is None:
        return None
    match = _NUMBER.search(text)
    if not match:
        raise ValueError(f"No numeric price in {value!r}")
    return float(match.group().replace(",", "."))


def parse_availability(value: object) -> bool:
    """Return ``True`` for "In stock" (any count suffix), ``False`` otherwise."""
    text = normalize_text(value)
    return bool(text) and text.lower().startswith("in stock")
