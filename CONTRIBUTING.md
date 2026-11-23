# チームでの進め方

## 基本の流れ

1. 作業前に main を最新にする
   ```
   git switch main
   git pull
   ```
2. 作業用のブランチを作る
   ```
   git switch -c feature/やることの名前
   ```
3. 変更してコミットする（小さく、こまめに）
   ```
   git add -A
   git commit -m "何をしたかを一文で"
   ```
4. GitHub に送って Pull Request（PR）を出す
   ```
   git push -u origin feature/やることの名前
   ```
5. 他のメンバー 1 人に見てもらってから main にマージする
6. マージしたブランチは消す

## ルール

- **main に直接 push しない。** main は「いつでも `python run.py` で動く」状態を保つ
- ブランチ名は `feature/〇〇`（機能追加）、`fix/〇〇`（修正）、`docs/〇〇`（文書だけ）
- PR は小さく出す。1 週間分をまとめない
- 自分の担当フォルダ以外を変えるときは、担当者に一声かける

## 担当フォルダ

| フォルダ | 内容 | 担当 |
|---|---|---|
| `body/` | 本体（登録・検索・保存・ESP32 への命令） | （名前を書く） |
| `vision/` | 画像処理（カメラ・肩幅・顔） | （名前を書く） |
| `esp32/` | ESP32 のスケッチ | （名前を書く） |
| `tools/` | 開発用の道具 | 全員 |

担当が分かれているので、同じファイルを同時に触ることは少ないはずです。

## 変えるときに全員の合意がいるもの

- **`PROTOCOL.md`**（画像処理と本体の約束）。変えると両方の担当に影響する
- **ラズパイ ↔ ESP32 の命令**（`PING` / `GET` / `PUT`）。`body/machine.py` と `esp32/` の両方を直す必要がある
- **`HANGER_COUNT`**。`body/config.py` と ESP32 のスケッチで同じ値にする

## コミットしてはいけないもの

`.gitignore` で除外してありますが、念のため。

- `body/data/`（登録した人の名前と顔のデータ。個人情報）
- モデルファイル（`*.onnx`、`*.pt`）。各自ダウンロードして `vision/models/` に置く
- パスワードやキー

## 自分の PC だけで設定を変えたいとき

`body/config.py` の `VISION_FILE` や `MACHINE_MODE` を手元で切り替えたら、その変更は**コミットしない**でください。main では「仮の画像処理 + 表示のみ」を初期値にしておきます（誰の PC でもすぐ動くように）。

## PR を出す前の確認

```
python run.py                                   ← 起動して list / quit が通る
python tools/check_vision.py vision/vision.py   ← 画像処理を変えたとき
```
