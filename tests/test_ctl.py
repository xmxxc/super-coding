"""Tests for ctl.py, the controller's routine checks, through its command-line interface.

Git runs for real against throwaway repositories; `gh` is a fake on PATH that logs its argv and
answers from files the test writes."""

import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CTL = Path(__file__).resolve().parent.parent / "skills" / "super-coding" / "scripts" / "ctl.py"


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


class Env:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()  # macOS: /var is a symlink to /private/var
        self.origin = self.root / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        self.clone = self.root / "clone"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.clone)], check=True, capture_output=True)
        git(self.clone, "config", "user.email", "t@example.com")
        git(self.clone, "config", "user.name", "t")
        self.commit("README.md", "base\n", "base")
        git(self.clone, "push", "-q", "origin", "HEAD:main")
        git(self.clone, "checkout", "-q", "-b", "5-feature")
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.calls = self.root / "gh-calls.jsonl"
        self.gh_dir = self.root / "gh"
        self.gh_dir.mkdir()
        # The fake gh answers `pr view` from gh/pr.json, `api .../comments/<id>` from gh/comment-<id>.json
        # (exit 1 if missing), `issue view` from gh/labels.json. `pr comment`/`issue comment` append to
        # gh/thread.json as the current login and print the new URL (with gh/post-502, create it and
        # still fail; with gh/post-fails, fail without creating it); `api .../issues/<n>/comments` lists
        # gh/thread.json one JSON object per line; `api user` answers the login in gh/login (ctl-bot).
        fake = self.bin / "gh"
        fake.write_text(
            f"#!{sys.executable}\nimport json, os, sys\n"
            f"d = {str(self.gh_dir)!r}\n"
            f"open({str(self.calls)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "a = sys.argv[1:]\n"
            "lp = os.path.join(d, 'login')\n"
            "login = open(lp).read().strip() if os.path.exists(lp) else 'ctl-bot'\n"
            "if a[:2] == ['pr', 'view']:\n"
            "    print(open(os.path.join(d, 'pr.json')).read())\n"
            "elif a[:2] == ['api', 'user']:\n"
            "    print(login if '--jq' in a else json.dumps({'login': login}))\n"
            "elif a[0] == 'api' and '/comments/' in a[1]:\n"
            "    p = os.path.join(d, 'comment-' + a[1].rsplit('/', 1)[1] + '.json')\n"
            "    if not os.path.exists(p): sys.exit(1)\n"
            "    print(open(p).read())\n"
            "elif a[0] == 'api' and a[1].endswith('/comments'):\n"
            "    if os.path.exists(os.path.join(d, 'list-fails')): sys.exit(1)\n"
            "    t = os.path.join(d, 'thread.json')\n"
            "    for c in (json.load(open(t)) if os.path.exists(t) else []): print(json.dumps(c))\n"
            "elif a[:2] in (['pr', 'comment'], ['issue', 'comment']):\n"
            "    body = open(a[a.index('--body-file') + 1]).read()\n"
            "    open(os.path.join(d, 'posted.md'), 'w').write(body)\n"
            "    if os.path.exists(os.path.join(d, 'post-fails')):\n"
            "        sys.stderr.write('HTTP 502: Bad Gateway\\n'); sys.exit(1)\n"
            "    t = os.path.join(d, 'thread.json')\n"
            "    thread = json.load(open(t)) if os.path.exists(t) else []\n"
            "    url = 'https://github.com/o/r/pull/1#issuecomment-' + str(99 + len(thread))\n"
            "    json.dump(thread + [{'html_url': url, 'body': body, 'user': {'login': login}}], open(t, 'w'))\n"
            "    if os.path.exists(os.path.join(d, 'post-502')):\n"
            "        sys.stderr.write('HTTP 502: Bad Gateway\\n'); sys.exit(1)\n"
            "    print(url)\n"
            "elif a[:2] == ['issue', 'edit']:\n"
            "    labels = json.load(open(os.path.join(d, 'labels.json')))\n"
            "    for i, x in enumerate(a):\n"
            "        if x == '--remove-label' and a[i + 1] in labels: labels.remove(a[i + 1])\n"
            "        if x == '--add-label': labels.append(a[i + 1])\n"
            "    json.dump(labels, open(os.path.join(d, 'labels.json'), 'w'))\n"
            "elif a[:2] == ['issue', 'view']:\n"
            "    print(','.join(json.load(open(os.path.join(d, 'labels.json')))))\n")
        fake.chmod(0o755)

    def commit(self, name, text, message):
        (self.clone / name).write_text(text)
        git(self.clone, "add", name)
        git(self.clone, "commit", "-q", "-m", message)
        return git(self.clone, "rev-parse", "HEAD")

    def push(self, force=False):
        git(self.clone, "push", "-q", *(["--force"] if force else []), "origin", "HEAD:5-feature")

    def pr(self, body="Refs #5", commits=("feat: x (Refs #5)",)):
        (self.gh_dir / "pr.json").write_text(json.dumps(
            {"body": body, "commits": [{"messageHeadline": c, "messageBody": ""} for c in commits]}))

    def comment(self, cid, body="## record"):
        (self.gh_dir / f"comment-{cid}.json").write_text(json.dumps({"id": cid, "body": body}))

    def run(self, *args, env=None):
        full = {**os.environ, "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}", **(env or {})}
        return subprocess.run([sys.executable, str(CTL), *args], capture_output=True, text=True, env=full,
                              timeout=60)

    def json(self, *args, ok=True, **kw):
        result = self.run(*args, **kw)
        if ok and result.returncode != 0:
            raise AssertionError(f"ctl {args[0]} exited {result.returncode}: {result.stderr}{result.stdout}")
        return json.loads(result.stdout)

    def close(self):
        self.tmp.cleanup()


