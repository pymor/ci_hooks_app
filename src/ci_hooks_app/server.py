
from sanic.exceptions import abort
from sanic.log import logger
from sanic_github_webhook import Webhook
from sanic import Sanic
from sanic.response import text

from ci_hooks_app.git import sync_pr_commit

app = Sanic()
# Defines '/postreceive' endpoint
from ci_hooks_app.config import config
webhook = Webhook(app, secret=config['github']['webhook_secret'])


async def sync_to_gitlab(data):
    from ci_hooks_app.git import setup_repo_mirror
    pr = data['pull_request']
    base_slug = pr['repo']['full_name']
    base_github_url = pr['repo']['clone_url']
    head_github_url = pr['head']['repo']['clone_url']
    if head_github_url != base_github_url:
        logger.info(f'Will not sync/build foreign PR from {head_github_url}')
        return
    repo = setup_repo_mirror(base_slug, base_github_url)
    base_refname = pr['base']['ref']
    head_refname = pr['head']['ref']
    sync_pr_commit(repo, pr['number'], base_refname, head_refname)


async def _manual_sync_to_gitlab(slug, github_url):
    from ci_hooks_app.git import setup_repo_mirror
    repo = setup_repo_mirror(slug, github_url)
    base_refname = 'master'
    head_refname = 'merge_test'
    sync_pr_commit(repo, 2, base_refname, head_refname)


@app.route("manual")
async def hello_world(request):
    app.add_task(_manual_sync_to_gitlab(slug='pymor/gitlab-ci-test',
                                        github_url='https://github.com/pymor/gitlab-ci-test.git'))
    return text('OK')
    return abort(404, "These are not the droids you're looking for.")


@webhook.hook(event_type='pull_request')
async def on_pull_request(request):
    data = request.json
    if data['action'] == 'synchronize':
        logger.info("queued synching to gitlab")
        app.add_task(sync_to_gitlab(data))
    logger.info("not a synchronize")
    return text("No action needed")

app.static('/favicon.png', './favicon.png', name='favicon')
app.static('/favicon.ico', './favicon.png', name='favicon')