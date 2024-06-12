FROM python:3.10

WORKDIR /crawler

COPY ./requirements.txt /crawler/requirements.txt

RUN pip install --no-cache-dir -r /crawler/requirements.txt

COPY ./src /crawler/src

COPY ./dockercrawler.py /crawler/dockercrawler.py

ENTRYPOINT ["python", "-u", "dockercrawler.py"]