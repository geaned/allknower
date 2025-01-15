from io import BytesIO
from typing import Tuple

from PIL import Image


def get_corrected_dimensions(w: int, h: int, max_image_size: int) -> Tuple[int, int]:
    reduction_ratio = (w + h) / (2 * max_image_size)
    reduction_ratio_corr = min(w, h) / min(
        int(w / reduction_ratio), int(h / reduction_ratio)
    )
    return round(w / reduction_ratio_corr), round(h / reduction_ratio_corr)


def parse_image_binary(raw_image: bytes, fmt: str, max_image_size: int = 0) -> bytes:
    if max_image_size <= 0:
        return raw_image

    image = Image.open(BytesIO(raw_image))

    width, height = image.size
    if width + height <= 2 * max_image_size:
        return raw_image

    new_width, new_height = get_corrected_dimensions(width, height, max_image_size)

    resized_raw_image = BytesIO()
    image.resize((new_width, new_height), resample=Image.Resampling.LANCZOS).save(
        resized_raw_image, format=fmt
    )

    return resized_raw_image.getvalue()
