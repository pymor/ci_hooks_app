#build stage
FROM python:3.6

# Install packages
RUN DEBIAN_FRONTEND=noninteractive apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get install -yqq \
    libssl-dev \
    libssh2-1-dev \
    libffi-dev \
    zlib1g-dev \
    python-cffi \
    python-dev \
    python-pip \
    build-essential \
    cmake \
    gcc \
    pkg-config \
    git \
    libhttp-parser-dev \
    python-setuptools \
    wget

RUN wget https://github.com/libgit2/libgit2/archive/v0.27.0.tar.gz && \
    tar xzf v0.27.0.tar.gz && \
    cd libgit2-0.27.0/ && \
    cmake . && \
    make && \
    make install

RUN ldconfig && pip install ipython github3.py jinja2 loguru gitpython sanic six pygit2==0.27 \
    && python -c 'import pygit2'

WORKDIR /ci_hooks_app/src
ENV PYTHONPATH=/ci_hooks_app/src
ADD . /ci_hooks_app

EXPOSE 8080
