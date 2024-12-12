import json
from multiprocessing import Pool
from typing import Dict, List, Optional, Tuple

import certifi
from mediawiki_dump.entry import DumpEntry
from mediawiki_dump.reader import DumpReader
import pycurl

from data import ContentData, ImageData
from utils import check_extension, make_par_id, make_mediawiki_stream, parse_args


class DocBuilder():
    def __init__(self):
        self.doc_id: Optional[int] = None
        self.page_url: Optional[str] = None
        self.title: Optional[str] = None
        self.contents: Optional[List[Tuple[str, str]]] = None
        self.redirect = False

        # refer to reference table to get actual doc_ids
        self.images: Optional[Dict[str, ImageData]] = None
        self.references: Optional[List[str]] = None
        self.categories: Optional[List[str]] = None

    @classmethod
    def from_entry(
        cls,
        entry: DumpEntry,
        with_images: bool = True,
        only_common_images: bool = False,
        max_image_size: int = 0,
    ):
        doc = DocBuilder()
        doc.doc_id = entry.page_id
        doc.page_url = entry.url
        doc.title = entry.title

        parsed = DocBuilder.parse_content(entry.content)
        if parsed[0].redirect:
            doc.redirect = True

        doc.contents = [
            (make_par_id(entry.page_id, par.id), par.text)
            for par in parsed
            if (
                par.text
                and par.has_text
            )
        ]

        doc.references = sorted(list(set([link for par in parsed for link in par.get_links()])))
        doc.categories = sorted(list(set([link for par in parsed for link in par.get_categories()])))

        client = None
        if with_images:
            client = pycurl.Curl()
            client.setopt(pycurl.FOLLOWLOCATION, True)
            client.setopt(pycurl.CAINFO, certifi.where())

        doc.images = {
            image.crc64: image
            for par in parsed for image in par.get_images(client, max_image_size)
            if (not only_common_images) or check_extension(image.title, ['.jpeg', '.jpg', '.png'])
            # preserves about 90 percent of all images
        }

        return doc

    @staticmethod
    def parse_content(data: str):
        return [ContentData(idx, raw) for idx, raw in enumerate(data.replace('\t', '').split('\n\n'))]

    def as_dict(self):
        if self.redirect:
            if not self.references:
                raise RuntimeError(f'Redirect page {self.title} has no references')
            return {
                'redirect': True,
                'redirect_to': self.references[0]
            }
        return {
            'redirect': False,
            'doc_id': self.doc_id,
            'page_url': self.page_url,
            'title': self.title,
            'contents': (
                [
                    {
                        'content_id': par_id,
                        'content': text,
                    }
                    for par_id, text in self.contents
                ]
                if self.contents is not None
                else None
            ),
            'images': (
                [
                    {
                        'image': image.data,
                        'metadata': {
                            'title': image.title,
                            'description': image.desc,
                        },
                        'crc64': crc64,
                    }
                    for crc64, image in self.images.items()
                ]
                if self.images is not None
                else None
            ),
            'references': self.references,
            'categories': self.categories,
        }


def parse_entry(
    entry: DumpEntry,
    with_images: bool,
    only_common_imgs: bool, 
    output_file: Optional[str] = None,
    max_image_size: int = 0,
):
    doc = DocBuilder.from_entry(entry, with_images, only_common_imgs, max_image_size)

    if output_file is None:
        output_file = f'page_{doc.doc_id}.json'

    with open(output_file, 'w') as result:
        json.dump(doc.as_dict(), result, ensure_ascii=False, indent=4)


def main(args):
    file_name: str = args.file
    mode: str = args.mode
    title: str = args.title
    output_file: str = args.output
    with_images: bool = not args.mock_images
    num_workers: int = args.num_workers
    only_common_imgs: int = not args.all_img_types
    max_image_size: int = args.max_img_dim

    dump = make_mediawiki_stream(file_name)
    reader = DumpReader()

    if mode == "stream":
        with Pool(processes=num_workers) as pool:
            for entry in reader.read(dump):
                pool.apply(parse_entry, (entry, with_images, only_common_imgs, max_image_size))
    
    if mode == "single":
        if title is None:
            raise ValueError("Title is required in single mode")

        for entry in reader.read(dump):
            if entry.title == title:
                break

        parse_entry(entry, with_images, only_common_imgs, output_file, max_image_size)


if __name__ == '__main__':
    main(parse_args())
