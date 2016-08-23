FROM alpine:3.4

# http://bugs.python.org/issue19846
# > At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
ENV LANG C.UTF-8

RUN apk add --update --repository http://nl.alpinelinux.org/alpine/edge/testing/ \
    python3 \
    python3-dev \
    py-pip \
    py3-zmq \
    libzmq \
    build-base \
  && rm -rf /var/cache/apk/*

# make some useful symlinks that are expected to exist
RUN cd /usr/local/bin \
	&& ln -s easy_install-3.5 easy_install \
	&& ln -s idle3 idle \
	&& ln -s pydoc3 pydoc \
	&& ln -s python3 python \
	&& ln -s python3-config python-config

WORKDIR /app

COPY requirements.txt /app
RUN pip3 install --no-cache-dir -r requirements.txt
COPY . /app
VOLUME ["/app"]

ENTRYPOINT ["/usr/bin/python3", "/app/builder.py"]
CMD ["start"]