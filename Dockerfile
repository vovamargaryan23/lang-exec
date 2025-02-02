FROM python:3.10-alpine

RUN pip install --upgrade pip

COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

RUN mkdir -p --mode=777 /media/code
WORKDIR /app
COPY src/ /app/src/

CMD ["uvicorn", "src.main:app", "--host=0.0.0.0"]