import os

import requests

from source.scrapers.base import BaseScraper


class TraktScraper(BaseScraper):
    name = "trakt"
    image = "trakt.png"

    def scrape(self, id, media):

        if media.get("media_type") == "movie":
            media_type = "movies"
        elif media.get("media_type") == "tv":
            media_type = "shows"
        else:
            return None

        url = f"https://api.trakt.tv/{media_type}/{id}/ratings"
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': os.getenv("TRAKT_CLIENT_ID")
        }

        response = requests.get(url, headers=headers)
        return round(response.json().get("rating", None), 1)
