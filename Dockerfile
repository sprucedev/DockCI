FROM debian:jessie

EXPOSE 5000
ENTRYPOINT ["/usr/bin/make"]
CMD ["run"]

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y \
    git nodejs npm locales \
    python3 python3-pip virtualenv
RUN ln -s $(which nodejs) /usr/bin/node

RUN echo 'en_AU.UTF-8 UTF-8' > /etc/locale.gen && locale-gen && update-locale LANG=en_AU.UTF-8
ENV LANG en_AU.UTF-8

RUN mkdir -p /code/data
WORKDIR /code
ADD Makefile /code/Makefile

ADD package.json /code/package.json
ADD bower.json /code/bower.json
RUN make htmldeps collectstatic

ADD requirements.txt /code/requirements.txt
RUN make pythondeps

ADD . /code
