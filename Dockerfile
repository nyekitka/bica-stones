FROM python:3.12-bullseye

RUN mkdir /app

WORKDIR /app

ADD . /app

WORKDIR /app

RUN apt-get update \
    && apt-get install gcc -y \
    && apt-get install postgresql -y \
    && apt-get install libpq-dev -y \
    && apt-get install libpq5 -y


RUN python3 -m pip install --upgrade pip

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

ADD . /app

COPY . .

