// hanger_esp32.ino（無印 ESP32 用：Freenove ESP32-WROVER / ESP32-WROOM など）
// 最小構成：ラズパイから Bluetooth Classic で命令を受け取り、返事をして、LED で知らせる。
// モーターはまだつながない。動きを足すときは doGet / doPut の中に書く。
//
//   ラズパイ5 ──Bluetooth Classic（SPP）──▶ ESP32
//
// ---- 受け取る命令（1 行 1 命令、改行で終わる）----
//   PING         → PONG を返す（つながっているかの確認）
//   GET:3        → 3 番のハンガーを取り出す        （今は LED を 3 回点滅）
//   PUT:3:42.5   → 3 番を肩幅 42.5cm で割り当てた  （今は LED を長く 1 回点灯）
//
// ---- 返す返事（1 行）----
//   PONG
//   OK:<受け取った命令そのまま>     例 OK:GET:3
//   ERR:<理由>:<命令>               例 ERR:RANGE:GET:25
//
// ---- 書き込み ----
//   Arduino IDE のボードマネージャで「esp32 by Espressif Systems」を入れ、
//   ボードは WROVER なら「ESP32 Wrover Module」、WROOM なら「ESP32 Dev Module」を選ぶ。
//   USB シリアルモニタ（115200bps）に、受け取った命令と返事が表示される。

#include "BluetoothSerial.h"

// 注意：#error の行は日本語にしない（読み飛ばされる行でもコンパイルエラーになるため）

#if !defined(CONFIG_BT_ENABLED) || !defined(CONFIG_BLUEDROID_ENABLED)
#error Bluetooth is not enabled. Check the board selection (ESP32 Wrover Module / ESP32 Dev Module).
#endif
#if !defined(CONFIG_BT_SPP_ENABLED)
#error Bluetooth Classic (SPP) is not available. Use the original ESP32 (not S2/S3/C3).
#endif

const char *BT_NAME = "HANGER-ESP32";  // ラズパイの Bluetooth 一覧に出る名前
const int HANGER_COUNT = 20;           // ラズパイ側 body/config.py の HANGER_COUNT と同じにする
const int LED_PIN = 2;                 // ボード上の LED（Freenove の ESP32 ボードは GPIO2）
const int CMD_MAX = 32;               // 1 行の最大文字数。これより長い行は捨てる

BluetoothSerial SerialBT;
String line = "";
bool overflow = false;

// 関数の宣言（定義より前の場所で使うため）
void reply(const String &text);
void handleCommand(const String &cmd);
void doGet(int hanger);
void doPut(int hanger, float shoulderCm);

void onBtEvent(esp_spp_cb_event_t event, esp_spp_cb_param_t *param) {
  if (event == ESP_SPP_SRV_OPEN_EVT) {
    Serial.println("[BT] ラズパイがつながりました");
  } else if (event == ESP_SPP_CLOSE_EVT) {
    Serial.println("[BT] ラズパイとの接続が切れました");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  SerialBT.register_callback(onBtEvent);
  SerialBT.begin(BT_NAME);
  Serial.print("[BT] 待ち受け開始: ");
  Serial.println(BT_NAME);
}

void loop() {
  while (SerialBT.available()) {
    char ch = SerialBT.read();
    if (ch == '\n') {
      if (overflow) {
        reply("ERR:TOO_LONG");
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

void reply(const String &text) {
  SerialBT.println(text);   // \r\n で終わる。ラズパイ側は \r を無視する
  Serial.print("-> ");
  Serial.println(text);
}

void handleCommand(const String &cmd) {
  Serial.print("<- ");
  Serial.println(cmd);

  if (cmd == "PING") {
    reply("PONG");
    return;
  }

  // 「種類:番号」または「種類:番号:肩幅」に分ける
  int p1 = cmd.indexOf(':');
  if (p1 < 0) {
    reply("ERR:BAD:" + cmd);
    return;
  }
  String kind = cmd.substring(0, p1);
  int p2 = cmd.indexOf(':', p1 + 1);
  String numText = (p2 < 0) ? cmd.substring(p1 + 1) : cmd.substring(p1 + 1, p2);
  int hanger = numText.toInt();
  if (hanger < 1 || hanger > HANGER_COUNT) {
    reply("ERR:RANGE:" + cmd);
    return;
  }

  if (kind == "GET") {
    reply("OK:" + cmd);   // 先に受け付けたことを返す（動作に時間がかかってもラズパイを待たせない）
    doGet(hanger);
  } else if (kind == "PUT") {
    float shoulderCm = (p2 < 0) ? 0 : cmd.substring(p2 + 1).toFloat();
    reply("OK:" + cmd);
    doPut(hanger, shoulderCm);
  } else {
    reply("ERR:UNKNOWN:" + cmd);
  }
}

// ---- ここから下を、モーターなどの実際の動きに置き換えていく ----

void doGet(int hanger) {
  // 仮の動き：番号の回数だけ LED を点滅
  for (int i = 0; i < hanger; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(150);
    digitalWrite(LED_PIN, LOW);
    delay(150);
  }
}

void doPut(int hanger, float shoulderCm) {
  // 仮の動き：LED を 1 秒点灯
  Serial.print("PUT hanger ");
  Serial.print(hanger);
  Serial.print(" shoulder ");
  Serial.println(shoulderCm);
  digitalWrite(LED_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_PIN, LOW);
}
