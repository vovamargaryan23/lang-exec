FROM python:3.10-alpine

ENV PYTHONUNBUFFERED=1

RUN addgroup -S executor && adduser -S executor -G executor

USER executor

ENTRYPOINT ["python3", "-B"]
