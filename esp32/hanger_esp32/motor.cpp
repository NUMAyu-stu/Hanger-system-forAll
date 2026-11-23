// motor.cpp
// ハンガーを動かす（モーター担当）。今はモーターの代わりにボード上の LED で知らせている。
// モーターをつないだら、この中身を書き換える。使うピンは pins.h に足すこと（GPIO4・5 は重量用なので使わない）。
//
// 注意：今の仮の動きは delay で止まるので、点滅している間は Bluetooth の命令も重さの計測も止まる。
// モーターに置き換えるときは、motorGet / motorPut では「動き始め」だけを決め、
// 実際に少しずつ動かすのは motorLoop で行う形にすると、ほかの処理を止めずに済む。

#include <Arduino.h>
#include "motor.h"
#include "pins.h"

void motorSetup() {
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
}

void motorLoop() {
  // 今はすることがない
}

void motorGet(int hanger) {
  // 仮の動き：番号の回数だけ LED を点滅
  for (int i = 0; i < hanger; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(150);
    digitalWrite(LED_PIN, LOW);
    delay(150);
  }
}

void motorPut(int hanger, float shoulderCm) {
  // 仮の動き：LED を 1 秒点灯
  Serial.print("PUT hanger ");
  Serial.print(hanger);
  Serial.print(" shoulder ");
  Serial.println(shoulderCm);
  digitalWrite(LED_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_PIN, LOW);
}
