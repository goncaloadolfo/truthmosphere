import re

from scrapy.selector import Selector, SelectorList

WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_text(text: str | None) -> str:
    return WHITESPACE_PATTERN.sub(" ", text).strip() if text else ""


def text_of(selector: Selector | SelectorList) -> str:
    return normalize_text(" ".join(selector.css("::text").getall()))


def own_text_of(selector: Selector | SelectorList) -> str:
    # Leaving out nested markup such as symbol captions
    return normalize_text(" ".join(selector.xpath("./text()").getall()))
