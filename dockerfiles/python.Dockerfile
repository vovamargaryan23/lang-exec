FROM python:3.10-alpine

ENV PYTHONUNBUFFERED=1

LABEL lang.exec="python3 -B"

RUN addgroup -S executor && adduser -S executor -G executor

USER executor

ENTRYPOINT ["python3", "-c", "import signal; signal.pause()"]
