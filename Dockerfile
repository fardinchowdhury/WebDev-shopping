# Following the example of https://shipyard.build/blog/first-flask-docker-compose-app/ -JG
FROM python:3.9.10-alpine3.14
WORKDIR /srv
RUN pip install --upgrade pip
RUN pip install flask
COPY . /srv
ENV FLASK_APP=app

ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.2.1/wait /wait
RUN chmod +x /wait
CMD /wait && python app.py