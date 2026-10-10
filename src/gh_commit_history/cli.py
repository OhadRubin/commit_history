"""
- description:
    Command-line entry point: exports every commit the gh-authenticated account authored on GitHub
    to a YAML file.
- usage:
    uv run gh-commit-history commits.yaml --store /dev/shm/mirrors  # Export your commits.
    uv run gh-commit-history commits.yaml --store /dev/shm/mirrors --email me@old-laptop.local  # Also match an address GitHub does not credit to you.
- user_story:
    content: |
      A developer applying for jobs wants a record of everything they have committed since their
      first year of university. They log in with `gh auth login`, run one command, and get
      commits.yaml. Commits made from a lab machine whose address was never added to GitHub are
      included by naming that address with --email.
    was_generated_via_skill: false
"""

import argparse
import pathlib
import sys

from gh_commit_history.discovery import Account
from gh_commit_history.export import write_yaml
from gh_commit_history.history import collect


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Export every commit you authored on GitHub, across all branches, tags, and '
                    'pull requests of every repository found, to a YAML file.')
    parser.add_argument('output', type=pathlib.Path, help='YAML file to write.')
    parser.add_argument('--store', type=pathlib.Path, required=True,
                        help='Directory for commit-only Git mirrors; later runs fetch only new history.')
    parser.add_argument('--email', action='append', default=[],
                        help='Author email GitHub does not credit to your account. Repeatable.')
    args = parser.parse_args()
    account = Account()
    args.store.mkdir(parents=True, exist_ok=True)
    commits = collect(account, account.emails | {email.lower() for email in args.email}, args.store)
    write_yaml(commits, account.login, args.output)
    print(f'Wrote {len(commits)} commits to {args.output}', file=sys.stderr)
