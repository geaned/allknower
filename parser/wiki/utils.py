import argparse
import bz2

from mediawiki_dump.dumps import IteratorDump


def make_par_id(doc_id: int, par_id: int) -> str:
    return f'{doc_id}-{par_id}'


def make_mediawiki_stream(file_name: str):
    def get_content(file_name: str):
        with bz2.open(file_name, mode="r") as fp:
            yield from fp

    return IteratorDump(iterator=get_content(file_name))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--file", type=str, default="enwiki-20241101-pages-articles-multistream.xml.bz2",
        help="Path to the MediaWiki dump file"
    )
    parser.add_argument(
        "--mode", type=str, default="stream",
        help="Parse the whole {{stream}} or a {{single}} document"
    )
    parser.add_argument(
        "--title", type=str,
        help="Parse a document with a certain title (used in single mode)"
    )
    parser.add_argument(
        "--no-images", action="store_true",
        help="Parse a document with a certain title (used in single mode)"
    )
    parser.add_argument(
        "--output", type=str, default="result.json",
        help="Path to output file (used in single mode)"
    )
    parser.add_argument(
        "--num-workers", type=int, default=1,
        help="Amount of workers used for dump processing (used in stream mode)"
    )

    return parser.parse_args()
