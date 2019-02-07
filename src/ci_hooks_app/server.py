from pprint import pformat

from sanic.exceptions import abort
from sanic.log import logger
from sanic_github_webhook import GitHubWebhook, GitLabWebhook
from sanic import Sanic
from sanic.response import text

from ci_hooks_app.git import sync_pr_commit

app = Sanic()

from ci_hooks_app.config import config
# Defines '/github' endpoint
hub_webhook = GitHubWebhook(app, secret=config['github']['webhook_secret'])
# Defines '/gitlab' endpoint
lab_webhook = GitLabWebhook(app, secret=config['github']['webhook_secret'])


async def sync_to_gitlab(data):
    from ci_hooks_app.git import setup_repo_mirror
    pr = data['pull_request']
    base_slug = pr['base']['repo']['full_name']
    base_github_url = pr['base']['repo']['clone_url']
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
def hello_world(request):
    app.add_task(_manual_sync_to_gitlab(slug='pymor/gitlab-ci-test',
                                        github_url='https://github.com/pymor/gitlab-ci-test.git'))
    return text('OK')
    return abort(404, "These are not the droids you're looking for.")


@hub_webhook.hook(event_type='pull_request')
def on_pull_request(data):
    if data['action'] == 'synchronize':
        logger.info("queued synching to gitlab")
        app.add_task(sync_to_gitlab(data))
        return text("Sync queued")
    logger.info("not a synchronize")
    return text("No action needed")


@lab_webhook.hook(event_type='Pipeline Hook')
def on_pipeline(data):
    if data['object_kind'] == 'pipeline':
        logger.info("queued synching to gitlab %s", pformat(data['object_attributes']))
        return text("Status queued")
    logger.info("not a pipeline")
    logger.info('\n'+pformat(data))
    return text("No action needed")

app.static('/favicon.png', './favicon.png', name='favicon')
app.static('/favicon.ico', './favicon.png', name='favicon')