ci-hooks-app
============

This Github App exists because
Gitlab Enterprise does not sync PR builds.

This is alpha-quality software. It might delete all your repositories.


How does this work
------------------

 - push branch to GitHub
 - create PR from that branch
 - Github posts to /github endpoint
 - ci-hooks-app pushes a merge commit to a new branch in gitlab
 - gitlab ci builds that branch, posts pipeline event to app
 - app creates GitHub status with corresponding state


Setup Instructions
--------------------

 - `cp config{.example,}.ini`
 - fill in your values as far as you can
 - `docker-compose build && docker-compose up`
 - create a new github app for your organization, get the private key
 - install app for the repo you're interested in, get the installation  id
 - update values in config
 - make `localhost:49000` externally reachable at SOMEURL
 - add a GitHub webhook (pull-request scope) for your repo, point it at http://SOMEURL/github, add secret from config.ini
 - add a GitLab webhook (pipeline scope) for your repo, point it at http://SOMEURL/gitlab, add secret from config.ini


Limitations
-----------

 - Project slugs on github and gitlab must match
 - you have to manually get app installation details from github
