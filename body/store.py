# store.py
# 人とハンガー番号の登録・検索・解放。JSON に保存するので再起動しても残る。
#
# 顔のデータ（face）は画像処理から預かったものを、中身を見ずにそのまま保存する。
# 顔の比べ方・モデルの違いの扱いは画像処理側の仕事なので、ここには numpy も しきい値 もない。

import json
import os


class Person:
    def __init__(self, name, hanger, shoulder_cm, face):
        self.name = name                # 名前
        self.hanger = hanger            # ハンガー番号
        self.shoulder_cm = shoulder_cm  # 肩幅(cm)
        self.face = face                # 画像処理から預かった顔（中身は見ない）


class Store:
    def __init__(self, path, hanger_count):
        self.path = path
        self.hanger_count = hanger_count
        self.people = {}   # {名前: Person}
        if path.exists():
            self.load()

    # ---- 保存と読み込み ----

    def load(self):
        data = json.loads(self.path.read_text(encoding="utf-8"))
        for row in data.get("people", []):
            p = Person(row["name"], row["hanger"], row.get("shoulder_cm"), row.get("face"))
            self.people[p.name] = p

    def save(self):
        rows = [
            {"name": p.name, "hanger": p.hanger, "shoulder_cm": p.shoulder_cm, "face": p.face}
            for p in sorted(self.people.values(), key=lambda p: p.hanger)
        ]
        text = json.dumps({"people": rows}, ensure_ascii=False, indent=1)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, self.path)   # 書き込み途中で電源が切れても元のファイルが壊れない

    # ---- ハンガー番号 ----

    def used(self):
        return {p.hanger for p in self.people.values()}

    def free_count(self):
        return self.hanger_count - len(self.people)

    def first_free(self):
        """空いている一番小さい番号。満杯なら None"""
        used = self.used()
        for n in range(1, self.hanger_count + 1):
            if n not in used:
                return n
        return None

    # ---- 登録・削除・検索 ----

    def register(self, name, shoulder_cm, face):
        n = self.first_free()
        if n is None:
            return None
        p = Person(name, n, shoulder_cm, face)
        self.people[name] = p
        self.save()
        return p

    def remove(self, name):
        p = self.people.pop(name, None)
        if p is not None:
            self.save()
        return p

    def find(self, name):
        return self.people.get(name)

    def faces(self):
        """画像処理に渡す {名前: 顔}"""
        return {p.name: p.face for p in self.people.values() if p.face is not None}

    def show(self):
        if not self.people:
            print("  登録: なし")
            return
        for p in sorted(self.people.values(), key=lambda p: p.hanger):
            print(f"  ハンガー {p.hanger:>2}: {p.name}（肩幅 {p.shoulder_cm} cm）")
        print(f"  空き: {self.free_count()} / {self.hanger_count}")
