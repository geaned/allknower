import os

import numpy as np
from catboost import CatBoostRanker
from loguru import logger

from src.backend.metrics import rank_latency
from src.backend.schemas import BaseSearchDocument, MidwaySearchDocument
from src.model.ranker.config import RankerConfig


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
        except Exception as error:
            logger.bind(error=error).error(
                "Failed to load CatBoost ranker model, falling back to DummyRanker"
            )
            self._ranker = DummyRanker()

    @rank_latency.labels(os.environ["MIDWAY_SEARCH_BACKEND__PROMETHEUS__APP_NAME"], "/rank").time()
    def rank(self, docs: list[BaseSearchDocument], top_n: int = 10) -> list[MidwaySearchDocument]:
        if isinstance(self._ranker, DummyRanker):
            features = list(map(lambda doc: [doc.features[0]], docs))
        else:
            features = list(map(lambda doc: doc.features, docs))

        logger.info("Started prediction")
        predictions = self._ranker.predict(
            features, thread_count=self._config.processes_num
        )
        logger.info("Finished prediction")

        logger.bind(predictions=predictions.tolist()).info("Got predictions")
        # sort in reverse order
        argsort_predictions = np.argsort(-predictions)

        return list(map(lambda idx: MidwaySearchDocument.model_validate(docs[idx].dict()), argsort_predictions[:top_n]))
