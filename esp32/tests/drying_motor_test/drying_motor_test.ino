// drying_motor_test.ino
// 乾燥完了の判定とモーター制御をつなぐためのテスト用スケッチ（重量計測担当から共有されたもの）。
// 乾燥判定はまだできていないので、loop の中で「乾燥完了」と仮定している。
// モーターを 1 回だけ動かす部分を、モーター担当がここに書いて単体で確かめる。
//
// 本番用の esp32/hanger_esp32/ とは別のスケッチ（setup / loop が別々）なので、書き込むときはどちらか一方だけ。
// ここで動いたモーターのコードは、本番用の motor.cpp に移す。
//
// ---- ピンの割り当て ----（本番用では esp32/hanger_esp32/pins.h にまとめている）
//   GPIO4, GPIO5 : 重量計測（ロードセル）で使う予定。モーターでは使わない
//   GPIO2        : ボード上の LED

bool dryingComplete = false;
bool motorActivated = false;

void setup() {
  Serial.begin(115200);
  // モーターの初期設定
}

void loop() {
  // テスト用に乾燥完了と仮定
  dryingComplete = true;

  if (dryingComplete && !motorActivated) {
    motorActivated = true;

    // ここにモーターを動かすコードを追加
  }
}
