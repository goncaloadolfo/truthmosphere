# Fact Checking API

Collects verifiable claims from Portuguese statistics providers and fact-checking outlets, to be
used as ground truth for fact-checking models.

The pipeline has two stages: **crawling** (this document) writes raw items to JSONL, and
**preprocessing** turns those into claims. Only crawling is documented for now.

## Crawling

Scrapy project living in `src/crawling/truthmosphere`, driven by a YAML config so that a crawl is
reproducible from a single file.

```
configs/crawl_config.yaml                       crawl settings (which spider, where to start)
scripts/run_crawl.py                            config -> env vars -> `scrapy crawl`
src/crawling/truthmosphere/
    truthmosphere/settings.py                   scrapy settings, read from env
    truthmosphere/items.py                      TruthmosphereItem, the shared output schema
    truthmosphere/utils.py                      text helpers shared by the spiders
    truthmosphere/spiders/                      one spider per source
data/raw/                                       crawl output
```

### Setup

Python 3.12.

```bash
pip install -r requirements.txt
```

`bpstat_facts` and `pordata_facts` also need Chrome available locally, some of their pages only
hold their data once javascript has run, so those are rendered through Selenium.

### Running a crawl

Point the config at the spider you want, then:

```bash
make crawl config_file=configs/crawl_config.yaml
```

Output is written to the `output_file` path as JSONL, one item per line.

### Configuration

`run_crawl.py` consumes `output_file` itself and exports every other key as
`TRUTHMOSPHERE_CRAWL_<KEY>` for the spider and scrapy settings to read. Lists are joined with
commas.

| Key                   | Required | Description                                                             |
| --------------------- | -------- | ----------------------------------------------------------------------- |
| `spider_name`         | yes      | Spider to run, e.g. `pordata_facts`                                     |
| `start_urls`          | yes      | URLs the crawl starts from                                              |
| `allowed_domains`     | yes      | Domains the crawl may not leave                                         |
| `output_file`         | yes      | JSONL destination, relative to the repo root                            |
| `extra_data_folder`   | no       | Where a spider writes data files alongside items (`pordata_facts` only) |
| `concurrent_requests` | no       | Parallel requests, default `1`                                          |
| `download_delay`      | no       | Seconds between requests to a domain, default `2`                       |
| `max_items`           | no       | Stop after N items, useful for tests. Default unlimited                 |

`robots.txt` is respected (`ROBOTSTXT_OBEY = True`). Be deliberate about lowering
`download_delay`, these are small public sites.

### Output schema

Every spider yields the same `TruthmosphereItem`, leaving unused fields empty:

| Field                | Description                                                                             |
| -------------------- | --------------------------------------------------------------------------------------- |
| `title`              | The claim itself                                                                        |
| `assessement_result` | Verdict. `"Verdadeiro"` for statistics sources, the outlet's own rating for fact-checks |
| `summary`            | Short description of what the claim is about                                            |
| `explanation`        | Supporting text for the verdict                                                         |
| `category`           | Topic, as classified by the source                                                      |
| `publication_date`   | When the source published or last updated the data                                      |
| `author`             | Originating entity                                                                      |
| `origin`             | Source identifier, e.g. `PORDATA`                                                       |
| `data_file`          | Name of the data file written into `extra_data_folder`, if any                          |

### Spiders

| Spider            | Source              | Notes                                               |
| ----------------- | ------------------- | --------------------------------------------------- |
| `pordata_facts`   | pordata.pt          | Statistics tables. Also writes a CSV per statistic  |
| `ine_facts`       | ine.pt              | Statistics releases ("destaques")                   |
| `bpstat_facts`    | bpstat.bportugal.pt | Bank of Portugal series                             |
| `poligrafo_facts` | poligrafo.sapo.pt   | Fact-check articles, with the outlet's own verdicts |
