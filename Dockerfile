FROM debian:jessie

EXPOSE 5000
ENTRYPOINT ["/code/manage.sh"]
CMD ["run"]

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y \
        git nodejs npm locales \
        python3 python3-setuptools
RUN easy_install3 pip wheel virtualenv
RUN ln -s $(which nodejs) /usr/bin/node

RUN echo 'en_AU.UTF-8 UTF-8' > /etc/locale.gen && locale-gen && update-locale LANG=en_AU.UTF-8
ENV LANG en_AU.UTF-8

RUN mkdir -p /code/data
WORKDIR /code
ADD ./manage.sh /code/manage.sh

ADD package.json /code/package.json
ADD bower.json /code/bower.json
RUN ./manage.sh htmldeps
ADD manage_collectstatic.sh /code/manage_collectstatic.sh
RUN ./manage.sh collectstatic

ADD requirements.txt /code/requirements.txt
ADD test-requirements.txt /code/test-requirements.txt
RUN ./manage.sh pythondeps

ADD dockci /code/dockci
ADD tests /code/tests
ADD pylint.conf /code/pylint.conf
ADD wsgi.py /code/wsgi.py
