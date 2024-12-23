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
ARG MIDWAY_SEARCH_BACKEND__BASESEARCH_ENDPOINT='http://195.70.199.13:7867/get_documents'
ARG MIDWAY_SEARCH_BACKEND__PROMETHEUS__HOST='0.0.0.0'
ARG MIDWAY_SEARCH_BACKEND__PROMETHEUS__PORT=8090
ARG MIDWAY_SEARCH_BACKEND__PROMETHEUS__APP_NAME='midway_search'

# define env variables
ENV PYTHONPATH=$PWD:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    LANG=C.UTF_8 \
    MIDWAY_SEARCH_BACKEND__APP_HOST=${MIDWAY_SEARCH_BACKEND__APP_HOST} \
    MIDWAY_SEARCH_BACKEND__APP_PORT=${MIDWAY_SEARCH_BACKEND__APP_PORT} \
    MIDWAY_SEARCH_BACKEND__BASESEARCH_ENDPOINT=${MIDWAY_SEARCH_BACKEND__BASESEARCH_ENDPOINT} \
    MIDWAY_SEARCH_BACKEND__PROMETHEUS__HOST=${MIDWAY_SEARCH_BACKEND__PROMETHEUS__HOST} \
    MIDWAY_SEARCH_BACKEND__PROMETHEUS__PORT=${MIDWAY_SEARCH_BACKEND__PROMETHEUS__PORT} \
    MIDWAY_SEARCH_BACKEND__PROMETHEUS__APP_NAME=${MIDWAY_SEARCH_BACKEND__PROMETHEUS__APP_NAME}

FROM base AS runtime

ARG AWS_ACCESS_KEY_ID
ARG AWS_SECRET_ACCESS_KEY
ARG AWS_ENDPOINT_URL='https://ya.cloud'
ARG S3_BUCKET_NAME=''
ARG S3_ARCHIVE_KEY=''

COPY requirements/requirements.txt requirements/requirements.txt
RUN --mount=type=secret,id=pip.conf,dst=/etc/pip.conf \
    pip install -r requirements/requirements.txt

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
EXPOSE ${MIDWAY_SEARCH_BACKEND__APP_PORT} ${MIDWAY_SEARCH_BACKEND__PROMETHEUS__PORT}

ENTRYPOINT ["tini", "-g", "--"]
CMD ["python", "main.py"]
