# deep-sleep 需求與驗收紀錄

更新日期：2026-10-11。本文整理使用者提出的需求、已同意的設計與目前驗證狀態；操作方式詳見 [README](../README.md)。

## 1. 目的與實作原則

提供 macOS CLI `deep-sleep`，依序完成：

1. 自動卸載使用者指定的一個或多個 volumes。
2. 執行標準系統睡眠命令 `pmset sleepnow`。
3. 系統從睡眠完整喚醒後，重新掛載指定 volumes。

能用 shell script 完成時，優先使用 shell script。已同意的第一版採用 macOS 內建 Bash 3.2、`diskutil`、`pmset` 與 `PlistBuddy`，不增加執行時套件依賴。需求中的 sleep 指標準系統睡眠，不要求修改 hibernation 或其他電源設定。

## 2. CLI 介面

介面應符合一般 CLI 慣例，提供可讀的錯誤訊息與明確退出碼。

| 介面 | 要求／已同意的用途 |
| --- | --- |
| `deep-sleep` | 依預設設定執行卸載、睡眠及恢復流程 |
| `--volume VOLUME` | 指定掛載路徑或 Volume UUID；可重複指定多個 volumes |
| `--config FILE` | 使用指定設定檔 |
| `--dry-run` | 檢查設定與目標，顯示預計操作，不卸載、不掛載、不睡眠 |
| `--help` | 提供給人閱讀的操作指引與範例 |
| `--skill [topic-id]` | 輸出內建的 agent 操作指引；topic-id 為選用 |
| `--recover` | 恢復中斷或失敗流程所記錄的掛載 |
| `--version` | 顯示版本 |

`--skill` 旨在讓 agent 直接掌握用法，使用者不需另外安裝搭配的 skill 或 plugin。省略 topic-id 時顯示總覽與主題索引；第一版主題為 `overview`、`sleep`、`configuration`、`recovery`。未知 topic 應報錯。指引採 Markdown，包含前置條件、命令、失敗處理及注意事項。

說明、skill 與操作計畫輸出到 stdout；進度及錯誤輸出到 stderr。說明類參數不應觸發磁碟或電源操作。

## 3. 設定檔

使用者要求加入設定檔，可採 `.env` 或 `~/.deep-sleep/config.toml`；已選定並獲同意的方式是 **`~/.deep-sleep/.env`**。

```dotenv
DEEP_SLEEP_VOLUME_1="/Volumes/SG-Backup"
DEEP_SLEEP_VOLUME_2="01234567-89AB-CDEF-0123-456789ABCDEF"
```

- 每個 volume 一行，使用 `DEEP_SLEEP_VOLUME_<正整數>`，依檔案順序處理。
- 預設讀取 `~/.deep-sleep/.env`；`--config` 選用另一個檔案。
- 命令列的 `--volume` 清單完全取代設定檔清單，不合併；有明確 volumes 時不讀設定檔。
- 未指定任何 volume、未知 key、重複 key、空值或格式錯誤時，應回報錯誤，不進入睡眠。
- 設定僅作為資料解析，不使用 `source` 或 `eval`，不執行命令或展開變數。
- 支援空白行、整行註解、CRLF 與引號包住的值。完整語法限制見 README 與 `--skill configuration`。

長期設定優先使用 Volume UUID，避免磁碟改名或 BSD 裝置編號變動影響恢復。

## 4. 睡眠／喚醒的非同步時序

使用者曾遇到 `pmset sleepnow` 返回後，電腦仍短暫醒著，下一行 restore 已開始執行，電腦才真正睡眠的情況。這是本專案必須處理的時序問題。

驗收要求：

- **不能將 `sleepnow` 返回視為已睡眠或已喚醒。**
- restore 必須等待本次睡眠之後的完整喚醒，不能使用先前殘留的 Sleep／Wake 記錄判斷。
- 背景維護喚醒（DarkWake）及預定喚醒請求（Wake Requests）不能觸發 restore。
- timeout 是失敗界線，不能把時間到視為完成，也不能因逾時而直接 restore。

目前第一版採用狀態輪詢：先保存睡眠紀錄 baseline，再執行 `sleepnow`；從 `pmset -g log` 確認新的 Sleep 及同一週期後續的完整 Wake，並以 `pmset -g systemstate` 確認目前已完整醒來、沒有待執行的電源轉換，才掛載。

