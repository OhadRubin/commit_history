# gh-commit-history

Exports every commit you authored on GitHub to one YAML file. Each entry gives the repository, the full commit message, and the authored date and time in UTC, newest first.

It reads every branch, tag, and pull request head of each repository it finds. That includes work that never reached a default branch.

## Requirements

- [`gh`](https://cli.github.com) logged in to your account (`gh auth login`). The default token scopes are enough.
- `git` and [`uv`](https://docs.astral.sh/uv/).

## Usage

```bash
uv tool install git+https://github.com/OhadRubin/commit_history
gh-commit-history commits.yaml --store ~/commit-mirrors
```

From a clone, run `uv run gh-commit-history ...` instead.

- `--store DIR` holds one Git mirror per repository. A mirror keeps only commit records. About 500 repositories took roughly 1 GB. Keep the directory and later runs fetch only new history.
- `--email ADDRESS` (repeatable) adds an author address that GitHub does not link to your account, such as a lab machine's default `user@hostname`.

## Output

```yaml
# Dates and times are UTC. Newest commits first.
- repo: you/project
  description: |-
    Add the parser

    Body lines are kept exactly as committed.
  date: '2026-10-07'
  time: 06:35:21
```

A commit found in several repositories, such as a fork and its source, is listed once. It appears under your own copy when you have one.

## How commits are found

1. **Your addresses.** A search for `author:<login>` returns every commit GitHub credits to you, and their author emails become the match set. GitHub credits a commit to an account only through an email address verified on that account. Reading the addresses off these commits avoids the `user` token scope that GitHub's email-listing endpoint requires.
2. **Repositories.** The tool takes the union of three sources:
   - repositories you own, collaborate on, or reach through an organization;
   - repositories that received your pull requests;
   - repositories where the search found your commits.
3. **Commits.** Each repository is fetched as a bare partial clone with `--filter=tree:0`, which keeps commit records and leaves out file trees and contents. The fetch includes `refs/pull/*/head`. A commit is yours when its author email is in the match set.

## Limits

- Commits that exist only in deleted or inaccessible repositories, or were never pushed, cannot be found.
- Search covers default branches only. An address you used only on other branches is missed; pass it with `--email`.
- GitHub search returns at most 1000 results per query, so the tool splits the date range until each part fits. More than 1000 of your commits on a single day stops the run with an error.
- A repository that fails to fetch stops the run. Mirrors that were already fetched are reused on the next run.
- `Co-authored-by` trailers do not count as authorship.

## Adding a repository source

```python
import pathlib
import gh_commit_history as g

@g.repository_source
def remembered(account):
    yield 'someone/old-project'

account = g.Account()
commits = g.collect(account, account.emails, pathlib.Path('/tmp/mirrors'))
g.write_yaml(commits, account.login, pathlib.Path('commits.yaml'))
```

## Verification

```bash
uv run python tests/e2e.py out.yaml --store DIR [--email ADDRESS ...]
```

This runs the command-line tool, then checks two things: the file is ordered newest first, and every commit GitHub search credits to you is in it. The results go to `out.e2e.json`.
