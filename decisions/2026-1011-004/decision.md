# 提供一行安裝入口

日期：2026-10-11（Asia/Taipei）

## 決策

提供 repository 內的 `install.sh`，讓其他 Mac 使用者以 `curl -fsSL …/install.sh | sh` 安裝 deep-sleep。使用者將自行把 repository 改為 public。

## 對話依據

使用者在討論一行安裝方式後明確要求：「新增這指令, 我會調整設定把 repo 改為 public」。

## 背景與影響

讓使用者不必 clone 整個 repository 即可安裝 CLI。安裝器建立設定範本、保留既有設定並提供 PATH 指引；各台電腦的卸載清單仍由使用者設定。
