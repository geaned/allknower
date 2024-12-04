import json
import regex

from mediawiki_dump.entry import DumpEntry
from mediawiki_dump.reader import DumpReader

from typing import Dict, List, Optional, Tuple

from data import ContentData, ImageData
from utils import make_par_id, make_mediawiki_stream, parse_args


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
    def from_entry(cls, entry: DumpEntry, with_images: bool = True):
        doc = DocBuilder()
        doc.doc_id = entry.page_id
        doc.page_url = entry.url
        doc.title = entry.title

        parsed = DocBuilder.parse_content(entry.content)
        if parsed[0].redirect:
            doc.redirect = True

        # TODO: add heuristics which would not pass technical contents
        doc.contents = [
            (make_par_id(entry.page_id, par.id), par.text)
            for par in parsed
            if (
                par.text
                and par.has_text                # remove technical lists and other data consitints of tags and links
            )
        ]

        doc.references = [link for par in parsed for link in par.get_links()]
        doc.categories = [link for par in parsed for link in par.get_categories()]

        if with_images:
            doc.images = {
                image.crc64: image
                for par in parsed for image in par.get_images()
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
                else None,
            ),
            'images': (
                [
                    {
                        'image': image.data,
                        'metadata': {
                            'title': image.title,
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


def main(args):
    file_name: str = args.file
    mode: str = args.mode
    title: str = args.title
    output_file: str = args.output

    dump = make_mediawiki_stream(file_name)
    reader = DumpReader()

    if mode == "stream":
        # TODO: add stream mode
        return

    for entry in reader.read(dump):
        if entry.title != title:
            continue

        doc = DocBuilder.from_entry(entry)
        with open(output_file, 'w') as result:
            json.dump(doc.as_dict(), result, ensure_ascii=False, indent=4)

        break


if __name__ == '__main__':
    main(parse_args())
