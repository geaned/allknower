FROM python:3.12-slim AS base

WORKDIR /app

RUN apt update && \
    apt install git tini build-essential -y && \
    apt clean && \
    apt autoremove -y && \
    rm -rf /root/.cache && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /etc/apt/sources.list.d/*

ARG MIDWAY_SEARCH_BACKEND__APP_HOST='0.0.0.0'
ARG MIDWAY_SEARCH_BACKEND__APP_PORT=7866
ARG MIDWAY_SEARCH_BACKEND__BASESEARCH_ENDPOINT='http://0.0.0.0:7867/get_documents'
# ARG METRICS_HOST='0.0.0.0'
# ARG METRICS_PORT=8090

# define env variables
ENV PYTHONPATH=$PWD:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    LANG=C.UTF_8 \
    # METRICS_HOST=${METRICS_HOST} \
    # METRICS_PORT=${METRICS_PORT} \
    MIDWAY_SEARCH_BACKEND__APP_HOST=${MIDWAY_SEARCH_BACKEND__APP_HOST} \
    MIDWAY_SEARCH_BACKEND__APP_PORT=${MIDWAY_SEARCH_BACKEND__APP_PORT}

COPY ../pyproject.toml ./

FROM base AS runtime

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_ENDPOINT_URL='https://ya.cloud'
ARG S3_BUCKET_NAME=''
ARG S3_ARCHIVE_KEY=''

COPY requirements/requirements.txt requirements/requirements.txt
RUN --mount=type=secret,id=pip.conf,dst=/etc/pip.conf \
    pip install -r requirements/requirements.txt

COPY ../data/ data/
COPY ../common/ common/
COPY src/ src/
COPY configs/ configs/


# download & unpack the model
# ENV AWS_ENDPOINT_URL=${AWS_ENDPOINT_URL} \
#     S3_BUCKET_NAME=${S3_BUCKET_NAME} \
#     S3_ARCHIVE_KEY=${S3_ARCHIVE_KEY} \
#     S3_ARCHIVE_KEY_BINARY=${S3_ARCHIVE_KEY_BINARY}

# RUN AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
#     AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
#     python /app/src/model/download_model.py

COPY main.py main.py
# expose ports for application server and Prometheus metrics
EXPOSE ${MIDWAY_SEARCH_BACKEND__APP_PORT}
# ${METRICS_PORT}

ENTRYPOINT ["tini", "-g", "--"]
CMD ["python", "main.py"]
