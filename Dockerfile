FROM python:3.11

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt .

RUN apt-get update \
    && apt-get install -y postgresql-client \
    && apt-get clean

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

WORKDIR /src

COPY ./entrypoint.sh .
COPY . .

ENTRYPOINT ["./entrypoint.sh"]
#CMD ["python", "src/scraper.py"]