import numpy as np
import Stemmer
from bm25s.tokenization import Tokenizer
from catboost import CatBoostRanker
from loguru import logger

from src.backend.schemas import BaseSearchDocument, MidwaySearchDocument
from src.model.ranker.config import RankerConfig
from src.model.ranker.features import (
    TokenType,
    calculate_features_by_doc,
    calculate_idf,
    calculate_statistics,
)

# import sys
# from loguru import logger

# from common.log import setup_logging
# from common.log.handler import StreamJsonHandler


# setup_logging(
#     extra_handlers=[StreamJsonHandler(stream=sys.stdout, prepend_value_types=True)]
# )


class DummyRanker:
    def predict(
        self, features: list[list[int | float]], thread_count: int = 10
    ) -> np.ndarray:
        # return bm25 scores
        return np.array(list(map(lambda doc_features: doc_features[0], features)))


class Ranker:
    def __init__(self, config: RankerConfig) -> None:
        self._config = config

        try:
            logger.info("Started loading CatBoost ranker model")
            self._ranker = CatBoostRanker()
            self._ranker.load_model(config.catboost_ranker_path)
            logger.info("Finished loading CatBoost ranker model")

            logger.info("Started loading stemmer")
            stemmer = Stemmer.Stemmer("english")
            logger.info("Finished loading stemmer")

            logger.info("Started loading tokenizer")
            self._tokenizer = Tokenizer(
                stemmer=stemmer,
                lower=config.tokenizer_config.lower,
                stopwords=config.tokenizer_config.stopwords,
                splitter=r"\w+",
            )
            self._tokenizer.load_vocab(config.tokenizer_config.tokenizer_path)
            logger.info("Finished loading tokenizer")
        except Exception as error:
            logger.bind(error=error).error(
                "Failed to load CatBoost ranker model, falling back to DummyRanker"
            )
            self._ranker = DummyRanker()

    def rank(
        self, query: str, docs: list[BaseSearchDocument], top_n: int = 10
    ) -> list[MidwaySearchDocument]:
        logger.info("Started features calculation")
        if isinstance(self._ranker, DummyRanker):
            features = list(map(lambda doc: [doc.bm25_score], docs))
        else:
            force_dummy_tokenization = False
            query_tokens = self._tokenize(
                [query], force_dummy_tokenization=force_dummy_tokenization
            )[0]
            if not len(query_tokens):
                logger.bind(query=query).warning(
                    "Tokenized query length is equal to 0, falling back to dummy tokenization"
                )
                force_dummy_tokenization = True
                query_tokens = self._tokenize(
                    [query], force_dummy_tokenization=force_dummy_tokenization
                )

            docs_texts = [doc.text for doc in docs]
            docs_tokens = self._tokenize(
                docs_texts, force_dummy_tokenization=force_dummy_tokenization
            )

            features = self._calculate_features(query_tokens, docs_tokens, docs)
        logger.info("Finished features calculation")

        logger.info("Started prediction")
        predictions = self._ranker.predict(
            features, thread_count=self._config.processes_num
        )
        logger.info("Finished prediction")

        logger.bind(predictions=predictions.tolist()).info("Got predictions")
        # sort in reverse order
        argsort_predictions = np.argsort(-predictions)
        return [
            MidwaySearchDocument.model_validate({"text": docs[idx].text})
            for idx in argsort_predictions[:top_n]
        ]

    def _tokenize(
        self, texts: str | list[str], force_dummy_tokenization: bool = False
    ) -> list[list[TokenType]]:
        if force_dummy_tokenization:
            logger.info("Force dummy tokenization")
            texts_tokens: list[list[str]] = [
                list(filter(lambda token: token, text.strip().split(" ")))
                for text in texts
            ]
        else:
            texts_tokens: list[list[int]] = self._tokenizer.tokenize(
                texts, show_progress=False
            )

        logger.info("Got tokenized texts")
        return texts_tokens

    def _calculate_features(
        self,
        query_tokens: list[TokenType],
        docs_tokens: list[list[TokenType]],
        docs: list[BaseSearchDocument],
    ) -> list[list[int | float]]:
        logger.info("Started idf calculation")
        idf_dict = calculate_idf(query_tokens, docs_tokens)
        logger.info("Finished idf calculation")

        logger.info("Started features without stats calculation")
        features = [
            calculate_features_by_doc(query_tokens, doc_tokens, docs[idx], idf_dict)
            for idx, doc_tokens in enumerate(docs_tokens)
        ]
        logger.info("Finished features without stats calculation")

        logger.info("Started features stats calculation")
        features_stats = [
            calculate_statistics(
                tuple(map(lambda doc_features: doc_features[idx], features))
            )
            for idx in [0, 1, 3, 4, 6, 8, 10, 12, 14]
        ]
        features_stats = [
            feature_stats_
            for feature_stats in features_stats
            for feature_stats_ in feature_stats
        ]
        logger.info("Finished features stats calculation")

        features = list(
            map(lambda doc_features: doc_features + features_stats, features)
        )
        return features


if __name__ == "__main__":
    import numpy as np
    import pandas as pd

    data = pd.read_csv("/storage/kliffeup/kliffeup/allknower/notebooks/stub_data.csv")
    queries = np.unique(data["query_id"].values)

    ranker = Ranker(
        RankerConfig.from_file(
            "/storage/kliffeup/kliffeup/allknower/midway_search/configs/ranker_config.json"
        )
    )

    for query_id in queries:
        query_data = data[data["query_id"] == query_id].values

        query = query_data[0, -1]
        query_docs = list(
            map(
                lambda sample: BaseSearchDocument.model_validate(
                    {"text": sample[-2], "bm25_score": sample[0]}
                ),
                query_data,
            )
        )
        logger.info("Start ranking")
        ranker.rank(query, query_docs)
        logger.info("Finish ranking")
        # exit(0)
