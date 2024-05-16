from source.providers.base import BaseProvider


class IMDBScraper(BaseProvider):
    name = "imdb"
    image = "imdb.png"

    def get_score(self, id, media):
        url = "https://www.imdb.com/title/" + id

        soup = self.get_scraper(url)

        rating_score_element = soup.find("div", attrs={'data-testid': 'hero-rating-bar__aggregate-rating__score'})
        rating_score_element_children = list(rating_score_element.children)

        if len(rating_score_element_children) > 0:
            return rating_score_element_children[0].text

        return None
