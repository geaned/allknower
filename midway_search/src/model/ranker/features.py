import math
from collections import defaultdict
from typing import TypeAlias

from numpy import median

from src.backend.schemas import BaseSearchDocument

TokenType: TypeAlias = int | str


def calculate_query_token_ngram_coverage(
    query_tokens: list[TokenType], doc_tokens: list[TokenType], n: int = 1
) -> tuple[int, float]:
    if n > min(len(query_tokens), len(doc_tokens)):
        return 0, 0

    query_ngram_counter = {}
    for i in range(len(query_tokens) - n + 1):
        query_ngram_counter[tuple(query_tokens[i : i + n])] = 0

    for i in range(len(doc_tokens) - n + 1):
        doc_ngram = tuple(doc_tokens[i : i + n])
        if doc_ngram in query_ngram_counter and query_ngram_counter[doc_ngram] == 0:
            query_ngram_counter[doc_ngram] = 1

    query_token_ngram_coverage = sum(query_ngram_counter.values())
    return query_token_ngram_coverage, query_token_ngram_coverage / len(
        query_ngram_counter
    )


def calculate_query_token_first_occurrence(
    query_tokens: list[TokenType], doc_tokens: list[TokenType]
) -> tuple[int, float]:
    first_occurrence = len(doc_tokens)

    for i, doc_token in enumerate(doc_tokens):
        if doc_token in query_tokens:
            first_occurrence = i
            break

    return first_occurrence, first_occurrence / len(doc_tokens)


def calculate_idf(
    query_tokens: list[TokenType], docs_tokens: list[list[TokenType]]
) -> dict[TokenType, int]:
    query_tokens_counts_per_doc = defaultdict(int)

    for doc_tokens in docs_tokens:
        doc_tokens_occurred_in_query = set()
        for token in doc_tokens:
            if token in query_tokens and token not in doc_tokens_occurred_in_query:
                query_tokens_counts_per_doc[token] += 1
                doc_tokens_occurred_in_query.add(token)

    num_docs = len(docs_tokens)
    idf_dict = {}
    for token, doc_count in query_tokens_counts_per_doc.items():
        idf_dict[token] = math.log(num_docs / (doc_count + 1)) + 1

    return idf_dict


def calculate_hh_proximity(
    query_tokens: list[TokenType],
    doc_tokens: list[list[TokenType]],
    idf_dict: dict[TokenType, int],
    z: float = 1.75,
) -> float:
    token_positions = defaultdict(list)
    for idx, token in enumerate(doc_tokens):
        if token in query_tokens:
            token_positions[token].append(idx)

    hh_proximity = 0

    for cur_token, cur_token_positions in token_positions.items():
        cur_token_idf = idf_dict.get(cur_token, 1)
        for cur_token_position in cur_token_positions:
            for other_token in query_tokens:
                if other_token == cur_token:
                    token_weight = 0.25
                else:
                    token_weight = 1

                other_positions = token_positions.get(other_token, [])

                if other_positions:
                    lmd = float("inf")
                    rmd = float("inf")
                    other_token_idf = idf_dict.get(other_token, 1)
                    for other_position in other_positions:
                        if other_position < cur_token_position:
                            lmd = min(lmd, cur_token_position - other_position)
                        elif other_position > cur_token_position:
                            rmd = min(rmd, other_position - cur_token_position)
                            break

                    hh_proximity += (
                        token_weight
                        * cur_token_idf
                        * ((other_token_idf / (lmd**z)) + (other_token_idf / (rmd**z)))
                    )

    return math.log(1 + hh_proximity)


def calculate_features_by_doc(
    query_tokens: list[TokenType],
    doc_tokens: list[TokenType],
    doc: BaseSearchDocument,
    idf_dict: dict[TokenType, int],
) -> list[int | float]:
    doc_length = len(doc_tokens)
    (
        query_token_first_occurrence_unnormalized,
        query_token_first_occurrence_normalized,
    ) = calculate_query_token_first_occurrence(query_tokens, doc_tokens)
    query_token_last_occurrence_unnormalized, _ = (
        calculate_query_token_first_occurrence(query_tokens, doc_tokens[::-1])
    )
    query_token_last_occurrence_unnormalized = (
        doc_length - 1
    ) - query_token_last_occurrence_unnormalized
    query_token_last_occurrence_normalized = (
        query_token_last_occurrence_unnormalized / doc_length
    )
    span_length_unnormalized = (
        query_token_last_occurrence_unnormalized
        - query_token_first_occurrence_unnormalized
        + 1
    )
    span_length_normalized = span_length_unnormalized / doc_length
    hh_proximity_score = calculate_hh_proximity(query_tokens, doc_tokens, idf_dict)

    return [
        doc.bm25_score,
        hh_proximity_score,
        len(query_tokens),
        doc_length,
        *calculate_query_token_ngram_coverage(query_tokens, doc_tokens, n=1),
        *calculate_query_token_ngram_coverage(query_tokens, doc_tokens, n=2),
        *calculate_query_token_ngram_coverage(query_tokens, doc_tokens, n=3),
        query_token_first_occurrence_unnormalized,
        query_token_first_occurrence_normalized,
        query_token_last_occurrence_unnormalized,
        query_token_last_occurrence_normalized,
        span_length_unnormalized,
        span_length_normalized,
    ]


def calculate_statistics(
    values: tuple[int | float],
) -> tuple[int | float, int | float, float, float]:
    max_value = float("-inf")
    min_value = float("inf")
    mean_value = 0.0

    for value in values:
        max_value = max(max_value, value)
        min_value = min(min_value, value)
        mean_value += value

    if len(values):
        mean_value = mean_value / len(values)

    return max_value, min_value, mean_value, median(values)
