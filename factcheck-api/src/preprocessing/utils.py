import re
import unicodedata

# some labels reach us as javascript escaped markup
JS_ESCAPE_PATTERN = re.compile(r"\\x([0-9a-fA-F]{2})")
MARKUP_PATTERN = re.compile(r"<[^>]+>")


def clean_label(text: str) -> str:
    text = JS_ESCAPE_PATTERN.sub(lambda match: chr(int(match.group(1), 16)), text)
    return MARKUP_PATTERN.sub("", text).strip()


def clean_filename(text: str) -> str:
    # remove accents
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.lower()

    # handle spaces, slashes and special chars
    text = text.replace(" ", "_").replace("/", "_")
    text = re.sub(r"[^a-z0-9_]", "", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip("_")

    return text