class Candidate(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.close)
        self.env.pr()
        self.secret = self.env.root / "secret.env"
        self.secret.write_text("PGHOST=localhost\nPGPASSWORD=s3cr3t-value\n")

    def check(self, head, *extra, ok=True):
        return self.env.json("candidate", "--git", str(self.env.clone), "--repo", "o/r", "--branch", "5-feature",
                             "--head", head, "--pr", "1", "--secret-file", str(self.secret), "--secret-key",
                             "PGPASSWORD", *extra, ok=ok)

    def failed(self, result):
        return sorted(name for name, check in result["checks"].items() if not check["ok"])

    def test_a_clean_candidate_passes_every_check_and_reports_its_tree(self):
        old = self.env.commit("a.txt", "1\n", "one")
        self.env.push()
        head = self.env.commit("a.txt", "2\n", "two")
        self.env.push()
        self.env.comment(11)

        result = self.check(head, "--since", old, "--comment", "11")

        self.assertTrue(result["ok"])
        self.assertEqual(result["tree"], git(self.env.clone, "rev-parse", f"{head}^{{tree}}"))
        self.assertEqual(self.failed(result), [])

    def test_a_remote_branch_at_another_commit_fails(self):
        self.env.commit("a.txt", "1\n", "one")
        self.env.push()
        local = self.env.commit("a.txt", "2\n", "two")  # not pushed

        result = self.check(local, ok=False)

        self.assertFalse(result["ok"])
        self.assertIn("remote-head", self.failed(result))

    def test_a_rewritten_history_fails_the_ancestor_check(self):
        old = self.env.commit("a.txt", "1\n", "one")
        self.env.push()
        git(self.env.clone, "reset", "-q", "--hard", "HEAD~1")
        head = self.env.commit("b.txt", "x\n", "rewritten")
        self.env.push(force=True)

        result = self.check(head, "--since", old, ok=False)

        self.assertEqual(self.failed(result), ["no-force-push"])

    def test_a_committed_secret_fails_without_printing_the_secret(self):
        head = self.env.commit("config.ts", "const p = 's3cr3t-value'\n", "oops")
        self.env.push()

        result = self.env.run("candidate", "--git", str(self.env.clone), "--repo", "o/r", "--branch", "5-feature",
                              "--head", head, "--pr", "1", "--secret-file", str(self.secret),
                              "--secret-key", "PGPASSWORD")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no-secret", self.failed(json.loads(result.stdout)))
        self.assertNotIn("s3cr3t-value", result.stdout + result.stderr)

    def test_a_failing_secret_scan_fails_closed(self):
        head = self.env.commit("a.txt", "1\n", "one")
        self.env.push()
        real_git = subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()
        fake = self.env.bin / "git"
        fake.write_text(f"#!{sys.executable}\nimport os, sys\n"
                        f"if 'grep' in sys.argv[1:4]: sys.exit(128)\n"
                        f"os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])\n")
        fake.chmod(0o755)

        result = self.check(head, ok=False)

        self.assertFalse(result["checks"]["no-secret"]["ok"])
        self.assertIn("128", result["checks"]["no-secret"]["detail"])

    def test_the_secret_never_appears_in_a_command_line(self):
        head = self.env.commit("a.txt", "1\n", "one")
        self.env.push()
        real_git = subprocess.run(["which", "git"], capture_output=True, text=True).stdout.strip()
        argv_log = self.env.root / "git-argv.log"
        fake = self.env.bin / "git"
        fake.write_text(f"#!{sys.executable}\nimport os, sys\n"
                        f"open({str(argv_log)!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
                        f"os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])\n")
        fake.chmod(0o755)

        result = self.check(head)

        self.assertTrue(result["checks"]["no-secret"]["ok"])
        self.assertIn("grep", argv_log.read_text())
        self.assertNotIn("s3cr3t-value", argv_log.read_text())

    def test_a_closing_keyword_in_a_commit_fails(self):
        head = self.env.commit("a.txt", "1\n", "one")
        self.env.push()
        self.env.pr(commits=("feat: x\n", "fix: y Closes #5"))

        self.assertEqual(self.failed(self.check(head, ok=False)), ["no-closing-keywords"])

    def test_a_missing_record_comment_fails(self):
        head = self.env.commit("a.txt", "1\n", "one")
        self.env.push()
        self.env.comment(11)

        result = self.check(head, "--comment", "11", "--comment", "12", ok=False)

        self.assertEqual(self.failed(result), ["comments"])
        self.assertIn("12", result["checks"]["comments"]["detail"])

    def test_a_port_still_in_use_fails(self):
        head = self.env.commit("a.txt", "1\n", "one")
        self.env.push()
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        self.addCleanup(listener.close)

        result = self.check(head, "--port", str(listener.getsockname()[1]), ok=False)

        self.assertEqual(self.failed(result), ["port-free"])


