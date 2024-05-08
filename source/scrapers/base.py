import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
ua = UserAgent()

class BaseScraper:
    name = "base"

    def request(self, url):
        headers = {'User-Agent': ua.random}
        page = requests.get(url, headers=headers)
        return BeautifulSoup(page.content, "html.parser")

    def scrape(self, id, media):
        raise NotImplementedError