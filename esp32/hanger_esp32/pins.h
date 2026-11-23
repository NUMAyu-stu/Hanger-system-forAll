// pins.h
// ESP32 で使うピンの一覧。ピンを使うときは、自分のファイルに直接番号を書かずに、ここに足すこと。
// 同じ番号が 2 回出てきたら、誰かとぶつかっている。
#pragma once

// ---- モーター担当（motor.cpp）----
const int LED_PIN = 2;   // ボード上の LED（Freenove の ESP32 ボードは GPIO2）。モーターができるまでの代用

// ---- 重量担当（weight.cpp）----
// GPIO4, GPIO5 はロードセル（重量計測）で使う予定。どちらを何に使うかは重量担当が決めて書く
// const int WEIGHT_???_PIN = 4;
// const int WEIGHT_???_PIN = 5;
