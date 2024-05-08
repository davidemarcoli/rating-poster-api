import os
import time
from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.responses import Response

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
        scores.append({"name": scraper.name, "image": scraper.image, "score": scraper().scrape(id, media)})
        print(scraper.name + " took " + str((time.time() - scraper_start_time) * 1000) + "ms")

    filter(filter_none, scores)

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


def add_text_overlay(image, scores):
    width, height = image.size

    # Create an overlay image
    overlay_height = int(height / 10)
    overlay = Image.new('RGBA', (width, overlay_height), (0, 0, 0, 240))  # Semi-transparent black
    draw = ImageDraw.Draw(overlay)

    # Calculate spacing and font
    font_size = 1000
    font = ImageFont.truetype("Ubuntu-C.ttf", font_size)

    total_text_width = 0
    total_text_height = 0
    text_spacing = 40  # Space between the texts
    logo_spacing = 20  # Space between the logo and the text
    max_total_text_width_factor = 0.9  # Maximum width of the text as a factor of the image width
    max_total_text_width = width * max_total_text_width_factor
    logos = []  # To store resized logos

    # Load and resize logos, and calculate total width required
    for score in scores:
        logo = None
        if score.get("image"):
            logo_path = f"source/assets/{score.get('image')}"  # Assume logos are named like 'imdb_logo.png'
            logo = Image.open(logo_path).convert("RGBA")
            # logo = logo.resize((int(overlay_height * 0.75), int(overlay_height * 0.75)), Image.Resampling.LANCZOS)
            logo.thumbnail((int(overlay_height * 0.75), int(overlay_height * 0.75)), Image.Resampling.LANCZOS)
            logos.append(logo)
        else:
            logos.append(None)
        _, _, text_width, text_height = draw.textbbox((0, 0), str(score.get("score")), font=font)
        print("TEXT WIDTH: " + str(text_width))
        # total_text_width += (text_width + text_spacing) + (
        #     (logo.width + logo_spacing) if logo else draw.textbbox((0, 0), score.get("name") + ": ", font=font)[2])

        total_text_width += (text_width + text_spacing)

        if logo:
            total_text_width += (logo.width + logo_spacing)
        else:
            total_text_width += draw.textbbox((0, 0), score.get("name") + ": ", font=font)[2]

        total_text_height = text_height

    print("TOTAL TEXT WIDTH: " + str(total_text_width))

    # Check if we need to scale down logos and text to fit
    if total_text_width > max_total_text_width or total_text_height > overlay_height * 0.7:
        scale_factor_width = (max_total_text_width - sum(logo.width if logo else 0 for logo in logos)) / total_text_width
        scale_factor_height = overlay_height * 0.7 / total_text_height
        scale_factor = min(scale_factor_width, scale_factor_height)
        print("Scale factors: " + str(scale_factor_width) + ", " + str(scale_factor_height))
        print("Old font size: " + str(font_size))
        font_size = int(font_size * scale_factor)
        print("New font size: " + str(font_size))
        font = ImageFont.truetype("Ubuntu-C.ttf", font_size)
        # logos = [logo.resize((int(logo.width * scale_factor), int(logo.height * scale_factor)), Image.Resampling.LANCZOS) if logo else logo for
        #          logo in logos]
        for logo in logos:
            if logo:
                logo.thumbnail((int(overlay_height * 0.75), int(overlay_height * 0.75)), Image.Resampling.LANCZOS)
                # logo.thumbnail((int(logo.height * scale_factor), int(logo.width * scale_factor)), Image.Resampling.LANCZOS)
        total_text_width = 0

    # Draw logos and texts on the overlay
    current_x = int(width * 0.01)

    for logo, score in zip(logos, scores):
        text = str(score.get("score"))
        print(score.get("name") + ": " + str(current_x))
        if logo:
            overlay.paste(logo, (int(current_x), (overlay_height - logo.height) // 2), logo)
            current_x += logo.width + logo_spacing
        else:
            text = score.get("name") + ": " + text
        print("Overlay height: " + str(overlay_height))
        print("Draw height: " + str(draw.textbbox((0, 0), text, font=font)[3]))
        text_position = (current_x, (overlay_height - draw.textbbox((0, 0), text, font=font)[3]) // 2)
        print(text_position)
        print(font.size)
        draw.text(text_position, text, font=font, fill=(255, 255, 255, 255))  # White text
        print(draw.textbbox((0, 0), text, font=font))
        current_x += draw.textbbox((0, 0), text, font=font)[2] + text_spacing

    # Merge the overlay with the original image
    image.paste(overlay, (0, height - overlay_height), overlay)

    return image


def filter_none(item):
    return item is not None and item.get("score") is not None
