FROM tiangolo/uwsgi-nginx-flask:python3.8

RUN apt-get -y update && apt-get -y upgrade

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt
COPY ./app/privatekey.json /app/privatekey.json

RUN pip install -r requirements.txt

COPY . /app

WORKDIR /app/app

