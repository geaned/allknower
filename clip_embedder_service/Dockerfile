FROM python:3.11-slim AS base

WORKDIR /app

RUN apt update && \
    apt install git tini build-essential -y && \
    apt clean && \
    apt autoremove -y && \
    rm -rf /root/.cache && \
    rm -rf /var/lib/apt/lists/* && \
    rm -rf /etc/apt/sources.list.d/*

ARG CLIP_SERVICE_DEVICE='cuda:0'
ARG APP_HOST='0.0.0.0'
ARG APP_PORT=8766
ARG HF_HOME='/app/.cache/huggingface'

# define env variables
ENV PYTHONPATH=$PWD:$PYTHONPATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    LANG=C.UTF_8 \
    CLIP_SERVICE_DEVICE=${CLIP_SERVICE_DEVICE} \
    APP_HOST=${APP_HOST} \
    APP_PORT=${APP_PORT} \
    HF_HOME=${HF_HOME}

FROM base AS runtime

# ARG AWS_ACCESS_KEY_ID
# ARG AWS_SECRET_ACCESS_KEY
# ARG AWS_ENDPOINT_URL='https://ya.cloud'
# ARG S3_BUCKET_NAME=''
# ARG S3_ARCHIVE_KEY=''

COPY requirements/requirements.txt requirements/requirements.txt
RUN --mount=type=secret,id=pip.conf,dst=/etc/pip.conf \
    pip install --no-cache-dir -r requirements/requirements.txt

COPY log_conf.yaml log_conf.yaml

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
EXPOSE ${APP_PORT}

ENTRYPOINT ["tini", "-g", "--"]
CMD python main.py --port ${APP_PORT}
