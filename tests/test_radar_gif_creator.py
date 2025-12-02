"""Tests for radar_gif_creator.py"""

from io import BytesIO
from unittest.mock import Mock, patch

from PIL import Image
import requests

from custom_components.hungaromet.radar_gif_creator import (
    get_latest_image_urls,
    download_images,
    create_gif,
    update_radar_gif,
)


@patch("custom_components.hungaromet.radar_gif_creator.requests.get")
def test_get_latest_image_urls_success(mock_get):
    """Test get_latest_image_urls successfully parses HTML."""
    html_content = """
    <html>
        <body>
            <a href="image_003.png">Image 3</a>
            <a href="image_001.png">Image 1</a>
            <a href="image_002.png">Image 2</a>
            <a href="not_an_image.txt">Not an image</a>
        </body>
    </html>
    """
    mock_response = Mock()
    mock_response.text = html_content
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = get_latest_image_urls("http://example.com/", count=3)

    assert len(result) == 3
    # Should be sorted and return latest (highest numbered) files
    assert "image_001.png" in result[0]
    assert "image_002.png" in result[1]
    assert "image_003.png" in result[2]


@patch("custom_components.hungaromet.radar_gif_creator.requests.get")
def test_get_latest_image_urls_removes_duplicates(mock_get):
    """Test get_latest_image_urls removes duplicate entries."""
    html_content = """
    <html>
        <body>
            <a href="image_001.png">Image 1</a>
            <a href="image_001.png">Image 1 duplicate</a>
            <a href="image_002.png">Image 2</a>
        </body>
    </html>
    """
    mock_response = Mock()
    mock_response.text = html_content
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = get_latest_image_urls("http://example.com/", count=10)

    assert len(result) == 2
    assert "image_001.png" in result[0]
    assert "image_002.png" in result[1]


@patch("custom_components.hungaromet.radar_gif_creator.requests.get")
def test_get_latest_image_urls_limits_count(mock_get):
    """Test get_latest_image_urls limits results to specified count."""
    html_content = """
    <html>
        <body>
            <a href="image_001.png">Image 1</a>
            <a href="image_002.png">Image 2</a>
            <a href="image_003.png">Image 3</a>
            <a href="image_004.png">Image 4</a>
            <a href="image_005.png">Image 5</a>
        </body>
    </html>
    """
    mock_response = Mock()
    mock_response.text = html_content
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = get_latest_image_urls("http://example.com/", count=3)

    assert len(result) == 3
    # Should get the 3 latest (highest numbered)
    assert "image_003.png" in result[0]
    assert "image_004.png" in result[1]
    assert "image_005.png" in result[2]


@patch("custom_components.hungaromet.radar_gif_creator.requests.get")
def test_get_latest_image_urls_non_tag_elements(mock_get):
    """Test get_latest_image_urls handles non-Tag elements."""
    html_content = """
    <html>
        <body>
            Some text
            <a href="image_001.png">Image 1</a>
        </body>
    </html>
    """
    mock_response = Mock()
    mock_response.text = html_content
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = get_latest_image_urls("http://example.com/", count=5)

    assert len(result) == 1
    assert "image_001.png" in result[0]


@patch("custom_components.hungaromet.radar_gif_creator.requests.get")
def test_download_images_success(mock_get):
    """Test download_images successfully downloads images."""
    # Create a simple test image
    img = Image.new("RGB", (100, 100), color="red")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    mock_response = Mock()
    mock_response.content = img_bytes.getvalue()
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    result = download_images([
        "http://example.com/img1.png",
        "http://example.com/img2.png",
    ])

    assert len(result) == 2
    assert all(isinstance(img, Image.Image) for img in result)


@patch("custom_components.hungaromet.radar_gif_creator.requests.get")
def test_download_images_handles_failure(mock_get):
    """Test download_images handles download failures gracefully."""
    mock_get.side_effect = requests.RequestException("Network error")

    result = download_images(["http://example.com/img1.png"])

    assert len(result) == 0


