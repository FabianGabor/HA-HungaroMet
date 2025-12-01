import logging
import os
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from PIL import Image

_LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 10

try:
    from .const import RADAR_BASE_URL
except ImportError:
    from const import RADAR_BASE_URL


def get_latest_image_urls(base_url, count=12):
    response = requests.get(base_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    png_files = []
    for a in soup.find_all("a"):
        if isinstance(a, Tag):
            href = a.get("href")
            if isinstance(href, str) and href.endswith(".png"):
                png_files.append(href)

    # Remove duplicates while preserving order
    seen = set()
    unique_png_files = []
    for fname in png_files:
        if fname not in seen:
            unique_png_files.append(fname)
            seen.add(fname)
    unique_png_files.sort(reverse=True)

    latest_files = unique_png_files[:count]
    latest_files.sort()
    return [base_url + fname for fname in latest_files]


def download_images(urls):
    images = []
    for url in urls:
        try:
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            images.append(img)
        except requests.RequestException as err:
            _LOGGER.error("Failed to download %s: %s", url, err)
    return images


def create_gif(images, output_path, duration=1000, end_delay=3000):
    """
    Create a GIF from a list of PIL Images.
    The last frame will have a longer delay (end_delay).
    """
    try:
        if not images:
            _LOGGER.error("No images to create GIF.")
            return
        durations = [duration] * (len(images) - 1) + [end_delay]
        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            duration=durations,
            loop=0,
        )
        _LOGGER.info(
            "GIF saved to %s (frames: %s, end delay: %s ms)",
            output_path,
            len(images),
            end_delay,
        )
    except Exception as err:  # pragma: no cover - defensive logging
        _LOGGER.error("Error creating GIF: %s", err)


def update_radar_gif():
    try:
        urls = get_latest_image_urls(RADAR_BASE_URL, count=6)
        if not urls:
            _LOGGER.error("No radar image URLs found. GIF not updated.")
            return
        images = download_images(urls)
        if not images:
            _LOGGER.error("No radar images downloaded. GIF not updated.")
            return
        www_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "www")
        if not os.path.exists(www_dir):
            os.makedirs(www_dir)
        output_gif = os.path.join(www_dir, "radar_animation.gif")
        create_gif(images, output_gif, duration=1000, end_delay=3000)
        frame_count = len(images)
        _LOGGER.info("Radar GIF updated at %s with %s frames.", output_gif, frame_count)
        print(f"Radar GIF updated at {output_gif} with {frame_count} frames.")
    except requests.RequestException as err:
        _LOGGER.error("Network error updating radar GIF: %s", err)
    except Exception as err:  # pragma: no cover - defensive logging
        _LOGGER.error("Exception in update_radar_gif: %s", err)


if __name__ == "__main__":
    update_radar_gif()
