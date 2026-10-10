"""
- description:
    Collects the account's commits from commit-only Git mirrors. Each repository becomes a bare
    partial clone holding its branches, tags, and pull request heads without file trees, so reading
    its whole history costs little more than the commit records themselves.
- usage:
    uv run python -c "import pathlib, gh_commit_history as g; a = g.Account(); print(len(g.collect(a, set(), pathlib.Path('/dev/shm/mirrors'))))"  # Count your commits.
- user_story:
    content: |
      A researcher's commits live on experiment branches that were never merged, in pull requests
      to upstream projects, and in forks of forks. Search sees only default branches, so the
      exporter reads every branch, tag, and pull request head of each repository, and counts a
      commit once even when ten forks contain it. A second run reuses the mirrors and fetches only
      what changed.
    was_generated_via_skill: false
"""

import concurrent.futures
import dataclasses
import datetime as dt
import itertools
import pathlib
import sys

from gh_commit_history.commands import git, run
from gh_commit_history.discovery import REPOSITORY_SOURCES, Account

# Pull request heads keep commits whose source branches or forks were deleted.
REFSPECS = ('+refs/heads/*:refs/heads/*', '+refs/tags/*:refs/tags/*',
            '+refs/pull/*/head:refs/pull/*/head')
# Unit and record separators cannot occur in a hash, a date, or an email address.
LOG_FORMAT = '%H%x1f%aI%x1f%ae%x1f%B%x1e'
WORKERS = 12


@dataclasses.dataclass
class Commit:
    sha: str
    utc: dt.datetime
    message: str
    repos: set[str]


def fetch(store: pathlib.Path, repo: str) -> pathlib.Path:
    """Bring `repo`'s mirror under `store` up to date and return its directory."""
    directory = store / repo.replace('/', '__')
    if not directory.exists():
        run('git', 'init', '--bare', str(directory))
        git(directory, 'remote', 'add', 'origin', f'https://github.com/{repo}.git')
        # A promisor remote may supply the omitted trees later, which a partial clone requires.
        git(directory, 'config', 'remote.origin.promisor', 'true')
        git(directory, 'config', 'remote.origin.partialclonefilter', 'tree:0')
    git(directory, '-c', 'gc.auto=0', 'fetch', '--filter=tree:0', '--no-recurse-submodules',
        '--no-auto-maintenance', 'origin', *REFSPECS)
    return directory


def scan(directory: pathlib.Path, emails: set[str]) -> list[tuple[str, dt.datetime, str]]:
    """(sha, utc, message) of every commit in the mirror authored under one of `emails`."""
    # Only commit records are read; asking for trees or diffs would download file contents.
    log = git(directory, 'log', '--all', f'--format={LOG_FORMAT}').decode(errors='replace')
    rows = []
    # The text after the last separator is Git's closing newline.
    for record in log.split('\x1e')[:-1]:
        sha, authored, email, message = record.lstrip('\n').split('\x1f', 3)
        if email.lower() in emails:
            utc = dt.datetime.fromisoformat(authored).astimezone(dt.timezone.utc)
            rows.append((sha, utc, message.strip('\n')))
    return rows


def collect(account: Account, extra_emails: set[str], store: pathlib.Path) -> list[Commit]:
    """Every commit authored under the account's or `extra_emails` addresses, newest first."""
    fetches = {}
    fetched = itertools.count(1)
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        for source in REPOSITORY_SOURCES:
            for repo in source(account):
                # A repository starts fetching as soon as it is found, while discovery continues.
                if repo not in fetches:
                    fetches[repo] = pool.submit(fetch, store, repo)
                    # A failure is printed when it happens; the run raises it once discovery ends.
                    fetches[repo].add_done_callback(lambda future, repo=repo: print(
                        f'[{next(fetched)}/{len(fetches)}] {repo}: {future.exception() or "fetched"}',
                        file=sys.stderr, flush=True))
        # The address search is the slowest discovery step, so it runs while the fetches proceed.
        emails = account.emails | extra_emails
        directories = [future.result() for future in fetches.values()]
        commits = {}
        for repo, rows in zip(fetches, pool.map(scan, directories, itertools.repeat(emails))):
            for sha, utc, message in rows:
                # One hash is one commit even when several forks contain it.
                commits.setdefault(sha, Commit(sha, utc, message, set())).repos.add(repo)
    return sorted(commits.values(), key=lambda commit: (commit.utc, commit.sha), reverse=True)
