#!/usr/bin/env python3
"""backlog.py のテスト。

使い方: python3 test_backlog.py
"""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import backlog


def write_ticket(path, body="# 本文", **fm):
    """frontmatter 付きの票ファイルを書く。"""
    lines = ["---"]
    lines += [f"{k}: {v}" for k, v in fm.items()]
    lines += ["---", body]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class ParseFrontmatterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_基本(self):
        p = self.dir / "t.md"
        write_ticket(p, id="T-001", title="件名", status="todo")
        fm = backlog.parse_frontmatter(p)
        self.assertEqual(fm["id"], "T-001")
        self.assertEqual(fm["title"], "件名")
        self.assertEqual(fm["status"], "todo")

    def test_frontmatterなし(self):
        p = self.dir / "t.md"
        p.write_text("# 見出しのみ\n", encoding="utf-8")
        self.assertEqual(backlog.parse_frontmatter(p), {})

    def test_行内コメント除去(self):
        p = self.dir / "t.md"
        write_ticket(p, id="T-001", status="todo # 着手前")
        self.assertEqual(backlog.parse_frontmatter(p)["status"], "todo")

    def test_引用符付き値は内部の行内コメント記号を保持(self):
        p = self.dir / "t.md"
        write_ticket(p, id="T-001", title='"Issue #12 修正" # 備考', memo="'a # b'")
        fm = backlog.parse_frontmatter(p)
        self.assertEqual(fm["title"], "Issue #12 修正")
        self.assertEqual(fm["memo"], "a # b")

    def test_ネストキーは拾わない(self):
        p = self.dir / "t.md"
        p.write_text(
            "---\nid: T-001\napprovals:\n  spec: 2026-08-21\n---\n",
            encoding="utf-8",
        )
        fm = backlog.parse_frontmatter(p)
        self.assertEqual(fm["id"], "T-001")
        self.assertNotIn("spec", fm)


class CollectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tasks = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.stderr = io.StringIO()

    def collect(self, **kwargs):
        with contextlib.redirect_stderr(self.stderr):
            return backlog.collect(self.tasks, **kwargs)

    def test_票の収集と除外(self):
        # 収集対象: 単票 + ディレクトリ票
        write_ticket(self.tasks / "T-001_単票.md", id="T-001", title="単票", status="todo")
        d = self.tasks / "T-002_dir"
        d.mkdir()
        write_ticket(d / "spec.md", id="T-002", title="ディレクトリ票", status="doing")
        # 除外対象: _config.md(無警告)/ spec.md 欠落ディレクトリ / 非 T-NNN 命名 / id なし
        (self.tasks / "_config.md").write_text("# 設定\n", encoding="utf-8")
        (self.tasks / "T-003_empty").mkdir()
        (self.tasks / "memo.md").write_text("# メモ\n", encoding="utf-8")
        write_ticket(self.tasks / "T-004_idなし.md", title="idなし")

        rows = self.collect()
        self.assertEqual([r["id"] for r in rows], ["T-001", "T-002"])
        self.assertEqual(rows[1]["link"], "T-002_dir/spec.md")
        err = self.stderr.getvalue()
        self.assertIn("T-003_empty", err)
        self.assertIn("memo.md", err)
        self.assertIn("T-004_idなし.md", err)
        self.assertNotIn("_config.md", err)

    def test_ID重複警告(self):
        write_ticket(self.tasks / "T-001_a.md", id="T-001", title="a", status="todo")
        write_ticket(self.tasks / "T-001_b.md", id="T-001", title="b", status="todo")
        self.collect()
        self.assertIn("重複", self.stderr.getvalue())

    def test_ディレクトリ票のid欠落は警告して索引に載せる(self):
        d = self.tasks / "T-003_dir"
        d.mkdir()
        write_ticket(d / "spec.md", title="idなし", status="todo")
        rows = self.collect()
        self.assertEqual([r["id"] for r in rows], ["T-003"])
        self.assertIn("T-003_dir", self.stderr.getvalue())

    def test_命名外ディレクトリは警告(self):
        (self.tasks / "notes").mkdir()
        (self.tasks / "archive").mkdir()
        (self.tasks / "_tmp").mkdir()
        self.collect()
        err = self.stderr.getvalue()
        self.assertIn("notes", err)
        self.assertNotIn("archive", err)
        self.assertNotIn("_tmp", err)

    def test_link_prefix(self):
        arch = self.tasks / "archive"
        arch.mkdir()
        write_ticket(arch / "T-001_旧.md", id="T-001", title="旧", status="done")
        with contextlib.redirect_stderr(self.stderr):
            rows = backlog.collect(arch, link_prefix="archive/")
        self.assertEqual(rows[0]["link"], "archive/T-001_旧.md")


