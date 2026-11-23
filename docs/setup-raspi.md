# ラズパイ5の準備

ラズパイ5で、本物のカメラと画像処理を使って動かすまでの手順です。
自分の PC で試すだけなら、この準備はいりません（[README](../README.md) の「まず動かす」だけで動きます）。

ESP32 とつなぐ手順は [setup-esp32.md](setup-esp32.md) にあります。

---

## 1. ライブラリを入れる

純正カメラを使う picamera2 は apt で入れるものなので、仮想環境は `--system-site-packages` 付きで作ります。

```
sudo apt install -y python3-picamera2
python3 -m venv --system-site-packages ~/hanger-venv
source ~/hanger-venv/bin/activate
pip install -r body/requirements.txt -r vision/requirements.txt
```

USB カメラを使うときは、`vision/vision.py` の `CAMERA` を `"usb"` にします。

## 2. モデルファイルを置く

モデルファイルは大きく、Git にも入れない決まりなので、各自で用意して `vision/models/` に置きます。

| ファイル | 使い道 |
|---|---|
| `face_detection_yunet_2023mar.onnx` | 顔の位置を見つける（OpenCV の YuNet） |
| `face_recognition_sface_2021dec.onnx` | 顔を 128 個の数値にする（OpenCV の SFace） |

どちらも OpenCV が公開しているモデル（opencv_zoo）です。
肩を測る YOLO のモデル（`yolo11n-pose.pt`）は、初めて動かしたときに ultralytics が自動でダウンロードします。

## 3. 動かす

```
python3 run.py
```

最初は `body/config.py` の `VISION_FILE` が仮の画像処理（`tools/fake_vision.py`）になっています。
本物を使うときは、自分の手元だけで `VISION_FILE = HERE.parent / "vision" / "vision.py"` にします（この変更はコミットしない）。

## 4. 画像処理を確かめる（画像処理担当）

```
python3 vision/vision.py                          ← 1 回測って結果を表示
python3 vision/vision.py calib 42.0               ← 肩幅 42.0cm の人で校正
python3 tools/check_vision.py vision/vision.py    ← 約束（PROTOCOL.md）どおりか確認
```

`calib` で表示された値を、`vision/vision.py` の `CM_PER_PX` に入れます。
今の `CM_PER_PX = 0.25` は仮の値なので、校正するまで肩幅は正しくありません。

## 5. YOLO を速くする（必要なら）

ラズパイ5の CPU だと、そのままの YOLO は少し遅めです。測定が時間切れになるときは NCNN 形式に変換します。

```
yolo export model=yolo11n-pose.pt format=ncnn
```

できたフォルダ名（`yolo11n-pose_ncnn_model`）を `vision/vision.py` の `POSE_MODEL` に入れます。
