# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


# missing category and fact summary
class TruthmosphereItem(scrapy.Item):
    title = scrapy.Field()
    assessement_result = scrapy.Field()
    summary = scrapy.Field()
    explanation = scrapy.Field()
    category = scrapy.Field()
    publication_date = scrapy.Field()
    author = scrapy.Field()