class Checks(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.close)
        self.head = self.env.commit("a.txt", "1\n", "one")
        self.env.push()
        self.snapshot = self.env.root / "snapshot"
        git(self.env.clone, "worktree", "add", "-q", "--detach", str(self.snapshot), "main")
        self.log = self.env.root / "verification.log"

    def test_the_snapshot_moves_to_the_head_and_each_real_exit_code_is_logged(self):
        result = self.env.json("checks", "--cwd", str(self.snapshot), "--head", self.head, "--log", str(self.log),
                               "--cmd", "cat a.txt", "--cmd", "sh -c 'echo broken; exit 7' | tail -1", ok=False)

        self.assertEqual(git(self.snapshot, "rev-parse", "HEAD"), self.head)
        self.assertEqual([r["exit"] for r in result["results"]], [0, 7])  # the pipeline's own status, not tail's
        self.assertFalse(result["ok"])
        log = self.log.read_text()
        self.assertIn(f"# snapshot {self.head}", log)
        self.assertIn("## exit=7", log)

    def test_the_log_keeps_the_last_lines_in_the_order_they_were_printed(self):
        self.env.json("checks", "--cwd", str(self.snapshot), "--head", self.head, "--log", str(self.log), "--tail", "2",
                      "--cmd", "echo log >&2; echo log >&2; echo summary")

        self.assertIn("log\nsummary\n## exit=0", self.log.read_text())

    def test_parallel_checks_on_one_snapshot_each_check_their_own_head(self):
        import concurrent.futures
        import shlex
        import time
        a = self.env.commit("a.txt", "alpha\n", "alpha")
        b = self.env.commit("a.txt", "beta\n", "beta")
        self.env.push()
        marker, release = self.env.root / "ready", self.env.root / "release"
        check = self.env.root / "check.py"
        check.write_text("from pathlib import Path\nimport time\n"
                         f"Path({str(marker)!r}).touch()\n"
                         f"while not Path({str(release)!r}).exists(): time.sleep(.01)\n"
                         "assert Path('a.txt').read_text().strip() == 'alpha'\n")
        command = f"{shlex.quote(sys.executable)} {shlex.quote(str(check))}"
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            first = pool.submit(self.env.run, "checks", "--cwd", str(self.snapshot), "--head", a, "--log",
                                str(self.env.root / "a.log"), "--cmd", command)
            for _ in range(1000):
                if marker.exists():
                    break
                time.sleep(0.01)
            second = pool.submit(self.env.run, "checks", "--cwd", str(self.snapshot), "--head", b, "--log",
                                 str(self.env.root / "b.log"), "--cmd", "grep -q beta a.txt")
            time.sleep(1)
            release.touch()
            results = [first.result(), second.result()]

        self.assertEqual([r.returncode for r in results], [0, 0], [r.stdout for r in results])

    def checks(self, *commands, ok=True):
        args = ["checks", "--cwd", str(self.snapshot), "--head", self.head, "--log", str(self.log)]
        for command in commands:
            args += ["--cmd", command]
        return self.env.json(*args, ok=ok)

    def test_a_clean_passing_run_reports_an_unchanged_snapshot(self):
        result = self.checks("cat a.txt")

        self.assertTrue(result["ok"])
        self.assertEqual(result["changed"], [])
        self.assertEqual(git(self.snapshot, "status", "--porcelain"), "")

    def test_a_command_that_edits_a_tracked_file_fails_and_the_edit_is_kept(self):
        result = self.checks("printf 'changed\\n' > a.txt", ok=False)

        self.assertEqual([r["exit"] for r in result["results"]], [0])
        self.assertFalse(result["ok"])
        self.assertTrue(any("a.txt" in c for c in result["changed"]), result["changed"])
        self.assertEqual((self.snapshot / "a.txt").read_text(), "changed\n")  # not reset
        self.assertIn("a.txt", self.log.read_text())

    def test_a_command_that_leaves_an_untracked_file_fails(self):
        result = self.checks("echo out > build.log", ok=False)

        self.assertFalse(result["ok"])
        self.assertTrue(any("build.log" in c for c in result["changed"]), result["changed"])
        self.assertTrue((self.snapshot / "build.log").exists())

    def test_a_command_that_moves_head_fails(self):
        result = self.checks("git -c user.name=t -c user.email=t@t commit -q --allow-empty -m moved", ok=False)

        self.assertFalse(result["ok"])
        self.assertEqual(result["head"], self.head)
        self.assertTrue(any("HEAD" in c for c in result["changed"]), result["changed"])
        self.assertNotEqual(git(self.snapshot, "rev-parse", "HEAD"), self.head)  # not reset

    def test_a_snapshot_with_an_untracked_file_is_not_used(self):
        (self.snapshot / "extra.ts").write_text("export {}\n")

        result = self.env.run("checks", "--cwd", str(self.snapshot), "--head", self.head, "--log", str(self.log),
                              "--cmd", "true")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local changes", result.stderr)

    def test_a_snapshot_with_local_changes_is_not_moved(self):
        (self.snapshot / "README.md").write_text("edited\n")

        result = self.env.run("checks", "--cwd", str(self.snapshot), "--head", self.head, "--log", str(self.log),
                              "--cmd", "true")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local changes", result.stderr)
        self.assertNotEqual(git(self.snapshot, "rev-parse", "HEAD"), self.head)


