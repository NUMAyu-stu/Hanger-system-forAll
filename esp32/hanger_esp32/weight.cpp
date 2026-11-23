// weight.cpp
// ロードセルで重さを測り、乾燥を判定する（重量担当）。まだ中身はない。
// 使うピン（GPIO4・5 の予定）は pins.h に書くこと。
//
// 予定している流れ
//   1. 重さを測る（キャリブレーション済みの値で g に直す）
//   2. 時間ごとの重さの変化を記録する
//   3. 変化が一定時間小さくなったら「乾燥候補」
//   4. 実験で決めた条件を満たしたら「乾燥完了」→ weightDryingComplete() が true を返す

#include <Arduino.h>
#include "weight.h"
#include "pins.h"

void weightSetup() {
  // ロードセルの初期設定
}

void weightLoop() {
  // 重さを測って乾燥を判定する
}

bool weightDryingComplete() {
  return false;   // 判定ができるまでは、ずっと「まだ乾いていない」
}
