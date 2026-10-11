# deep-sleep 需求規格

更新：2026-10-11（Asia/Taipei）。本文件定義目前版本的可驗收行為；每個 R 編號對應 [implementation](implementation.md) 的 I 編號。舊版設定檔決策由[新決策](../decisions/2026-1011-005/decision.md)取代。

| ID | 需求與驗收條件 |
| --- | --- |
| R-01 | 不需設定檔。預設列出目前已掛載、位於 `/Volumes/`、具有 Volume UUID、由外接實體磁碟承載的資料 volumes；包含該磁碟上的 APFS volumes。忽略舊 `.env`。找不到目標時不睡眠。 |
| R-02 | `--dry-run` 列出全部預計卸載與恢復的目標和模式，不卸載、不掛載、不睡眠、不寫 run 狀態。`--volume` 可供單次明確指定，取代預設探索。`--config` 拒絕並提示遷移。 |
| R-03 | 在任何卸載前驗證全部目標的 UUID、掛載點、唯讀模式及電源狀態。卸載前重新檢查。一般卸載失敗取消睡眠並回復已卸載 volumes；不 force、eject、sudo 或改電源設定。 |
| R-04 | `pmset sleepnow` 返回後，只能在觀察本次新的 Sleep、同週期完整 Wake，且 `systemstate` 顯示完全醒來且沒有待轉換狀態後恢復掛載。DarkWake、Wake Requests、舊事件及單純逾時均不得觸發恢復。 |
| R-05 | 每次實際 run 在卸載前持久記錄 UUID 和讀寫模式，以 UUID 重新辨識並恢復；唯讀維持唯讀。恢復最多重試五次，已掛載的 UUID 不重複掛載。 |
| R-06 | `state/runs/RUN_ID.tsv` 保存每次 run 的事件流水帳；`state/active` 指向未完成 run，`state/pending` 保存本次待恢復操作。完成後保留流水帳，清除 active/pending。所有狀態在 `~/.deep-sleep/state/`，權限限目前使用者。舊版 pending 可恢復。 |
| R-07 | 喚醒後若 volume 無法由 UUID 取得資訊，記錄 `MISSING` 與未解決事項，清除 active/pending，允許下一次 run；重新接上後可用 run ID 補救。若 volume 存在但掛載失敗，保留 active/pending，阻擋新 run。尚未實作 T500 白名單或特殊警告。 |
| R-08 | 提供 `runs list/show/recover/dismiss/prune --before`。list/show 唯讀；recover 補掛載歷史未解決 UUID；dismiss 明確放棄一個 UUID；prune 只刪除指定日期以前、無未解決 UUID 的 run。變更恢復狀態的命令須由 lock 序列化。 |
| R-09 | 說明、version、skill 輸出不觸發磁碟／電源操作；一般操作啟動時在 stderr 顯示與 `--version` 相同的版本。安裝器只安裝可執行檔，不產生設定檔，也不執行睡眠。 |

## 範圍與風險

這是使用者前景程序，不提供開機後自動恢復。網路分享、系統磁碟、自訂掛載點及無 Volume UUID 的 volumes 不在預設探索範圍。掛載位置由 macOS 決定。`pmset` 回傳失敗但睡眠仍發生的競態仍需真機驗收；目前會嘗試 rollback。磁碟突然拔除時的 `MISSING` 判斷取決於 `diskutil info UUID` 的可用性。

## 驗收狀態

- [x] 模擬外接 APFS 探索、完整循環、DarkWake、失敗恢復、離線與歷史維護命令。
- [x] 本機唯讀 dry-run 辨識 `/Volumes/T500-Work` 和 `/Volumes/T500-Media`。
- [ ] 真實卸載、睡眠、喚醒、掛載的完整循環。
- [ ] 真機忙碌磁碟及睡眠期間拔除磁碟的情境。
