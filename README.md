# deep-sleep

在 macOS 睡眠前卸載指定 volumes，完整喚醒後重新掛載。使用系統內建 Bash 3.2、`diskutil`、`pmset` 與 `PlistBuddy`，執行時不需 Homebrew、Python、額外 skill 或 plugin。

需求、設計決策與驗收狀態記錄於 [docs/requirements.md](docs/requirements.md)。

專案的關鍵設計決策依發生順序保存於 [decisions/index.md](decisions/index.md)。收到新的設計決策時，依索引中的記錄方式新增獨立紀錄並更新索引；一般操作要求不列入。

## 快速開始

在一般 macOS 終端機中執行：

```sh
./deep-sleep --help
./deep-sleep --dry-run --volume "/Volumes/My Backup"
./deep-sleep --volume "/Volumes/My Backup"
```

最後一行會卸載磁碟並讓電腦睡眠。保持程式執行，喚醒後會自動恢復掛載。`--dry-run` 只讀取設定、磁碟資訊與電源狀態，顯示 UUID 和預計操作。

想在任何目錄使用，可將單一腳本放進 `PATH`，例如：

```sh
mkdir -p "$HOME/.local/bin"
install -m 755 deep-sleep "$HOME/.local/bin/deep-sleep"
```

若尚未設定，將 `export PATH="$HOME/.local/bin:$PATH"` 加入 shell 設定檔。腳本包含全部操作指引，不需要複製其他檔案。版本可用 `deep-sleep --version` 查詢。

## 設定檔

預設讀取 `~/.deep-sleep/.env`：

```dotenv
# 每個 volume 一行；依檔案順序處理，數字用來識別設定項目。
DEEP_SLEEP_VOLUME_1="/Volumes/My Backup"
DEEP_SLEEP_VOLUME_2="/Volumes/Archive"
```

首次設定可複製範本，再改成自己的 volumes：

```sh
mkdir -p "$HOME/.deep-sleep"
cp -n examples/config.env "$HOME/.deep-sleep/.env"
```

也可填入 `diskutil info /Volumes/Archive` 顯示的 **Volume UUID**。長期設定建議使用 UUID，磁碟改名後仍能辨識。不接受 `disk4s1` 等可能變動的裝置編號。

掛載路徑若只有大小寫或別名差異，會以檔案系統目錄識別確認是否為同一個掛載點；不會直接將路徑轉成小寫比較。指向 volume 內部子目錄的路徑仍會被拒絕。

```sh
deep-sleep                              # 使用預設設定
deep-sleep --config ./nightly.env       # 指定設定檔
deep-sleep --volume /Volumes/Archive --volume "/Volumes/My Backup"
```

命令列有 `--volume` 時，會完全取代設定檔清單；即使同時傳入 `--config`，也不讀取該檔案。沒有 volumes 或找不到設定檔時會報錯，不睡眠。

設定語法為 `DEEP_SLEEP_VOLUME_<正整數>=值`，不接受前置零或重複 key。支援空白行、整行 `#` 註解、CRLF、等號旁空白、單引號與雙引號。未加引號的值不能包含空白、引號或 `#`。加引號的值必須在同一行，不能包含相同種類的內部引號。所有值均為字面文字，不支援跳脫、行尾註解、`export`、變數／`~` 展開或命令替換。程式不會 `source` 或 `eval` 設定，也不讀取同名環境變數。

## CLI 與 agent 指引

```sh
deep-sleep --help
deep-sleep --skill
deep-sleep --skill sleep
deep-sleep --skill configuration
deep-sleep --skill recovery
deep-sleep --recover --dry-run
deep-sleep --recover
```

`--skill [topic]` 輸出帶有 name／description frontmatter 的 Markdown 操作指引，供 agent 直接讀取；省略 topic 顯示總覽與主題索引。未知 topic 回傳錯誤。說明、計畫與 skill 輸出到 stdout；執行進度與錯誤輸出到 stderr。說明類參數不存取磁碟或電源服務。

## 執行與恢復行為

1. 在任何卸載前，先檢查全部 targets，解析 UUID、原始掛載狀態及唯讀屬性，並去除重複項目。
2. 跳過原本未掛載的 volume；對已掛載者先寫入恢復紀錄，再執行 `diskutil unmount UUID`。
3. 卸載全部成功並確認狀態後，執行標準的 `pmset sleepnow`。
4. 觀察新的睡眠紀錄及同一週期後續的完整 Wake，並確認目前有 CPU／Graphics 能力且無待執行的電源轉換。
5. 以 UUID 掛載本次記錄的 volumes；唯讀 volume 使用 `diskutil mount readOnly UUID`。每個 volume 最多嘗試五次，間隔兩秒。成功後刪除恢復紀錄。

