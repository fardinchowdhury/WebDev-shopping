FROM python:3.8.2
ENV HOME /root
WORKDIR /root
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.2.1/wait /wait
RUN chmod +x /wait
ENTRYPOINT [ "python" ]
CMD /wait && appserver.py