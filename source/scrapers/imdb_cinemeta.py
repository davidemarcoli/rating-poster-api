import json

import requests

from source.scrapers.base import BaseScraper


class IMDBCinemetaScraper(BaseScraper):
    name = "imdb"

    def scrape(self, id, media):

        if media.get("media_type") == "movie":
            media_type = "movie"
        elif media.get("media_type") == "tv":
            media_type = "series"
        else:
            return None

        url = f"https://v3-cinemeta.strem.io/meta/{media_type}/{id}.json"

        response = requests.get(url)
        return response.json().get("meta", None).get("imdbRating", None)