import csv
import os
import re

import scrapy
from scrapy.http import Response
from scrapy.selector import Selector, SelectorList
from selenium.common.exceptions import TimeoutException
from src.preprocessing.utils import clean_filename
from truthmosphere.browser import build_chrome_driver, render
from truthmosphere.items import TruthmosphereItem
from truthmosphere.utils import own_text_of, text_of

STAT_ID_PATTERN = re.compile(r"-(\d+)/?$")
LAST_UPDATE_LABEL = r"[ÚU]ltima actualiza[çc][ãa]o:"
SOURCES_PATTERN = re.compile(rf"Fontes/Entidades:\s*(.*?)\s*(?:{LAST_UPDATE_LABEL}|$)")
LAST_UPDATE_PATTERN = re.compile(rf"{LAST_UPDATE_LABEL}\s*([\d-]+)")
CSV_COLUMNS = ["Ano", "Território", "Indicador", "Dimensão", "Categoria", "Escala", "Símbolo", "Valor"]
YEAR_AXIS_LABEL = "Anos"

# The values, the header labels and the row labels are each put in place by a different script,
# so wait for all three. The row labels come last and are moved out of the table altogether when
# the first column gets frozen, hence counting them across the whole page.
TABLE_READY_SCRIPT = """
var rows = document.querySelectorAll('#MicroPageTable tbody tr').length;

return rows > 0
    && document.querySelectorAll('#MicroPageTable td.ValueCell').length > 0
    && Array.from(document.querySelectorAll('th.HeaderVarCellBottom')).some(c => c.textContent.trim())
    && document.querySelectorAll('td.YearCell').length >= rows;
"""


