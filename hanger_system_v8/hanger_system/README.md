# ハンガー管理システム（第3版：ラズパイ5 1台・1つのプログラム）

## 全体の形

```
          ラズパイ5（python3 run.py で 1 つのプログラムとして動く）
 ┌──────────────────────────────────────────────────────┐
 │  画像処理 vision/vision.py     本体 body/              │
 │  ┌─────────────────┐        ┌─────────────────┐       │  Bluetooth   ┌────────┐
 │  │ measure(         │ ◀─呼ぶ─ │ main.py         │       │  Classic     │ ESP32  │
 │  │  want_shoulder,  │        │ store.py        │ ─GET:3────────────▶ │（無印）│
 │  │  known)          │ ─dict─▶ │ machine.py      │ ◀─OK:GET:3──────── │        │
 │  └─────────────────┘        └─────────────────┘       │              └────────┘
 │   カメラ・AI・顔の照合           登録・検索・保存・操作      │
 └──────────────────────────────────────────────────────┘
```

画像処理と本体は同じラズパイの同じプログラムの中で動きます。サーバーは使いません。
それでも、お互いの約束は **`measure` 関数 1 つと、やりとりする dict の形だけ**（PROTOCOL.md）です。

## フォルダと担当

```
hanger_system/
├─ run.py                 ← 起動用（python3 run.py）
├─ PROTOCOL.md            ← 画像処理と本体の約束（これだけを共有する）
├─ body/                  ← 本体担当
│   ├─ main.py            コマンド（reg / get / face / del / list / quit）
│   ├─ config.py          本体の設定（ハンガー数・保存先・画像処理のファイル・Bluetooth）
│   ├─ store.py           登録・検索・保存（顔は中身を見ずに預かるだけ）
│   ├─ vision_client.py   画像処理のファイルを読み込み、measure を呼ぶ窓口
│   ├─ machine.py         ESP32 へ命令を送る（自動でつなぎ直す）
│   └─ requirements.txt   pyserial
├─ vision/                ← 画像処理担当（中身は自由に作り替えてよい）
│   ├─ vision.py          本物の見本（YOLO で肩、YuNet + SFace で顔）
│   ├─ models/            ONNX モデルを置く
│   └─ requirements.txt   numpy / opencv-python / ultralytics
├─ tools/
│   ├─ fake_vision.py     仮の画像処理（カメラなし・標準ライブラリだけ）
│   ├─ check_vision.py    画像処理が約束どおりか確かめる（標準ライブラリだけ）
│   └─ bt_test.py         ラズパイ ⇔ ESP32 の通信だけを手で試す
└─ esp32/hanger_esp32/hanger_esp32.ino   ESP32：命令を受けて返事をし、動かす（今は LED で代用）
```

- 画像処理は本体のファイルを import しません。本体は画像処理の `measure` 以外に触りません
- 本体はパッケージ（`body.`〇〇）になっているので、画像処理側に `config.py` などの同じ名前のファイルがあってもぶつかりません
- どの画像処理を使うかは `body/config.py` の `VISION_FILE` で選びます（仮 ⇔ 本物の切り替えはここだけ）

## 前の版から減った約束

| 第1版で必要だった約束 | 今の版 |
|---|---|
| 画像処理が本体の `vision_api.py` を import する | 何も import しない（共有ファイルなし） |
| 定数4つ（API_VERSION, FACE_DIM, FACE_MODEL_ID, しきい値）を持つ | 不要 |
| 関数3つ（open_vision / capture / close_vision）を作る | `measure` 1 つだけ。準備・片付けは画像処理が自分でする |
| Measurement クラスを使って返す | ふつうの dict |
| 顔は128個の小数・長さ1にそろえる | 形は自由。本体は中身を見ない |
| 本体が内積で顔を比べ、しきい値で判定する | 画像処理が判定して `match` で返す |
| 本体がモデルの違いを検知して顔検索を止める | 画像処理が古い顔を照合から外し、`note` で知らせる |
| エラーの種類を4つのコードで返す | 利用者向けの文を返すか、例外を投げるだけ |

画像処理が例外を投げても、変な値を返しても、本体は「測定失敗」と表示して動き続けます。

## ラズパイ5での準備

### 1. ライブラリ

純正カメラを使う picamera2 は apt で入れるものなので、仮想環境は `--system-site-packages` 付きで作ります。

```
sudo apt install -y python3-picamera2
python3 -m venv --system-site-packages ~/hanger-venv
source ~/hanger-venv/bin/activate
pip install -r body/requirements.txt -r vision/requirements.txt
```

USB カメラを使うときは、`vision/vision.py` の `CAMERA` を `"usb"` にします。

### 2. 動かす

```
python3 run.py
```

最初は `body/config.py` の `VISION_FILE` が仮の画像処理（tools/fake_vision.py）になっています。
`reg` や `face` を打つと「カメラの前にいる人の名前」を聞いてくるので、名前を入れて試します。
本物を使うときは `VISION_FILE = HERE.parent / "vision" / "vision.py"` にします。

