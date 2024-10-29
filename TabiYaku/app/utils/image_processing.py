# app/utils/image_processing.py
import base64
import os
from PIL import Image
from io import BytesIO

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def compress_image(image_path, output_path, quality=70):
    image = Image.open(image_path)
    image.save(output_path, "JPEG", quality=quality)