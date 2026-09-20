import re
import unicodedata


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
