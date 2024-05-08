import os

import requests

from source.scrapers.base import BaseScraper


class TMDBScraper(BaseScraper):
    name = "tmdb"
    image = "tmdb.png"

    def scrape(self, id, media):
        return round(media.get("vote_average", None), 1)