class RenderTest(unittest.TestCase):
    def test_タスクなしの空行(self):
        text = backlog.render([], [])
        self.assertIn("(タスクなし)", text)

    def test_アーカイブ表に状態列(self):
        archived = [
            {"id": "T-001", "title": "完了分", "scale": "small", "status": "done",
             "priority": "mid", "updated": "2026-08-21", "link": "archive/T-001_x.md"},
            {"id": "T-002", "title": "廃番分", "scale": "small", "status": "dropped",
             "priority": "mid", "updated": "2026-08-21", "link": "archive/T-002_y.md"},
        ]
        text = backlog.render([], archived)
        self.assertIn("| ID | 件名 | 状態 |", text)
        self.assertIn("| T-001 | 完了分 | done |", text)
        self.assertIn("| T-002 | 廃番分 | dropped |", text)

    def test_件名のパイプをエスケープ(self):
        row = {"id": "T-001", "title": "a|b", "scale": "small", "status": "todo",
               "priority": "mid", "updated": "2026-09-25", "link": "T-001_x.md"}
        text = backlog.render([row], [dict(row, status="done")])
        self.assertNotIn("a|b", text)
        self.assertEqual(text.count("a\\|b"), 2)


class MainTest(unittest.TestCase):
    """スクリプト実行での end-to-end 検証。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tasks = Path(self.tmp.name) / "docs" / "tasks"
        self.tasks.mkdir(parents=True)
        self.addCleanup(self.tmp.cleanup)

    def run_script(self):
        return subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "backlog.py"), str(self.tasks)],
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_初期生成と手書き節の保持(self):
        write_ticket(self.tasks / "T-001_a.md", id="T-001", title="a", status="todo")
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        backlog_md = self.tasks / "BACKLOG.md"
        text = backlog_md.read_text(encoding="utf-8")
        self.assertIn("| T-001 |", text)
        self.assertIn("## 着手順方針", text)

        # 手書き節へ追記後に再生成しても保持される
        backlog_md.write_text(
            text.replace("## 着手順方針", "## 着手順方針\n- 2026-08-21: T-001 を優先。"),
            encoding="utf-8",
        )
        write_ticket(self.tasks / "T-002_b.md", id="T-002", title="b", status="todo")
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        text = backlog_md.read_text(encoding="utf-8")
        self.assertIn("- 2026-08-21: T-001 を優先。", text)
        self.assertIn("| T-002 |", text)

    def test_採番候補はアーカイブと廃番を含む(self):
        write_ticket(self.tasks / "T-001_a.md", id="T-001", title="a", status="todo")
        arch = self.tasks / "archive"
        arch.mkdir()
        write_ticket(arch / "T-005_旧.md", id="T-005", title="旧", status="done")
        result = self.run_script()
        self.assertIn("T-006", result.stdout)

        # 廃番節(手書き)の記載 ID も考慮される
        backlog_md = self.tasks / "BACKLOG.md"
        text = backlog_md.read_text(encoding="utf-8")
        backlog_md.write_text(text + "- T-009: 方針変更のため廃番。\n", encoding="utf-8")
        result = self.run_script()
        self.assertIn("T-010", result.stdout)

    def test_マーカー欠落はエラー(self):
        (self.tasks / "BACKLOG.md").write_text("# 索引(マーカーなし)\n", encoding="utf-8")
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("マーカー", result.stderr)

    def test_現役とアーカイブのID重複を警告(self):
        write_ticket(self.tasks / "T-001_a.md", id="T-001", title="a", status="todo")
        arch = self.tasks / "archive"
        arch.mkdir()
        write_ticket(arch / "T-001_旧.md", id="T-001", title="旧", status="done")
        result = self.run_script()
        self.assertEqual(result.returncode, 0)
        self.assertIn("T-001", result.stderr)
        self.assertIn("重複", result.stderr)

    def test_出力はロケールに依存せずUTF8(self):
        # Windows ではパイプ出力の既定が cp932 となり、呼び出し側のエージェントで文字化けする
        env = {**os.environ, "PYTHONIOENCODING": "cp932"}
        script = [sys.executable, str(SCRIPT_DIR / "backlog.py")]
        result = subprocess.run(script + [str(self.tasks)], capture_output=True, env=env)
        self.assertIn("次の採番候補".encode("utf-8"), result.stdout)
        result = subprocess.run(script + [str(self.tasks / "なし")], capture_output=True, env=env)
        self.assertIn("エラー".encode("utf-8"), result.stderr)


if __name__ == "__main__":
    unittest.main()
