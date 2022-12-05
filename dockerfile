FROM python:3.9

ENV HOME /root
WORKDIR /root

COPY . .

RUN pip3 install pymongo
RUN pip3 install bcrypt

EXPOSE 8080

CMD python3 -u server.py