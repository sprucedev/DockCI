FROM debian:jessie

EXPOSE 5000
ENTRYPOINT ["/code/manage.sh"]
CMD ["run"]

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y \
        git locales python3 python3-setuptools
RUN easy_install3 pip wheel virtualenv

RUN echo 'en_AU.UTF-8 UTF-8' > /etc/locale.gen && locale-gen && update-locale LANG=en_AU.UTF-8
ENV LANG en_AU.UTF-8

RUN mkdir -p /code/data
WORKDIR /code
ADD ./manage.sh /code/manage.sh

ADD ./util/bower_components /code/bower_components
ADD manage_collectstatic.sh /code/manage_collectstatic.sh
RUN ./manage.sh collectstatic

ADD requirements.txt /code/requirements.txt
ADD test-requirements.txt /code/test-requirements.txt
ADD ./util/wheelhouse /code/wheelhouse
RUN ./manage.sh pythondeps

ADD dockci /code/dockci
ADD tests /code/tests
ADD pylint.conf /code/pylint.conf
ADD wsgi.py /code/wsgi.py
