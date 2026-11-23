# fake_vision.py
# 画像処理の「仮実装」。カメラも AI も使わず、Python 標準ライブラリだけで動く。
# 本体担当が、本物の画像処理ができる前に開発・テストするためのもの。
# 本物と同じく PROTOCOL.md の約束（measure 関数 1 つ）だけを守る。
# 本体の config.py の VISION_FILE をこのファイルにすれば使える。
#
# 本体で reg / face を打つと「カメラの前にいる人の名前」を聞いてくる。
#   名前を入力 → その人が立っている想定で測定成功
#   何も入れずに Enter → 「顔が映らなかった」失敗
#   ! だけ入力 → 両肩が映らなかった失敗（肩を測るときだけ）

import random
import zlib


def measure(want_shoulder, known):
    name = input("  （仮）カメラの前にいる人の名前: ").strip()

    if name == "":
        return {"ok": False, "message": "顔が十分に映っていません（仮：誰も立っていない想定）"}
    if name == "!" and want_shoulder:
        return {"ok": False, "message": "両肩が十分に映っていません（仮）"}

    # 仮の顔は「名前」そのもの。本体は中身を見ないので、これで十分に試せる
    face = {"model": "fake-1", "who": name}

    match, skipped = None, 0
    for key, other in known.items():
        if not (isinstance(other, dict) and other.get("model") == "fake-1"):
            skipped += 1
        elif other.get("who") == name:
            match = key

    reply = {"ok": True, "face": face, "match": match,
             "score": 0.9 if match else round(random.uniform(0.0, 0.3), 2)}
    if want_shoulder:
        base = 38 + (zlib.crc32(name.encode("utf-8")) % 1200) / 100   # 名前ごとに 38〜50cm
        reply["shoulder_cm"] = round(base + random.gauss(0, 0.3), 1)
    if skipped:
        reply["note"] = f"{skipped} 人分の顔は仮実装の形式ではないので照合していません"
    return reply
