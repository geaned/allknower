# import hashlib
import mwparserfromhell
import regex

from mwparserfromhell.nodes._base import Node
from mwparserfromhell.wikicode import Wikicode

from dataclasses import dataclass
from typing import List, Union

@dataclass
class ImageData:
    title: str
    data: str   # base64 encoded
    crc64: str


class ContentData:
    def __init__(self, idx: int, s: str):
        self.id = idx
        self.redirect = False
        self.has_text = False

        self.links: List[str] = list()
        self.categories: List[str] = list()
        self.images: List[ImageData] = list()
        self.text = self.__parse(s)

    def __parse(self, s: str):
        nodes = mwparserfromhell.parse(s).nodes     # useful for debugging with types
        filtered: List[Union[Node, Wikicode]] = list()

        for node in nodes:
            if isinstance(node, (
                mwparserfromhell.nodes.Template,
                mwparserfromhell.nodes.Heading,
                mwparserfromhell.nodes.Comment,
            )):
                continue

            if isinstance(node, mwparserfromhell.nodes.Tag):
                if str(node).startswith('\'\'\'') and node.endswith('\'\'\''):
                    filtered.append(node.contents)
                continue

            if isinstance(node, mwparserfromhell.nodes.Wikilink):
                if node.title.startswith('File:'):
                    image_title = str(node.title).replace('File:', '')

                    # TODO: download image and calculate crc64
                    self.images.append(ImageData(
                        image_title,
                        "",
                        ""
                    ))
                    continue

                if node.title.startswith('Category:'):
                    category_title = str(node.title).replace('Category:', '')
                    self.categories.append(category_title)
                    continue

                if node.text is not None:
                    filtered.append(node.text)
                else:
                    filtered.append(node.title)
                
                self.links.append(str(node.title))
                continue

            if isinstance(node, mwparserfromhell.nodes.text.Text):
                if any(x.isalpha() for x in str(node)):
                    self.has_text = True

            filtered.append(node)
        
        result = "".join(map(str, filtered)).strip()

        if result.startswith('REDIRECT'):
            self.redirect = True
        
        return result

    def __str__(self):
        return self.text

    def get_links(self):
        return self.links

    def get_categories(self):
        return self.links

    def get_images(self):
        return self.images
