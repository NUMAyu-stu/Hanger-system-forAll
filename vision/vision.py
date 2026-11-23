# vision.py
# 画像処理の「本物」の見本。画像処理担当はこのフォルダを自由に作り替えてよい。
# 本体のコードは一切 import しない。守るのは PROTOCOL.md の約束（measure 関数 1 つ）だけ。
#
#   肩: YOLO の骨格推定（COCO 形式で 5 = 左肩, 6 = 右肩）
#   顔: OpenCV の YuNet（顔の位置）＋ SFace（顔を 128 個の数値に変換）
#   カメラ: ラズパイ純正カメラ（picamera2）か USB カメラ（OpenCV）
#
# 単体での使い方
#   python3 vision/vision.py             ← 1 回測って結果を表示（本体なしで試す）
#   python3 vision/vision.py calib 42.0  ← 肩幅 42.0cm と分かっている人で校正
#
# 顔の比べ方・しきい値・モデル名はすべてこのファイルの中だけで決める。
# 本体に渡す face は {"model": FACE_MODEL_ID, "v": [...]} の形にしているが、
# これは画像処理側の都合であり、本体は中身を見ない（形を変えても本体は直さなくてよい）。

import atexit
import sys
import time
from pathlib import Path

import numpy as np

# ---- 画像処理の設定（本体は知らない）----
HERE = Path(__file__).resolve().parent
CAMERA = "picamera2"      # "picamera2": ラズパイ純正カメラ / "usb": USB カメラ
USB_CAMERA_INDEX = 0
FRAME_SIZE = (640, 480)
SAMPLE_FRAMES = 15        # 何フレーム分を集めるか（ラズパイ5の CPU で 10 秒以内に集まる量）
CAPTURE_TIMEOUT = 12.0    # 秒。この時間で集まらなければ失敗（約束の 20 秒より短く）
POSE_MODEL = "yolo11n-pose.pt"   # 速くしたいときは NCNN に変換したもの（docs/setup-raspi.md 参照）
POSE_IMGSZ = 320                 # YOLO に入れる画像の大きさ。小さいほど速い
FACE_DETECT_MODEL = HERE / "models" / "face_detection_yunet_2023mar.onnx"
FACE_RECOG_MODEL = HERE / "models" / "face_recognition_sface_2021dec.onnx"
FACE_MODEL_ID = "sface-2021dec"
FACE_DIM = 128
FACE_MATCH_THRESHOLD = 0.363  # SFace の推奨値。取り違えが多ければ上げる
CM_PER_PX = 0.25              # calib で求めた値を入れる
SHOULDER_CORRECTION = 1.15    # 関節の中心 → 肩先〜肩先 に近づける補正


# =====================================================================
# 約束の関数（本体が呼ぶのはこれだけ）
# =====================================================================

def measure(want_shoulder, known):
    v = get_vision()
    widths, faces = v.collect(want_shoulder)
    minimum = SAMPLE_FRAMES // 2
    if widths is None:
        return {"ok": False, "message": "カメラから画像が取れません"}
    if len(faces) < minimum:
        return {"ok": False, "message": f"顔が十分に映っていません（{len(faces)} / {SAMPLE_FRAMES} フレーム）"}
    if want_shoulder and len(widths) < minimum:
        return {"ok": False, "message": f"両肩が十分に映っていません（{len(widths)} / {SAMPLE_FRAMES} フレーム）"}

    vec = average_face(faces)
    match, score, skipped = best_match(vec, known if isinstance(known, dict) else {})
    reply = {"ok": True, "face": pack_face(vec), "match": match, "score": round(score, 3)}
    if want_shoulder:
        reply["shoulder_cm"] = round(px_to_cm(float(np.median(widths))), 1)
    if skipped:
        reply["note"] = f"{skipped} 人分の顔は今の方式と違うため照合していません（登録し直してください）"
    return reply


# =====================================================================
# カメラとモデル（初めて measure が呼ばれたときに準備し、終了時に片付ける）
# =====================================================================

_vision = None


def get_vision():
    global _vision
    if _vision is None:
        _vision = Vision()
        atexit.register(_vision.close)
    return _vision


class Camera:
    """read() で OpenCV 形式（BGR）の画像を 1 枚返す。読めなければ None"""

    def __init__(self):
        if CAMERA == "picamera2":
            from picamera2 import Picamera2   # sudo apt install python3-picamera2
            self.picam = Picamera2()
            # "RGB888" は OpenCV と同じ BGR の並びで出てくる
            config = self.picam.create_preview_configuration(
                main={"size": FRAME_SIZE, "format": "RGB888"})
            self.picam.configure(config)
            self.picam.start()
            time.sleep(1.0)   # 露出が落ち着くまで待つ
            self.cap = None
        else:
            import cv2
            self.picam = None
            self.cap = cv2.VideoCapture(USB_CAMERA_INDEX)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_SIZE[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_SIZE[1])
            if not self.cap.isOpened():
                raise RuntimeError("USB カメラを開けません。USB_CAMERA_INDEX を確認してください")

    def read(self):
        if self.picam is not None:
            try:
                return self.picam.capture_array()
            except Exception:
                return None
        ok, img = self.cap.read()
        return img if ok else None

    def close(self):
        if self.picam is not None:
            self.picam.stop()
            self.picam.close()
        if self.cap is not None:
            self.cap.release()


