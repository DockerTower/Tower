FROM alpine:3.4

ENV LANG C.UTF-8
RUN apk add --update --repository http://nl.alpinelinux.org/alpine/edge/testing/ \
    openssl \
    openssh \
    ca-certificates \
    nginx \
    git \
    python3-dev \
    py-pip

WORKDIR /app

# Make some useful symlinks that are expected to exist
RUN cd /usr/local/bin \
	&& ln -s easy_install-3.5 easy_install \
	&& ln -s idle3 idle \
	&& ln -s pydoc3 pydoc \
	&& ln -s python3 python \
	&& ln -s python3-config python-config

COPY requirements.txt /app
RUN pip3 install -r requirements.txt
COPY . /app
VOLUME ["/app"]
VOLUME ["/storage"]
VOLUME ["/.ssh_host"]
VOLUME ["/etc/nginx/conf.d/"]

RUN echo "    IdentityFile /.ssh_host/id_rsa" >> /etc/ssh/ssh_config \
    && echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config

COPY ./docker/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
EXPOSE 443

ENTRYPOINT ["/usr/bin/python3", "/app/tower.py"]
CMD ["sh"]