"""
- description:
    End-to-end check. Runs the CLI for the gh-authenticated account, then confirms that the YAML is
    newest first and holds every commit GitHub search credits to the account. Writes the findings
    to a JSON report beside the YAML, so a run leaves both the export and its verification.
- usage:
    uv run python tests/e2e.py /dev/shm/e2e/commits.yaml --store /dev/shm/e2e/mirrors  # Export and verify.
    uv run python tests/e2e.py out.yaml --store /dev/shm/mirrors --email me@lab.local  # Arguments after the script go to the CLI.
- user_story:
    content: |
      Before trusting the export, its author wants independent evidence that nothing GitHub knows
      about was dropped. Search sees only default branches, so every commit it credits must be in
      the export; the export may hold more, from other branches and pull requests.
    was_generated_via_skill: false
"""

import datetime as dt
import json
import pathlib
import subprocess
import sys

import yaml

from gh_commit_history.discovery import Account

output = pathlib.Path(sys.argv[1])
subprocess.run(['gh-commit-history', *sys.argv[1:]], check=True)

rows = yaml.safe_load(output.read_text(encoding='utf-8'))
# PyYAML loads unquoted dates as date objects, so rows are compared as text.
moments = [(str(row['date']), row['time']) for row in rows]
exported = {(str(row['date']), row['time'], row['description']) for row in rows}
credited, missing = set(), set()
for item in Account().authored:
    utc = dt.datetime.fromisoformat(item['commit']['author']['date']).astimezone(dt.timezone.utc)
    credited.add(item['sha'])
    if (f'{utc:%Y-%m-%d}', f'{utc:%H:%M:%S}', item['commit']['message'].strip('\n')) not in exported:
        missing.add(item['html_url'])

report = {'exported': len(rows), 'credited_by_search': len(credited), 'missing': sorted(missing),
          'newest_first': moments == sorted(moments, reverse=True)}
output.with_suffix('.e2e.json').write_text(json.dumps(report, indent=2))
print(json.dumps({**report, 'missing': len(missing)}, indent=2))
assert report['newest_first'] and not missing, f'see {output.with_suffix(".e2e.json")}'
