import os
from urllib.parse import parse_qs, urlparse

import requests
import scrapy
from scrapy.http import Response
from truthmosphere.items import TruthmosphereItem

STAT = "estatisticas/"


class PORDATAFactsSpider(scrapy.Spider):
    name = "pordata_facts"

    start_urls = os.getenv("TRUTHMOSPHERE_CRAWL_START_URLS").split(",")

    allowed_domains = os.getenv(
        "TRUTHMOSPHERE_CRAWL_ALLOWED_DOMAINS",
        "www.pordata.pt",
    ).split(",")

    data_folder = os.getenv("TRUTHMOSPHERE_CRAWL_EXTRA_DATA_FOLDER")

    def parse(self, response: Response):
        page_url = response.url

        if STAT not in page_url:
            return

        stat_path = page_url.split(STAT)[1]
        stat_subpath = stat_path.split("/")

        # listing page of a given topic
        if len(stat_subpath) == 1:
            subtopic_links = response.css(".content-zone a.card-link::attr(href)").getall()

            if len(subtopic_links) > 0:
                for link in subtopic_links:
                    if STAT in link:
                        yield response.follow(link, callback=self.parse)

                parsed_url = urlparse(response.url)
                query_params = parse_qs(parsed_url.query)
                parsed_url = parsed_url._replace(query=f"page={int(query_params["page"][0]) + 1}")
                yield response.follow(parsed_url.geturl(), callback=self.parse)

        # stat page
        if len(stat_subpath) >= 2:
            item = TruthmosphereItem()
            item["title"] = response.css(".header-content .field--type-string-long::text").get().strip()
            item["assessement_result"] = "Verdadeiro"
            item["summary"] = response.css(".header-content h2 span::text").get().strip()
            item["category"] = response.css(".breadcrumb li a::text").getall()[2].strip()
            item["origin"] = "PORDATA"

            if self.data_folder:
                try:
                    item["data_file"] = self.download_data_csv(
                        response.css("#download-btn-csv a::attr(href)").get(),
                        item["summary"].lower().replace(" ", "_") + ".csv",
                    )
                except Exception as e:
                    self.logger.error(f"Failed to download CSV file: {e}")
                    item["data_file"] = None
            else:
                item["data_file"] = response.css("#download-btn-csv a::attr(href)").get()

            yield item

    def download_data_csv(self, file_url: str, file_name: str) -> str:
        file_path = os.path.join(self.data_folder, file_name)
        os.makedirs(self.data_folder, exist_ok=True)

        csv_response = requests.get(file_url)
        csv_response.raise_for_status()

        with open(file_path, "wb") as f:
            f.write(csv_response.content)

        return file_path
