// hanger_esp32.ino（無印 ESP32 用：Freenove ESP32-WROVER / ESP32-WROOM など）
// ハンガー側の ESP32 1 台で、次の 3 つを動かす。担当ごとにファイルを分けている。
//
//   bt_command.cpp  ラズパイから Bluetooth Classic で命令を受け、返事をする   … 本体担当
//   motor.cpp       ハンガーを動かす（今は LED で代用）                       … モーター担当
//   weight.cpp      ロードセルで重さを測り、乾燥を判定する（まだ空）           … 重量担当
//   pins.h          使うピンの一覧。ピンを使うときは必ずここに書く             … 全員
//
// このファイルは全体の setup() と loop() だけを持ち、各担当の関数を呼ぶ。
// 各担当の loop 関数は、長く止まらない（delay で何秒も待たない）ように書くこと。
// 1 つが止まると、その間ほかの担当の処理も止まってしまうため。
//
// ---- 書き込み ----
//   Arduino IDE のボードマネージャで「esp32 by Espressif Systems」を入れ、
//   ボードは WROVER なら「ESP32 Wrover Module」、WROOM なら「ESP32 Dev Module」を選ぶ。
//   このフォルダを開くと、ファイルがタブで並ぶ。書き込むとフォルダ全体が 1 つのプログラムになる。
//   USB シリアルモニタ（115200bps）に、受け取った命令と返事が表示される。

#include "bt_command.h"
#include "motor.h"
#include "weight.h"

void setup() {
  Serial.begin(115200);
  motorSetup();
  weightSetup();
  btSetup();
}

void loop() {
  btLoop();       // ラズパイからの命令を受け取り、GET / PUT なら motor を呼ぶ
  motorLoop();
  weightLoop();

  // 乾燥が完了したときに何をするか（ラズパイに知らせる・ハンガーを動かすなど）はまだ決まっていない。
  // ラズパイに知らせる命令を増やすときは、チーム全員で決めてから body/machine.py と一緒に直す。
  // if (weightDryingComplete()) { ... }
}
