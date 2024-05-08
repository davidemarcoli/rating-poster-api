import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
ua = UserAgent()

class IMDBSpider:
    def parse(self, id):
        headers = {'User-Agent': ua.random}
        URL = "https://www.imdb.com/title/" + id
        page = requests.get(URL, headers=headers)

        soup = BeautifulSoup(page.content, "html.parser")

        elements = soup.find_all("span", class_="cMEQkK")
        if len(elements) > 0:
            return elements[0].text

