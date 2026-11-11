"""Regression test for issue #20.

README.md's "Usage" quick start tells a first-time user to run two
`goldpath new` commands back to back into the same --output directory.
If both commands target the same service name, the second one collides
with the first (scaffold_service refuses to overwrite an existing
target directory) and the quick start fails top to bottom.

This test extracts the actual commands from the README's Usage code
block and runs them in order through the real CLI, so it tracks
whatever the README says today rather than a hard-coded guess.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest

from goldpath.cli import main

README_PATH = Path(__file__).resolve().parent.parent / "README.md"


def _extract_usage_commands() -> list[str]:
    text = README_PATH.read_text()
    match = re.search(r"^## Usage\s*\n\s*```bash\n(.*?)```", text, re.S | re.M)
    assert match, "README.md must have a '## Usage' section with a bash code block"
    lines = []
    for raw_line in match.group(1).splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line.startswith("goldpath "):
            lines.append(line)
    assert lines, "expected at least one `goldpath` command in the Usage block"
    return lines


def test_readme_quickstart_commands_run_cleanly(tmp_path, capsys):
    """Running the README's quick start commands in order must not fail."""
    commands = _extract_usage_commands()

    for command in commands:
        args = shlex.split(command)[1:]  # drop the leading "goldpath"

        if "--output" in args:
            idx = args.index("--output")
            output_dir = (tmp_path / args[idx + 1]).resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            args[idx + 1] = str(output_dir)

        exit_code = main(args)
        err = capsys.readouterr().err
        assert exit_code == 0, (
            f"README quick start command failed: `{command}`\n"
            f"stderr: {err}"
        )
