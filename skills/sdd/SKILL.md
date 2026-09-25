---
name: sdd
description: タスク管理(SDD)。docs/tasks/ 配下でタスクの起票・要件定義、実装計画、進捗記録・引き継ぎ、検証・完了判定を承認ゲート付きで運用する。新しい作業依頼の起票時、タスクへの着手・再開時、進捗の記録時、完了処理時に使用する。
---

# SDD タスク管理

タスクを `docs/tasks/` 配下の文書で管理し、工程ごとにユーザー承認ゲートを設ける。
本ファイルには工程判定と常時規則のみを置く。各工程の詳細手順は該当する `references/` を**その工程の作業直前に読む**こと(先読みしない)。

本ファイルおよび `references/` 内の `references/…` `scripts/…` は、本 SKILL.md が置かれたスキルディレクトリからの相対パスを指す(配置先のハーネスに依存しない)。

## 文書構成

- `docs/tasks/_config.md` — プロジェクト固有設定(恒久仕様書のパス・形式、検証系統、リリース運用)。無ければ初回セットアップ、有っても起票時に必須項目を検証(references/01-intake.md §0)
- `docs/tasks/BACKLOG.md` — 索引。表は scripts/backlog.py で自動生成し**手編集しない**。「着手順方針」「廃番」(票ファイルを持たない欠番 ID のみ)節のみ手書き
- 中・大規模タスク: `docs/tasks/T-NNN_件名/` に spec.md(要件)+plan.md(計画)+log.md(経過)
- 小規模タスク: `docs/tasks/T-NNN_件名.md` 1枚
- 併設資料(要件定義の別紙・調査メモ等)はタスクディレクトリ内に置く。`docs/tasks/` 直下への平置きは禁止(索引が誤認する)。小規模票で併設資料が必要になった時点で中規模へ昇格する
- 完了・廃番後: `docs/tasks/archive/` へ移動。アーカイブ済みの票は履歴として変更しない。再発・再開は新 ID で起票し、目的・背景に旧 ID を参照する

frontmatter の値域:
- `scale`: small / medium / large
- `status`: todo / doing / blocked / done / dropped
- `priority`: high / mid / low
- `approvals`: spec / plan(small には無い)/ done に承認日を記録する。未承認は null
- 値に ` #` を含む場合(例: 件名 `Issue #12 修正`)は引用符で囲む。囲まない場合、` #` 以降は YAML と同じくコメントとして扱われる

役割分担(1つの事実は1ファイルにだけ):
仕様の正=恒久仕様書 / 要件の一時的な正=spec.md / 実装詳細(ファイル名・関数名)=plan.md のみ / 経過・検証結果=log.md のみ。
承認事実や検証消化が frontmatter・plan.md のチェック欄(現在状態)と log.md(履歴)の両方に現れるのは、状態と履歴の役割分担であり本規則に反する重複ではない。

## 工程判定

対象タスクの frontmatter(approvals・status)を確認し、該当工程の reference を読んでから作業する。

| 状況 | 工程 | 読む reference |
|---|---|---|
| 新規依頼で票が存在しない、または approvals.spec が null | 起票・要件定義 | references/01-intake.md |
| approvals.spec 済みで approvals.plan が null(小規模を除く) | 実装計画 | references/02-plan.md |
| 承認済みで実装・検証中(status: todo / doing / blocked) | 実装・進捗 | references/03-work.md |
| 受入条件・検証を満たし完了処理へ進むとき、または廃番 | 検証・完了判定 | references/04-done.md |

## 常時規則

1. **承認ゲート**: G1(起票=規模・確定要件・受入条件)、G2(計画)、G3(完了=検証消化・仕様書反映)。各ゲートでユーザー承認を得て frontmatter の `approvals` に承認日を記録してから次工程へ進む。工程開始時は前工程の承認日を検証し、無ければ停止してユーザーに確認する。承認日はユーザーの承認発言があった場合のみ記録し、エージェントの自己判断で書いてはならない。
2. **工程境界**: ユーザーの依頼が実装まで含んでいても、G1・G2 の承認前に次工程の成果物を作らない。承認待ちで停止する。
3. **検証の区別**: 検証方法は「エージェント実施」と「実環境・ユーザー実施」を必ず区別する。後者が未了の間は status を done にしない(blocked 止まり)。
4. **索引の再生成**: frontmatter を変更したら `python3 <スキルディレクトリ>/scripts/backlog.py docs/tasks` を実行して BACKLOG.md を再生成する(`python3` が無い、または Microsoft Store のスタブに解決される Windows 環境では `py -3` または `python` で代替する)。ブランチ間で競合したら手で解消せず再実行して生成し直す。形式外ファイルの警告が出たら扱いをユーザーに確認して解消する(references/01-intake.md §0)。
5. **記録の正と main 同期**: セッションをまたぐ引き継ぎ・コンテキスト圧縮後は、自分の記憶より log.md(引き継ぎサマリ)と git log を正とする。タスク文書を実装ブランチに同梱する運用(`_config.md` リリース運用)では、当該タスクの作業ブランチ上の票を正とし、main 側の票は同期時点のスナップショットとする。状態変化(G1/G2/G3 承認・status 変更)が作業ブランチ上で生じたら、その都度 main へ同期する(手順は references/03-work.md §5。粒度を変える場合は `_config.md` に記載)。
6. **規模の昇格**: 作業中に設計判断や未確定点が現れたら規模を一段上げ、該当ゲートへ差し戻す(references/03-work.md §3)。降格はしない。
7. **ID**: 採番は archive・廃番を含む最大値+1。ID は再利用しない。
