# syntax = docker/dockerfile:experimental

FROM python:3.8 as base

ENV PYTHONUNBUFFERED=1

RUN python -m pip install --upgrade pip

WORKDIR /home/docker

FROM base

COPY requirements/ requirements/
RUN --mount=type=cache,target=/root/.cache/pip python -m pip install -r requirements/base.txt
RUN --mount=type=cache,target=/root/.cache/pip python -m pip install -r requirements/extras/postgres.txt

COPY taskrabbit/ taskrabbit/
COPY setup.py .
COPY README.md .
RUN pip install .

CMD ["python", "taskrabbit"]
