FROM debian:jessie

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y python3 python3-pip
RUN apt-get install -y make
RUN which make

RUN mkdir -p /code
ADD requirements.txt /code/requirements.txt
RUN pip3 install -r /code/requirements.txt

ADD . /code

WORKDIR /code
ENTRYPOINT ["/usr/bin/make"]
CMD ["run"]
