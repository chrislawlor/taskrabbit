# syntax = docker/dockerfile:experimental

FROM python:3.8

ENV PYTHONUNBUFFERED=1

RUN python -m pip install --upgrade pip

WORKDIR /home/docker

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip python -m pip install -r requirements.txt

COPY message_drain.py .


CMD ["python", "message_drain.py"]
