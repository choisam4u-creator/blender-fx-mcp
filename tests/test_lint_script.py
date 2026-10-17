# scripts/lint.sh 가 CI lint 잡과 같은 도구·판으로 같은 검사를 돌리는지. 진짜 uvx 대신 가짜 uvx(파이썬)로 돈다(네트워크 없이).
# bash 스크립트라 Windows 에서는 건너뛴다(@posix_only, 개수는 CONTRIBUTING 에 적혀 있다).
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash") or "bash"
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="bash 스크립트는 POSIX 전용")


def run(*args, cwd=ROOT, env=None):
    return subprocess.run([BASH, str(cwd / "scripts" / "lint.sh"), *args], capture_output=True, text=True, env=env, check=False)


def ci_lint_commands():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    lint = ci.split("\n  lint:\n", 1)[1].split("\n  server-tests:", 1)[0]
    return [c for c in re.findall(r"^      - run: (.*)$", lint, re.M) if re.search(r"\b(ruff|actionlint|zizmor)\b", c)]


@posix_only
def test_lint_script_runs_exactly_the_ci_lint_commands():
    out = run("--print")
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == ci_lint_commands()
    assert len(ci_lint_commands()) == 3
    assert os.access(ROOT / "scripts" / "lint.sh", os.X_OK)
    bad = run("--fix")
    assert bad.returncode == 2 and "쓰는 법" in bad.stderr


@pytest.fixture
def sandbox(tmp_path):
    """스크립트·CONTRIBUTING 복사본과, 이름에 zizmor 가 든 명령만 실패하는 가짜 uvx."""
    (tmp_path / "scripts").mkdir()
    shutil.copy(ROOT / "scripts" / "lint.sh", tmp_path / "scripts" / "lint.sh")
    shutil.copy(ROOT / "CONTRIBUTING.md", tmp_path / "CONTRIBUTING.md")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "uvx"
    fake.write_text(f"#!{sys.executable}\n" + (
        "import os, sys\n"
        "cmd = ' '.join(['uvx', *sys.argv[1:]])\n"
        "open(os.environ['LOG'], 'a').write(cmd + '\\n')\n"
        "sys.exit(1 if 'zizmor' in cmd and os.environ.get('FAIL_ZIZMOR') else 0)\n"))
    fake.chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}", LOG=str(tmp_path / "log"))
    return tmp_path, env


@posix_only
def test_lint_script_runs_all_and_names_the_failure(sandbox):
    root, env = sandbox
    out = run(cwd=root, env=env)
    assert out.returncode == 0, out.stderr
    assert "lint 모두 통과" in out.stdout
    assert (root / "log").read_text().splitlines() == ci_lint_commands()
    (root / "log").unlink()
    out = run(cwd=root, env=dict(env, FAIL_ZIZMOR="1"))
    assert out.returncode == 1
    assert len((root / "log").read_text().splitlines()) == 3   # 하나가 실패해도 셋 다 돌린다
    assert "실패한 검사 1개" in out.stderr and "zizmor" in out.stderr.splitlines()[-1]


@posix_only
def test_lint_script_says_which_table_row_is_missing(sandbox):
    root, env = sandbox
    doc = root / "CONTRIBUTING.md"
    doc.write_text(re.sub(r"^\| zizmor \|.*\n", "", doc.read_text(encoding="utf-8"), flags=re.M), encoding="utf-8")
    out = run("--print", cwd=root, env=env)
    assert out.returncode == 2
    assert "zizmor" in out.stderr and "표에" in out.stderr
