# vision_client.py
# 画像処理のファイルを読み込み、「今カメラの前にいる人を測って」と頼む。
#
# 約束は PROTOCOL.md だけ。画像処理のファイルからは measure 関数しか使わない。
# 顔のデータ（face）は中身を見ずに受け取り、そのまま保存・返送する。

import copy
import importlib.util
import json
import sys
from pathlib import Path


class VisionError(Exception):
    """測定できなかった。str(e) がそのまま利用者に見せる文"""


class Scan:
    """1 回の測定結果"""

    def __init__(self, face, shoulder_cm, match, score, note):
        self.face = face                # 中身は見ない
        self.shoulder_cm = shoulder_cm  # want_shoulder=False なら None
        self.match = match              # known のキー or None
        self.score = score              # なければ None
        self.note = note                # なければ None


class Vision:
    def __init__(self, path):
        """画像処理のファイルを読み込む。読み込めなくても本体は動く（測るときにエラーを出す）"""
        self.path = Path(path).resolve()
        self.measure_fn = None
        self.load_error = None
        try:
            self.measure_fn = load_measure(self.path)
        except Exception as e:
            self.load_error = f"画像処理を読み込めません（{self.path.name}: {e}）"

    def scan(self, want_shoulder, known):
        """1 回測ってもらう。失敗したら VisionError"""
        if self.measure_fn is None:
            raise VisionError(self.load_error)
        try:
            reply = self.measure_fn(bool(want_shoulder), copy.deepcopy(known))
        except KeyboardInterrupt:
            raise VisionError("測定を中断しました")
        except Exception as e:
            raise VisionError(f"画像処理でエラーが起きました（{type(e).__name__}: {e}）")

        # 画像処理の持ち物を本体に持ち込まないよう、JSON に一度通して写しにする
        try:
            reply = json.loads(json.dumps(reply, ensure_ascii=False))
        except (TypeError, ValueError) as e:
            raise VisionError(f"画像処理の戻り値が保存できる形ではありません（{e}）")
        return to_scan(reply, want_shoulder, known)


def load_measure(path):
    """ファイルを読み込んで measure 関数を取り出す"""
    if not path.exists():
        raise FileNotFoundError("ファイルがありません")
    # 画像処理のファイルが自分のフォルダの別ファイルを import できるようにする
    folder = str(path.parent)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    spec = importlib.util.spec_from_file_location("hanger_vision", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fn = getattr(module, "measure", None)
    if not callable(fn):
        raise AttributeError("measure 関数がありません")
    return fn


def to_scan(reply, want_shoulder, known):
    """戻り値を確かめて Scan にする。約束と違えば VisionError"""
    if not isinstance(reply, dict):
        raise VisionError("画像処理の戻り値が dict ではありません")

    if reply.get("ok") is not True:
        raise VisionError(str(reply.get("message") or "測定に失敗しました"))

    if "face" not in reply:
        raise VisionError("画像処理の戻り値に face がありません")

    shoulder = None
    if want_shoulder:
        shoulder = reply.get("shoulder_cm")
        if isinstance(shoulder, bool) or not isinstance(shoulder, (int, float)):
            raise VisionError("画像処理の戻り値に肩幅（shoulder_cm）がありません")
        shoulder = round(float(shoulder), 1)

    match = reply.get("match")
    if match is not None and match not in known:
        raise VisionError(f"画像処理が知らない人（{match}）を返しました")

    score = reply.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        score = None

    note = reply.get("note")
    if note is not None:
        note = str(note)

    return Scan(reply["face"], shoulder, match, score, note)
