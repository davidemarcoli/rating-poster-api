from source.scrapers.base import BaseScraper


class IMDBScraper(BaseScraper):
    name = "imdb"
    image = "imdb.png"

    def scrape(self, id, media):
        url = "https://www.imdb.com/title/" + id

        soup = self.request(url)

        rating_score_element = soup.find("div", attrs={'data-testid': 'hero-rating-bar__aggregate-rating__score'})
        rating_score_element_children = list(rating_score_element.children)

        if len(rating_score_element_children) > 0:
            return rating_score_element_children[0].text

        return None