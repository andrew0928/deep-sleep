# CLI 內建人類與 agent 操作指引

日期：2026-10-11（Asia/Taipei；依對話回填）。

## 決策

CLI 符合一般命令列慣例。提供 `--help` 給人閱讀，以及 `--skill [topic-id]` 給 agent 讀取；topic-id 為選用，可按主題或使用案例提供不同指引。

## 對話依據

> 同時我要追加 --skill [topic-id], 會用 skill 的方式顯示給 agent 的操作指引

> 這些是為了方便讓 agent 能掌握用法的設計, 而不需要使用者另外安裝搭配的 skill / plugin

## 背景與影響

指引隨 CLI 一起交付，agent 可以透過指令自行取得用法。第一版提供 overview、sleep、configuration、recovery 四個主題；這些具體名稱是實作選擇，使用者要求的是可選主題與免額外安裝。
