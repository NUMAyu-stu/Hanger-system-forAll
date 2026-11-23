// bt_command.h
// ラズパイとの Bluetooth のやりとり（本体担当）
#pragma once

#include <Arduino.h>

const int HANGER_COUNT = 20;   // ラズパイ側 body/config.py の HANGER_COUNT と同じにする

void btSetup();
void btLoop();
void btSend(const String &text);   // ラズパイへ 1 行送る
