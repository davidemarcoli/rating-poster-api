import os
import time
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_cache.coder import Coder
from fastapi_cache.decorator import cache
from redis import asyncio as aioredis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import Response

from source.providers.imdb_cinemeta import IMDBCinemetaScraper
from source.providers.tmdb import TMDBScraper
from source.providers.trakt import TraktScraper

load_dotenv()

if not os.getenv("TMDB_API_KEY"):
    exit()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

providers = [
    # IMDBScraper,
    IMDBCinemetaScraper,
    TMDBScraper,
    TraktScraper
]


class CustomResponseCoder(Coder):
    @classmethod
    def encode(cls, value: Response) -> bytes:
        return value.body

    @classmethod
    def decode(cls, value: bytes) -> Response:
        return Response(content=value, media_type="image/jpeg")


def request_key_builder(
        func,
        namespace: str = "",
        *,
        request: Request = None,
        response: Response = None,
        **kwargs,
):
    return request.url.path


@app.get("/{id}")
@cache(expire=3600 * 24, coder=CustomResponseCoder, namespace="get_poster", key_builder=request_key_builder)
@limiter.limit("50/second")
def get_poster(request: Request, id: str):
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

    poster_url = "https://image.tmdb.org/t/p/original" + media.get("poster_path")

    image_fetch_start_time = time.time()
    image_response = requests.get(poster_url)
    print("Image fetch took " + str((time.time() - image_fetch_start_time) * 1000) + "ms")

    poster_img = Image.open(BytesIO(image_response.content))

    # imdb_rating = IMDBScraper().scrape(id, media)

    scores = []

    for provider in providers:
        try:
            scraper_start_time = time.time()
            scores.append({"name": provider.name, "image": provider.image, "score": provider().get_score(id, media)})
            print(provider.name + " took " + str((time.time() - scraper_start_time) * 1000) + "ms")
        except Exception as e:
            print(e)

    scores = list(filter(filter_none, scores))
    print(scores)

    # texts = []
    #
    # for score in scores:
    #     texts.append(score.get("name") + ": " + str(score.get("score")))

    overlay_start_time = time.time()
    poster_img = add_text_overlay(poster_img, scores)
    print("Text overlay took " + str((time.time() - overlay_start_time) * 1000) + "ms")

    # poster_img.show()

    output_start_time = time.time()
    output = BytesIO()
    poster_img.save(output, format="jpeg")
    print("Output took " + str((time.time() - output_start_time) * 1000) + "ms")

    print("Total time: " + str((time.time() - start_time) * 1000) + "ms")
    return Response(content=output.getvalue(), media_type="image/jpeg")


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url("redis://localhost:6379")
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    # FastAPICache.init(InMemoryBackend())


def add_text_overlay(image, scores):
    width, height = image.size

    # Create an overlay image
    overlay_height = int(height / 10)
    overlay = Image.new('RGBA', (width, overlay_height), (0, 0, 0, 240))  # Semi-transparent black
    draw = ImageDraw.Draw(overlay)

    # Calculate spacing and font
    font_size = 1000
    font = ImageFont.truetype("Ubuntu-C.ttf", font_size)

    total_width = 0
    total_height = 0
    text_spacing = 40  # Space between the texts
    logo_spacing = 20  # Space between the logo and the text
    max_total_text_width_factor = 0.9  # Maximum width of the text as a factor of the image width
    max_total_text_width = width * max_total_text_width_factor
    max_total_text_height_factor = 0.8  # Maximum height of the text as a factor of the overlay height
    max_total_text_height = overlay_height * max_total_text_height_factor
    logos = []  # To store resized logos

    # Load and resize logos, and calculate total width required
    for score in scores:
        _, _, text_width, text_height = draw.textbbox((0, 0), str(score.get("score")), font=font)

        if score.get("image"):
            logo_path = f"source/assets/{score.get('image')}"  # Assume logos are named like 'imdb_logo.png'
            logo = Image.open(logo_path).convert("RGBA")
            # logo = logo.resize((int(overlay_height * 0.75), int(overlay_height * 0.75)), Image.Resampling.LANCZOS)
            logo.thumbnail((int(max_total_text_height), int(max_total_text_width)), Image.Resampling.LANCZOS)
            logos.append(logo)
            total_width += (logo.width + logo_spacing)
        else:
            logos.append(None)
            total_width += draw.textbbox((0, 0), score.get("name") + ": ", font=font)[2]
        # print("TEXT WIDTH: " + str(text_width))

        total_width += (text_width + text_spacing)
        total_height = text_height

    print("MAX TOTAL TEXT WIDTH: " + str(max_total_text_width))
    print("TOTAL TEXT WIDTH: " + str(total_width))
    print("WIDTH RATIO: " + str(total_width / max_total_text_width))
    print("MAX TOTAL TEXT HEIGHT: " + str(max_total_text_height))
    print("TOTAL TEXT HEIGHT: " + str(total_height))
    print("HEIGHT RATIO: " + str(total_height / max_total_text_height))

    # Check if we need to scale down logos and text to fit
    if total_width > max_total_text_width or total_height > max_total_text_height:
        scale_factor_width = max_total_text_width / total_width
        scale_factor_height = max_total_text_height / total_height
        scale_factor = min(scale_factor_width, scale_factor_height)
        # print("Scale factors: " + str(scale_factor_width) + ", " + str(scale_factor_height))
        # print("Old font size: " + str(font_size))
        font_size = int(font_size * scale_factor)
        # print("New font size: " + str(font_size))
        font = ImageFont.truetype("Ubuntu-C.ttf", font_size)

        _, _, _, text_height = draw.textbbox((0, 0), str("Test"), font=font)

        for logo in logos:
            if logo:
                logo.thumbnail((int(logo.width * text_height / overlay_height), int(logo.height)),
                               Image.Resampling.LANCZOS)

    # Draw logos and texts on the overlay
    current_x = int(width * 0.03)

    for logo, score in zip(logos, scores):
        text = str(score.get("score"))
        # print(score.get("name") + ": " + str(current_x))
        if logo:
            overlay.paste(logo, (current_x, (overlay_height - logo.height) // 2), logo)
            current_x += logo.width + logo_spacing
        else:
            text = score.get("name") + ": " + text
        # print("Overlay height: " + str(overlay_height))
        # print("Draw height: " + str(draw.textbbox((0, 0), text, font=font)[3]))
        text_position = (current_x, overlay_height // 2)
        # print(text_position)
        # print(font.size)
        draw.text(text_position, text, font=font, anchor="lm", fill=(255, 255, 255, 255))  # White text
        # print(draw.textbbox((0, 0), text, font=font))
        current_x += draw.textbbox((0, 0), text, font=font)[2] + text_spacing

    # Merge the overlay with the original image
    image.paste(overlay, (0, height - overlay_height), overlay)

    return image


def filter_none(item):
    return item is not None and item.get("score") is not None and item.get("score") != "" and str(
        item.get("score")) != "0.0"