class Vision:
    def __init__(self):
        import cv2
        from ultralytics import YOLO

        print("（画像処理）カメラとモデルを準備しています…")
        self.camera = Camera()
        self.pose = YOLO(POSE_MODEL, task="pose")
        self.face_det = cv2.FaceDetectorYN.create(str(FACE_DETECT_MODEL), "", (320, 320), 0.8)
        self.face_rec = cv2.FaceRecognizerSF.create(str(FACE_RECOG_MODEL), "")

    def close(self):
        self.camera.close()

    def collect(self, want_shoulder):
        """フレームを集める。カメラが読めなければ widths=None"""
        widths, faces = [], []
        start = time.time()
        while time.time() - start < CAPTURE_TIMEOUT:
            img = self.camera.read()
            if img is None:
                return None, faces
            if want_shoulder and len(widths) < SAMPLE_FRAMES:
                px = self.shoulder_px(img)
                if px is not None:
                    widths.append(px)
            if len(faces) < SAMPLE_FRAMES:
                feature = self.face_feature(img)
                if feature is not None:
                    faces.append(feature)
            if len(faces) >= SAMPLE_FRAMES and (not want_shoulder or len(widths) >= SAMPLE_FRAMES):
                break
        return widths, faces

    def shoulder_px(self, img):
        result = self.pose(img, imgsz=POSE_IMGSZ, verbose=False)[0]
        if result.keypoints is None or len(result.boxes) == 0:
            return None
        boxes = result.boxes.xywh.cpu().numpy()
        i = int(np.argmax(boxes[:, 2] * boxes[:, 3]))   # 一番大きく映っている人
        xy = result.keypoints.xy[i].cpu().numpy()
        conf = result.keypoints.conf[i].cpu().numpy()
        LEFT, RIGHT = 5, 6
        if conf[LEFT] < 0.5 or conf[RIGHT] < 0.5:
            return None
        return float(np.linalg.norm(xy[LEFT] - xy[RIGHT]))

    def face_feature(self, img):
        h, w = img.shape[:2]
        self.face_det.setInputSize((w, h))
        _, found = self.face_det.detect(img)
        if found is None or len(found) == 0:
            return None
        i = int(np.argmax(found[:, 2] * found[:, 3]))   # 一番大きい顔
        aligned = self.face_rec.alignCrop(img, found[i])
        return self.face_rec.feature(aligned).flatten().astype(np.float32)


def px_to_cm(px):
    return px * CM_PER_PX * SHOULDER_CORRECTION


def average_face(faces):
    total = np.zeros_like(faces[0])
    for f in faces:
        total = total + f / np.linalg.norm(f)
    return total / np.linalg.norm(total)


# =====================================================================
# 顔の保存形式と照合（画像処理側だけが知っていればよい）
# =====================================================================

def pack_face(vec):
    return {"model": FACE_MODEL_ID, "v": [round(float(x), 6) for x in vec]}


def unpack_face(face):
    """自分の形式でなければ None（古いモデル・壊れたデータなど）"""
    if not isinstance(face, dict) or face.get("model") != FACE_MODEL_ID:
        return None
    try:
        vec = np.array(face["v"], dtype=np.float32)
    except (KeyError, TypeError, ValueError):
        return None
    if vec.shape != (FACE_DIM,) or not np.all(np.isfinite(vec)) or np.linalg.norm(vec) == 0:
        return None
    return vec / np.linalg.norm(vec)


def best_match(vec, known):
    """(一番似ているキー or None, 類似度, 照合できなかった人数)"""
    best, best_score, skipped = None, 0.0, 0
    for key, face in known.items():
        other = unpack_face(face)
        if other is None:
            skipped += 1
            continue
        score = float(np.dot(vec, other))
        if score > best_score:
            best, best_score = key, score
    if best_score < FACE_MATCH_THRESHOLD:
        best = None
    return best, best_score, skipped


# =====================================================================
# 単体で動かすとき
# =====================================================================

def calibrate(real_cm):
    widths, _ = get_vision().collect(want_shoulder=True)
    if not widths:
        print("両肩が映りませんでした")
        return
    px = float(np.median(widths))
    print(f"肩の間 {px:.1f} px → CM_PER_PX = {real_cm / (px * SHOULDER_CORRECTION):.4f}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "calib":
        calibrate(float(sys.argv[2]))
    elif len(sys.argv) == 1:
        r = measure(True, {})
        if r.get("ok"):
            r["face"] = f"（{len(r['face']['v'])} 個の数値）"
        print(r)
    else:
        print("使い方: python3 vision/vision.py  /  python3 vision/vision.py calib <実際の肩幅cm>")