一般卸載失敗會取消睡眠，並嘗試恢復先前的掛載。`pmset sleepnow` 失敗也會嘗試恢復。程式不強制卸載、不 eject、不自動呼叫 sudo，也不調整休眠設定。掛載位置由 macOS 決定，不保證保留原先路徑名稱；其他自訂 mount options 不會還原。

`pmset sleepnow` 返回不代表已喚醒。第一版每次輪詢 `pmset -g log` 後暫停兩秒，以 UUID 和時間戳識別睡眠紀錄，忽略 DarkWake 及 Wake Requests。尚未看到新睡眠紀錄時，30 次輪詢後以錯誤結束；看到睡眠後則持續等候完整喚醒，不因睡眠時間長而逾時。這個方式依賴 macOS 的記錄格式及寫入時機，並非 OS 通知 API；無法讀取或辨識時會報錯。

發出睡眠請求後若無法確認喚醒，或收到 HUP／INT／TERM，會保留 `~/.deep-sleep/state/pending`，避免在睡眠轉換尚未明確時掛載。睡眠請求前收到這些訊號則會嘗試恢復。終端關閉、SIGKILL、重新開機會中斷自動流程；這不是常駐服務。恢復紀錄在卸載**之前**寫入，因此可能包含尚未完成卸載的 volume；恢復時會跳過已掛載者。

確認電腦已完全醒來後，執行 `deep-sleep --recover`。它依據紀錄恢復，不讀目前的 volume 設定、不睡眠；若磁碟未連接或已鎖定，先重新連接／解鎖再重試。部分失敗會保留整份紀錄，下次恢復會跳過已完成者。存在待恢復紀錄時禁止開始新的睡眠流程。

`~/.deep-sleep/state/lock` 防止同一使用者同時執行。程序被強制終止時可能留下鎖；先查看 `lock/pid`，確認該程序已不存在，才能刪除 `lock/pid` 與空的 `lock` 目錄，再執行恢復。程式不自動移除過期鎖，也不協調其他使用者或外部磁碟管理工具的操作。

## 支援範圍與退出碼

適用於有 Volume UUID 的本機資料 volumes；已掛載者必須位於 `/Volumes/` 下。原本未掛載者須使用 UUID 指定。系統磁碟、網路分享、自訂 mount point、無法讀取資訊的加密鎖定 volumes 均不在第一版範圍。

| 退出碼 | 意義 |
| --- | --- |
| 0 | 成功，或唯讀操作完成 |
| 2 | 參數／設定錯誤 |
| 3 | 前置檢查失敗 |
| 4 | 卸載或睡眠請求失敗，已嘗試恢復 |
| 5 | 無法確認睡眠／完整喚醒，或恢復時電源狀態不符 |
| 6 | 恢復不完整，紀錄保留 |
| 7 | 已有鎖、待恢復紀錄或狀態檔錯誤 |
| 129／130／143 | 收到 HUP／INT／TERM；若恢復失敗則回傳 6 |

## 開發與驗證

```sh
make check     # Bash 語法檢查
make test      # macOS 上的 Python 3 unittest 模擬整合測試
```

`deep-sleep` 為單一可執行腳本；`examples/config.env` 是設定範本；`tests/` 使用模擬磁碟和電源服務，測試不會真的卸載或睡眠。維持 Bash 3.2 相容、四個空白縮排、`ds_` 函式前綴與完整的參數 quoting。修改操作流程時，補上失敗與恢復情境測試。

第一版已用模擬流程驗證，並核對本機實際電源記錄的解析結果。開發沙箱無法存取 DiskManagement，因此尚未完成真實磁碟睡眠／喚醒測試。手動驗收請選擇測試用 volume，先執行 dry-run，再執行睡眠並喚醒，確認掛載恢復及退出碼；也應驗證忙碌磁碟會取消睡眠，以及醒來時未連接磁碟可稍後 `--recover`。

電源記錄與狀態格式依據本機 `man pmset` 及 [Apple PowerManagement 的 pmset 原始碼](https://github.com/apple-oss-distributions/PowerManagement/blob/main/pmset/pmset.m) 核對。macOS 改版若改變輸出格式，需重新驗證解析器。
