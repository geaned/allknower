from prometheus_client import Counter, Histogram

COMMON_LABELS = ("backend_name", "api_endpoint")

error_count = Counter(
    "error_count", "The number of errors count", labelnames=COMMON_LABELS
)

e2e_response_latency = Histogram(
    "e2e_rank_response_latency",
    "The distribution of the end-to-end rank response latency time",
    labelnames=COMMON_LABELS,
    buckets=[0.05, 0.1, 0.15, 0.2, 1],
)

rank_latency = Histogram(
    "rank_response_latency",
    "The distribution of the rank latency time",
    labelnames=COMMON_LABELS,
    buckets=[0.05, 0.1, 0.15, 0.2, 1],
)
