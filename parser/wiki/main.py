from __future__ import annotations

import json
import logging
import os
import sys
import time
from functools import partial
from multiprocessing import Manager, Pool, Process, Queue
from pathlib import Path
from typing import Any, Optional, cast

from data import ImageParsingMethod, ImageTypes, TextParsingMethod
from doc import DocBuilder
from mediawiki_dump.entry import DumpEntry
from mediawiki_dump.reader import DumpReader
from utils import is_title_appropriate, make_mediawiki_stream, parse_args
from writer import write_messages_file, write_messages_kafka


def parse_entry(  # noqa: PLR0913
    entry: DumpEntry,
    queue: Optional[Queue[Any]] = None,
    image_method: ImageParsingMethod = ImageParsingMethod.WithImagesOnlyRaw,
    text_method: TextParsingMethod = TextParsingMethod.WithTextsOnlyRaw,
    image_types: ImageTypes = ImageTypes.OnlyCommonTypes,
    max_image_size: int = 0,
    output_dir: Optional[str] = None,
    output_file: Optional[str] = None,
    log_dir: str = ".",
    start_index: int = 0,
) -> None:
    if entry.page_id < start_index:
        return

    logging.basicConfig(
        level=logging.INFO,
        filename=Path(log_dir, f"output_{os.getpid()}.log"),
        filemode="a",
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not is_title_appropriate(entry.title):
        logging.info(f"Skipping page {entry.page_id}: {entry.title}")
        return

    start_time = time.time()
    logging.info(f"Working on page {entry.page_id}: {entry.title}")

    doc = DocBuilder.from_entry(
        entry, image_method, text_method, image_types, max_image_size
    )

    parsed_time = time.time()
    if doc.redirect:
        logging.info("Page is a redirection")
    else:
        logging.info(f"Took {parsed_time - start_time:.2f}s to parse")

    if output_file is None:
        output_file = f"page_{doc.doc_id}.json"

    if queue is None:
        with open(output_file, "w") as result:
            # intent set for readability purposes during testing
            json.dump(doc.as_dict(), result, ensure_ascii=False, indent=4)
        return

    if output_dir is None:
        raise ValueError("Output directory is required in stream mode")

    # strict format: ID: int, path: str, doc: str
    queue.put(
        (
            entry.page_id,
            Path(output_dir, output_file).as_posix(),
            json.dumps(doc.as_dict(), ensure_ascii=False),
        )
    )


def main(args) -> None:  # noqa: PLR0912, PLR0915
    file_name: str = args.file
    mode: str = args.mode
    title: str = args.title
    output_dir: str = args.output_dir
    output_file: str = args.output_file
    output_mode: str = args.output_mode
    num_workers: int = args.num_workers
    max_image_size: int = args.max_img_dim
    config_path: str = args.kafka_config
    log_dir: str = args.log_dir
    start_id: int = args.start_id

    match args.no_images, args.use_clip:
        case True, True:
            image_method = ImageParsingMethod.WithImagesOnlyEmbeddings
        case False, True:
            image_method = ImageParsingMethod.WithImagesRawAndEmbeddings
        case True, False:
            image_method = ImageParsingMethod.WithoutImages
        case _:
            image_method = ImageParsingMethod.WithImagesOnlyRaw
    text_method: TextParsingMethod = (
        TextParsingMethod.WithTextsWithEmbeddings
        if args.use_text_model
        else TextParsingMethod.WithTextsOnlyRaw
    )
    image_types: ImageTypes = (
        ImageTypes.AllTypes if args.all_img_types else ImageTypes.OnlyCommonTypes
    )

    dump = make_mediawiki_stream(file_name)
    reader = DumpReader()

    Path(log_dir).mkdir(parents=True, exist_ok=True)

    match mode:
        case "stream":
            m = Manager()
            parsed_queue = cast(Queue, m.Queue(maxsize=1))

            match output_mode:
                case "file":
                    Path(output_dir).mkdir(parents=True, exist_ok=True)

                    Process(
                        target=write_messages_file, args=(parsed_queue, log_dir)
                    ).start()

                case "kafka":
                    with open(config_path) as config_in:
                        config = json.load(config_in)

                    Process(
                        target=write_messages_kafka,
                        args=(parsed_queue, log_dir, config),
                    ).start()

                case _:
                    raise ValueError(
                        f"Unsupported output mode {{{output_mode}}} passed"
                    )

            with Pool(processes=num_workers) as pool:
                try:
                    pool.imap_unordered(
                        partial(
                            parse_entry,
                            queue=parsed_queue,
                            image_method=image_method,
                            text_method=text_method,
                            image_types=image_types,
                            max_image_size=max_image_size,
                            output_dir=output_dir,
                            log_dir=log_dir,
                            start_index=start_id,
                        ),
                        reader.read(dump),
                    )
                    pool.close()
                    pool.join()
                except EOFError:
                    sys.stdout.write(
                        "End of dump file encountered, gracefully stopping...\n"
                    )
                except KeyboardInterrupt:
                    sys.stdout.write(
                        "Interrupted from keyboard, gracefully stopping...\n"
                    )

        case "single":
            if output_mode == "kafka":
                logging.warning(
                    "Only {{file}} output mode available in {{single}} mode"
                )

            if title is None:
                raise ValueError("Title is required in single mode")

            try:
                for entry in reader.read(dump):
                    if entry.title == title:
                        break

                parse_entry(
                    entry,
                    image_method=image_method,
                    text_method=text_method,
                    image_types=image_types,
                    max_image_size=max_image_size,
                    output_file=output_file,
                    log_dir=log_dir,
                )
            except EOFError:
                sys.stdout.write(
                    "End of dump file encountered, gracefully stopping...\n"
                )
            except KeyboardInterrupt:
                sys.stdout.write(
                    "Interrupted execution from keyboard, gracefully stopping...\n"
                )
                return

        case _:
            raise ValueError(f"Unsupported mode {{{mode}}} passed")


if __name__ == "__main__":
    main(parse_args())
