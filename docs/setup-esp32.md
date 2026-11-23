# ESP32 の準備（ラズパイ5 ⇔ ESP32）

ハンガー側は **無印 ESP32 1 台** です。この 1 台で、ラズパイからの命令の受け取り（Bluetooth）、モーター、重量計測をまとめて動かします。Arduino は使いません。

Bluetooth Classic を使うので、**無印 ESP32**（ESP32-WROVER / ESP32-WROOM-32 など。S3 や C3 ではないもの）が必要です。

今は **最小構成** です。命令を受け取ったら返事をして、モーターの代わりにボード上の LED を光らせます。重量計測はまだ入っていません。

---

## スケッチの分け方

```
esp32/
├─ hanger_esp32/          ← 本番用。このフォルダ全体を 1 つのプログラムとして書き込む
│   ├─ hanger_esp32.ino   全体の setup / loop。各担当の関数を呼ぶだけ
│   ├─ pins.h             使うピンの一覧
│   ├─ bt_command.cpp/.h  ラズパイからの命令を受けて返事をする
│   ├─ motor.cpp/.h       ハンガーを動かす（今は LED で代用）
│   └─ weight.cpp/.h      重さを測って乾燥を判定する（まだ空）
└─ tests/                 ← 部品を 1 つずつ試すための、別のスケッチ
    └─ drying_motor_test/ 乾燥完了と仮定して、モーターを 1 回だけ動かす
```

- Arduino IDE で `hanger_esp32.ino` を開くと、同じフォルダのファイルがタブで並びます。書き込むと全部まとめて 1 つのプログラムになります
- `tests/` のスケッチは、それぞれが自分の `setup` / `loop` を持つ別のプログラムです。ESP32 に入るのは一度に 1 つだけなので、試し終わったら本番用を書き込み直してください
- 使うピンは必ず `pins.h` に書きます。**GPIO4・GPIO5 は重量計測で使う予定**なので、ほかでは使いません
- 各担当の loop 関数（`motorLoop` など）では、`delay` で何秒も止めないでください。1 台で全部を動かしているので、止まっている間はほかの処理も止まります

---

## 1. スケッチを書き込む

1. Arduino IDE のボードマネージャで「esp32 by Espressif Systems」を入れる
2. ボードは WROVER なら「ESP32 Wrover Module」、WROOM なら「ESP32 Dev Module」を選ぶ（ポートが出ないときは USB 変換チップのドライバーを入れる）
3. `esp32/hanger_esp32/hanger_esp32.ino` を開いて書き込む
4. シリアルモニタ（115200bps）に `[BT] 待ち受け開始: HANGER-ESP32` と出れば OK

## 2. ラズパイとペアリングしてポートを作る

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

## 3. 通信だけを試す

```
python3 tools/bt_test.py
```

つながると自動で `PING` を送り、`← PONG` と出ます。続けて `GET:3` と打つと `← OK:GET:3` が返り、ESP32 の LED が3回点滅します。`PUT:3:42.5` なら LED が1秒点きます。

送れる命令と返事の決まりは [esp32-commands.md](esp32-commands.md) にあります。

## 4. 本体から使う

自分の手元だけで `body/config.py` の `MACHINE_MODE` を `"bt"` にして（この変更はコミットしない）、`python3 run.py` で起動します。

| 起動時の表示 | 状態 | 確認するところ |
|---|---|---|
| `/dev/rfcomm0 で ESP32 につながりました` | つながった | ― |
| `ESP32 にはつながりましたが PONG が返りません` | Bluetooth はつながったが、スケッチが返事をしない | 本番用の `esp32/hanger_esp32/` が書き込まれているか（`tests/` のスケッチのままでないか） |
| `ESP32 につながりません` | Bluetooth がつながらない | ESP32 の電源、ペアリング、`rfcomm bind` |
