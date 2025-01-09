from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, cast, Dict, List, Tuple, Optional

import json
import logging
import time
import requests
from data import (
    ContentData,
    ImageData,
    ImageParsingMethod,
    ImageTypes,
    TextData,
    TextParsingMethod
)
from mediawiki_dump.entry import DumpEntry
from utils import check_extension, make_par_id


CLIP_ENDPOINT = "http://195.70.199.13:8765/embed/images/base64"
TEXT_ENDPOINT = "http://195.70.199.13:8766/embed/texts"
HEADERS = {"Content-Type": "application/json"}


class Enrichment(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def enrich(self, data: List[str], doc: DocBuilder) -> None:
        raise NotImplementedError()


class WebEnrichment(Enrichment, ABC):
    def __init__(self, endpoint: str, headers: Dict[str, str]):
        super().__init__()

        self.endpoint = endpoint
        self.headers = headers

    def enrich(self, doc: DocBuilder) -> None:
        keys, values = self.__class__.prepare(doc)

        if not keys:
            logging.warning(
                f"Empty web enrichment {self.__class__.__name__} "
                f"for document {doc.doc_id}"
            )
            return

        resp = requests.post(
            self.endpoint,
            headers=self.headers,
            json=values,
            timeout=60,
        ).content
        results = self.__class__.parse(resp)

        if len(keys) != len(results):
            raise Exception(
                f"Encountered unequal amounts of keys ({len(keys)}) "
                f"and results ({len(results)}) for web enrichment "
                f"{self.__class__.__name__} for document {doc.doc_id}"
            )

        self.__class__.emplace(doc, keys, results)

    @staticmethod
    @abstractmethod
    def prepare(doc: DocBuilder) -> Tuple[List[str], List[str]]:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def parse(data: bytes) -> List[Any]:
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    def emplace(doc: DocBuilder, keys: List[str], results: List[Any]) -> None:
        raise NotImplementedError()


class CLIPEnrichment(WebEnrichment):
    @staticmethod
    def prepare(doc: DocBuilder) -> Tuple[List[str], List[str]]:
        if not doc.images:
            return [], []

        crc64s, images_data = list(zip(*doc.images.items()))
        images = [image_data.data for image_data in images_data]
        return crc64s, images

    @staticmethod
    def parse(data: bytes) -> List[Any]:
        return json.loads(data)["embeddings"]

    @staticmethod
    def emplace(doc: DocBuilder, keys: List[str], results: List[Any]) -> None:
        if doc.images is None:
            return

        for crc64, embedding in zip(keys, results):
            doc.images[crc64].data = None
            doc.images[crc64].embedding = [round(val, ndigits=7) for val in cast(List[float], embedding)]


class TextEnrichment(WebEnrichment):
    @staticmethod
    def prepare(doc: DocBuilder) -> Tuple[List[str], List[str]]:
        if not doc.contents:
            return [], []

        ids, texts_data = list(zip(*doc.contents.items()))
        texts = [text_data.text for text_data in texts_data]
        return ids, texts

    @staticmethod
    def parse(data: bytes) -> List[Any]:
        return json.loads(data)["embeddings"]

    @staticmethod
    def emplace(doc: DocBuilder, keys: List[str], results: List[Any]) -> None:
        if doc.contents is None:
            return

        for idx, embedding in zip(keys, results):
            doc.contents[idx].embedding = [round(val, ndigits=7) for val in cast(List[float], embedding)]


class DocBuilder:
    def __init__(self):
        self.doc_id: Optional[int] = None
        self.page_url: Optional[str] = None
        self.title: Optional[str] = None
        self.contents: Optional[Dict[str, TextData]] = None
        self.redirect = False

        # refer to reference table in the index to get actual doc_ids
        self.images: Optional[Dict[str, ImageData]] = None
        self.references: Optional[List[str]] = None
        self.categories: Optional[List[str]] = None

    @classmethod
    def from_entry(
        cls,
        entry: DumpEntry,
        image_method: ImageParsingMethod = ImageParsingMethod.WithImagesOnlyRaw,
        text_method: TextParsingMethod = TextParsingMethod.WithTextsOnlyRaw,
        image_types: ImageTypes = ImageTypes.OnlyCommonTypes,
        max_image_size: int = 0
    ) -> DocBuilder:
        doc = DocBuilder()
        doc.doc_id = entry.page_id
        doc.page_url = entry.url
        doc.title = entry.title

        parsed = DocBuilder.parse_content(entry.content)
        if parsed[0].redirect:
            doc.redirect = True

        doc.contents = {
            make_par_id(entry.page_id, par.id): par.text
            for par in parsed
            if (par.text and par.has_text)
        }

        doc.references = sorted({link for par in parsed for link in par.get_links()})
        doc.categories = sorted(
            {link for par in parsed for link in par.get_categories()}
        )

        if doc.redirect:
            return doc

        doc.images = {
            image.crc64: image
            for par in parsed
            for image in par.get_images(image_method, max_image_size)
            if image_types == ImageTypes.AllTypes
            or check_extension(image.title, [".jpeg", ".jpg", ".png"])
        }

        if image_method in (
            ImageParsingMethod.WithImagesOnlyEmbeddings,
            ImageParsingMethod.WithImagesRawAndEmbeddings
        ):
            try:
                clip_start_time = time.time()
                CLIPEnrichment(
                    endpoint=CLIP_ENDPOINT,
                    headers=HEADERS
                ).enrich(doc)

                clip_finish_time = time.time()
                logging.info(
                    f"Request to CLIP server took "
                    f"{clip_finish_time - clip_start_time:.2f}s"
                )

                if image_method == ImageParsingMethod.WithImagesOnlyEmbeddings:
                    for image in doc.images.values():
                        image.data = None
            except Exception:  # noqa: BLE001
                logging.exception(f"While applying CLIP")

        if text_method == TextParsingMethod.WithTextsWithEmbeddings:
            try:
                text_start_time = time.time()
                TextEnrichment(
                    endpoint=TEXT_ENDPOINT,
                    headers=HEADERS
                ).enrich(doc)

                text_finish_time = time.time()
                logging.info(
                    f"Request to text model server took "
                    f"{text_finish_time - text_start_time:.2f}s"
                )
            except Exception:  # noqa: BLE001
                logging.exception(f"While applying text model")

        return doc

    @staticmethod
    def parse_content(data: str) -> List[ContentData]:
        return [
            ContentData(idx, raw)
            for idx, raw in enumerate(data.replace("\t", "").split("\n\n"))
        ]

    def as_dict(self) -> Dict[str, Any]:
        if self.redirect:
            if not self.references:
                raise RuntimeError(f"Redirect page {self.title} has no references")
            return {"redirect": True, "redirect_to": self.references[0]}
        return {
            "redirect": False,
            "doc_id": self.doc_id,
            "page_url": self.page_url,
            "title": self.title,
            "contents": (
                [
                    {
                        "content_id": par_id,
                        "content": text.text,
                        "embedding": text.embedding
                    }
                    for par_id, text in self.contents.items()
                ]
                if self.contents is not None
                else None
            ),
            "images": (
                [
                    {
                        "crc64": crc64,
                        "image": image.data,
                        "embedding": image.embedding,
                        "metadata": {
                            "title": image.title,
                            "description": image.desc
                        },
                    }
                    for crc64, image in self.images.items()
                ]
                if self.images is not None
                else None
            ),
            "references": self.references,
            "categories": self.categories,
        }
