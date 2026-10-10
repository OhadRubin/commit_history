"""
- description:
    End-to-end check. Collects and exports the gh-authenticated account's commits, then confirms
    that the YAML is newest first and holds every commit GitHub search credits to the account.
    Writes the findings to a JSON report beside the YAML, so a run leaves both the export and its
    verification.
- usage:
    uv run python tests/e2e.py /dev/shm/e2e/commits.yaml /dev/shm/e2e/mirrors  # Export and verify.
    uv run python tests/e2e.py out.yaml /dev/shm/mirrors me@lab.local  # Also match an extra address.
- user_story:
    content: |
      Before trusting the export, its author wants independent evidence that nothing GitHub knows
      about was dropped. Search sees only default branches, so every commit it credits must be in
      the export; the export may hold more, from other branches and pull requests.
    was_generated_via_skill: false
"""

import json
import pathlib
import sys

import yaml

from gh_commit_history import Account, collect, write_yaml

output, store = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
# One account object serves the export and the check, so the long author search runs once.
account = Account()
store.mkdir(parents=True, exist_ok=True)
write_yaml(collect(account, set(sys.argv[3:]), store), account.login, output)

rows = yaml.safe_load(output.read_text(encoding='utf-8'))
# PyYAML loads unquoted dates as date objects, so moments are compared as text.
moments = [(str(row['date']), row['time']) for row in rows]
exported = {row['sha'] for row in rows}
credited = {item['sha']: item['html_url'] for item in account.authored}
missing = sorted(url for sha, url in credited.items() if sha not in exported)

report = {'exported': len(rows), 'unique_shas': len(exported), 'credited_by_search': len(credited),
          'missing': missing, 'newest_first': moments == sorted(moments, reverse=True)}
output.with_suffix('.e2e.json').write_text(json.dumps(report, indent=2))
print(json.dumps({**report, 'missing': len(missing)}, indent=2))
assert report['newest_first'] and not missing, f'see {output.with_suffix(".e2e.json")}'
