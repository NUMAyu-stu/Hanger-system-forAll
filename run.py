# run.py
# ハンガー管理システムの起動用。このフォルダで  python3 run.py
#
# 本体（body/）はパッケージにしてあるので、画像処理側のファイル名
# （config.py など）と本体のファイル名がぶつかっても問題にならない。

from body.main import main

main()
