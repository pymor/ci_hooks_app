#build stage python:3.6
#FROM python@sha256:da022140db3b40d07c81815158092ff8ccfd967926b533a7c0b573eeeb5be120
#build stage python:3.8
FROM python@sha256:fe08f4b7948acd9dae63f6de0871f79afa017dfad32d148770ff3a05d3c64363

# Install packages
RUN DEBIAN_FRONTEND=noninteractive apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get install -yqq \
    python-cffi \
    python-dev \
    python-pip \
    git \
    python-setuptools 

#RUN wget https://github.com/libgit2/libgit2/archive/v0.27.0.tar.gz && \
    #tar xzf v0.27.0.tar.gz && \
    #cd libgit2-0.27.0/ && \
    #cmake . && \
    #make && \
    #make install

RUN ldconfig && pip install ipython github3.py jinja2 loguru gitpython sanic==18.12 six pygit2==1.4.0 \
    && python -c 'import pygit2'

WORKDIR /ci_hooks_app/src
ENV PYTHONPATH=/ci_hooks_app/src
ADD . /ci_hooks_app

EXPOSE 8080
