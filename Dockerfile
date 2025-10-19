FROM python:3.13.5-slim

RUN apt-get update && apt-get install -y ffmpeg git build-essential

WORKDIR /app

COPY . /app

RUN pip install -r requirements.txt

COPY run.sh /run.sh
RUN chmod +x /run.sh

ENTRYPOINT ["/run.sh"]