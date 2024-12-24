import argparse
import bz2
from typing import List, Optional, Tuple

from mediawiki_dump.dumps import IteratorDump  # noqa: E501
import mwparserfromhell  # noqa: E501


def make_par_id(doc_id: int, par_id: int) -> str:
    return f"{doc_id}-{par_id}"


def make_mediawiki_stream(file_name: str) -> IteratorDump:
    def get_content(file_name: str):
        with bz2.open(file_name, mode="r") as fp:
            yield from fp

    return IteratorDump(iterator=get_content(file_name))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--file",
        type=str,
        default="./enwiki-20241101-pages-articles-multistream.xml.bz2",
        help="Path to the MediaWiki dump file",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="stream",
        help="Parse the whole {stream} or a {single} document",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./parsed",
        help="Directory to store parsed documents (used in stream mode)",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="result.json",
        help="Path to output file (used in single mode)",
    )
    parser.add_argument(
        "--output-mode",
        type=str,
        default="file",
        help="Write to a {file} or {kafka} event store (the latter does not use "
        "other output settings)",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="Parse a document with a certain title (used in single mode)",
    )
    parser.add_argument(
        "--mock-images",
        action="store_true",
        help="Write placeholders instead of actual images (substantally increases "
        "performance)",
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=1,
        help="Amount of workers used for dump processing (used in stream mode), "
        "setting a high value might cause difficulties with image downloading "
        "process",
    )
    parser.add_argument(
        "--all-img-types",
        action="store_true",
        help="Add uncommon image types (may be hard to parse on later stages), "
        "by default .jpeg, .jpg and .png files are added to the result",
    )
    parser.add_argument(
        "--max-img-dim",
        type=int,
        default=512,
        help="Enables image size reduction down to the average value of "
        "width and height being less or equal to the passed value "
        "(0 for no reduction)",
    )
    parser.add_argument(
        "--use-clip",
        action="store_true",
        help="Use a hardcoded endpoint to retrieve CLIP embeddings and return "
        "them instead of raw images",
    )
    parser.add_argument(
        "--kafka-config",
        type=str,
        default="./config/kafka.json",
        help="Path to kafka config",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="./logs",
        help="Path to log directory"
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=0,
        help="Skip all pages with IDs less than the passed value "
        "(stream mode only)",
    )

    return parser.parse_args()


def parse_as_of_template(params: List[mwparserfromhell.nodes.extras.Parameter]) -> str:
    begin: str = "As of"
    lowercase: bool = False
    end: str = ""
    year: Optional[str] = None
    month: Optional[str] = None
    day: Optional[str] = None

    month_to_name = {
        "1": "January",
        "2": "February",
        "3": "March",
        "4": "April",
        "5": "May",
        "6": "June",
        "7": "July",
        "8": "August",
        "9": "September",
        "10": "October",
        "11": "November",
        "12": "December",
    }

    for param in map(str, params):
        match str(param).split("="):
            case k, v:
                match k:
                    case "lc":
                        if v == "y":
                            lowercase = True
                    case "since":
                        if v == "y":
                            begin = "Since"
                    case "alt":
                        begin = v
                    case "post":
                        end = v
            case k:
                val = k[0]
                if year is None:
                    year = " " + str(val)
                elif month is None:
                    month_key = str(val).lstrip("0")
                    parsed_month = month_to_name.get(month_key, month_key)
                    month = " " + parsed_month
                elif day is None:
                    day = " " + str(val)

    if lowercase:
        begin = begin[0].lower() + begin[1:]

    if year is None:
        raise ValueError("""Incorrect 'as of' template""")

    return f"""{begin}{day if day is not None else ''}{month if month is not None else ''}{year}{end}"""


def check_extension(name: str, exts: List[str]) -> bool:
    return any(name.endswith(ext) for ext in exts)


def get_corrected_dimensions(w: int, h: int, max_image_size: int) -> Tuple[int, int]:
    reduction_ratio = (w + h) / (2 * max_image_size)
    reduction_ratio_corr = min(w, h) / min(
        int(w / reduction_ratio), int(h / reduction_ratio)
    )
    return round(w / reduction_ratio_corr), round(h / reduction_ratio_corr)
