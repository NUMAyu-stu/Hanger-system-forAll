// motor.h
// ハンガーを動かす（モーター担当）
#pragma once

void motorSetup();
void motorLoop();                              // 毎回の loop で呼ばれる。長く止まらないこと
void motorGet(int hanger);                     // GET:<番号> を受けたとき
void motorPut(int hanger, float shoulderCm);   // PUT:<番号>:<肩幅> を受けたとき
