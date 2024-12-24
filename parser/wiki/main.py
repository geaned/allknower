import json
import logging
from mediawiki_dump.entry import DumpEntry
from mediawiki_dump.reader import DumpReader
from multiprocessing import Manager, Pool, Process, Queue
import os
from pathlib import Path
import requests
import time
from typing import Dict, List, Optional, Tuple

from data import ContentData, ImageData
from utils import check_extension, make_par_id, make_mediawiki_stream, parse_args
from writer import write_messages_file, write_messages_kafka


CLIP_ENDPOINT = 'http://195.70.199.13:8765/embed/images/base64'
CLIP_HEADERS = {
    'Content-Type': 'application/json'
}


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
        use_clip: bool = True
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

        doc.images = {
            image.crc64: image
            for par in parsed for image in par.get_images(with_images, max_image_size)
            if (not only_common_images) or check_extension(image.title, ['.jpeg', '.jpg', '.png'])
            # preserves about 90 percent of all images
        }

        if doc.images:
            clip_start_time = time.time()
            if use_clip:
                DocBuilder.enrich_with_clip_embeddings(list(doc.images.values()))

            clip_finish_time = time.time()
            logging.info(f'Request to CLIP server took {clip_finish_time - clip_start_time:.2f}s')

        return doc

    @staticmethod
    def parse_content(data: str):
        return [ContentData(idx, raw) for idx, raw in enumerate(data.replace('\t', '').split('\n\n'))]

    @staticmethod
    def enrich_with_clip_embeddings(images: List[ImageData]) -> None:
        try:
            resp = requests.post(
                CLIP_ENDPOINT,
                headers=CLIP_HEADERS,
                json=[image.data for image in images]
            ).content
            embeddings = json.loads(resp)['embeddings']

            if len(images) != len(embeddings):
                raise Exception(
                    f'Encountered unequal amounts of images ({len(images)}) '
                    f'and embeddings ({len(embeddings)})'
                )
            for image, embedding in zip(images, embeddings):
                image.data = None
                image.embedding = [round(val, ndigits=7) for val in embedding]
        except Exception as e:
            logging.error(f'While applying CLIP: {str(e)}')

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
                        'embedding': image.embedding,
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
    queue: Optional[Queue],
    with_images: bool = True,
    only_common_imgs: bool = True,
    max_image_size: int = 0,
    use_clip: bool = True,
    output_dir: Optional[str] = None,
    output_file: Optional[str] = None,
    log_dir: str = '.'
):
    logging.basicConfig(
        level=logging.INFO,
        filename=Path(log_dir, f'output_{os.getpid()}.log'),
        filemode='a',
        format='%(asctime)s %(levelname)s %(message)s'
    )

    start_time = time.time()
    logging.info(f'Working on page {entry.page_id}: {entry.title}')

    doc = DocBuilder.from_entry(entry, with_images, only_common_imgs, max_image_size, use_clip)

    parsed_time = time.time()
    if doc.redirect:
        logging.info('Page is a redirection')
    else:
        logging.info(f'Took {parsed_time - start_time:.2f}s to parse')

    if output_file is None:
        output_file = f'page_{doc.doc_id}.json'

    if queue is None:
        with open(output_file, 'w') as result:
            json.dump(doc.as_dict(), result, ensure_ascii=False)
        return

    if output_dir is None:
        raise ValueError('Output directory is required in stream mode')

    queue.put((
        Path(output_dir, output_file),
        json.dumps(doc.as_dict(), ensure_ascii=False, indent=4)
    ))


def write_from_queue(q: Queue):
    while True:
        dump, file_name = q.get()
        with open(file_name, 'w') as result:
            result.write(dump)


def main(args):
    file_name: str = args.file
    mode: str = args.mode
    title: str = args.title
    output_dir: str = args.output_dir
    output_file: str = args.output_file
    output_mode: str = args.output_mode
    with_images: bool = not args.mock_images
    num_workers: int = args.num_workers
    only_common_imgs: int = not args.all_img_types
    max_image_size: int = args.max_img_dim
    use_clip: bool = args.use_clip
    config_path: str = args.kafka_config
    log_dir: str = args.log_dir
    start_id: int = args.start_id

    dump = make_mediawiki_stream(file_name)
    reader = DumpReader()

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    match mode:
        case 'stream':
            m = Manager()
            parsed_queue = m.Queue(maxsize=1)

            match output_mode:
                case 'file':
                    Path(output_dir).mkdir(parents=True, exist_ok=True)

                    Process(target=write_messages_file, args=(parsed_queue, log_dir)).start()

                case 'kafka':
                    config = json.load(open(config_path))
                    Process(target=write_messages_kafka, args=(parsed_queue, log_dir, config)).start()

                case _:
                    raise ValueError(f'Unsupported output mode {{{output_mode}}} passed')

            with Pool(processes=num_workers) as pool:
                for entry in reader.read(dump):
                    if entry.page_id < start_id:
                        continue
                    pool.apply_async(
                        parse_entry,
                        (
                            entry,
                            parsed_queue,
                            with_images,
                            only_common_imgs, 
                            max_image_size,
                            use_clip,
                            output_dir,
                            None,
                            log_dir
                        )
                    )

                pool.join()

        case 'single':
            if output_mode == 'kafka':
                print('Only {{file}} output mode available in {{single}} mode')

            if title is None:
                raise ValueError('Title is required in single mode')

            for entry in reader.read(dump):
                if entry.title == title:
                    break

            parse_entry(
                entry,
                None,
                with_images,
                only_common_imgs,
                max_image_size,
                use_clip,
                None,
                output_file,
                log_dir
            )

        case _:
            raise ValueError(f'Unsupported mode {{{mode}}} passed')


if __name__ == '__main__':
    main(parse_args())
