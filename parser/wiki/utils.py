import argparse
import bz2
from typing import List, Optional

from mediawiki_dump.dumps import IteratorDump
import mwparserfromhell


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
        "--mock-images", action="store_true",
        help="Write placeholders instead of actual images (substantally increases performance)"
    )
    parser.add_argument(
        "--output", type=str, default="result.json",
        help="Path to output file (used in single mode)"
    )
    parser.add_argument(
        "--num-workers", type=int, default=1,
        help="Amount of workers used for dump processing (used in stream mode)"
    )
    parser.add_argument(
        "--all-img-types", action="store_true",
        help="Add uncommon image types (which may be hard to parse on later stages), "
        "by default .jpeg, .jpg and .png files are added to the result"
    )
    parser.add_argument(
        "--max-img-dim", type=int, default=640,
        help="Enables image size reduction down to the largest dimension,"
        "being of the same size as the passed value (0 for no reduction)"
    )

    return parser.parse_args()


def parse_as_of_template(params: List[mwparserfromhell.nodes.extras.Parameter]) -> str:
    begin: str = 'As of'
    lowercase: bool = False
    end: str = ''
    year: Optional[str] = None
    month: Optional[str] = None
    day: Optional[str] = None

    month_to_name = {
        '01': 'January',
        '02': 'February',
        '03': 'March',
        '04': 'April',
        '05': 'May',
        '06': 'June',
        '07': 'July',
        '08': 'August',
        '09': 'September',
        '10': 'October',
        '11': 'November',
        '12': 'December',
    }

    for param in map(str, params):
        match str(param).split('='):
            case k, v:
                match k:
                    case 'lc':
                        if v == 'y':
                            lowercase = True
                    case 'since':
                        if v == 'y':
                            begin = 'Since'
                    case 'alt':
                        begin = v
                    case 'post':
                        end = v
            case k:
                val = k[0]
                if year is None:
                    year = " " + str(val)
                elif month is None:
                    month = " " + month_to_name[str(val)]
                elif day is None:
                    day = " " + str(val)

    if lowercase:
        begin = begin[0].lower() + begin[1:]

    if year is None:
        raise ValueError('Incorrect "as of" template')

    return f'''{begin}{day if day is not None else ""}{month if month is not None else ""}{year}{end}'''


def check_extension(name: str, exts: List[str]) -> bool:
    return any(name.endswith(ext) for ext in exts)
