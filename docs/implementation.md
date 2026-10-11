# deep-sleep 運作機制與實作對照

此文件對照 [requirements](requirements.md) 的編號。程式入口是 repository 根目錄的 `deep-sleep`，以 macOS Bash 3.2 執行。`tests/fake_system.py` 模擬 `diskutil`、`pmset`；`tests/test_cli.py` 驗收流程；`tests/test_install.py` 驗收安裝器。

| 需求 | 實作位置 | 驗證重點 |
| --- | --- | --- |
| R-01 | `ds_discover`, `ds_preflight` | `diskutil list -plist external physical` 決定實體來源；`external` 清單查其 partitions 及 APFS 容器，後者須以 `APFSPhysicalStores` 連到外接實體磁碟。只有清單上已有 `/Volumes/` MountPoint 的 volume 才進候選；再以 `diskutil info -plist` 讀 UUID、掛載與唯讀資訊。 |
| R-02 | `ds_main` 參數解析與 dry-run 分支 | dry-run 在 `ds_new_run` 前返回；明確 `--volume` 跳過 `ds_discover`。舊 `.env` 完全不讀；`--config` 提示停用。 |
| R-03 | `ds_preflight`, `ds_main` 卸載迴圈, `ds_cleanup` | 全部先檢查；每筆在卸載前重驗身分及狀態。準備階段失敗時 cleanup 呼叫 `ds_restore`。 |
| R-04 | `ds_power_log`, `ds_full_wake`, `ds_wait_for_wake` | 以睡眠前 baseline 對照新 Sleep；FullWake 加 `systemstate` 才恢復。未見新 Sleep 時 30 次、每次 2 秒後失敗；見到 Sleep 後無睡眠時間上限。 |
| R-05 | `ds_new_run`, `ds_event`, `ds_restore`, `ds_mounted` | `INTENT` 和 pending 在 unmount 前落盤；以 UUID mount，唯讀使用 `diskutil mount readOnly`；五次重試且核對實際掛載狀態。 |
| R-06 | `ds_new_run`, `ds_close_run`, `ds_load_pending`, `ds_lock` | run 日誌持續保留；active/pending 是本次恢復操作狀態；lock 用原子 `mkdir`。無 active 的舊 pending 仍可由 `--recover` 處理。 |
| R-07 | `ds_restore`, `ds_runs_command recover` | 五次嘗試後，`diskutil info UUID` 不可用記 `MISSING`，run 標 `INCOMPLETE` 並釋放 active；若 info 可用則 pending 保留並記 `RECOVERY_REQUIRED`。 |
| R-08 | `ds_runs_command`, `ds_run_outstanding`, `ds_run_path` | 由 INTENT 扣除 RESTORED/DISMISSED 重建未解決 UUID；MISSING 只是事件，並非結案。prune 只處理無未解決 UUID 的舊 run。 |
| R-09 | `ds_version`, `ds_help`, `ds_skill`, `ds_main`, `install.sh` | 腳本頂部的 `ds_version` 是唯一版號來源。一般操作以 `ds_log` 在 stderr 報告它；`--version` 讀取同一個值。測試核對 release note 最新標題一致。查詢類參數在磁碟操作前返回；安裝器只下載、驗證及替換腳本。 |

## 狀態格式與生命週期

`RUN_ID` 格式為 UTC `YYYYMMDDTHHMMSSZ-PID-RANDOM`。每個 `runs/RUN_ID.tsv` 是逐行追加的 UTF-8 TSV，四欄依序為 `UTC_TIMESTAMP<TAB>EVENT<TAB>UUID<TAB>MODE`，無適用值用 `-`。事件包括 `START`、`INTENT`、`UNMOUNTED`、`SLEEP_REQUESTED`、`FULL_WAKE`、`RESTORED`、`MISSING`、`RECOVERY_REQUIRED`、`RECOVERY_STARTED`、`WAKE_UNCONFIRMED`、`DISMISSED`、`DONE`、`INCOMPLETE`。不可直接編輯流水帳。

`state/pending` 仍採舊版每行 `UUID readWrite|readOnly` 格式，用於當前可重試操作。`state/active` 一行 RUN_ID；`state/lock/pid` 一行 PID。這些檔案位於使用者 home 的 `~/.deep-sleep/state/`，狀態目錄權限 700，新檔案由 umask 077 建立。成功完成或僅有失聯 volumes 時，active/pending 移除；流水帳保留。連接但掛載失敗時 active/pending 保留；直到 `--recover` 成功或使用者明確 dismiss。歷史失聯 volumes 的補救透過 `runs recover RUN_ID` 重新建立 active/pending。

`runs list/show` 不需 lock；其輸出是讀取當下快照。`runs recover/dismiss/prune` 與睡眠主流程使用同一把 lock。`runs dismiss` 要求目前完全喚醒，避免不確定電源狀態下結案。`runs prune` 用 RUN_ID 的 UTC 日期比較截止日，只刪無未解決 UUID 的歷史；保留 active run。

## 執行時序

```text
探索 → 全部 preflight → 電源 baseline → 建立 run → 每筆 INTENT → unmount
→ SLEEP_REQUESTED → pmset sleepnow → 新 Sleep → FullWake → restore
→ DONE / INCOMPLETE / RECOVERY_REQUIRED
```

若 `sleepnow` 已提出但未確認完整喚醒，`pending` 保留並阻擋新循環。這時需在確定機器已完全醒來後才執行 `--recover`。HUP/INT/TERM 在準備階段觸發回復，在 sleep request 後保留恢復狀態。SIGKILL 與斷電無法捕捉；重啟後可查看 `runs list/show` 與 `--recover --dry-run`。

真機驗證目前只做唯讀 dry-run；完整睡眠與拔除測試仍待手動執行。模擬測試不等同 Disk Arbitration 與實際硬體時序驗證。
