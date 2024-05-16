from source.providers.base import BaseProvider


class TMDBScraper(BaseProvider):
    name = "tmdb"
    image = "tmdb.png"

    def get_score(self, id, media):
        return round(media.get("vote_average", None), 1)
