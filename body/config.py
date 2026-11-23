# config.py
# 本体側の設定。画像処理側の設定（カメラ番号・換算係数・しきい値など）は、ここには一切ない。

from pathlib import Path

HERE = Path(__file__).resolve().parent


# ---- ハンガーと保存先 ----
HANGER_COUNT = 20                       # ESP32 側の HANGER_COUNT と同じにする
DATA_FILE = HERE / "data" / "people.json"


# ---- 画像処理のファイル（measure 関数があるファイル）----
# 本物:  HERE.parent / "vision" / "vision.py"
# 仮:    HERE.parent / "tools" / "fake_vision.py"   ← カメラなしで開発するとき
VISION_FILE = HERE.parent / "tools" / "fake_vision.py"

# 本体が受け入れる肩幅の範囲（本体側の安全確認。画像処理との約束ではない）
SHOULDER_MIN_CM = 20.0
SHOULDER_MAX_CM = 80.0


# ---- 機械（ラズパイ ─Bluetooth Classic─ ESP32）----
# "print": 画面に表示するだけ（機械なしで開発するとき）
# "bt"   : Bluetooth で ESP32 に送る
MACHINE_MODE = "print"

# ESP32 の無線シリアルポート。ラズパイでは rfcomm bind で作る（README 参照）
BT_PORT = "/dev/rfcomm0"
BT_BAUD = 9600           # Bluetooth のポートでは実質使われない
BT_ACK_TIMEOUT = 3.0     # 秒。ESP32 から OK が返るまで待つ時間
BT_RETRY_SEC = 5.0       # 秒。つながらないとき、次に試すまでの間隔