@patch("custom_components.hungaromet.radar_gif_creator.requests.get")
def test_download_images_partial_success(mock_get):
    """Test download_images with some failures."""
    # First call succeeds, second fails
    img = Image.new("RGB", (100, 100), color="blue")
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    success_response = Mock()
    success_response.content = img_bytes.getvalue()
    success_response.raise_for_status = Mock()

    mock_get.side_effect = [success_response, requests.RequestException("Error")]

    result = download_images([
        "http://example.com/img1.png",
        "http://example.com/img2.png",
    ])

    assert len(result) == 1


def test_create_gif_success(tmp_path):
    """Test create_gif successfully creates a GIF."""
    # Create test images
    images = [
        Image.new("RGB", (100, 100), color="red"),
        Image.new("RGB", (100, 100), color="green"),
        Image.new("RGB", (100, 100), color="blue"),
    ]

    output_path = tmp_path / "test.gif"

    create_gif(images, str(output_path), duration=500, end_delay=2000)

    assert output_path.exists()
    # Verify it's a valid GIF
    with Image.open(output_path) as img:
        assert img.format == "GIF"
        assert img.n_frames == 3


def test_create_gif_empty_images_list(tmp_path):
    """Test create_gif handles empty image list."""
    output_path = tmp_path / "test.gif"

    create_gif([], str(output_path))

    # Should not create the file
    assert not output_path.exists()


@patch("custom_components.hungaromet.radar_gif_creator.get_latest_image_urls")
@patch("custom_components.hungaromet.radar_gif_creator.download_images")
@patch("custom_components.hungaromet.radar_gif_creator.create_gif")
@patch("custom_components.hungaromet.radar_gif_creator.os.path.exists")
@patch("custom_components.hungaromet.radar_gif_creator.os.makedirs")
def test_update_radar_gif_success(
    mock_makedirs, mock_exists, mock_create_gif, mock_download, mock_get_urls
):
    """Test update_radar_gif successfully updates GIF."""
    mock_get_urls.return_value = [
        "http://example.com/img1.png",
        "http://example.com/img2.png",
    ]
    mock_download.return_value = [
        Image.new("RGB", (100, 100), color="red"),
        Image.new("RGB", (100, 100), color="green"),
    ]
    mock_exists.return_value = True

    update_radar_gif()

    mock_get_urls.assert_called_once()
    mock_download.assert_called_once()
    mock_create_gif.assert_called_once()


@patch("custom_components.hungaromet.radar_gif_creator.get_latest_image_urls")
def test_update_radar_gif_no_urls(mock_get_urls):
    """Test update_radar_gif handles no URLs found."""
    mock_get_urls.return_value = []

    update_radar_gif()

    mock_get_urls.assert_called_once()


@patch("custom_components.hungaromet.radar_gif_creator.get_latest_image_urls")
@patch("custom_components.hungaromet.radar_gif_creator.download_images")
def test_update_radar_gif_no_images_downloaded(mock_download, mock_get_urls):
    """Test update_radar_gif handles no images downloaded."""
    mock_get_urls.return_value = ["http://example.com/img1.png"]
    mock_download.return_value = []

    update_radar_gif()

    mock_download.assert_called_once()


@patch("custom_components.hungaromet.radar_gif_creator.get_latest_image_urls")
@patch("custom_components.hungaromet.radar_gif_creator.download_images")
@patch("custom_components.hungaromet.radar_gif_creator.create_gif")
@patch("custom_components.hungaromet.radar_gif_creator.os.path.exists")
@patch("custom_components.hungaromet.radar_gif_creator.os.makedirs")
def test_update_radar_gif_creates_www_dir(
    mock_makedirs, mock_exists, mock_create_gif, mock_download, mock_get_urls
):
    """Test update_radar_gif creates www directory if it doesn't exist."""
    mock_get_urls.return_value = ["http://example.com/img1.png"]
    mock_download.return_value = [Image.new("RGB", (100, 100), color="red")]
    mock_exists.return_value = False

    update_radar_gif()

    mock_makedirs.assert_called_once()


@patch("custom_components.hungaromet.radar_gif_creator.get_latest_image_urls")
def test_update_radar_gif_handles_network_error(mock_get_urls):
    """Test update_radar_gif handles network errors."""
    mock_get_urls.side_effect = requests.RequestException("Network error")

    # Should not raise exception
    update_radar_gif()

    mock_get_urls.assert_called_once()
