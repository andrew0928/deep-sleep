# deep-sleep

macOS 睡眠前自動卸載目前已掛載的外接實體磁碟資料 volumes，完整喚醒後依本次清單恢復掛載。使用內建 Bash 3.2、`diskutil`、`pmset` 和 `PlistBuddy`，不需設定檔或額外執行時套件。

[需求與驗收](docs/requirements.md)逐項對照[實作規格](docs/implementation.md)。[設計決策](decisions/index.md)保留版本演進；[研究索引](docs/research/index.md)整理外接 SSD 睡眠發熱資料。

版本變更見 [release notes](CHANGELOG.md)。

**目前版號的唯一來源**是執行檔 [deep-sleep](deep-sleep) 開頭的 `ds_version`。`--version` 與一般操作啟動時的版本訊息都由它產生；`CHANGELOG.md` 的最上方版本是發行紀錄，測試會檢查兩者一致。下一次發版只需在腳本修改 `ds_version` 並新增對應的 release note，不另設版本設定檔，確保單行安裝的腳本可獨立運作。

## 安裝與使用

```sh
curl -fsSL https://raw.githubusercontent.com/andrew0928/deep-sleep/main/install.sh | sh
~/.local/bin/deep-sleep --dry-run
~/.local/bin/deep-sleep
```

安裝器只安裝 `~/.local/bin/deep-sleep`，不建立或讀取 `.env`；既有 `~/.deep-sleep/.env` 會留在原位，但程式忽略它。請先核對 dry-run 顯示的所有 volumes，再執行會真正卸載磁碟及要求睡眠的命令。讓前景程序維持執行直到醒來。若沒有符合條件且已掛載的 volume，程式會取消睡眠。

預設從外接實體磁碟及其 APFS 容器選出位於 `/Volumes/` 下、有 Volume UUID 的已掛載資料 volumes。可用 `--volume /Volumes/Archive` 或 `--volume UUID` 做單次明確指定；此時不做自動探索。`--config` 已停用。白名單／特別警告尚未實作。

## 紀錄與維護

```sh
deep-sleep runs list
deep-sleep runs show RUN_ID
deep-sleep --recover --dry-run
deep-sleep --recover
deep-sleep runs recover RUN_ID
deep-sleep runs dismiss RUN_ID UUID
deep-sleep runs prune --before 2026-10-01
```

每次實際循環在 `~/.deep-sleep/state/runs/RUN_ID.tsv` 留下 UTF-8、tab 分隔的事件流水帳；欄位為 UTC 時間、事件、Volume UUID、掛載模式。`state/active` 指向目前未完成的 run，`state/pending` 是這次待恢復 UUID 與模式的可操作清單。每筆 `INTENT` 在卸載前寫入；醒來後有 `RESTORED`、`MISSING` 或 `RECOVERY_REQUIRED` 等事件。正常完成保留流水帳，移除 `active` 與 `pending`。舊版 `state/pending` 仍可用 `--recover` 處理。

若醒來時某顆磁碟已不在系統中，run 記為 `MISSING` 與 `INCOMPLETE`，不阻擋下一次睡眠；重新接上後用 `runs recover RUN_ID` 補掛載。若磁碟仍可辨識卻掛載失敗，保留 active/pending，阻擋新循環，處理原因後執行 `--recover`。`runs dismiss RUN_ID UUID` 在完整喚醒狀態下明確放棄該 UUID 的補救要求；`runs prune` 僅清除指定日期以前、無未解決 UUID 的歷史。`runs list/show` 不修改狀態，`--dry-run` 不建立 run。

準備階段任一卸載失敗會取消睡眠並嘗試恢復。`sleepnow` 返回不算喚醒證據：程式等待本次新 Sleep、同一週期的完整 Wake，並檢查 `systemstate`；DarkWake 不觸發掛載。請勿自行刪除 `active` 或 `pending` 來略過失敗。`state/lock` 保護同一使用者的並行操作；強制終止留下鎖時，先核對 `lock/pid` 的程序確已結束。

## 開發驗證

```sh
make check
make test
```

測試以模擬磁碟與電源服務執行，沒有真的卸載或睡眠。已在本機唯讀 dry-run 驗證 APFS 外接磁碟探索；真實睡眠循環仍待手動驗收。其他選項與退出碼見 `deep-sleep --help`，agent 指引見 `deep-sleep --skill`。