每次輪詢後暫停兩秒；未看到新 Sleep 時，30 次輪詢後報錯並保留恢復紀錄。看到 Sleep 後，持續等候完整喚醒，不限制睡眠時間。這是記錄與狀態輪詢，不是直接訂閱 OS 通知；真機驗收仍須確認記錄寫入時機與解析結果。

已知待釐清的錯誤路徑：目前 `sleepnow` 回傳失敗時會直接嘗試 rollback，未經同樣的喚醒門檻。它尚未證實能涵蓋「回傳失敗但系統仍準備睡眠」的情境，不能將它當成已有完整同步保證。

## 5. Volume 操作與恢復

已同意的第一版行為：

- 卸載前檢查全部目標，記錄 UUID、原始掛載狀態及唯讀屬性，並去除重複 volumes。
- 正常卸載，不強制卸載；任一卸載失敗就取消睡眠，嘗試恢復先前的掛載。
- 原本未掛載的 volume 不應在醒來後被主動掛載。
- 恢復以 UUID 重新辨識磁碟，保留唯讀狀態；不自動提升權限。
- 在卸載前保存恢復紀錄；中斷或恢復失敗後可用 `--recover` 重試。
- 有待恢復紀錄時，禁止開始另一個睡眠流程；同一使用者的並行執行以鎖保護。

第一版支援具有 Volume UUID 的本機資料 volumes；已掛載者必須位於 `/Volumes/` 下。網路分享、系統 volumes、自訂 mount point 與無法讀取資訊的鎖定 volumes 不在目前範圍。前景程序需持續存在到喚醒後；常駐服務及重開機後自動恢復未列入第一版。

## 6. 測試標的與驗收

使用者指定測試標的為 `/volumes/sg-backup`；系統回傳的實際掛載點為 **`/Volumes/SG-Backup`**。設定使用 `/Volumes/sg-backup` 時，應辨識同一目錄，而非因字串大小寫差異誤判成子目錄。不能直接將所有路徑轉成小寫，真正的子目錄仍須拒絕。

已修正的相容性問題：`diskutil info -plist` 應使用 `WholeDisk` 欄位，並由 `MountPoint` 判斷是否掛載；不能假設存在文字輸出中的 `Whole` 或 `Mounted` 欄位。

驗收清單：

- [x] CLI、設定解析、內建 skill topics 與錯誤處理的模擬測試。
- [x] 卸載失敗回復、唯讀恢復、UUID 去重、掛載重試與中斷恢復的模擬測試。
- [x] `sleepnow` 提早返回、DarkWake、完整喚醒尚未就緒及逾時不掛載的模擬測試。
- [x] 修正 plist 欄位與掛載點大小寫問題；確認兩種大小寫路徑指向同一目錄。
- [x] 真機 `SG-Backup` 的 dry-run 成功驗收。
- [ ] 真實卸載 → 睡眠 → 喚醒 → 掛載的完整循環驗收。
- [ ] 真機驗證忙碌磁碟取消睡眠、磁碟離線後可重新連接並恢復。

CLI 的 38 個模擬測試通過。更新權限後，已完成包含 SG-Backup、WD-TimeMachine、WD-Temp、T500-Media、T500-Work 的真機 dry-run；尚未完成真實磁碟睡眠循環。

## 7. 版本控制與 GitHub 交付

使用者要求初始化 Git，並將專案 push 至 GitHub 帳號 **`andrew0928`** 下的 **private** repository，名稱為 `deep-sleep`。

認證應交由使用者輸入。開啟認證流程時使用系統預設瀏覽器，不指定瀏覽器；使用者慣用 Edge，以保留其既有登入資訊。不得將 credential、token 或使用者實際 `.env` 加入 repository。

第一版已推送至 `andrew0928/deep-sleep`，當時確認 visibility 為 private；後續使用者決定自行改為 public，供一行安裝使用。

## 8. 其他電腦的安裝

使用者決定新增 `curl -fsSL …/install.sh | sh` 安裝方式，並將自行把 repository 改為 public，讓其他使用者不需 clone repository 即可安裝。安裝器支援 macOS，安裝至 `~/.local/bin/deep-sleep`；缺少設定時建立範本，已有設定時保留。提供 PATH 與修改 volumes 的指引，不自動修改 shell 設定或執行睡眠。
