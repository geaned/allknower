import base64
from crc64iso.crc64iso import crc64
from dataclasses import dataclass
from io import BytesIO
import json
import logging
import mwparserfromhell
from PIL import Image
import regex
import requests
from typing import List, Optional, Tuple, Union
import urllib.parse
import warnings

from utils import check_extension, get_corrected_dimensions, parse_as_of_template


DOWNLOAD_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
}

CLIP_ENDPOINT = 'http://195.70.199.13:8765/embed/images/base64'
CLIP_HEADERS = {
    'Content-Type': 'application/json'
}

def parse_image_binary(raw_image: bytes, fmt: str, max_image_size: int = 0) -> bytes:
    if max_image_size <= 0:
        return raw_image

    with warnings.catch_warnings(
        category=Image.DecompressionBombWarning,
        record=True
    ) as warning_list:
        image = Image.open(BytesIO(raw_image))

    for w in warning_list:
        logging.warning(w.message)

    w, h = image.size
    if w + h <= 2 * max_image_size:
        return raw_image

    new_w, new_h = get_corrected_dimensions(w, h, max_image_size)

    logging.info(f'Resized image from {w}x{h} to {new_w}x{new_h}')

    resized_raw_image = BytesIO()
    image.resize(
        (new_w, new_h),
        resample=Image.Resampling.LANCZOS
    ).save(resized_raw_image, format=fmt)

    return resized_raw_image.getvalue()


@dataclass
class ImageData:
    title: str
    data: Optional[str]                 # base64 encoded
    embedding: Optional[List[float]]    # CLIP embedding
    crc64: str
    desc: str


class ContentData:
    wiki_image_exts = ['.jpeg', '.jpg', '.jpe', '.jps', '.png', '.apng', '.gif', '.webp', '.tiff', '.tif', '.xcf']

    def __init__(self, idx: int, s: str):
        self.id = idx
        self.redirect = False
        self.has_text = False

        self.links: List[str] = list()
        self.categories: List[str] = list()
        self.images: List[Tuple[str, str]] = list()
        self.text = self.__parse(s)

    def __parse(self, s: str):
        nodes = mwparserfromhell.parse(s).nodes
        filtered: List[Union[
            str,
            mwparserfromhell.nodes._base.Node,
            mwparserfromhell.wikicode.Wikicode
        ]] = list()

        for node in nodes:
            match type(node):
                case (
                    mwparserfromhell.nodes.Heading |
                    mwparserfromhell.nodes.Comment
                ):
                    pass

                case mwparserfromhell.nodes.html_entity.HTMLEntity:
                    if node.value == 'nbsp':
                        filtered.append(' ')

                case mwparserfromhell.nodes.Template:
                    if node.name.lower() == 'as of':
                        filtered.append(parse_as_of_template(node.params))

                case mwparserfromhell.nodes.ExternalLink:
                    filtered.append(node.title)

                case mwparserfromhell.nodes.Tag:
                    if str(node).startswith('\'\'') and str(node).endswith('\'\''):
                        filtered.append(str(node.contents).replace('[[', '').replace(']]', ''))
                    continue

                case mwparserfromhell.nodes.Wikilink:
                    if node.title.startswith('File:'):
                        image_title = str(node.title).replace('File:', '')
                        
                        if not check_extension(node.title, ContentData.wiki_image_exts):
                            continue

                        description = self.__parse_reduced(node.text.nodes)

                        self.images.append((image_title, description))

                    elif node.title.startswith('Category:'):
                        category_title = str(node.title).replace('Category:', '')
                        self.categories.append(category_title)

                    else:
                        if node.text is not None:
                            filtered.append(node.text)
                        else:
                            filtered.append(node.title)

                        self.links.append(str(node.title))

                case _:
                    if isinstance(node, mwparserfromhell.nodes.text.Text):
                        if any(x.isalpha() for x in str(node)):
                            self.has_text = True

                    filtered.append(node)

        result = ''.join(map(lambda x: regex.sub(r'\'{2,}', '', str(x)), filtered)).strip()

        if result.startswith('REDIRECT'):
            self.redirect = True

        return result

    def __parse_reduced(self, nodes: List[mwparserfromhell.nodes._base.Node]) -> str:
        filtered: List[Union[
            mwparserfromhell.nodes._base.Node,
            mwparserfromhell.wikicode.Wikicode
        ]] = list()

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

        return ''.join(map(str, filtered)).strip().split('|')[-1]

    def __str__(self):
        return self.text

    def get_links(self):
        return self.links

    def get_categories(self):
        return self.categories

    def get_images(self, with_images: bool = True, max_image_size: int = 0, use_clip: bool = True) -> List[ImageData]:
        if max_image_size < 0:
            raise ValueError('Cannot reduce image dimensions to a negative values')

        image_data: List[ImageData] = list()

        if not with_images:
            # return mocked images
            for title, description in self.images:
                image_data.append(self.__make_mock_image(title, description))
    
            return image_data

        for title, description in self.images:
            file_name = urllib.parse.quote(title.replace(' ', '_'), safe='/', encoding=None, errors=None)
            url = f'''http://commons.wikimedia.org/wiki/Special:FilePath/{file_name}'''

            try:
                buffer = requests.get(url, headers=DOWNLOAD_HEADERS).content
            except Exception as e:
                logging.warning(f'While downloading image {title}:', e)
                continue

            try:
                image_format = Image.registered_extensions()[title[title.rfind('.'):]]
                parsed_image = parse_image_binary(buffer, image_format, max_image_size)
                data = base64.b64encode(parsed_image).decode()
            except Exception as e:
                logging.warning(f'While parsing image {title}: {str(e)}')
                continue


            image_data.append(ImageData(
                title,
                data,
                None,
                crc64(data),
                description
            ))

            logging.info(f'Successfully parsed image {title}')

        # batch CLIP inference
        try:
            if use_clip:
                resp = requests.post(
                    CLIP_ENDPOINT,
                    headers=CLIP_HEADERS,
                    json=[image.data for image in image_data]
                ).content
                embeddings = json.loads(resp)['embeddings']

                if len(image_data) != len(embeddings):
                    raise Exception(
                        f'Encountered unequal amounts of images ({len(image_data)}) '
                        f'and embeddings ({len(embeddings)})'
                    )
                for image, embedding in zip(image_data, embeddings):
                    image.data = None
                    image.embedding = embedding
        except Exception as e:
            logging.error(f'While applying CLIP: {str(e)}')

        return image_data

    @staticmethod
    def __make_mock_image(title: str, description: str) -> ImageData:
        return ImageData(
            title,
            None,
            None,
            crc64(title),
            description
        )
