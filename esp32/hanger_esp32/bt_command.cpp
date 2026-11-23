// bt_command.cpp
// ラズパイから Bluetooth Classic（SPP）で命令を受け取り、返事をする（本体担当）。
//
//   ラズパイ5 ──Bluetooth Classic（SPP）──▶ ESP32
//
// ---- 受け取る命令（1 行 1 命令、改行で終わる）----
//   PING         → PONG を返す（つながっているかの確認）
//   GET:3        → 3 番のハンガーを取り出す        → motorGet(3)
//   PUT:3:42.5   → 3 番を肩幅 42.5cm で割り当てた  → motorPut(3, 42.5)
//
// ---- 返す返事（1 行）----
//   PONG
//   OK:<受け取った命令そのまま>     例 OK:GET:3
//   ERR:<理由>:<命令>               例 ERR:RANGE:GET:25
//
// 命令を増やす・変えるときは、ラズパイ側の body/machine.py も直す必要がある（チーム全員で決める）。

#include "BluetoothSerial.h"
#include "bt_command.h"
#include "motor.h"

// 注意：#error の行は日本語にしない（読み飛ばされる行でもコンパイルエラーになるため）

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled. Check the board selection (ESP32 Wrover Module / ESP32 Dev Module).
#endif
#if !defined(CONFIG_BT_SPP_ENABLED)
#error Bluetooth Classic (SPP) is not available. Use the original ESP32 (not S2/S3/C3).
#endif

static const char *BT_NAME = "HANGER-ESP32";  // ラズパイの Bluetooth 一覧に出る名前
static const int CMD_MAX = 32;               // 1 行の最大文字数。これより長い行は捨てる

static BluetoothSerial SerialBT;
static String line = "";
static bool overflow = false;

static void handleCommand(const String &cmd);

static void onBtEvent(esp_spp_cb_event_t event, esp_spp_cb_param_t *param) {
  if (event == ESP_SPP_SRV_OPEN_EVT) {
    Serial.println("[BT] ラズパイがつながりました");
  } else if (event == ESP_SPP_CLOSE_EVT) {
    Serial.println("[BT] ラズパイとの接続が切れました");
  }
}

void btSetup() {
  SerialBT.register_callback(onBtEvent);
  SerialBT.begin(BT_NAME);
  Serial.print("[BT] 待ち受け開始: ");
  Serial.println(BT_NAME);
}

void btLoop() {
  while (SerialBT.available()) {
    char ch = SerialBT.read();
    if (ch == '\n') {
      if (overflow) {
        btSend("ERR:TOO_LONG");
      } else {
        line.trim();
        if (line.length() > 0) handleCommand(line);
      }
      line = "";
      overflow = false;
    } else if (ch != '\r') {
      if (line.length() < CMD_MAX) {
        line += ch;
      } else {
        overflow = true;
      }
    }
  }
}

void btSend(const String &text) {
  SerialBT.println(text);   // \r\n で終わる。ラズパイ側は \r を無視する
  Serial.print("-> ");
  Serial.println(text);
}

static void handleCommand(const String &cmd) {
  Serial.print("<- ");
  Serial.println(cmd);

  if (cmd == "PING") {
    btSend("PONG");
    return;
  }

  // 「種類:番号」または「種類:番号:肩幅」に分ける
  int p1 = cmd.indexOf(':');
  if (p1 < 0) {
    btSend("ERR:BAD:" + cmd);
    return;
  }
  String kind = cmd.substring(0, p1);
  int p2 = cmd.indexOf(':', p1 + 1);
  String numText = (p2 < 0) ? cmd.substring(p1 + 1) : cmd.substring(p1 + 1, p2);
  int hanger = numText.toInt();
  if (hanger < 1 || hanger > HANGER_COUNT) {
    btSend("ERR:RANGE:" + cmd);
    return;
  }

  if (kind == "GET") {
    btSend("OK:" + cmd);   // 先に受け付けたことを返す（動作に時間がかかってもラズパイを待たせない）
    motorGet(hanger);
  } else if (kind == "PUT") {
    float shoulderCm = (p2 < 0) ? 0 : cmd.substring(p2 + 1).toFloat();
    btSend("OK:" + cmd);
    motorPut(hanger, shoulderCm);
  } else {
    btSend("ERR:UNKNOWN:" + cmd);
  }
}
