"""
- description:
    Writes collected commits as a YAML list of repo, sha, description, date, and time, newest
    first, in UTC. Multi-line messages become literal blocks and long lines are never folded, so
    every description loads back exactly as it was committed.
- usage:
    uv run python -c "import pathlib, gh_commit_history as g; a = g.Account(); g.write_yaml(g.collect(a, a.emails, pathlib.Path('/dev/shm/mirrors')), a.login, pathlib.Path('commits.yaml'))"  # Export to commits.yaml.
- user_story:
    content: |
      Someone wants their commit history as a file they can read, grep, and hand to other tools.
      They open commits.yaml and see each full message laid out as it was typed, under the
      repository they would look for it in: their own copy when a fork shares the commit. The
      repo and sha together give the commit's page, https://github.com/{repo}/commit/{sha}.
    was_generated_via_skill: false
"""

import pathlib

import yaml

from gh_commit_history.history import Commit


class LiteralDumper(yaml.SafeDumper):
    """Writes multi-line strings as literal blocks so commit messages keep their line breaks."""


LiteralDumper.add_representer(str, lambda dumper, text: dumper.represent_scalar(
    'tag:yaml.org,2002:str', text, style='|' if '\n' in text else None))


def write_yaml(commits: list[Commit], login: str, path: pathlib.Path) -> None:
    rows = [{
        # A commit shared by forks is listed under the account's own copy when one exists.
        'repo': min(commit.repos, key=lambda repo: (not repo.startswith(f'{login}/'), repo)),
        'sha': commit.sha,
        'description': commit.message,
        'date': f'{commit.utc:%Y-%m-%d}',
        'time': f'{commit.utc:%H:%M:%S}',
    } for commit in commits]
    with path.open('w', encoding='utf-8') as output:
        output.write('# Dates and times are UTC. Newest commits first.\n')
        # The largest width PyYAML accepts turns off its folding of long lines.
        yaml.dump(rows, output, Dumper=LiteralDumper, allow_unicode=True, sort_keys=False,
                  width=2147483647)
