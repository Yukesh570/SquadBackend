import os
import sys
from io import BytesIO
from PIL import Image
import uuid
from django.core.files.uploadedfile import InMemoryUploadedFile


# utils.py
def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")


def get_browser_device(user_agent):
    ua = user_agent.lower()
    browser = "Unknown"
    device = "Desktop"

    if "chrome" in ua:
        browser = "Chrome"
    elif "firefox" in ua:
        browser = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Safari"

    if "mobile" in ua:
        device = "Mobile"

    return browser, device


def compress_image(uploaded_image, max_size=(400, 400), quality=85):
    """
    Resizes and compresses an uploaded image.
    """
    if not uploaded_image:
        return None

    # Open the image using Pillow
    img = Image.open(uploaded_image)
    img_format = img.format if img.format else "JPEG"

    # Convert RGBA to RGB if saving as JPEG (prevents crashing)
    if img.mode in ("RGBA", "P") and img_format == "JPEG":
        img = img.convert("RGB")

    # Resize the image keeping the aspect ratio
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Save the manipulated image to a BytesIO object in memory
    output = BytesIO()
    img.save(output, format=img_format, optimize=True, quality=quality)
    output.seek(0)
    # Get the original extension (like .png)
    ext = os.path.splitext(uploaded_image.name)[1]
    unique_name = f"{uuid.uuid4()}{ext}"

    # Wrap the BytesIO object back into a Django InMemoryUploadedFile
    compressed_file = InMemoryUploadedFile(
        output,
        "ImageField",
        unique_name,
        uploaded_image.content_type,
        sys.getsizeof(output),
        None,
    )
    return compressed_file
