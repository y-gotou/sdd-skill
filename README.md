# sdd-skill

Claude Code / Codex 向けの、承認ゲート付きタスク管理スキルです。
プロジェクトの `docs/tasks/` 配下にタスク文書を置き、起票・計画・実装・完了の各工程でユーザーの承認を得ながら進めます。

## 特徴

- **承認ゲート**: G1(起票=規模・要件・受入条件)、G2(実装計画)、G3(完了=検証消化・仕様書反映)。承認日を票の frontmatter に記録し、次工程の開始時に検証する。
- **規模に応じた文書**: 小規模は1ファイル票、中・大規模は spec.md(要件)・plan.md(計画)・log.md(経過)に分ける。
- **役割分担**: 1つの事実は1ファイルにだけ書く(仕様の正=恒久仕様書、実装詳細=plan.md、経過・検証結果=log.md)。
- **引き継ぎ**: log.md の引き継ぎサマリを常に最新化し、別セッションが途中から再開できるようにする。
- **索引の自動生成**: 各票の frontmatter から BACKLOG.md の索引表を `scripts/backlog.py` で生成する。
- **プロジェクト固有設定**: 恒久仕様書の場所、検証手段、ブランチ・リリース運用を `docs/tasks/_config.md` に記載する(初回に対話で作成)。

## 前提

- git
- Python 3(標準ライブラリのみ使用)。Windows で `python3` が使えない場合は `py -3` または `python` で代替する。

## 導入

### Claude Code(プラグイン)

```
/plugin marketplace add y-gotou/sdd-skill
/plugin install sdd@sdd-skill
```

呼び出し名は `/sdd:sdd` です。

### Claude Code(スキルとして直接配置)

```sh
git clone https://github.com/y-gotou/sdd-skill.git
ln -s "$PWD/sdd-skill/skills/sdd" ~/.claude/skills/sdd
```

呼び出し名は `/sdd` です。シンボリックリンクの代わりに `skills/sdd` をコピーしても動作します。

### Codex(プラグイン)

```sh
codex plugin marketplace add y-gotou/sdd-skill
codex plugin add sdd@sdd-skill
```

Codex アプリではプラグイン一覧から `SDD タスク管理` をインストールできます。既存の Claude Code 用プラグインと同じ `skills/sdd` を使用します。

ワークスペース全体に配布する場合は、管理者が「Workspace settings > Plugins > Add > Import marketplace」で Source に `https://github.com/y-gotou/sdd-skill` を指定します。Path は空欄にし、インポート後に対象ロールの Installation policy を設定してください。

### Codex(スキルとして直接配置)

```sh
ln -s "$PWD/sdd-skill/skills/sdd" ~/.codex/skills/sdd
```

## 使い方

作業を依頼する際にスキルを呼び出すか、「タスクとして起票して」のように依頼します。エージェントは票の状態から現在の工程を判定し、該当する手順(`references/`)に従って進めます。

初回は `docs/tasks/_config.md` が無いため、恒久仕様書・検証手段・リリース運用をヒアリングして作成します。

作成される文書の例:

```
docs/tasks/
├── _config.md              # プロジェクト固有設定
├── BACKLOG.md              # 索引(表は自動生成)
├── T-001_login-fix.md      # 小規模タスク
├── T-002_export/           # 中・大規模タスク
│   ├── spec.md
│   ├── plan.md
│   └── log.md
└── archive/                # 完了・廃番タスク
```

## 構成

```
skills/sdd/
├── SKILL.md          # 工程判定と常時規則
├── references/       # 工程別の詳細手順とテンプレート
└── scripts/
    ├── backlog.py    # BACKLOG.md 索引の再生成
    └── test_backlog.py
```

テストは `python3 skills/sdd/scripts/test_backlog.py` で実行します。

## ライセンス

MIT
