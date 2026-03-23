import requests
import base64


def get_picture(url: str) -> str:
    """Download image from URL and return as base64-encoded string."""
    response = requests.get(url)
    response.raise_for_status()
    base64_string = base64.b64encode(response.content).decode("utf-8")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_string}"}}
    # return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_string}", "detail": "high"}}
    # return {"type": "image_url", "image_url": {"url": url, "detail": "high"}}
