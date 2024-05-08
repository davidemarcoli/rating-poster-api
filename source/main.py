import json
import os
import time
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont
from fastapi import FastAPI
from starlette.responses import Response

from dotenv import load_dotenv

from source.scrapers.imdb import IMDBScraper
from source.scrapers.imdb_cinemeta import IMDBCinemetaScraper
from source.scrapers.tmdb import TMDBScraper
from source.scrapers.trakt import TraktScraper

load_dotenv()

if not os.getenv("TMDB_API_KEY"):
    exit()

app = FastAPI()

scrapers = [
    # IMDBScraper,
    IMDBCinemetaScraper,
    TMDBScraper,
    TraktScraper
]


@app.get("/{id}")
async def get_poster(id: str):
    start_time = time.time()
    url = f"https://api.themoviedb.org/3/find/{id}?api_key={os.getenv("TMDB_API_KEY")}&external_source=imdb_id"
    response = requests.get(url)
    data = response.json()
    # print(json.dumps(data, indent=2))

    if len(data.get("movie_results")) > 0:
        media = data.get("movie_results")[0]
    elif len(data.get("tv_results")) > 0:
        media = data.get("tv_results")[0]
    else:
        return Response("No Results")

    poster_url = "https://image.tmdb.org/t/p/original" + data.get("tv_results")[0].get("poster_path")

    image_fetch_start_time = time.time()
    image_response = requests.get(poster_url)
    print("Image fetch took " + str((time.time() - image_fetch_start_time) * 1000) + "ms")

    poster_img = Image.open(BytesIO(image_response.content))

    # imdb_rating = IMDBScraper().scrape(id, media)

    scores = []

    for scraper in scrapers:
        scraper_start_time = time.time()
        scores.append({"name": scraper.name, "score": scraper().scrape(id, media)})
        print(scraper.name + " took " + str((time.time() - scraper_start_time) * 1000) + "ms")

    print(scores)

    scores = filter(filter_none, scores)

    texts = []

    for score in scores:
        texts.append(score.get("name") + ": " + str(score.get("score")))

    overlay_start_time = time.time()
    poster_img = add_text_overlay(poster_img, "   ".join(texts))
    print("Text overlay took " + str((time.time() - overlay_start_time) * 1000) + "ms")

    # poster_img.show()

    output_start_time = time.time()
    output = BytesIO()
    poster_img.save(output, format="jpeg")
    print("Output took " + str((time.time() - output_start_time) * 1000) + "ms")

    print("Total time: " + str((time.time() - start_time) * 1000) + "ms")
    return Response(content=output.getvalue(), media_type="image/jpeg")


def add_text_overlay(image, text):
    width, height = image.size

    # Create an overlay image
    overlay_height = int(height / 10)
    overlay = Image.new('RGBA', (width, overlay_height), (0, 0, 0, 240))  # Grey, semi-transparent
    draw = ImageDraw.Draw(overlay)

    # Define the font and add text
    font_size = 10
    text_width = 0
    text_height = 0
    while font_size < 1000:
        font = ImageFont.truetype("Ubuntu-C.ttf", font_size)
        _, _, text_width, text_height = draw.textbbox((0, 0), text, font=font)
        if text_width < width * 0.9:
            font_size += 1
        else:
            break
    # font = ImageFont.truetype("Ubuntu-C.ttf", font_size)
    # _, _, text_width, text_height = draw.textbbox((0, 0), text, font=font)

    if text_width == 0 or text_height == 0:
        return image

    text_position = ((width - text_width) // 2, (overlay_height - text_height) // 2)
    draw.text(text_position, text, font=font, fill=(255, 255, 255, 255))  # White text

    # Merge the overlay with the original image
    image.paste(overlay, (0, height - overlay_height), overlay)

    return image


def filter_none(item):
    return item is not None and item.get("score") is not None
