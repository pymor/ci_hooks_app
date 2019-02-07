ci-hooks-app
============

This Github webhook consumer exists because
Gitlab Enterprise does not sync PR builds.


Quick Start
--------------------
 - `cp config.ini{.example,}`
 - fill in your values
 - `docker-compose build && docker-compose up`
 - make `localhost:49000` reachable for GitHub at SOMEURL
 - add a GitHub webhook for your repo, point it at http://SOMEURL/postreceive, add secret from config.ini
 - open a new pull request

