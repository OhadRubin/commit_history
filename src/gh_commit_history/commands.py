"""
- description:
    Wrappers over the two command-line tools the library drives: `gh api` for GitHub's REST API and
    `git` for commit-only mirrors. A failure raises with the tool's own diagnostics.
- usage:
    uv run python -c "from gh_commit_history.commands import gh; print(gh('user')['login'])"  # Print the logged-in login.
- user_story:
    content: |
      Someone exporting their history hits a GitHub outage halfway through a search. The request is
      retried; if it keeps failing, the error names the exact gh or git call and shows what the
      tool printed, so they know whether to rerun, re-authenticate, or drop a repository.
    was_generated_via_skill: false
"""

import itertools
import json
import pathlib
import shlex
import subprocess
import time

# Seconds to wait before each retry, by a marker in gh's error. Server errors clear within
# seconds. For rate limits GitHub asks for at least a minute, growing on every repeat.
RETRY_WAITS = {'(HTTP 5': (10, 10), 'rate limit': (60, 120, 240, 480)}


def run(*args: str) -> bytes:
    result = subprocess.run(args, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'{shlex.join(args)} exited {result.returncode}:\n'
                           f'{result.stderr.decode(errors="replace")}')
    return result.stdout


def gh(endpoint: str, **fields) -> object:
    """GET a GitHub REST endpoint and return its parsed JSON."""
    args = ['gh', 'api', '--method', 'GET', endpoint]
    for key, value in fields.items():
        args += ['-f', f'{key}={value}']
    for attempt in itertools.count():
        try:
            return json.loads(run(*args))
        except RuntimeError as error:
            waits = next((waits for marker, waits in RETRY_WAITS.items() if marker in str(error)), ())
            if attempt >= len(waits):
                raise
            time.sleep(waits[attempt])


def git(directory: pathlib.Path, *args: str) -> bytes:
    return run('git', '-C', str(directory), *args)
