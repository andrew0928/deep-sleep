# Release notes

## 0.2.0 — 2026-10-11

- 預設自動探索已掛載的外接實體磁碟資料 volumes，包含 APFS volumes；不再需要 `.env`。`--volume` 仍可用於單次指定，`--config` 已停用。
- 每次執行保留 `~/.deep-sleep/state/runs/` 事件紀錄；新增 `runs list/show/recover/dismiss/prune`，並保留舊版 `pending` 的恢復能力。
- 喚醒後若磁碟已離線，將未解決項目留在 run 紀錄中供重新連接後補掛載，不阻擋下一次循環；可辨識但掛載失敗的磁碟仍保留 active recovery。
- 安裝器不再下載或建立設定檔。新增[需求與實作對照](docs/implementation.md)及外接 SSD 睡眠行為的[研究紀錄](docs/research/index.md)。
- 一般操作啟動時會在 stderr 顯示目前版本；`--version` 使用同一個版本值。

驗證：46 項模擬整合測試通過；本機唯讀 dry-run 正確辨識 `T500-Work` 與 `T500-Media`。真實卸載、睡眠、喚醒、掛載循環及拔除磁碟情境仍待正式驗收。

## 0.1.0

首次提供手動指定 volumes、睡前卸載、完整喚醒後恢復掛載，以及單行安裝器。
