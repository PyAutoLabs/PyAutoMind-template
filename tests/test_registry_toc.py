"""Tests for scripts/registry_toc.py — the generated contents blocks.

The block is generated and self-healed, so the properties that matter are the
contract ones: rendering is idempotent, --check detects drift without writing,
GitHub anchors are derived the way GitHub derives them (duplicates suffixed,
punctuation stripped), fenced code blocks cannot inject phantom sections, and
short files carry no block at all.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import registry_toc  # noqa: E402

SCRIPT = Path(registry_toc.__file__)


def _sections(slugs):
    return "".join(f"## {s}\n- status: x\n\n" for s in slugs)


def test_render_is_idempotent():
    text = "# Parked tasks\n\npreamble prose.\n\n" + _sections(["a-one", "b-two", "c-three"])
    once = registry_toc.render(text)
    assert registry_toc.render(once) == once
    assert registry_toc.TOC_START in once
    assert "- [a-one](#a-one)" in once


def test_block_lands_above_first_section_and_below_preamble():
    text = "# Title\n\npreamble.\n\n" + _sections(["a", "b", "c"])
    out = registry_toc.render(text).splitlines()
    assert out.index("preamble.") < out.index(registry_toc.TOC_START)
    assert out.index(registry_toc.TOC_END) < out.index("## a")


def test_headingless_top_still_works():
    # planned.md carries no H1: the file starts at its first section.
    text = _sections(["x", "y", "z"])
    out = registry_toc.render(text)
    assert out.splitlines()[0] == registry_toc.TOC_START
    assert registry_toc.render(out) == out


def test_short_files_get_no_block_and_lose_a_stale_one():
    short = "# Parked tasks\n\n" + _sections(["only", "two"])
    assert registry_toc.TOC_START not in registry_toc.render(short)
    # a file that shrank below the threshold sheds its old block
    grown = registry_toc.render("# T\n\n" + _sections(["a", "b", "c"]))
    shrunk = grown.replace("## c\n- status: x\n\n", "")
    assert registry_toc.TOC_START not in registry_toc.render(shrunk)


def test_anchors_match_github_slugs():
    text = _sections(["feature/abandoned-spike", "Entry schema", "dup", "dup"])
    out = registry_toc.render(text)
    assert "- [feature/abandoned-spike](#featureabandoned-spike)" in out
    assert "- [Entry schema](#entry-schema)" in out
    assert "- [dup](#dup)" in out
    assert "- [dup](#dup-1)" in out


def test_fenced_headings_are_not_sections():
    fenced = "```\n## not-a-section\n## nor-this\n## nope\n```\n"
    text = fenced + _sections(["real-a", "real-b", "real-c"])
    out = registry_toc.render(text)
    assert "not-a-section" not in out.split(registry_toc.TOC_END)[0]


def test_check_detects_drift_and_write_heals_it(tmp_path):
    (tmp_path / "planned.md").write_text(_sections(["a", "b", "c"]))
    (tmp_path / "parked.md").write_text("# Parked tasks\n\nfresh enough.\n")
    check = ["python3", str(SCRIPT), "--root", str(tmp_path)]
    assert subprocess.run([*check, "--check"]).returncode == 1
    assert subprocess.run([*check, "--write"]).returncode == 0
    assert subprocess.run([*check, "--check"]).returncode == 0
    # --check never writes
    stamped = (tmp_path / "planned.md").read_text()
    subprocess.run([*check, "--check"])
    assert (tmp_path / "planned.md").read_text() == stamped


def test_live_registry_files_are_fresh():
    """The repo's own planned/parked/condemned carry current blocks."""
    rc = subprocess.run(
        ["python3", str(SCRIPT), "--check"], capture_output=True
    ).returncode
    assert rc == 0, "run `python3 scripts/registry_toc.py --write` and commit"
