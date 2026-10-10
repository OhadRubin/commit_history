"""
- description:
    Finds what to collect for the account `gh` is logged in as: the author emails GitHub credits to
    it, and every repository that may hold its commits. Repository sources register themselves with
    `@repository_source`, so a new source is one decorated generator.
- usage:
    uv run python -c "from gh_commit_history.discovery import Account; print(sorted(Account().emails))"  # Print the account's commit emails.
    uv run python -c "from gh_commit_history.discovery import pull_request_targets as s, Account; print(set(s(Account())))"  # Repositories that received your pull requests.
- user_story:
    content: |
      A GitHub user committed under a university address, a personal address, and GitHub's noreply
      address over the years. They run the exporter without listing any of them: the addresses
      come from the commits GitHub already credits to their account. Their work in other people's
      repositories, such as upstream projects they sent pull requests to, is found as well.
    was_generated_via_skill: false
"""

import datetime as dt
import functools
import itertools
import sys
import time
from collections.abc import Callable, Iterator

from gh_commit_history.commands import gh

# GitHub returns at most 1000 results for one search query.
SEARCH_CAP = 1000
# Keeps search requests under GitHub's budget of 30 per minute.
SEARCH_SPACING = 2.1
# Authored dates come from the committer's clock, so they can fall far outside GitHub's lifetime.
EARLIEST, LATEST = dt.date(1970, 1, 1), dt.date(2100, 12, 31)


def search(endpoint: str, query: str, field: str, lo: dt.date, hi: dt.date) -> Iterator[dict]:
    """Yield every result of a GitHub search, halving the `field` date range until each part fits."""
    for page in itertools.count(1):
        time.sleep(SEARCH_SPACING)
        result = gh(endpoint, q=f'{query} {field}:{lo}..{hi}', sort=field, order='asc',
                    per_page=100, page=page)
        if result['total_count'] > SEARCH_CAP or result['incomplete_results']:
            # Splitting after earlier pages were yielded repeats them; every consumer builds a set.
            if lo == hi:
                raise RuntimeError(f'{endpoint} "{query}" cannot be split below {lo}: {result}')
            middle = lo + (hi - lo) // 2
            yield from search(endpoint, query, field, lo, middle)
            yield from search(endpoint, query, field, middle + dt.timedelta(days=1), hi)
            return
        yield from result['items']
        if page * 100 >= result['total_count']:
            print(f'{endpoint} "{query}" {field}:{lo}..{hi}: {result["total_count"]} results',
                  file=sys.stderr, flush=True)
            return


class Account:
    """The GitHub account `gh` is logged in as."""

    @functools.cached_property
    def login(self) -> str:
        return gh('user')['login']

    @functools.cached_property
    def authored(self) -> list[dict]:
        """Commits GitHub credits to the account on default branches of searchable repositories."""
        return list(search('search/commits', f'author:{self.login}', 'author-date', EARLIEST, LATEST))

    @property
    def emails(self) -> set[str]:
        # GitHub credits a commit to an account only through an address verified on it. Reading the
        # addresses off credited commits avoids the `user` token scope that `user/emails` demands.
        return {item['commit']['author']['email'].lower() for item in self.authored}


REPOSITORY_SOURCES: list[Callable[[Account], Iterator[str]]] = []


def repository_source(source: Callable[[Account], Iterator[str]]) -> Callable[[Account], Iterator[str]]:
    REPOSITORY_SOURCES.append(source)
    return source


@repository_source
def accessible(account: Account) -> Iterator[str]:
    """Repositories the account owns, collaborates on, or reaches through an organization."""
    for page in itertools.count(1):
        repositories = gh('user/repos', affiliation='owner,collaborator,organization_member',
                          per_page=100, page=page)
        if not repositories:
            return
        yield from (repository['full_name'] for repository in repositories)


@repository_source
def pull_request_targets(account: Account) -> Iterator[str]:
    """Repositories that received the account's pull requests, whose heads outlive deleted forks."""
    for item in search('search/issues', f'type:pr author:{account.login}', 'created', EARLIEST, LATEST):
        yield item['repository_url'].removeprefix('https://api.github.com/repos/')


@repository_source
def credited(account: Account) -> Iterator[str]:
    """Repositories of other owners holding credited commits, including ones the account has no role in."""
    # `accessible` already lists the account's own repositories, which hold most of its commits.
    query = f'author:{account.login} -user:{account.login}'
    yield from (item['repository']['full_name']
                for item in search('search/commits', query, 'author-date', EARLIEST, LATEST))
