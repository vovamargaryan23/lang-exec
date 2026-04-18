FROM python:3.10-alpine

RUN pip install --upgrade pip

COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

RUN mkdir -p --mode=777 /media/code
WORKDIR /app
COPY src/ /app/src/

ENV WORKERS=4

CMD ["sh", "-c", "gunicorn src.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers $WORKERS --timeout 120 --access-logfile -"]
