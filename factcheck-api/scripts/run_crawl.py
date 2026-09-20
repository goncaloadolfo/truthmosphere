import logging
import os
import subprocess

import fire
import yaml

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def run_crawl(config_file: str):
    with open(config_file, "r") as file:
        config: dict = yaml.safe_load(file)

    working_dir = os.getcwd()
    output_file = config.pop("output_file")
    if not output_file:
        raise ValueError("Output file must be specified in the configuration.")

    # env variables for the crawler
    for key, value in config.items():
        logger.info(f"Setting environment variable: {key}={value}")

        if isinstance(value, list):
            os.environ[f"TRUTHMOSPHERE_CRAWL_{key}".upper()] = ",".join(value)

        elif not isinstance(value, str):
            os.environ[f"TRUTHMOSPHERE_CRAWL_{key}".upper()] = str(value)

        else:
            os.environ[f"TRUTHMOSPHERE_CRAWL_{key}".upper()] = value

    # start crawl process
    logger.info("Starting crawl process...")
    output_path = f"{working_dir}/{output_file}"
    subprocess.run(
        f"cd src/crawling/truthmosphere && scrapy crawl {config['spider_name']} -o {output_path}",
        shell=True,
        check=True,
    )


if __name__ == "__main__":
    fire.Fire(run_crawl)
