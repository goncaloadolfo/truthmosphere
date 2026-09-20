import os
from string import Template
from urllib.parse import urlparse

import scrapy
from scrapy.http import HtmlResponse, Response
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from truthmosphere.browser import build_chrome_driver
from truthmosphere.items import TruthmosphereItem

FACT_TEMPLATE = Template(
    "O valor da serie '$serie_name' foi de $current_value em $current_date "
    "e tinha sido $last_month_value em $last_month."
)

EXPLANATION_TEMPLATE = Template(
    """
Análise da Série: $serie_name
Período de Referência: $current_date

---

Análise dos Valores:

- Valor Atual: $current_value
- Valor do Mês Anterior: $last_month_value
- Valor do Mesmo Mês do Ano Anterior: $same_month_last_year_value

Notas:
$notes
"""
)


class BPStatFactsSpider(scrapy.Spider):
    name = "bpstat_facts"

    start_urls = os.getenv("TRUTHMOSPHERE_CRAWL_START_URLS").split(",")

    allowed_domains = os.getenv(
        "TRUTHMOSPHERE_CRAWL_ALLOWED_DOMAINS",
        "bpstat.bportugal.pt",
    ).split(",")

    series_per_subdomain_limit = 80

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)

        self.driver = build_chrome_driver()

    def closed(self, reason):
        self.driver.quit()

    def parse(self, response: Response):
        try:
            page_selector = self.get_source_selector(response, "div[class*='InfoWrapper']")
        except Exception as e:
            self.logger.warning(f"Could not get page source for URL: {response.url} due to {e}")
            return

        subdomain_links = page_selector.css(
            "a[class*='SubdomaisListItem__SubdomainsListItemWrapper']::attr(href)"
        ).getall()

        # if no subdomain links found, parse the current page as subdomain
        # some times there are no subdomains
        if len(subdomain_links) == 0:
            yield response.follow(response.url, callback=self.parse_subdomain)
        else:
            for link in subdomain_links:
                yield response.follow(link, callback=self.parse_subdomain)

    def parse_subdomain(self, response: Response):
        subdomain_number = response.url.split("/")[-1]
        subdomain_url = urlparse(response.url)
        base_url = f"{subdomain_url.scheme}://{subdomain_url.netloc}"

        yield response.follow(
            f"{base_url}/api/series?domain_ids={subdomain_number}&page=1&page_size={self.series_per_subdomain_limit}",
            callback=self.parse_series_list,
        )

    def parse_series_list(self, response: Response):
        subdomain_url = urlparse(response.url)
        base_url = f"{subdomain_url.scheme}://{subdomain_url.netloc}"

        # json data
        data = response.json()
        series_results = data.get("data", [])

        # iterate over the series and follow each link
        for series in series_results:
            series_id = series.get("id")
            if series_id:

                yield response.follow(
                    f"{base_url}/serie/{series_id}",
                    callback=self.parse_series_values,
                )

    def parse_series_values(self, response: Response):
        try:
            page_selector = self.get_source_selector(response, "section[class*='Serie__Content']")
        except Exception as e:
            self.logger.warning(f"Could not get page source for URL: {response.url} due to {e}")
            return

        item = TruthmosphereItem()
        item["title"] = self.build_fact(page_selector)
        item["assessement_result"] = "Verdadeiro"
        item["summary"] = page_selector.css("section[class*='Serie__Content'] p::text").get()
        item["explanation"] = self.build_explanation(page_selector)
        item["category"] = page_selector.css("div[class*='SerieWrapper'] dl dd")[0].css("::text").get()
        item["publication_date"] = page_selector.css(".dates_container .dates-item time")[1].css("::text").get()
        item["origin"] = "BPstat"
        yield item

    def build_fact(self, page_selector: scrapy.Selector) -> str:
        serie_section = page_selector.css("div[class*='SerieWrapper'] section")
        serie_name = serie_section.css("h1 span::text").get()

        # observation values
        current_values = serie_section.css("div[class*='ObservationsWrapper'] section h4 span::text").getall()
        current_value = "".join(current_values)
        current_date = serie_section.css("div[class*='ObservationsWrapper'] section time::text").get()
        last_month_value = serie_section.css("div[class*='ObservationsWrapper'] section.beforeObs span::text").get()
        last_month = serie_section.css("div[class*='ObservationsWrapper'] section.beforeObs time::text").get()

        return FACT_TEMPLATE.substitute(
            serie_name=serie_name,
            current_value=current_value,
            current_date=current_date,
            last_month_value=last_month_value,
            last_month=last_month,
        ).strip()

    def build_explanation(self, page_selector: scrapy.Selector) -> str:
        serie_section = page_selector.css("div[class*='SerieWrapper'] section")
        serie_name = serie_section.css("h1 span::text").get()
        ref_date = serie_section.css("div[class*='ObservationsWrapper'] section time::text").get()

        # values
        ref_values = serie_section.css("div[class*='ObservationsWrapper'] section h4 span::text").getall()
        ref_value = "".join(ref_values)
        last_month_value = serie_section.css("div[class*='ObservationsWrapper'] section.beforeObs span::text").get()
        last_year_value = serie_section.css("div[class*='ObservationsWrapper'] section.counterPartObs span::text").get()

        # additional notes
        notes = page_selector.css("section[class*='Serie__Content'] p::text").get()

        # build explanation text
        return EXPLANATION_TEMPLATE.substitute(
            serie_name=serie_name,
            current_date=ref_date,
            current_value=ref_value,
            last_month_value=last_month_value,
            same_month_last_year_value=last_year_value,
            notes=notes,
        ).strip()

    def get_source_selector(self, response: Response, wait_selector: str) -> scrapy.Selector | None:
        self.driver.get(response.url)

        # Wait for SPA content to render
        _ = WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector)),
        )

        page_source = self.driver.page_source
        body = str.encode(page_source)

        return scrapy.Selector(
            HtmlResponse(
                url=response.url,
                body=body,
                encoding="utf-8",
            )
        )
