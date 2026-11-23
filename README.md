# ハンガー管理システム

カメラの前に立つと、肩幅と顔を測ってハンガーを割り当てます。あとから名前か顔で、その人のハンガーを機械が取り出します。
ハンガーには重さを測るしくみも付け、服が乾いたかどうかを判定する予定です。

## 全体の形

```
           ラズパイ5（python3 run.py で 1 つのプログラムとして動く）
 ┌────────────────────────────────────────────────┐
 │  画像処理 vision/            本体 body/            │                  ESP32（無印）1 台
 │  ┌────────────────┐       ┌────────────────┐   │   Bluetooth     ┌──────────────────┐
 │  │ measure(        │ ◀呼ぶ─ │ 登録・検索・保存 │   │   Classic       │ 命令の受け取り   │
 │  │  want_shoulder, │       │ 機械への命令    │ ──GET:3──────────▶ │ モーター         │
 │  │  known)         │ ─dict▶ │                │ ◀─OK:GET:3─────── │ 重量計測・乾燥判定│
 │  └────────────────┘       └────────────────┘   │                  └──────────────────┘
 │   カメラ・肩幅・顔の照合                             │
 └────────────────────────────────────────────────┘
```

- 画像処理と本体は、同じラズパイの同じプログラムの中で動きます。サーバーは使いません
- 画像処理と本体の約束は、`measure` 関数 1 つと、やりとりする dict の形だけです（[PROTOCOL.md](PROTOCOL.md)）
- ラズパイと ESP32 の約束は、`PING` / `GET` / `PUT` の短い命令だけです（[docs/esp32-commands.md](docs/esp32-commands.md)）

## まず動かす（カメラも ESP32 もなしで試せる）

```
git clone https://github.com/NUMAyu-stu/Hanger-system-forAll.git
cd Hanger-system-forAll
python run.py
```

最初は仮の画像処理（`tools/fake_vision.py`）と、画面に表示するだけの機械（`MACHINE_MODE = "print"`）になっているので、追加のライブラリなしで Windows でも動きます。
`reg 田中` と打つと「カメラの前にいる人の名前」を聞いてくるので、名前を入れて試します。ほかに `get` / `face` / `del` / `list` / `quit` が使えます。

---

## ファイル構造

```
Hanger-system-forAll/
├─ README.md              ← この案内
├─ CONTRIBUTING.md        ← チームでの進め方（ブランチ・PR・担当・守ること）
├─ PROTOCOL.md            ← 画像処理と本体の約束（measure 関数）
├─ FLOW.md                ← 処理の流れ（図）
├─ run.py                 ← 起動用（python3 run.py）
│
├─ body/                  ← 本体（ラズパイ）
│   ├─ main.py            コマンド（reg / get / face / del / list / quit）
│   ├─ config.py          設定（ハンガー数・保存先・どの画像処理を使うか・機械のつなぎ方）
│   ├─ store.py           登録・検索・保存（顔のデータは中身を見ずに預かるだけ）
│   ├─ vision_client.py   画像処理のファイルを読み込み、measure を呼ぶ窓口
│   ├─ machine.py         ESP32 へ命令を送る（切れたら自動でつなぎ直す）
│   ├─ requirements.txt   必要なライブラリ（pyserial）
│   └─ data/              登録データ（自動でできる。個人情報なので Git には入れない）
│
├─ vision/                ← 画像処理（ラズパイ）。中身は自由に作り替えてよい
│   ├─ vision.py          本物の見本（YOLO で肩、YuNet + SFace で顔）
│   ├─ models/            モデルファイルを置く（各自で用意。Git には入れない）
│   └─ requirements.txt   必要なライブラリ（numpy / opencv-python / ultralytics）
│
├─ esp32/                 ← ハンガー側の ESP32 1 台
│   ├─ hanger_esp32/      本番用。このフォルダ全体を 1 つのプログラムとして書き込む
│   │   ├─ hanger_esp32.ino   全体の setup / loop。各担当の関数を呼ぶだけ
│   │   ├─ pins.h             使うピンの一覧（GPIO4・5 は重量計測用）
│   │   ├─ bt_command.cpp/.h  ラズパイからの命令を受けて返事をする
│   │   ├─ motor.cpp/.h       ハンガーを動かす（今は LED で代用）
│   │   └─ weight.cpp/.h      重さを測って乾燥を判定する（まだ空）
│   └─ tests/             部品を 1 つずつ試すための別のスケッチ
│       └─ drying_motor_test/   乾燥完了と仮定して、モーターを 1 回だけ動かす
│
├─ tools/                 ← 開発用の道具（Python 標準ライブラリだけで動く）
│   ├─ fake_vision.py     仮の画像処理（カメラなしで本体を試す）
│   ├─ check_vision.py    画像処理が PROTOCOL.md どおりか確かめる
│   └─ bt_test.py         ラズパイ ⇔ ESP32 の通信だけを手で試す
│
└─ docs/                  ← 詳しい手順と決まりごと
    ├─ setup-raspi.md     ラズパイ5の準備（ライブラリ・モデル・カメラの校正）
    ├─ setup-esp32.md     ESP32 の準備（書き込み・ペアリング・通信の確認）
    ├─ esp32-commands.md  ラズパイ ⇔ ESP32 の命令の決まり
    └─ history.md         前の版からの変更
```

