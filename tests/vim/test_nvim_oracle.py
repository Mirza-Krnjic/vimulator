"""Fidelity check: run every case in cases.py through a real Neovim and compare.

Skipped when nvim is not on PATH. Neovim defaults ('nostartofline', 'autoindent',
'backspace=indent,eol,start') are the reference, which is what the engine follows.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from vimulator.vim.editor import Editor
from vimulator.vim.keys import format_keys, parse_keys

from .cases import CASES

NVIM = shutil.which("nvim")
pytestmark = pytest.mark.skipif(NVIM is None, reason="nvim not installed")

# `:normal!` aborts the whole key sequence at the first beep, so cases that continue after an
# invalid key cannot be checked this way. The engine resets and carries on, as interactive
# Vim does.
ORACLE_SKIP = {"invalid after operator resets"}


def _vim_string(notation: str) -> str:
    """Escape key notation for use inside a Vim double-quoted string."""
    return notation.replace("\\", "\\\\").replace('"', '\\"').replace("<", "\\<")


def nvim_run(
    lines: list[str], cursor: tuple[int, int], keys: str
) -> tuple[list[str], tuple[int, int]]:
    assert NVIM is not None
    notation = format_keys(parse_keys(keys))
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.txt"
        out = Path(tmp) / "out.txt"
        src.write_text("\n".join(lines) + "\n")
        cmd = [
            NVIM,
            "--headless",
            "--clean",
            "-n",
            "-c",
            f"call cursor({cursor[0] + 1}, {cursor[1] + 1})",
            "-c",
            f'execute "normal! {_vim_string(notation)}"',
            "-c",
            'let g:pos = [line(".") - 1, col(".") - 1]',
            "-c",
            f'call writefile(getline(1, "$") + [string(g:pos)], "{out}")',
            "-c",
            "qa!",
            str(src),
        ]
        subprocess.run(cmd, check=True, timeout=20, capture_output=True)
        result = out.read_text().split("\n")
    pos = ast.literal_eval(result[-2])
    return result[:-2], (pos[0], pos[1])


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_engine_matches_nvim(case) -> None:
    name, start, cursor, keys, _expected_lines, _expected_cursor = case
    if name in ORACLE_SKIP:
        pytest.skip("cannot be replayed through :normal!")
    editor = Editor(start, cursor)
    editor.feed_all(parse_keys(keys))
    nvim_lines, nvim_cursor = nvim_run(start, cursor, keys)
    assert editor.lines == nvim_lines, name
    assert editor.cursor.pos == nvim_cursor, name
