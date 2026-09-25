#!/usr/bin/env python3
"""docs/tasks/ 配下の各票の frontmatter を集計し、BACKLOG.md の索引表を再生成する。

使い方: python3 backlog.py [docs/tasks へのパス](省略時: ./docs/tasks)

- 索引表はマーカー行の間のみを書き換える。「着手順方針」「廃番」などの手書き節には触れない。
- BACKLOG.md が無ければ雛形ごと新規作成する。
- 終了時に次の採番候補(archive・BACKLOG 記載の廃番を含む最大 ID+1)を表示する。
"""
import re
import sys
from pathlib import Path

MARK_S = "<!-- backlog:auto:start -->"
MARK_E = "<!-- backlog:auto:end -->"

DEFAULT_BACKLOG = f"""# タスクバックログ

タスク一覧の索引。次の表は backlog.py により自動生成される(手編集しない)。詳細は各票を参照。

{MARK_S}
{MARK_E}

## 着手順方針
<!-- 手書き節。日付付きで方針を記録する -->

## 廃番
<!-- 手書き節。票ファイルを持たない欠番 ID と理由を記録する(廃番タスクの票は archive/ に置き、ここには書かない)。ID は再利用しない -->
"""


def parse_frontmatter(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fm = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            # YAML と同じく引用符内の " #" はコメントとして扱わない
            q = re.match(r"""^(["'])(.*)\1(\s+#.*)?$""", m.group(2).strip())
            fm[m.group(1)] = q.group(2) if q else m.group(2).split(" #")[0].strip()
    return fm


def id_num(id_str):
    m = re.search(r"(\d+)", id_str)
    return int(m.group(1)) if m else 0


def make_row(source_path, entry_name, link):
    fm = parse_frontmatter(source_path)
    parts = entry_name.split("_", 1)
    return {
        "id": fm.get("id", parts[0]),
        "title": fm.get("title", parts[-1]),
        "scale": fm.get("scale", "-"),
        "status": fm.get("status", "-"),
        "priority": fm.get("priority", "-"),
        "updated": fm.get("updated", "-"),
        "link": link,
    }


def collect(dir_path, link_prefix=""):
    rows = []
    if not dir_path.is_dir():
        return rows
    for p in sorted(dir_path.iterdir()):
        if p.name == "archive" or p.name.startswith("_"):
            continue
        if p.is_dir() and re.match(r"T-\d+", p.name):
            if not (p / "spec.md").exists():
                print(f"警告: {p} に spec.md が無いため索引から除外しました", file=sys.stderr)
                continue
            if "id" not in parse_frontmatter(p / "spec.md"):
                print(
                    f"警告: {p}/spec.md の frontmatter に id が無いため、ディレクトリ名の ID で索引に載せました",
                    file=sys.stderr,
                )
            rows.append(make_row(p / "spec.md", p.name, f"{link_prefix}{p.name}/spec.md"))
        elif p.is_dir():
            if not p.name.startswith("."):
                print(
                    f"警告: {p} は票の命名(T-NNN)に合致しないため索引から除外しました。"
                    "票へ移行するか docs/tasks/ 外へ移動してください",
                    file=sys.stderr,
                )
        elif p.is_file() and p.suffix == ".md":
            if not re.match(r"T-\d+", p.name):
                # BACKLOG.md 以外の T- 命名でない .md は管理対象外(旧形式・誤配置)
                if p.name != "BACKLOG.md":
                    print(
                        f"警告: {p} は票の命名(T-NNN)に合致しないため索引から除外しました。"
                        "票へ移行するか docs/tasks/ 外へ移動してください",
                        file=sys.stderr,
                    )
                continue
            # frontmatter に id を持たないファイルは票ではない(併設資料の誤配置)
            if "id" not in parse_frontmatter(p):
                print(
                    f"警告: {p} は frontmatter に id が無いため索引から除外しました。"
                    "併設資料はタスクディレクトリ内に置いてください",
                    file=sys.stderr,
                )
                continue
            rows.append(make_row(p, p.stem, f"{link_prefix}{p.name}"))
    rows.sort(key=lambda r: id_num(r["id"]))
    seen = set()
    for r in rows:
        if r["id"] in seen:
            print(f"警告: ID {r['id']} が重複しています({r['link']})", file=sys.stderr)
        seen.add(r["id"])
    return rows


def cell(text):
    return text.replace("|", "\\|")


def render(rows, archived):
    out = [MARK_S, ""]
    out.append("| ID | 件名 | 規模 | 状態 | 優先度 | 更新日 | 票 |")
    out.append("|----|------|------|------|--------|--------|----|")
    if rows:
        for r in rows:
            out.append(
                f"| {r['id']} | {cell(r['title'])} | {r['scale']} | {r['status']} "
                f"| {r['priority']} | {r['updated']} | [{r['id']}]({r['link']}) |"
            )
    else:
        out.append("| - | (タスクなし) | - | - | - | - | - |")
    if archived:
        out += ["", "### アーカイブ済み", "", "| ID | 件名 | 状態 |", "|----|------|------|"]
        for r in archived:
            out.append(f"| {r['id']} | {cell(r['title'])} | {r['status']} |")
    out += ["", MARK_E]
    return "\n".join(out)


def main():
    tasks_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/tasks")
    if not tasks_dir.is_dir():
        print(f"エラー: {tasks_dir} が存在しません", file=sys.stderr)
        return 1

    rows = collect(tasks_dir)
    archived = collect(tasks_dir / "archive", link_prefix="archive/")
    for dup in sorted({r["id"] for r in rows} & {r["id"] for r in archived}):
        print(f"警告: ID {dup} が現役票とアーカイブで重複しています", file=sys.stderr)

    backlog = tasks_dir / "BACKLOG.md"
    text = backlog.read_text(encoding="utf-8") if backlog.exists() else DEFAULT_BACKLOG
    if MARK_S not in text or MARK_E not in text:
        print(
            f"エラー: {backlog} にマーカー行({MARK_S} / {MARK_E})がありません。"
            "手書き節を保持したままマーカーを追記してから再実行してください",
            file=sys.stderr,
        )
        return 1

    block = render(rows, archived)
    pattern = re.escape(MARK_S) + r".*?" + re.escape(MARK_E)
    new_text = re.sub(pattern, lambda _: block, text, count=1, flags=re.DOTALL)
    backlog.write_text(new_text, encoding="utf-8")

    all_ids = [id_num(r["id"]) for r in rows + archived]
    all_ids += [int(n) for n in re.findall(r"\bT-(\d+)", new_text)]
    next_id = max(all_ids, default=0) + 1
    print(f"BACKLOG.md を更新しました(現役 {len(rows)} 件・アーカイブ {len(archived)} 件)")
    print(f"次の採番候補: T-{next_id:03d}(BACKLOG.md の廃番節も確認のこと)")
    return 0


if __name__ == "__main__":
    # Windows ではパイプ出力の既定がロケール(cp932)となり、呼び出し側で文字化けするため固定する
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