---

## 担当ごとに見るところ

### 本体担当

| 主に触るファイル | `body/` の全部、`esp32/hanger_esp32/bt_command.cpp/.h` |
|---|---|
| まず読む | [PROTOCOL.md](PROTOCOL.md)、[FLOW.md](FLOW.md)、[docs/esp32-commands.md](docs/esp32-commands.md) |
| 試し方 | `python run.py`（仮の画像処理で動く） |

- 画像処理の中身には触りません。使うのは `measure` 関数だけです
- 顔のデータ（`face`）は中身を見ずに保存するだけです

### 画像処理担当

| 主に触るファイル | `vision/` の全部 |
|---|---|
| まず読む | [PROTOCOL.md](PROTOCOL.md)、[docs/setup-raspi.md](docs/setup-raspi.md) |
| 試し方 | `python3 vision/vision.py`、`python3 tools/check_vision.py vision/vision.py` |

- 本体のファイルは import しません。PROTOCOL.md の約束さえ守れば、中身は自由に作り替えてかまいません

### モーター担当

| 主に触るファイル | `esp32/hanger_esp32/motor.cpp/.h`、`pins.h`（自分のピンを書き足す） |
|---|---|
| まず読む | [docs/setup-esp32.md](docs/setup-esp32.md)、[docs/esp32-commands.md](docs/esp32-commands.md) |
| 試し方 | `esp32/tests/drying_motor_test/` で単体で動かし、動いたら `motor.cpp` に移す |

- `motorGet(番号)` と `motorPut(番号, 肩幅)` の中身を、LED からモーターに置き換えます
- GPIO4・GPIO5 は重量計測で使うので、使いません

### 重量計測担当

| 主に触るファイル | `esp32/hanger_esp32/weight.cpp/.h`、`pins.h`（GPIO4・5 を書く） |
|---|---|
| まず読む | [docs/setup-esp32.md](docs/setup-esp32.md) |
| 試し方 | `esp32/tests/` に自分用のスケッチを作って単体で動かし、動いたら `weight.cpp` に移す |

- 乾燥が完了したら `weightDryingComplete()` が `true` を返すようにします
- 乾燥完了をラズパイに知らせる命令はまだありません。作るときはチームで決めます

---

## 知りたいこと別に見るところ

| 知りたいこと | 見るところ |
|---|---|
| チームでの作業の進め方（ブランチ・PR） | [CONTRIBUTING.md](CONTRIBUTING.md) |
| ほかの人と同時に作業するときの決まり・コンフリクトの直し方 | [CONTRIBUTING.md](CONTRIBUTING.md) の「並行して作業するとき」 |
| PR を出す前に確かめること | [CONTRIBUTING.md](CONTRIBUTING.md) の「PR を出す前の確認」 |
| 誰がどのファイルの担当か | [CONTRIBUTING.md](CONTRIBUTING.md) の「担当」 |
| `reg` や `face` を打ったとき、何がどの順で動くか | [FLOW.md](FLOW.md) |
| 画像処理が何を受け取り、何を返せばいいか | [PROTOCOL.md](PROTOCOL.md) |
| ラズパイから ESP32 に送る命令と返事 | [docs/esp32-commands.md](docs/esp32-commands.md) |
| ESP32 のどのピンが空いているか | `esp32/hanger_esp32/pins.h` |
| ハンガーの数を変えたい | `body/config.py` と `esp32/hanger_esp32/bt_command.h` の `HANGER_COUNT`（両方同じ値に。全員で相談） |
| 仮の画像処理 ⇔ 本物を切り替えたい | `body/config.py` の `VISION_FILE`（手元だけで変え、コミットしない） |
| 機械なし ⇔ ESP32 につなぐを切り替えたい | `body/config.py` の `MACHINE_MODE`（手元だけで変え、コミットしない） |
| 肩幅が正しく出ない | [docs/setup-raspi.md](docs/setup-raspi.md) の「画像処理を確かめる」（校正） |
| 測定が遅い・時間切れになる | [docs/setup-raspi.md](docs/setup-raspi.md) の「YOLO を速くする」 |
| ESP32 につながらない | [docs/setup-esp32.md](docs/setup-esp32.md) の「本体から使う」の表 |
| ESP32 に書き込む方法 | [docs/setup-esp32.md](docs/setup-esp32.md) の「スケッチを書き込む」 |
| 登録データがどこにあるか | `body/data/people.json`（個人情報。Git には入れない） |

---

## 今の状態

| 部分 | 状態 |
|---|---|
| 本体（`body/`） | 6 つのコマンドが動く。仮の画像処理と「表示だけの機械」で動作確認済み |
| 画像処理（`vision/`） | 見本はある。ラズパイ実機・カメラでの確認はまだ。肩幅の換算値（`CM_PER_PX`）は仮 |
| ESP32 の命令の受け取り | できている。実機での確認はまだ |
| モーター | まだ。今は LED で代用 |
| 重量計測・乾燥判定 | まだ（担当者が作成中） |
| 乾燥完了をラズパイに知らせる | まだ決まっていない |
