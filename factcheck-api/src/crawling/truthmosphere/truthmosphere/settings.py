# Scrapy settings for truthmosphere project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import os

LOG_LEVEL = "INFO"

BOT_NAME = "truthmosphere"

SPIDER_MODULES = ["truthmosphere.spiders"]
NEWSPIDER_MODULE = "truthmosphere.spiders"

ADDONS = {}


# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = "truthmosphere"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Max number of items to scrape before closing the spider
max_items = os.getenv("TRUTHMOSPHERE_CRAWL_MAX_ITEMS", None)
CLOSESPIDER_ITEMCOUNT = int(max_items) if max_items is not None else None

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = int(os.getenv("TRUTHMOSPHERE_CRAWL_CONCURRENT_REQUESTS", 1))

# Configure a delay for requests for the same website (default: 0)
# See https://docs.scrapy.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = int(os.getenv("TRUTHMOSPHERE_CRAWL_DOWNLOAD_DELAY", 2))

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"
