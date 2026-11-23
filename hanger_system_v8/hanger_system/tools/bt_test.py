# bt_test.py
# ラズパイ ⇔ ESP32 の通信だけを確かめる最小ツール。本体（カメラ・登録）は使わない。
#
# 使い方
#   python3 tools/bt_test.py                 ← /dev/rfcomm0 につなぐ
#   python3 tools/bt_test.py /dev/rfcomm1    ← 別のポートのとき
#
# つないだら PING を自動で送る。そのあとは命令を打って Enter で送る。
#   PING / GET:3 / PUT:3:42.5 など。q で終了。
# ESP32 から届いた行は「← 」を付けて表示する。

import sys
import threading
import time

import serial   # pip install pyserial


def reader(ser, stop):
    buf = b""
    while not stop.is_set():
        try:
            buf += ser.read(64)
        except (serial.SerialException, OSError) as e:
            print(f"\n受信中に切れました（{e}）")
            stop.set()
            return
        while b"\n" in buf:
            raw, buf = buf.split(b"\n", 1)
            text = raw.decode("ascii", "replace").strip()
            if text:
                print(f"← {text}")


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "/dev/rfcomm0"
    print(f"{port} につないでいます…")
    try:
        ser = serial.serial_for_url(port, baudrate=9600, timeout=0.2, write_timeout=2)
    except (serial.SerialException, OSError, ValueError) as e:
        print(f"つながりません（{e}）")
        print("ESP32 の電源、ペアリング、rfcomm bind を確認してください")
        return 1
    print("つながりました。命令を打って Enter（q で終了）")

    stop = threading.Event()
    threading.Thread(target=reader, args=(ser, stop), daemon=True).start()
    time.sleep(0.5)

    def send(text):
        ser.write((text + "\n").encode("ascii"))
        ser.flush()
        print(f"→ {text}")

    try:
        send("PING")
        while not stop.is_set():
            text = input().strip()
            if text in ("q", "quit"):
                break
            if text:
                send(text)
    except (EOFError, KeyboardInterrupt):
        pass
    except (serial.SerialException, OSError) as e:
        print(f"送れませんでした（{e}）")
    finally:
        stop.set()
        time.sleep(0.3)
        ser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
