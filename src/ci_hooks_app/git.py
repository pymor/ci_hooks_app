from pathlib import Path
from sanic.log import logger
import pygit2 as pg
from pygit2.errors import GitError

from ci_hooks_app.config import config

STORAGE_ROOT = Path(config['local']['repository_storage'])
AUTHOR = pg.Signature(config['author']['name'], config['author']['mail'])


def _first_clone(slug, github_url):
    path = STORAGE_ROOT / slug
    repo = pg.clone_repository(github_url, str(path), bare=True)
    parent_group = config['gitlab']['parent_group']
    if parent_group:
        gitlab_url = f"{config['gitlab']['url']}/{parent_group}/{slug}"
    else:
        gitlab_url = f"{config['gitlab']['url']}/{slug}"
    logger.info(f'CLONING {github_url} with gitlab remote {gitlab_url}')
    gitlab = repo.remotes.create(name='gitlab', url=gitlab_url)
    repo.remotes.set_push_url('gitlab', gitlab_url)
    # the cloned repo object has no branches attrib
    repo = pg.Repository(str(path))
    return repo


def _push_to_gitlab(repo, refspec, force=True):
    gl_cfg = config['gitlab']
    cred = pg.credentials.UserPass(username=gl_cfg['user'], password=gl_cfg['private_token'])
    gitlab_remote = repo.remotes['gitlab']
    callbacks = pg.RemoteCallbacks(credentials=cred)
    if force:
        gitlab_remote.push([f'+{refspec}'], callbacks=callbacks)
    else:
        gitlab_remote.push([refspec], callbacks=callbacks)


def _setup_base_repo_for_sync(base_repo, pr_number, base_refname):
    pr_branch_name = f'github/PR_{pr_number}'
    # create a branch from PR Target, merge PR source into it
    base = base_repo.branches[base_refname]
    # start with clean slate for teh target merge branch
    try:
        base_repo.branches[pr_branch_name].delete()
    except KeyError:
        pass
    pr_branch = base_repo.create_branch(pr_branch_name, base.get_object())

    return pr_branch, pr_branch_name, base


def sync_pr_commit(repo, pr_number, base_refname, head_refname):
    pr_branch, pr_branch_name, base = _setup_base_repo_for_sync(repo, pr_number, base_refname)

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
    commit = repo.create_commit(pr_refspec, AUTHOR, AUTHOR, message, tree,
                                [base.target, fetch_head.target])
    _push_to_gitlab(repo, pr_refspec)


def sync_forked_pr_commit(head_repo, base_repo, pr_number, base_refname, head_refname, head_sha):
    pr_branch, pr_branch_name, base = _setup_base_repo_for_sync(base_repo, pr_number, base_refname)

    origin = base_repo.remotes['origin']
    f = origin.fetch([f'pull/{pr_number}/head'])
    try:
        head_remote = base_repo.create_remote(name='fork', url=head_repo.path)
    except ValueError:
        head_remote = base_repo.remotes['fork']
    head_remote.fetch([f'refs/heads/{head_refname}'])
    fetch_head = base_repo.get(head_sha)
    ind = base_repo.merge_commits(base.get_object(), fetch_head)
    if ind.conflicts is not None:
        logger.info(f'not syncing merge commit for {pr_branch_name} due to existing conflicts')
        return
    tree = ind.write_tree()
    info = {"repo_url": origin.url, "pr": pr_number, "base": base_refname,
            "head_ref": head_refname, "pr_branch": pr_branch_name,
            "commit_sha": head_sha}
    import json
    message = json.dumps(info)
    pr_refspec = f'refs/heads/{pr_branch_name}'
    commit = base_repo.create_commit(pr_refspec, AUTHOR, AUTHOR, message, tree,
                                     [base.target, head_sha])
    _push_to_gitlab(base_repo, pr_refspec)


def sync_forked_branch_commit(head_repo, base_repo, head_refname, head_sha):
    origin = base_repo.remotes['origin']
    try:
        head_remote = base_repo.create_remote(name='fork', url=head_repo.path)
    except ValueError:
        head_remote = base_repo.remotes['fork']
    head_refspec = [f'refs/heads/{head_refname}']
    head_branch = head_remote.fetch(head_refspec)
    fetch_head = base_repo.get(head_sha)
    gitlab_branch = f'github/PUSH_{head_refname}'
    gitlab_refspec = f'refs/heads/{gitlab_branch}'
    base_repo.create_branch(gitlab_branch, fetch_head, True)
    _push_to_gitlab(base_repo, gitlab_refspec)


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

