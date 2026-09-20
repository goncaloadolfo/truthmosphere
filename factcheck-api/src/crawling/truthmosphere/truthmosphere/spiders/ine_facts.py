import os
from urllib.parse import parse_qs, urlparse

import scrapy
from scrapy.http import Response
from truthmosphere.items import TruthmosphereItem
from truthmosphere.utils import normalize_text


class INEFactsSpider(scrapy.Spider):
    name = "ine_facts"

    start_urls = os.getenv("TRUTHMOSPHERE_CRAWL_START_URLS").split(",")

    allowed_domains = os.getenv(
        "TRUTHMOSPHERE_CRAWL_ALLOWED_DOMAINS",
        "www.ine.pt",
    ).split(",")

    def parse(self, response: Response):
        # listing page
        ine_items = response.css("#destaques_lista .linkdestaques > a::attr(href)").getall()
        if ine_items:
            for item in ine_items:
                yield response.follow(item, callback=self.parse)

            parsed_url = urlparse(response.url)
            query_params = parse_qs(parsed_url.query)
            query_params["DESTAQUESpagenumber"][0] = str(int(query_params["DESTAQUESpagenumber"][0]) + 1)

            query_params_string = "&".join([f"{key}={value[0]}" for key, value in query_params.items()])
            parsed_url = parsed_url._replace(query=query_params_string)
            yield response.follow(parsed_url.geturl(), callback=self.parse)

        # stat page
        is_content_page = response.css(".resumo")
        if is_content_page:
            item = TruthmosphereItem()

            item["title"] = normalize_text(response.css(".linkpublicacoes_b::text").get())

            item["assessement_result"] = "Verdadeiro"
            item["category"] = response.css("#DESTAQUEStema option[selected]::text").get()
            item["publication_date"] = response.css(".datapublicacoes::text").get()
            item["origin"] = "INE"

            resume_paragraphs = response.css(".resumo p::text").getall()

            if not resume_paragraphs:
                resume_paragraphs = response.css(".resumo::text").getall()

            explanation = " ".join(resume_paragraphs).strip()
            if explanation.startswith("Resumo"):
                explanation = explanation[7:].strip()

            item["explanation"] = explanation

            yield item