### 3. 画像処理担当の確認

```
python3 vision/vision.py                          ← 1 回測って結果を表示
python3 vision/vision.py calib 42.0               ← 肩幅 42.0cm の人で校正
python3 tools/check_vision.py vision/vision.py    ← 約束どおりか確認
```

### 4. YOLO を速くする（必要なら）

ラズパイ5の CPU だと、そのままの YOLO は少し遅めです。測定が時間切れになるときは NCNN 形式に変換します。

```
yolo export model=yolo11n-pose.pt format=ncnn
```

できたフォルダ名（`yolo11n-pose_ncnn_model`）を `vision/vision.py` の `POSE_MODEL` に入れます。

## ESP32 の準備（ラズパイ5 ⇔ ESP32）

今は **最小構成** です。Arduino は使わず、ハンガー側は無印 ESP32 だけで、命令を受け取ったら返事をしてボード上の LED を光らせます。モーターは、スケッチの `doGet` / `doPut` に後から足します。

Bluetooth Classic を使うので、**無印 ESP32**（ESP32-WROVER / ESP32-WROOM-32 など。S3 や C3 ではないもの）が必要です。

### 1. スケッチの書き込み

1. Arduino IDE のボードマネージャで「esp32 by Espressif Systems」を入れる
2. ボードは WROVER なら「ESP32 Wrover Module」、WROOM なら「ESP32 Dev Module」を選ぶ（ポートが出ないときは USB 変換チップのドライバーを入れる）
3. `esp32/hanger_esp32/hanger_esp32.ino` を書き込む
4. シリアルモニタ（115200bps）に `[BT] 待ち受け開始: HANGER-ESP32` と出れば OK

### 2. ラズパイとペアリングしてポートを作る

ESP32 は「HANGER-ESP32」という名前で見えます。

```
bluetoothctl
  power on
  scan on                  ← 「HANGER-ESP32」と出たらアドレス（xx:xx:xx:xx:xx:xx）をメモ
  scan off
  pair xx:xx:xx:xx:xx:xx   ← PIN や確認を聞かれたら、1234 を入れるか yes と答える
  trust xx:xx:xx:xx:xx:xx
  quit

sudo rfcomm bind 0 xx:xx:xx:xx:xx:xx 1     ← /dev/rfcomm0 ができる
sudo usermod -aG dialout $USER             ← sudo なしで使えるようにする（一度ログアウト）
```

`rfcomm bind` は再起動すると消えます。毎回自動でやるなら、次の内容で `/etc/systemd/system/rfcomm0.service` を作り、`sudo systemctl enable --now rfcomm0` します。

```
[Unit]
Description=ESP32 rfcomm0
After=bluetooth.service
Requires=bluetooth.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/bin/rfcomm bind 0 xx:xx:xx:xx:xx:xx 1
ExecStop=/usr/bin/rfcomm release 0

[Install]
WantedBy=multi-user.target
```

### 3. 通信だけを試す

```
python3 tools/bt_test.py
```

つながると自動で `PING` を送り、`← PONG` と出ます。続けて `GET:3` と打つと `← OK:GET:3` が返り、ESP32 の LED が3回点滅します。`PUT:3:42.5` なら LED が1秒点きます。

### 4. 本体から使う

`body/config.py` の `MACHINE_MODE` を `"bt"` にして `python3 run.py` で起動します。

| 起動時の表示 | 状態 | 確認するところ |
|---|---|---|
| `/dev/rfcomm0 で ESP32 につながりました` | つながった | ― |
| `ESP32 にはつながりましたが PONG が返りません` | Bluetooth はつながったが、スケッチが返事をしない | `hanger_esp32.ino` が書き込まれているか |
| `ESP32 につながりません` | Bluetooth がつながらない | ESP32 の電源、ペアリング、`rfcomm bind` |

### 通信の決まり（ラズパイ ↔ ESP32）

- ラズパイ → ESP32：`PING` / `GET:3` / `PUT:3:42.5`（1行1命令）
- ESP32 → ラズパイ：`PONG` / `OK:<命令>` / `ERR:<理由>:<命令>`。それ以外の行は読み捨てるので、デバッグ表示を混ぜても大丈夫です
- 切れたら自動でつなぎ直します。まだ送れていない命令は、つながってから送ります
- 送ったのに `OK` が来ない命令は送り直しません（届いていた場合、2回動いてしまうため）。警告だけ出します
- `HANGER_COUNT` は `body/config.py` と ESP32 のスケッチで同じ値にしてください

## 前の版のデータについて

第1版の `data/people.json` は読み込めますが、顔の形が変わったため、顔での呼び出しには使えません（名前での呼び出しはできます）。画像処理が「〇人分の顔は今の方式と違う」と知らせるので、その人は登録し直してください。
