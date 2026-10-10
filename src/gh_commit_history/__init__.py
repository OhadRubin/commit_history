"""
- description:
    Exports every commit the gh-authenticated GitHub account authored, across all branches, tags,
    and pull request heads of every repository it can find, to a YAML file.
- usage:
    uv run gh-commit-history commits.yaml --store /dev/shm/mirrors  # Export from the shell.
    uv run python -c "import pathlib, gh_commit_history as g; a = g.Account(); g.write_yaml(g.collect(a, a.emails, pathlib.Path('/dev/shm/mirrors')), a.login, pathlib.Path('commits.yaml'))"  # Same, from Python.
- user_story:
    content: |
      Anyone with a GitHub account wants one file listing every commit they ever authored, with
      the repository, full message, and UTC date and time. A script that needs more than the CLI
      offers, such as an extra repository source, imports the same pieces and registers its
      source with @repository_source.
    was_generated_via_skill: false
"""

from gh_commit_history.discovery import REPOSITORY_SOURCES, Account, repository_source
from gh_commit_history.export import write_yaml
from gh_commit_history.history import Commit, collect

__all__ = ['REPOSITORY_SOURCES', 'Account', 'Commit', 'collect', 'repository_source', 'write_yaml']
