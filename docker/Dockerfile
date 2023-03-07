FROM python:3.11.2-slim-bullseye

WORKDIR /app/

COPY /requirements.txt ./

RUN pip install -r ./requirements.txt
RUN apt-get -y update
RUN apt-get -y install ffmpeg
RUN apt-get -y install tree
RUN mkdir ./log

COPY /src/ ./src/
COPY /.env ./.env

# CMD [ "tree"]
CMD [ "python", "src/main.py" ]