# machine.py
# ハンガー側の ESP32 へ命令を送る。
#
# つながり方
#   ラズパイ5 ──Bluetooth Classic（SPP）──▶ ESP32（無印）
#   ラズパイからは ESP32 が /dev/rfcomm0 というシリアルポートに見える（docs/setup-esp32.md 参照）。
#   命令の決まりは docs/esp32-commands.md。ESP32 側は esp32/hanger_esp32/bt_command.cpp。
#
# 送る命令（1 行 1 命令、ASCII、最後に改行）
#   PING         → つながっているかの確認。ESP32 は PONG を返す
#   GET:3        → 3 番のハンガーを取り出す
#   PUT:3:42.5   → 3 番を新しく割り当てた（肩幅 42.5cm）
#
# ESP32 からの返事（1 行）
#   PONG / OK:<受け取った命令> / ERR:<理由>
#   それ以外の行（デバッグ表示など）は読み捨てる
#
# 送信は別スレッドで行うので、通信待ちで入力が止まらない。
# Bluetooth は切れることがあるので、切れたら自動でつなぎ直す。
#   - 書き込めなかった命令 → つながってから送り直す（まだ届いていないので安全）
#   - 書き込めたが OK が来ない命令 → 送り直さない（届いていたら 2 回動いてしまうため）。警告だけ出す

import queue
import threading
import time


def open_machine(cfg):
    if cfg.MACHINE_MODE == "bt":
        return BtMachine(cfg.BT_PORT, cfg.BT_BAUD, cfg.BT_ACK_TIMEOUT, cfg.BT_RETRY_SEC)
    return PrintMachine()


def log(text):
    print(f"  [機械] {text}", flush=True)


class PrintMachine:
    """機械なしで開発するとき用。送る内容を表示するだけ"""

    def send(self, text):
        log(f"送信（表示のみ） {text}")

    def close(self):
        pass


class BtMachine:
    """Bluetooth の無線シリアルポート越しに ESP32 へ送る"""

    def __init__(self, port, baud, ack_timeout, retry_sec):
        import serial   # pip install pyserial
        self.serial = serial
        self.port_name = port
        self.baud = baud
        self.ack_timeout = ack_timeout
        self.retry_sec = retry_sec

        self.ser = None
        self.rx = b""
        self.quiet = False   # つながらない警告を出し済みなら True（同じ警告を繰り返さない）
        self.box = queue.Queue()
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()
        self.box.put(("CONNECT", None))   # 起動時に一度つないでおく

    # ---- 呼ぶ側から使うもの ----

    def send(self, text):
        """命令を待ち行列に入れるだけ（すぐ戻る）"""
        self.box.put(("SEND", text))

    def close(self):
        self.box.put(("QUIT", None))
        self.thread.join(timeout=self.ack_timeout + 2)
        self.stop.set()
        self.disconnect()

    # ---- ここから下は送信スレッドの中 ----

    def loop(self):
        while True:
            kind, text = self.box.get()
            if kind == "QUIT":
                return
            if kind == "CONNECT":
                self.connect()
            else:
                self.deliver(text)

    def deliver(self, text):
        waiting = False
        while not self.stop.is_set():
            if self.ser is None and not self.connect():
                if not waiting:
                    log(f"{text} はつながってから送ります（{self.retry_sec:.0f} 秒ごとに試します）")
                    waiting = True
                self.stop.wait(self.retry_sec)
                continue
            try:
                self.write_line(text)
            except (self.serial.SerialException, OSError) as e:
                log(f"送れませんでした（{e}）。つなぎ直します")
                self.disconnect()
                continue

            reply = self.wait_reply(lambda r: r == f"OK:{text}" or r.startswith("ERR:"))
            if reply is None:
                log(f"{text} の返事がありません（届いたか不明なので送り直しません）")
            elif reply.startswith("ERR:"):
                log(f"{text} → ESP32 がエラーを返しました: {reply[4:]}")
            else:
                log(f"{text} → 受け付けられました")
            return

    def connect(self):
        if self.ser is not None:
            return True
        if not self.quiet:
            log(f"{self.port_name} につないでいます…")
        try:
            # ポートを開いた時点で、ラズパイが ESP32 に Bluetooth でつなぎにいく
            self.ser = self.serial.serial_for_url(
                self.port_name, baudrate=self.baud, timeout=0.2, write_timeout=2)
        except (self.serial.SerialException, OSError, ValueError) as e:
            if not self.quiet:
                log(f"ESP32 につながりません（{e}）。"
                    "ESP32 の電源・ペアリング・rfcomm の設定を確認してください")
                self.quiet = True
            self.ser = None
            return False

        self.rx = b""
        time.sleep(0.5)   # つないだ直後は少し待つ
        try:
            self.write_line("PING")
        except (self.serial.SerialException, OSError) as e:
            log(f"ESP32 につながりません（{e}）")
            self.disconnect()
            return False
        if self.wait_reply(lambda r: r == "PONG") is None:
            # Bluetooth はつながったが、ESP32 のスケッチが返事をしない
            log("ESP32 にはつながりましたが PONG が返りません"
                "（hanger_esp32.ino が書き込まれているか確認）")
        else:
            log(f"{self.port_name} で ESP32 につながりました")
        self.quiet = False
        return True

    def disconnect(self):
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None

    def write_line(self, text):
        self.ser.reset_input_buffer()
        self.rx = b""
        self.ser.write((text + "\n").encode("ascii"))
        self.ser.flush()

    def wait_reply(self, wanted):
        """wanted(行) が True になる行が来るまで待つ。時間切れ・切断なら None"""
        deadline = time.time() + self.ack_timeout
        while time.time() < deadline:
            try:
                chunk = self.ser.read(64)
            except (self.serial.SerialException, OSError) as e:
                log(f"受信中に切れました（{e}）")
                self.disconnect()
                return None
            self.rx += chunk
            while b"\n" in self.rx:
                raw, self.rx = self.rx.split(b"\n", 1)
                line = raw.decode("ascii", "replace").strip()
                if line and wanted(line):
                    return line
        return None
