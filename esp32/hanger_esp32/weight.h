// weight.h
// ロードセルで重さを測り、乾燥を判定する（重量担当）
#pragma once

void weightSetup();
void weightLoop();               // 毎回の loop で呼ばれる。長く止まらないこと
bool weightDryingComplete();     // 乾燥が完了したら true
