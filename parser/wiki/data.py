import base64
import logging
import urllib.parse
import warnings
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import List, Optional, Tuple, Union

import mwparserfromhell
import regex
import requests
from crc64iso.crc64iso import crc64
from PIL import Image
from utils import check_extension, get_corrected_dimensions, parse_as_of_template

DOWNLOAD_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}


class ParsingMethod(Enum):
    WithImages = 1
    WithoutImages = 2


class ImageTypes(Enum):
    OnlyCommonTypes = 1
    AllTypes = 2


class ImageResult(Enum):
    Image = 1
    Embedding = 2


def parse_image_binary(raw_image: bytes, fmt: str, max_image_size: int = 0) -> bytes:
    if max_image_size <= 0:
        return raw_image

    with warnings.catch_warnings(
        category=Image.DecompressionBombWarning, record=True
    ) as warning_list:
        image = Image.open(BytesIO(raw_image))

    for w in warning_list:
        logging.warning(w.message)

    width, height = image.size
    if width + height <= 2 * max_image_size:
        return raw_image

    new_width, new_height = get_corrected_dimensions(width, height, max_image_size)
    logging.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")

    resized_raw_image = BytesIO()
    image.resize((new_width, new_height), resample=Image.Resampling.LANCZOS).save(
        resized_raw_image, format=fmt
    )

    return resized_raw_image.getvalue()


@dataclass
class ImageData:
    title: str
    data: Optional[str]  # base64 encoded
    embedding: Optional[List[float]]  # CLIP embedding
    crc64: str
    desc: str


class ContentData:
    wiki_image_exts = [
        ".jpeg",
        ".jpg",
        ".jpe",
        ".jps",
        ".png",
        ".apng",
        ".gif",
        ".webp",
        ".tiff",
        ".tif",
        ".xcf",
    ]

    def __init__(self, idx: int, s: str):
        self.id = idx
        self.redirect = False
        self.has_text = False

        self.links: List[str] = []
        self.categories: List[str] = []
        self.images: List[Tuple[str, str]] = []
        self.text = self.__parse(s)

    def __parse(self, s: str):  # noqa: PLR0912
        nodes = mwparserfromhell.parse(s).nodes
        filtered: List[
            Union[
                str,
                mwparserfromhell.nodes._base.Node,
                mwparserfromhell.wikicode.Wikicode,
            ]
        ] = []

        for node in nodes:
            match type(node):
                case mwparserfromhell.nodes.Heading | mwparserfromhell.nodes.Comment:
                    pass

                case mwparserfromhell.nodes.html_entity.HTMLEntity:
                    if node.value == "nbsp":
                        filtered.append(" ")

                case mwparserfromhell.nodes.Template:
                    if node.name.lower() == "as of":
                        filtered.append(parse_as_of_template(node.params))
                        continue

                    for param in node.params:
                        if param.name.strip() == "image":
                            self.images.append((param.value.strip(), ""))

                case mwparserfromhell.nodes.ExternalLink:
                    filtered.append(node.title)

                case mwparserfromhell.nodes.Tag:
                    if str(node).startswith("''") and str(node).endswith("''"):
                        filtered.append(
                            str(node.contents).replace("[[", "").replace("]]", "")
                        )
                    continue

                case mwparserfromhell.nodes.Wikilink:
                    if node.title.startswith("File:"):
                        image_title = str(node.title).replace("File:", "")

                        if not check_extension(node.title, ContentData.wiki_image_exts):
                            continue

                        description = self.__parse_reduced(node.text.nodes)

                        self.images.append((image_title, description))

                    elif node.title.startswith("Category:"):
                        category_title = str(node.title).replace("Category:", "")
                        self.categories.append(category_title)

                    else:
                        if node.text is not None:
                            filtered.append(node.text)
                        else:
                            filtered.append(node.title)

                        self.links.append(str(node.title))

                case _:
                    if isinstance(node, mwparserfromhell.nodes.text.Text) and any(
                        x.isalpha() for x in str(node)
                    ):
                        self.has_text = True

                    filtered.append(node)

        result = "".join(regex.sub(r"\'{2,}", "", str(x)) for x in filtered).strip()

        if result.startswith("REDIRECT"):
            self.redirect = True

        return result

    def __parse_reduced(self, nodes: List[mwparserfromhell.nodes._base.Node]) -> str:
        filtered: List[
            Union[mwparserfromhell.nodes._base.Node, mwparserfromhell.wikicode.Wikicode]
        ] = []

        for node in nodes:
            match type(node):
                case mwparserfromhell.nodes.Wikilink:
                    if node.text is not None:
                        filtered.append(node.text)
                    else:
                        filtered.append(node.title)

                    self.links.append(str(node.title))

                case mwparserfromhell.nodes.Text:
                    filtered.append(node)

        return "".join(map(str, filtered)).strip().split("|")[-1]

    def __str__(self):
        return self.text

    def get_links(self):
        return self.links

    def get_categories(self):
        return self.categories

    def get_images(
        self, method=ParsingMethod.WithImages, max_image_size: int = 0
    ) -> List[ImageData]:
        if max_image_size < 0:
            raise ValueError("Cannot reduce image dimensions to a negative values")

        image_data: List[ImageData] = []

        if method == ParsingMethod.WithoutImages:
            # return mocked images
            for title, description in self.images:
                image_data.append(self.__make_mock_image(title, description))

            return image_data

        for title, description in self.images:
            file_name = urllib.parse.quote(
                title.replace(" ", "_"), safe="/", encoding=None, errors=None
            )
            url = f"""http://commons.wikimedia.org/wiki/Special:FilePath/{file_name}"""

            try:
                buffer = requests.get(url, headers=DOWNLOAD_HEADERS, timeout=60).content
            except Exception as e:  # noqa: BLE001
                logging.warning(f"While downloading image {title}:", e)
                continue

            try:
                image_format = Image.registered_extensions()[title[title.rfind(".") :]]
                parsed_image = parse_image_binary(buffer, image_format, max_image_size)
                data = base64.b64encode(parsed_image).decode()
            except Exception as e:  # noqa: BLE001
                logging.warning(f"While parsing image {title}: {str(e)}")
                continue

            image_data.append(ImageData(title, data, None, crc64(data), description))

            logging.info(f"Successfully parsed image {title}")

        return image_data

    @staticmethod
    def __make_mock_image(title: str, description: str) -> ImageData:
        return ImageData(title, None, None, crc64(title), description)
