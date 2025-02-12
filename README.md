# Jupyter Finance


<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

![finances.png](./img/finances.png)

## Risks

This product is in a pre-release stage.

## Developer Guide

If you are new to using `nbdev` here are some useful pointers to get you
started.

### Setup environmental variables

Set up all your variables in `.env.example` first

``` sh
$ cp .env.example .env
```

### Install jupyter_finance in Development mode

``` sh
# make sure jupyter_finance package is installed in development mode
$ pip install -e .

# make changes under nbs/ directory
# ...

# compile to have changes apply to jupyter_finance
$ nbdev_prepare
```

### Building jupyter_finance in Development mode

``` sh
$ ./build-dist.sh
# ensure prior instances of docker volumes are removed
$ docker-compose up --build
```

## Usage

### Installation

### Documentation

Documentation can be found hosted on this GitHub
[repository](https://github.com/billthan/jupyter-finance)’s [API
pages](https://billthan.github.io/jupyter-finance/).
