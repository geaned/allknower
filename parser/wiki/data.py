import base64
from dataclasses import dataclass
from io import BytesIO
from typing import List, Optional, Tuple, Union
import regex

from crc64iso.crc64iso import crc64
import mwparserfromhell
import pycurl

from utils import check_extension, parse_as_of_template


@dataclass
class ImageData:
    title: str
    data: str   # base64 encoded
    crc64: str
    desc: str


class ContentData:
    image_exts = ['.jpeg', '.jpg', '.jpe', '.jps', '.png', '.apng', '.gif', '.webp', '.tiff', '.tif', '.xcf']

    def __init__(self, idx: int, s: str):
        self.id = idx
        self.redirect = False
        self.has_text = False

        self.links: List[str] = list()
        self.categories: List[str] = list()
        # self.images: List[ImageData] = list()
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
                    if str(node).startswith('\'\'') and node.endswith('\'\''):
                        filtered.append(node.contents)
                    continue

                case mwparserfromhell.nodes.Wikilink:
                    if node.title.startswith('File:'):
                        image_title = str(node.title).replace('File:', '')
                        
                        if not check_extension(node.title, ContentData.image_exts):
                            continue

                        description = self.__parse_reduced(node.text.nodes)

                        # TODO: download image and calculate crc64 from it instead of the title
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

        result = "".join(map(lambda x: regex.sub(r'\'{2,}', '', str(x)), filtered)).strip()

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

        # for node in filtered:
        #     print(type(node))
        #     print(node)
        return "".join(map(str, filtered)).strip().split('|')[-1]

    def __str__(self):
        return self.text

    def get_links(self):
        return self.links

    def get_categories(self):
        return self.categories

    def get_images(self, client: Optional[pycurl.Curl]) -> List[ImageData]:
        image_data: List[ImageData] = list()

        if client is None:
            # return mocked images
            for title, description in self.images:
                image_data.append(ImageData(
                    title,
                    "",
                    crc64(title),
                    description
                ))
    
            return image_data

        for title, description in self.images:
            buffer = BytesIO()
            url = f'''http://commons.wikimedia.org/wiki/Special:FilePath/{title.replace(' ', '_')}'''

            client.setopt(pycurl.URL, url)
            client.setopt(pycurl.WRITEDATA, buffer)
            client.perform()

            data = base64.b64encode(buffer.getvalue()).decode()

            image_data.append(ImageData(
                title,
                data,
                crc64(data),
                description
            ))

        return image_data
