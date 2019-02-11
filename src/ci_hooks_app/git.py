from pathlib import Path
from sanic.log import logger
import pygit2 as pg
from pygit2.errors import GitError

from ci_hooks_app.config import config

STORAGE_ROOT = Path(config['local']['repository_storage'])


def _first_clone(slug, github_url):
    path = STORAGE_ROOT / slug
    repo = pg.clone_repository(github_url, str(path), bare=True)
    gitlab_url = f"{config['gitlab']['url']}/{slug}"
    logger.info(f'CLONING {github_url}')
    gitlab = repo.remotes.create(name='gitlab', url=gitlab_url)
    repo.remotes.set_push_url('gitlab', gitlab_url)
    # the cloned repo object has no branches attrib
    repo = pg.Repository(str(path))
    return repo


def _push_to_gitlab(repo, refspec):
    gl_cfg = config['gitlab']
    cred = pg.credentials.UserPass(username=gl_cfg['user'], password=gl_cfg['private_token'])
    gitlab_remote = repo.remotes['gitlab']
    callbacks = pg.RemoteCallbacks(credentials=cred)
    gitlab_remote.push([f'+{refspec}'], callbacks=callbacks)


def sync_pr_commit(repo, pr_number, base_refname, head_refname):
    author = pg.Signature('pyMOR Bot', 'bot@pymor.org')
    pr_branch_name = f'github/PR_{pr_number}'
    # create a branch from PR Target, merge PR source into it
    base = repo.branches[base_refname]
    # start with clean slate for teh target merge branch
    try:
        repo.branches[pr_branch_name].delete()
    except KeyError:
        pass
    pr_branch = repo.create_branch(pr_branch_name, base.get_object())
    origin = repo.remotes['origin']
    f = origin.fetch([f'pull/{pr_number}/head'])
    fetch_head = repo.lookup_reference('FETCH_HEAD')
    ind = repo.merge_commits(base.get_object(), fetch_head.get_object())
    if ind.conflicts is not None:
        logger.info(f'not syncing merge commit for {pr_branch_name} due to existing conflicts')
        return
    tree = ind.write_tree()
    info = {"repo_url": origin.url, "pr": pr_number, "base": base_refname,
            "head_ref": head_refname, "pr_branch": pr_branch_name,
            "commit_sha": str(fetch_head.target)}
    import json
    message = json.dumps(info)
    pr_refspec = f'refs/heads/{pr_branch_name}'
    commit = repo.create_commit(pr_refspec, author, author, message, tree,
                                [base.target, fetch_head.target])
    _push_to_gitlab(repo, pr_refspec)
    print(commit)


def setup_repo_mirror(slug, github_url):
    path = STORAGE_ROOT / slug
    try:
        repo = pg.Repository(str(path))
    except: #pg.errors.GitError as ge:
        # not found just means we've never cloned the repo
        # if 'not found' not in str(ge):
        #     raise ge
        repo = _first_clone(slug, github_url)
    assert repo.is_bare
    return repo

