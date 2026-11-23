# main.py
# 本体の入口
#
# コマンド:
#   reg <名前>     カメラの前の人を測って登録し、ハンガーを割り当てる
#   get <名前>     名前でハンガーを呼び出す
#   face           カメラの前の人を顔で判定してハンガーを呼び出す
#   del <名前>     登録を消してハンガーを空ける
#   list           登録状況を表示
#   quit           終了
#
# 起動: リポジトリのフォルダで  python3 run.py
#
# 画像処理は config.VISION_FILE のファイルの measure 関数だけを使う（PROTOCOL.md）。
# 画像処理が読み込めなくても get / del / list は使える。

from . import config, machine
from .store import Store
from .vision_client import Vision, VisionError


def measure(vs, st, want_shoulder):
    """画像処理に測ってもらう。だめなら理由を表示して None"""
    try:
        s = vs.scan(want_shoulder, st.faces())
    except VisionError as e:
        print("  測定失敗:", e)
        return None
    if s.note:
        print("  画像処理より:", s.note)
    if want_shoulder and not config.SHOULDER_MIN_CM <= s.shoulder_cm <= config.SHOULDER_MAX_CM:
        print(f"  肩幅 {s.shoulder_cm} cm は範囲外です。もう一度測ってください")
        return None
    return s


def score_text(s):
    return f"（類似度 {s.score:.2f}）" if s.score is not None else ""


def do_register(vs, st, mc, name):
    if st.find(name) is not None:
        print(f"  {name} はすでに登録されています（del で消してから登録し直してください）")
        return
    if st.free_count() == 0:
        print("  空いているハンガーがありません")
        return

    print("  カメラの正面に立ってください。測定します…")
    s = measure(vs, st, want_shoulder=True)
    if s is None:
        return
    if s.match is not None:
        print(f"  この顔は {s.match} として登録済みです{score_text(s)}")
        return

    p = st.register(name, s.shoulder_cm, s.face)
    print(f"  {p.name} を登録しました → ハンガー {p.hanger}（肩幅 {p.shoulder_cm} cm）")
    mc.send(f"PUT:{p.hanger}:{p.shoulder_cm}")


def do_get_by_name(st, mc, name):
    p = st.find(name)
    if p is None:
        print(f"  {name} は登録されていません")
        return
    print(f"  ハンガー {p.hanger}（{p.name}）を呼び出します")
    mc.send(f"GET:{p.hanger}")


def do_get_by_face(vs, st, mc):
    if not st.faces():
        print("  顔が登録されている人がいません")
        return
    print("  カメラの正面を向いてください。顔を確認します…")
    s = measure(vs, st, want_shoulder=False)
    if s is None:
        return
    if s.match is None:
        print(f"  登録された人が見つかりません{score_text(s)}")
        return
    p = st.find(s.match)
    print(f"  {p.name} と判定しました{score_text(s)} → ハンガー {p.hanger} を呼び出します")
    mc.send(f"GET:{p.hanger}")


def do_delete(st, name):
    p = st.remove(name)
    if p is None:
        print(f"  {name} は登録されていません")
        return
    print(f"  {p.name} の登録を消しました（ハンガー {p.hanger} が空きました）")


def main():
    st = Store(config.DATA_FILE, config.HANGER_COUNT)
    vs = Vision(config.VISION_FILE)
    mc = machine.open_machine(config)
    print(f"画像処理: {vs.path.name} / 機械: {config.MACHINE_MODE}")
    if vs.load_error:
        print("  注意:", vs.load_error)
    print("コマンド: reg <名前> / get <名前> / face / del <名前> / list / quit")

    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            cmd, _, arg = line.partition(" ")
            arg = arg.strip()

            if cmd in ("reg", "get", "del") and arg == "":
                print(f"  使い方: {cmd} <名前>")
            elif cmd == "reg":
                do_register(vs, st, mc, arg)
            elif cmd == "get":
                do_get_by_name(st, mc, arg)
            elif cmd == "face":
                do_get_by_face(vs, st, mc)
            elif cmd == "del":
                do_delete(st, arg)
            elif cmd == "list":
                st.show()
            elif cmd == "quit":
                break
            elif cmd != "":
                print("  reg / get / face / del / list / quit のどれかを入力してください")
    except KeyboardInterrupt:
        pass
    finally:
        mc.close()

