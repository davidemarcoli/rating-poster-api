import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
ua = UserAgent()

class BaseProvider:
    name = "base"
    image = None

    def get_scraper(self, url):
        headers = {'User-Agent': ua.random}
        page = requests.get(url, headers=headers)
        return BeautifulSoup(page.content, "html.parser")

    def get_score(self, id, media):
        raise NotImplementedError