import json
from json import JSONDecodeError
from pprint import pformat

from sanic.exceptions import abort
from sanic.log import logger
from sanic_github_webhook import GitHubWebhook, GitLabWebhook
from sanic import Sanic
from sanic.response import text
from sanic_githubapp import GitHubApp

from ci_hooks_app.git import sync_pr_commit

app = Sanic()

from ci_hooks_app.config import config
# Defines '/github' endpoint
hub_webhook = GitHubWebhook(app, secret=config['github']['webhook_secret'])
# Defines '/gitlab' endpoint
lab_webhook = GitLabWebhook(app, secret=config['github']['webhook_secret'])

app.config['GITHUBAPP_SECRET'] = config['github']['app_secret']
app.config['GITHUBAPP_KEY'] = open(config['github']['app_key'], 'rb').read()
app.config['GITHUBAPP_ID'] = config['github']['app_id']
app.config['GITHUBAPP_ROUTE'] = '/githubapp'
github_app = GitHubApp(app)

LAB_TO_HUB_STATE = {'pending': 'pending', 'running': 'pending', 'success': 'success',
                    'failed': 'failure', 'canceled': 'error'}
GITLAB_PR_PREFIX = 'github/PR'

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


async def _on_pipeline(data):
    pipeline = data['object_attributes']
    pipeline['status']
    cl = github_app.installation_client(config['github']['installation_id'])

    msg = data['commit']['message']
    # we're only interested in (self-created) PR builds:
    if not pipeline['ref'].startswith(GITLAB_PR_PREFIX):
        return
    logger.info(f"MSG:\n{msg}")
    try:
        info = json.loads(msg)
    except JSONDecodeError:
        logger.error(f'DECODE ERROR\n{data}')
        return
    logger.info(f'Reconstruct info:\n{pformat(info)}')
    owner, repo = data['project']['path_with_namespace'].split('/')
    repo = cl.repository(owner, repo)
    context = 'ci/gitlab/PR'
    url = f"{data['project']['web_url']}/pipelines/{pipeline['id']}"

    def _create_status(state):
        return repo.create_status(
            description="GitLab PR Pipeline", sha=info['commit_sha'],
            target_url=url, context=context,
            state=state
        )

    try:
        hub_state = LAB_TO_HUB_STATE[pipeline['status']]
    except KeyError:
        logger.error(f'unknown pipeline status {pipeline["status"]}: {pformat(data)}')
        hub_state = 'failure'
    status = _create_status(hub_state)
    logger.info(f"created new status {status} for {info['commit_sha']} on {url}")


@hub_webhook.hook(event_type='pull_request')
def on_pull_request(data):
    if data['action'] in ['synchronize', 'opened']:
        logger.info("queued synching to gitlab")
        app.add_task(sync_to_gitlab(data))
        return text("Sync queued")
    logger.info(f"not a synchronize {data['action']}")
    return text("No action needed")


@lab_webhook.hook(event_type='Pipeline Hook')
def on_pipeline(data):
    if data['object_kind'] == 'pipeline':
        logger.info("pipeline update from gitlab %s", pformat(data['object_attributes']))
        app.add_task(_on_pipeline(data))
        return text("Status queued")
    logger.info("not a pipeline")
    logger.info('\n'+pformat(data))
    return text("No action needed")

app.static('/favicon.png', './favicon.png', name='favicon')
app.static('/favicon.ico', './favicon.png', name='favicon')