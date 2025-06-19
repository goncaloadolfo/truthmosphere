import os
import re

import scrapy
from scrapy.http import Response

from ..items import TruthmosphereItem


class FactsSpider(scrapy.Spider):
    name = "facts"

    start_urls = os.getenv(
        "TRUTHMOSPHERE_CRAWL_START_URLS",
        "https://poligrafo.sapo.pt/ultimas/",
    ).split(",")

    allowed_domains = os.getenv(
        "TRUTHMOSPHERE_CRAWL_ALLOWED_DOMAINS",
        "poligrafo.sapo.pt",
    ).split(",")

    fact_check_page_pattern = r"^https:\/\/poligrafo\.sapo\.pt\/fact-check\/.*$"

    def parse(self, response: Response):
        # fact check page
        if re.match(self.fact_check_page_pattern, response.url):
            fact_check_section = response.css(".fact_check")

            if fact_check_section:
                item = TruthmosphereItem()

                # missing category and fact summary
                item["title"] = fact_check_section[0].css(".elementor-heading-title::text").get()
                item["explanation"] = self._get_explanation(fact_check_section[0])
                item["assessement_result"] = fact_check_section.css(".fact-check-result span::text").get()
                item["summary"] = fact_check_section[0].css(".post-excerpt::text").get()
                item["category"] = fact_check_section[0].css(".custom-post-categories::text").get()
                item["publication_date"] = fact_check_section[0].css(".custom-post-date-time::text").get()
                item["author"] = fact_check_section[0].css(".custom-post-author-name::text").get().strip()

                yield item

        # listing page
        elif self.start_urls[0] in response.url:
            next_fact_articles = response.css(
                "article.type-fact_check .elementor-widget-container > a::attr(href)"
            ).getall()

            for article in next_fact_articles:
                yield response.follow(article, callback=self.parse)

            yield response.follow(self._get_next_page_url(response.url), callback=self.parse)

    def _get_next_page_url(self, current_url: str) -> str:
        url = current_url
        if url.endswith("/"):
            url = url[:-1]

        path_parts = url.split("/")

        if path_parts[-1].isdigit():
            next_page = int(path_parts[-1]) + 1
            return f"{'/'.join(path_parts[:-1])}/{next_page}"

        return f"{url}/2"

    def _get_explanation(self, fact_check_section) -> str:
        subsections = []

        for element in fact_check_section.css(".elementor-widget-theme-post-content p"):
            text = "".join(element.xpath(".//text()").getall())

            if text and text.strip("_") != "" and "Avaliação do Polígrafo" not in text:
                subsections.append(text.strip())

        return " ".join(subsections) if subsections else ""
