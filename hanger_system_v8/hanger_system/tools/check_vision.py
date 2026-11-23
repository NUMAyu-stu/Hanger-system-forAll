# check_vision.py
# 画像処理のファイルが PROTOCOL.md の約束どおりか確かめる。
# Python 標準ライブラリだけで動き、本体のコードは import しない。
#
# 使い方（カメラの前に 1 人立った状態で）
#   python3 tools/check_vision.py vision/vision.py
#   python3 tools/check_vision.py tools/fake_vision.py

import importlib.util
import json
import sys
import time
from pathlib import Path

TIME_LIMIT = 20.0


def load(path):
    path = Path(path).resolve()
    sys.path.append(str(path.parent))
    spec = importlib.util.spec_from_file_location("vision_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_reply(reply, sec, want_shoulder, known):
    """問題点のリスト（空なら OK）"""
    problems = []
    if sec > TIME_LIMIT:
        problems.append(f"{TIME_LIMIT:.0f} 秒を超えました（{sec:.1f} 秒）")
    try:
        json.dumps(reply)
    except (TypeError, ValueError) as e:
        problems.append(f"戻り値に基本の型でないものが入っています（{e}）。numpy は .tolist() / float() で直す")
    if not isinstance(reply, dict):
        return problems + ["戻り値が dict ではありません"]
    ok = reply.get("ok")
    if ok is False:
        if not isinstance(reply.get("message"), str) or not reply["message"]:
            problems.append("失敗なのに message（文字列）がありません")
        return problems
    if ok is not True:
        return problems + ["ok が True / False ではありません"]
    if "face" not in reply:
        problems.append("face がありません")
    if "match" not in reply:
        problems.append("match がありません（いなければ None を入れる）")
    elif reply["match"] is not None and reply["match"] not in known:
        problems.append(f"match に known にないキーが入っています（{reply['match']}）")
    if want_shoulder:
        cm = reply.get("shoulder_cm")
        if isinstance(cm, bool) or not isinstance(cm, (int, float)):
            problems.append("shoulder_cm（数）がありません")
        elif not 20 <= cm <= 80:
            problems.append(f"shoulder_cm が人の肩幅らしくありません（{cm}）")
    if "score" in reply and (isinstance(reply["score"], bool) or not isinstance(reply["score"], (int, float))):
        problems.append("score が数ではありません")
    if "note" in reply and not isinstance(reply["note"], str):
        problems.append("note が文字列ではありません")
    return problems


def step(no, title, measure, want_shoulder, known):
    print(f"[{no}] {title}")
    start = time.time()
    try:
        reply = measure(want_shoulder, known)
    except Exception as e:
        # 例外は約束上ゆるされている（本体は失敗として表示する）
        print(f"  OK（例外で失敗を知らせた）{type(e).__name__}: {e}")
        return None, True
    sec = time.time() - start
    problems = check_reply(reply, sec, want_shoulder, known)
    for p in problems:
        print("  NG:", p)
    if problems:
        return reply, False
    if reply.get("ok"):
        extra = f"肩幅 {reply['shoulder_cm']} cm  " if want_shoulder else ""
        print(f"  OK  {extra}match={reply['match']}  {sec:.1f} 秒")
    else:
        print(f"  OK（失敗の返し方は正しい）{reply['message']}  {sec:.1f} 秒")
    if reply.get("note"):
        print("      note:", reply["note"])
    return reply, True


def main():
    if len(sys.argv) != 2:
        print("使い方: python3 tools/check_vision.py <画像処理のファイル>")
        return False
    print(f"[0] {sys.argv[1]} を読み込みます")
    try:
        module = load(sys.argv[1])
    except Exception as e:
        print(f"  NG: 読み込めません（{type(e).__name__}: {e}）")
        return False
    measure = getattr(module, "measure", None)
    if not callable(measure):
        print("  NG: measure 関数がありません")
        return False
    print("  OK  measure 関数があります")

    all_ok = True
    r1, ok = step(1, "肩＋顔を測る（登録者なし）", measure, True, {})
    all_ok &= ok

    if r1 and r1.get("ok"):
        known = {"本人": json.loads(json.dumps(r1["face"])),
                 "読めない顔1": [1, 2, 3], "読めない顔2": "abc", "読めない顔3": None}
        r2, ok = step(2, "顔だけ測る（同じ人＋読めない顔が混ざった登録者）", measure, False, known)
        all_ok &= ok
        if r2 and r2.get("ok") and r2.get("match") != "本人":
            print("  注意: 同じ人が立っているなら match は「本人」になるはずです")
    else:
        print("[2] 1 が測定成功しなかったので飛ばします（カメラの前に立って、やり直してください）")
        all_ok = False

    print("結果:", "すべてOK" if all_ok else "NG あり")
    return all_ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
