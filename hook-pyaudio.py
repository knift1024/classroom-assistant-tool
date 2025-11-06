# hook-pyaudio.py
from PyInstaller.utils.hooks import collect_dynamic_libs

# PyAudio 包含一個底層的 C 函式庫 (_portaudio.pyd)，它是一個二進位檔案。
# 使用 collect_dynamic_libs 可以確保這個二進位檔案及其依賴被正確地包含進來。
# 這比只複製元數據 (copy_metadata) 更為穩健。
binaries = collect_dynamic_libs('pyaudio')
datas = []