class Transcribe(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.close)
        self.report = self.env.root / "r2.md"
        self.report.write_text("# report\n\nnotes\n\n## 独立复核记录 · 第2轮\nbody line\n\n### Spec\nV1\n\n"
                               "## 最终完整审查状态\nnot run\n")

    def test_the_section_is_posted_verbatim_under_an_attribution_line(self):
        result = self.env.json("transcribe", "--repo", "o/r", "--pr", "1", "--report", str(self.report),
                               "--start", "## 独立复核记录", "--end", "## 最终完整审查状态",
                               "--author", "Codex 审查者（router dispatch `d-1`）")

        posted = (self.env.gh_dir / "posted.md").read_text()
        self.assertEqual(result["url"], "https://github.com/o/r/pull/1#issuecomment-99")
        self.assertIn("\n> 总控转录：原作者为 Codex 审查者（router dispatch `d-1`）", posted)
        self.assertIn("## 独立复核记录 · 第2轮\nbody line\n\n### Spec\nV1", posted)
        self.assertNotIn("not run", posted)

    def transcribe(self, *extra, ok=True):
        return self.env.json("transcribe", "--repo", "o/r", "--pr", "1", "--report", str(self.report),
                             "--start", "## 独立复核记录", "--end", "## 最终完整审查状态", "--author", "x",
                             *extra, ok=ok)

    def thread(self):
        return json.loads((self.env.gh_dir / "thread.json").read_text())

    def test_a_first_post_carries_a_hidden_marker_and_is_not_existing(self):
        result = self.transcribe()

        self.assertFalse(result["existing"])
        self.assertRegex(self.thread()[0]["body"], r"^<!-- ctl:transcribe [0-9a-f]{16} -->\n> 总控转录")

    def test_a_rerun_returns_the_existing_comment_instead_of_posting_again(self):
        first = self.transcribe()
        again = self.transcribe()

        self.assertEqual(len(self.thread()), 1)
        self.assertEqual(again["url"], first["url"])
        self.assertTrue(again["existing"])

    def test_another_section_or_target_gets_another_marker(self):
        self.transcribe()
        self.env.json("transcribe", "--repo", "o/r", "--pr", "1", "--report", str(self.report),
                      "--start", "## 最终完整审查状态", "--author", "x")
        self.env.json("transcribe", "--repo", "o/r", "--issue", "2", "--report", str(self.report),
                      "--start", "## 独立复核记录", "--end", "## 最终完整审查状态", "--author", "x")

        markers = {c["body"].splitlines()[0] for c in self.thread()}
        self.assertEqual(len(markers), 3)

    def test_a_502_after_the_comment_was_created_counts_as_posted(self):
        (self.env.gh_dir / "post-502").touch()

        result = self.transcribe()

        self.assertEqual(result["url"], self.thread()[0]["html_url"])
        self.assertTrue(result["existing"])
        self.assertEqual(len(self.thread()), 1)

    def test_a_failed_post_that_left_no_comment_fails(self):
        (self.env.gh_dir / "post-fails").touch()

        result = self.env.run("transcribe", "--repo", "o/r", "--pr", "1", "--report", str(self.report),
                              "--start", "## 独立复核记录", "--author", "x")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("502", result.stderr)

    def set_thread(self, comments):
        (self.env.gh_dir / "thread.json").write_text(json.dumps(comments))

    def test_a_comment_quoting_the_marker_or_the_failure_log_is_not_the_transcript(self):
        (self.env.gh_dir / "post-fails").touch()
        failed = self.env.run("transcribe", "--repo", "o/r", "--pr", "1", "--report", str(self.report),
                              "--start", "## 独立复核记录", "--end", "## 最终完整审查状态", "--author", "x")
        marker = re.search(r"<!-- ctl:transcribe [0-9a-f]{16} -->", failed.stderr).group(0)
        # Pasted by the operator under the same gh account, and by someone else with the marker first.
        self.set_thread([
            {"html_url": "https://github.com/o/r/pull/1#issuecomment-7", "user": {"login": "ctl-bot"},
             "body": "transcribe failed:\n```\n" + failed.stderr + "```\n"},
            {"html_url": "https://github.com/o/r/pull/1#issuecomment-8", "user": {"login": "ctl-bot"},
             "body": marker + "\nsee the failure above"},
        ])

        again = self.env.run("transcribe", "--repo", "o/r", "--pr", "1", "--report", str(self.report),
                             "--start", "## 独立复核记录", "--end", "## 最终完整审查状态", "--author", "x")
        self.assertNotEqual(again.returncode, 0)

        (self.env.gh_dir / "post-fails").unlink()
        result = self.transcribe()
        self.assertFalse(result["existing"])
        self.assertEqual(len(self.thread()), 3)

    def test_an_edited_transcript_is_not_the_transcript(self):
        self.transcribe()
        thread = self.thread()
        thread[0]["body"] = thread[0]["body"].replace("V1", "V2")
        self.set_thread(thread)

        result = self.transcribe()

        self.assertFalse(result["existing"])
        self.assertEqual(len(self.thread()), 2)

    def test_a_transcript_by_another_account_is_not_the_transcript(self):
        self.transcribe()
        thread = self.thread()
        thread[0]["user"]["login"] = "someone-else"
        self.set_thread(thread)

        result = self.transcribe()

        self.assertFalse(result["existing"])
        self.assertEqual(len(self.thread()), 2)

    def test_a_502_does_not_count_a_quoted_marker_as_posted(self):
        self.transcribe()
        thread = self.thread()
        thread[0]["user"]["login"] = "someone-else"
        self.set_thread(thread)
        (self.env.gh_dir / "post-fails").touch()

        result = self.env.run("transcribe", "--repo", "o/r", "--pr", "1", "--report", str(self.report),
                              "--start", "## 独立复核记录", "--end", "## 最终完整审查状态", "--author", "x")

        self.assertNotEqual(result.returncode, 0)

    def test_crlf_line_endings_from_github_still_match(self):
        first = self.transcribe()
        thread = self.thread()
        thread[0]["body"] = thread[0]["body"].replace("\n", "\r\n")
        self.set_thread(thread)

        again = self.transcribe()

        self.assertTrue(again["existing"])
        self.assertEqual(again["url"], first["url"])

    def test_an_unreadable_thread_posts_nothing(self):
        (self.env.gh_dir / "list-fails").touch()

        result = self.env.run("transcribe", "--repo", "o/r", "--pr", "1", "--report", str(self.report),
                              "--start", "## 独立复核记录", "--author", "x")

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.env.gh_dir / "posted.md").exists())

    def test_a_missing_heading_posts_nothing(self):
        result = self.env.run("transcribe", "--repo", "o/r", "--pr", "1", "--report", str(self.report),
                              "--start", "## 独立审查记录 · 最终完整", "--author", "x")

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.env.gh_dir / "posted.md").exists())


class Label(unittest.TestCase):
    def setUp(self):
        self.env = Env()
        self.addCleanup(self.env.close)
        (self.env.gh_dir / "labels.json").write_text(json.dumps(["P1", "in-review"]))

    def test_the_lifecycle_label_is_switched_and_read_back(self):
        result = self.env.json("label", "--repo", "o/r", "--issue", "5", "--from", "in-review",
                               "--to", "changes-requested")

        self.assertEqual(sorted(result["labels"]), ["P1", "changes-requested"])
