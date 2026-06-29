import re
import unicodedata


def slugify(text: str) -> str:
    s = text.strip().lower()

    # Normalize Unicode (e.g. Café → Cafe, façade → facade)
    s = unicodedata.normalize("NFKD", s)
    # Remove combining diacritical marks (accents, umlauts, etc.)
    s = s.encode("ascii", "ignore").decode("ascii")

    # Replace any non-alphanumeric, non-hyphen, non-underscore with a hyphen
    s = re.sub(r"[^a-z0-9_-]", "-", s)

    # Collapse multiple consecutive hyphens/underscores into one hyphen
    s = re.sub(r"[-_]+", "-", s)

    # Remove leading and trailing hyphens
    s = s.strip("-")

    # If the result is empty, return a fallback
    if not s:
        s = "untitled"

    return s