class PORDATAFactsSpider(scrapy.Spider):
    """
    Walks the three PORDATA statistics roots (/portugal, /municipios, /europa) down to the
    individual statistic pages:

        root (/portugal)
          -> theme ("Agricultura, Floresta e Pescas")
            -> subtheme (/subtema/portugal/exploracoes+agricolas+e+superficie-421)
              -> statistic (/portugal/dimensao+media+das+exploracoes+agricolas-3458)

    Themes and their subtheme links are all rendered on the root page, so a root page yields
    one request per subtheme, and each subtheme page yields one request per statistic page.

    Statistic pages no longer expose a CSV download link (export is an ASP.NET postback), so the
    data table rendered on the page is scraped into a CSV instead. /portugal pages ship theirs
    inline, while /municipios and /europa fill theirs in client-side and are re-fetched through
    a headless browser.
    """

    name = "pordata_facts"

    start_urls = os.getenv("TRUTHMOSPHERE_CRAWL_START_URLS").split(",")

    allowed_domains = os.getenv(
        "TRUTHMOSPHERE_CRAWL_ALLOWED_DOMAINS",
        "www.pordata.pt",
    ).split(",")

    data_folder = os.getenv("TRUTHMOSPHERE_CRAWL_EXTRA_DATA_FOLDER")

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)

        # only statistic pages that turn out to need rendering pay for starting a browser
        self.driver = None

    def closed(self, reason):
        if self.driver:
            self.driver.quit()

    def parse(self, response: Response):
        themes = response.css("div.Themes_List_Item")

        if not themes:
            self.logger.error(f"No themes found on root page: {response.url}")
            return

        for theme in themes:
            category = text_of(theme.css(".Themes_List_Item_Label_Title"))

            for link in theme.css(".SubThemes_Item a::attr(href)").getall():
                yield response.follow(
                    link,
                    callback=self.parse_subtheme,
                    cb_kwargs={"category": category},
                )

    def parse_subtheme(self, response: Response, category: str):
        stat_links = response.css(".SubTheme_Container_Right .SubTheme_List a::attr(href)").getall()

        if not stat_links:
            self.logger.warning(f"No statistic links found on subtheme page: {response.url}")
            return

        for link in stat_links:
            yield response.follow(
                link,
                callback=self.parse_stat,
                cb_kwargs={"category": category},
            )

    def parse_stat(self, response: Response, category: str):
        header = response.css(".MicroHeader")
        indicator = header.css("h1::attr(title)").get() or text_of(header.css("h1"))

        if not indicator:
            self.logger.warning(f"No indicator title found on statistic page: {response.url}")
            return

        sources, last_update = self.parse_legend(response)

        item = TruthmosphereItem()
        item["title"] = text_of(header.css("h2"))
        item["assessement_result"] = "Verdadeiro"
        item["summary"] = indicator.strip()
        item["category"] = category
        item["publication_date"] = last_update
        item["author"] = sources
        item["origin"] = "PORDATA"
        item["data_file"] = self.store_data_table(response, item["summary"])

        yield item

    def parse_legend(self, response: Response) -> tuple[str | None, str | None]:
        sources = None
        last_update = None

        # statistic pages repeat the legend, and the hidden copies omit the update date
        for legend in response.css(".DataSourceLegend"):
            text = text_of(legend)

            if sources is None:
                sources_match = SOURCES_PATTERN.search(text)
                sources = sources_match.group(1) if sources_match else None

            if last_update is None:
                last_update_match = LAST_UPDATE_PATTERN.search(text)
                last_update = last_update_match.group(1) if last_update_match else None

        return sources, last_update

    def store_data_table(self, response: Response, indicator: str) -> str | None:
        if not self.data_folder:
            return None

        rows = self.build_data_rows(response.selector, indicator)

        # /municipios and /europa tables are injected by javascript, so the response only holds
        # an empty table shell and the page has to be loaded again through a browser
        if not rows:
            rows = self.build_data_rows(self.render_page(response.url), indicator)

        if not rows:
            self.logger.warning(f"No data table found on statistic page: {response.url}")
            return None

        stat_id_match = STAT_ID_PATTERN.search(response.url)
        stat_id = stat_id_match.group(1) if stat_id_match else None

        # the indicator name alone is not unique across the three roots
        file_name = "_".join(filter(None, [clean_filename(indicator), stat_id])) + ".csv"
        file_path = os.path.join(self.data_folder, file_name)

        try:
            os.makedirs(self.data_folder, exist_ok=True)

            with open(file_path, "w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
        except OSError as e:
            self.logger.error(f"Failed to write data file {file_name}: {e}")
            return None

        return file_name

    def render_page(self, url: str) -> Selector:
        if not self.driver:
            self.driver = build_chrome_driver()

        try:
            return render(self.driver, url, TABLE_READY_SCRIPT)
        except TimeoutException:
            # a table that never settled is still worth more than no table at all
            self.logger.warning(f"Timed out waiting for the data table on {url}")
            return Selector(text=self.driver.page_source)
        except Exception as e:
            self.logger.warning(f"Could not render statistic page {url}: {e}")
            return Selector(text="")

    def build_data_rows(self, page: Selector, indicator: str) -> list[dict[str, str]]:
        """
        Turn the wide page table into one record per observation.

        The table has two axes, one of which is always time. On /portugal the rows are the
        years and the columns the breakdown; on /municipios and /europa the rows are instead
        territories and the years move into the bottom header row.
        """
        values = page.css("#MicroPageTable tbody tr")
        header = self.header_source(page)

        if not values or not header:
            return []

        row_axis = text_of(header.css("th.HeaderYear")[:1])
        rows_are_years = row_axis == YEAR_AXIS_LABEL

        column_count = len(values[0].css("td.ValueCell"))

        if not column_count:
            return []

        breakdowns, years = self.header_columns(header, column_count, rows_are_years)
        labels = self.row_labels(page, len(values))
        scale = text_of(page.css(".DataSourceUnit td:nth-child(1)")[:1])

        if not labels:
            self.logger.warning(f"No row labels line up with the {len(values)} data rows")

        rows = []
        for index, table_row in enumerate(values):
            row_label = labels[index] if index < len(labels) else ""

            for column, cell in enumerate(table_row.css("td.ValueCell")):
                column_labels = breakdowns[column] if column < len(breakdowns) else []

                rows.append(
                    {
                        "Ano": row_label if rows_are_years else (years[column] if column < len(years) else ""),
                        "Território": "" if rows_are_years else row_label,
                        "Indicador": indicator,
                        "Dimensão": " - ".join(column_labels[:-1]),
                        "Categoria": column_labels[-1] if column_labels else "",
                        "Escala": scale,
                        "Símbolo": text_of(cell.css("span.SymbolCaption")),
                        "Valor": own_text_of(cell),
                    }
                )

        return rows

    @staticmethod
    def row_labels(page: Selector, row_count: int) -> list[str]:
        """
        Read the label of every data row, which is a year or a territory depending on the root.

        A table wide enough to scroll sideways has its first column frozen by the DataTables
        plugin, which moves those cells into a cloned table and leaves the original rows
        holding values only. Only a table holding one label per data row can be that column,
        so that a half built clone is never lined up against the values.
        """
        for table in page.css("table"):
            labels = table.css("tbody td.YearCell")

            if len(labels) == row_count:
                return [text_of(cell) for cell in labels]

        return []

    @staticmethod
    def header_source(page: Selector) -> SelectorList | None:
        """
        Pick the table header that actually carries labels.

        On a rendered page the DataTables plugin collapses the real header and clones a
        labelled copy of it into its own scrolling container, leaving the original blank.
        """
        headers = []
        for table in page.css("table"):
            header = table.css("thead")

            if header.css("th.HeaderVarCellBottom") and text_of(header):
                headers.append(header)

        return max(headers, key=lambda header: len(header.css("th")), default=None)

    @classmethod
    def header_columns(
        cls,
        header: SelectorList,
        column_count: int,
        rows_are_years: bool,
    ) -> tuple[list[list[str]], list[str]]:
        """
        Read the breakdown labels and the year of every value column off the table header.

        Reading down a column of the header grid gives that value column its labels, from the
        widest grouping to the narrowest. The last of them is the year when the rows are
        territories, and the deepest breakdown level when the rows are years.
        """
        grid = cls.header_grid(header)

        if not grid:
            return [], []

        paths = []
        # the leading columns belong to the row axis, the value columns are the last ones
        for column in range(max(len(grid[0]) - column_count, 0), len(grid[0])):
            path: list[str] = []

            for row in grid:
                label = row[column]

                # cells spanning several rows repeat their label down the grid
                if label and (not path or path[-1] != label):
                    path.append(label)

            paths.append(path)

        if rows_are_years:
            # a header of a single row carries no grouping, it only restates the indicator
            return ([] if len(grid) == 1 else paths), []

        return [path[:-1] for path in paths], [path[-1] if path else "" for path in paths]

    @staticmethod
    def header_grid(header: SelectorList) -> list[list[str]]:
        """
        Expand the header cells onto a row by column grid.

        Header cells span both ways and not every row fills every column: an "Ásia" cell can
        reach down past the row that splits "Europa" into its own columns. A cell's column is
        therefore only known once the cells reaching into its row have been placed.
        """
        grid: dict[tuple[int, int], str] = {}

        for row_index, row in enumerate(header.css("tr")):
            column = 0

            for cell in row.css("th"):
                while (row_index, column) in grid:
                    column += 1

                label = text_of(cell)
                row_span = int(cell.attrib.get("rowspan") or 1)
                column_span = int(cell.attrib.get("colspan") or 1)

                for row_offset in range(row_span):
                    for column_offset in range(column_span):
                        grid[(row_index + row_offset, column + column_offset)] = label

                column += column_span

        if not grid:
            return []

        depth = max(row_index for row_index, _ in grid) + 1
        width = max(column for _, column in grid) + 1

        return [[grid.get((row_index, column), "") for column in range(width)] for row_index in range(depth)]
