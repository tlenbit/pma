FROM python:3.12-slim
# todo: use something smaller


WORKDIR /app
COPY requirements.txt .

RUN apt-get update
RUN apt-get install gcc -y
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

WORKDIR /app/src
ENTRYPOINT python3 main.py