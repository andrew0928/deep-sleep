# Mac 外接 Thunderbolt SSD：睡眠供電、發熱與替代方案

查證日期：2026-10-11。範圍：Mac mini、Apple silicon、macOS 27，以及外接 TB4／USB4 SSD。價格與相容性以查證當日官方網站為準。

## 原始問題與使用情境

使用者觀察到外接 TB4 SSD 在 Mac 睡眠時仍供電，長時間閒置會持續發熱。使用者曾實測 `hibernatemode 25` 可使 TB4 斷電，但目前 Mac mini + macOS 27 無法使用該模式；提出「是否只有有電池的 Mac 才支援」的假設。

另一項使用者觀察是卸載 SSD 可降低活動與溫度。因此需求不是攔截每次睡眠，而是晚上長時間不用電腦時明確執行 `deep-sleep`：卸載指定 volumes → 標準 sleep → 等待完整喚醒 → 恢復掛載。先前實測 hibernation 的 Mac 型號、晶片、OS 與連接拓撲尚未記錄，不能直接比較兩台機器。

## 查證結論

| 方向 | 結論 | 證據限制 |
| --- | --- | --- |
| (1) `hibernatemode 25` | 官方手冊描述為保存記憶體到磁碟並移除記憶體供電；不能推導為所有 TB4 ports 必定斷電 | 本機沒有列出此功能；未找到 Apple 對 macOS 27 Mac mini「因無電池而移除」的說明 |
| (2) 睡前卸載、醒後掛載 | 有成熟工具實作；適合降低檔案系統活動，但不保證橋接晶片斷電或完全冷卻 | 商用工具主要解決不正常退出磁碟通知，不提供通用的降溫保證 |
| (3) 只在夜間明確執行 | 合理且符合本專案；可由 shell 配合系統工具完成 | 等待喚醒、卸載失敗與恢復處理需要額外邏輯，不能只串接三個命令 |

## (1) Hibernation：已證實的部分與不能泛化的部分

Apple 的 `pmset` 手冊說明：桌機預設 mode 0，筆電預設 mode 3；mode 25 保存記憶體到持久儲存並移除記憶體供電，醒來由磁碟恢復。手冊也明確討論支援 standby 的桌機產生 hibernation image，因此「桌機一概沒有 hibernation」並不成立。手冊描述的斷電對象是記憶體，沒有保證每個外接埠、dock 或 SSD 都失去電源。[Apple pmset 原始手冊](https://raw.githubusercontent.com/apple-oss-distributions/PowerManagement/main/pmset/pmset.1)

Apple 使用者文件將 safe sleep 描述為 Mac 筆電功能；但 safe sleep 保留狀態的說明，不等於所有現代 MacBook 都支援使用 mode 25 強制切斷 TB4 電源，也不能證明 Mac mini 在 macOS 27 被移除了該模式。[Apple：What is safe sleep on Mac?](https://support.apple.com/guide/mac-help/what-is-safe-sleep-mh10328/mac)

本次只讀檢查本機：

```text
uname -m                    arm64
sw_vers -productVersion     27.0.1
pmset -g custom             AC Power，standby=1；沒有 hibernatemode
pmset -g cap                有 standby；沒有 hibernatemode
```

這支持「本機沒有公開列出的 hibernatemode 控制」，不證明硬體內部完全沒有 hibernation 能力，也不能從 `standby=1` 推定外接 SSD 會斷電。本次沒有變更電源設定或嘗試強制 mode 25。**建議不要把 mode 25 作為 Apple silicon Mac mini 的通用解法，也不要把原因定論為是否有電池。**

此外，供電來源很重要：自帶電源的 Thunderbolt dock 可能在主機睡眠時繼續供電。OWC 官方明確描述這項行為；即使某台 Mac 會切斷直連裝置供電，也不能套用到所有 dock。[OWC Thunderbolt Dock](https://www.owc.com/solutions/thunderbolt-dock)

## (2) Unmount、eject 與降溫的區別

本機 macOS 27.0.1 的 `man diskutil` 說明：

- `unmount`：卸載單一 volume；會等待卸載協調及檔案系統資料 flush，忙碌時可能失敗。
- `unmountDisk`：嘗試卸載整個磁碟所涵蓋的 volumes，包括儲存架構輸出的邏輯 volumes。
- `eject`：先卸載 volumes，讓媒體在系統儲存用途上 offline；不承諾關閉實體電源。

所以本專案目前的 **volume unmount** 不等於整顆磁碟 eject，更不等於切斷供電。若同一顆 SSD 還有其他 mounted volumes，只卸載其中一個也無法排除其餘活動。整顆 eject 後可能需要重新連接才能讓系統再看到裝置；Ejectify 2.1 官方把 eject 選項定位為適合醒來後仍保持 eject 的情境。[Ejectify 官方 FAQ](https://ejectify.app/)

推論：卸載可阻止一般應用程式、索引與備份經該 mounted volume 讀寫，因此可能降溫；但不能排除控制器待機耗電、其他 volumes 或底層裝置活動。實際效果需測量，**「降低活動」和「完全斷電」是不同的驗收指標。**

## 社群回報：與原始問題相符，但結果不一致

2024-12-28 的 r/macmini 討論有人回報 M4 Pro + OWC 1M2 睡眠時活動燈持續閃爍、比清醒時更熱；有人同款外接盒卻正常。原發文者調整網路喚醒及自動睡眠後，一度回報溫度由 51°C 降至 44°C，後续又表示仍偶發發熱，長時間不用改為關機。因同時改了兩項設定，無法單獨歸因為關閉網路喚醒。討論中也推薦 Jettison／Ejectify，但不構成它們保證降溫的證據。[原始社群討論](https://www.reddit.com/r/macmini/comments/1ho6jrx/)

另有 Mac Studio 使用者回報 OWC Express 1M2 即使閒置或 eject 後仍發熱。這是個別硬體的使用者回報，支持「eject 不必然冷卻」的實驗方向，不能當成所有外接盒的結論。[Mac Studio 社群討論](https://www.reddit.com/r/MacStudio/comments/1legxk1/)

## 可用的替代工具

| 工具 | 官方提供的功能 | 費用／相容性 | 對本需求的適合程度 |
| --- | --- | --- | --- |
| [Jettison](https://www.stclairsoft.com/Jettison/) | 睡前卸載／退出、醒後恢復，可指定例外；也有手動控制 | US$6.95 單人授權、15 天試用；官方列 macOS 10.13–27、Intel／Apple silicon | 適合不想維護腳本者；也可手動 eject-and-sleep，並非只能每次自動執行 |
| [Ejectify](https://ejectify.app/) | 指定 volumes，睡前 unmount、醒後 mount；2.1 另有整顆 eject 與加密 APFS 功能 | 官方下載 €6.99，macOS 14+；[MIT 原始碼](https://github.com/nielsmouthaan/ejectify-macos) 可自行編譯 | 不一定要付費；但需 Xcode 建置與可能的 helper 配置，成本不是零 |
| [SleepWatcher](https://www.bernhard-baehr.de/) | 常駐監聽 sleep／wake 並執行自訂 Unix 命令；附原始碼 | 免費；官方說 Apple silicon 可用 Rosetta 2，另提供原生編譯 Makefile；部分 display hooks 不支援 | 免費的事件驅動替代方案，但通常攔截每次睡眠；只想夜間使用需額外啟停或條件控制 |
| [Mountain](https://appgineers.de/mountain/) | 群組卸載、手動「卸載全部並睡眠」、自動卸載與掛載、hotkeys | 官方列 1.6.6、OS X 10.8+；未查到明確 macOS 27 保證 | 功能符合；網站提供的最新版相容性資訊較少，需真機試用 |
| 本專案 `deep-sleep` | 明確呼叫時才卸載指定 volumes、標準睡眠、完整喚醒後恢復 | 單一 Bash 腳本，不需常駐程式或額外 runtime 套件 | 最貼近「只在晚上需要時執行」；真實睡眠循環與溫度效果仍待驗收 |

Jettison 手動 eject-and-sleep 與 remount hotkeys 的依據為官方 [release notes](https://www.stclairsoft.com/Jettison/release_notes.html)。各工具均不是 Thunderbolt 埠電源控制器；不應因為有 eject 功能就假定能切斷供電。

## (3) Shell 方案與非每次睡眠的操作

原始方向可行：`diskutil unmount` → `pmset sleepnow` → 等待新 sleep/full-wake cycle → `diskutil mount`。關鍵是 `sleepnow` 返回不代表已睡過並醒來，不能在下一行直接 mount，也不能用固定等待幾秒當成喚醒證據。

本專案讀取新 Sleep 及其後的 full Wake，並檢查目前 CPU／Graphics 電源狀態；DarkWake、Wake Requests 不視為恢復時機。這是專案目前實作，非 Apple 保證永遠固定的 log 格式。未來 OS 更新需重新驗證。[本機實作](../../deep-sleep)、[需求及驗收狀態](../requirements.md)

若偏好 GUI，可用 Shortcuts／Automator 包裝一次 `deep-sleep` 呼叫；這只改變入口，等待與恢復仍交給腳本。若要改成所有睡眠都自動處理，才需要 SleepWatcher 或上述常駐工具。一般 `launchd` 排程本身不提供睡眠與喚醒事件處理。

## 其他通用方向與本機優先順序

1. **減少非必要喚醒。** Apple 建議排查意外喚醒時關閉 Wake for network access；但本機已是 `womp=0`、`tcpkeepalive=0`、`powernap=0`，不宜再宣稱這一定是缺少的設定。Apple 說 Power Nap 的 UI 選項僅限 Intel Macs，不能將舊 Intel 教學原樣套用。[Apple：意外睡眠或喚醒](https://support.apple.com/en-in/guide/mac-help/-mchlp2995/mac)、[Power Nap](https://support.apple.com/en-lamr/guide/mac-help/turn-power-nap-on-or-off-mh40774/26/mac/26)
2. **確認磁碟與主機的睡眠不同。** Apple 提供 Put hard disks to sleep；`pmset` 將 disksleep 定義為磁碟 spindown timer，不是通用的 TB4 NVMe 斷電控制。本機已 `disksleep=10`。主機 `sleep=0` 表示不因閒置自動 sleep；仍可明確使用 `pmset sleepnow`。[Apple：sleep/wake 設定](https://support.apple.com/en-euro/guide/mac-help/mchle41a6ccd/27/mac/27)、[pmset 手冊](https://raw.githubusercontent.com/apple-oss-distributions/PowerManagement/main/pmset/pmset.1)
3. **若降溫仍不足，調查外接盒與拓撲。** 比較直連、經 dock、不同 SSD／橋接晶片與廠商韌體的待機行為；先借用或量測，不因社群個案直接購買替代盒。不應假定 USB-C 10Gbps 一定比 TB4 冷，或某種 port 保證斷電。
4. **真正要求零供電時，在安全卸載後斷開實際電源。** bus-powered 裝置需斷開供電連接；外接電源盒／dock 需關閉其電源。一般 USB hub 電源工具不能視為適用所有 TB4／USB4 拓撲。Mac 關機可作比較組，但有獨立電源的 dock 未必跟著斷電，也會失去睡眠的快速恢復體驗。

目前未找到 Apple 公開支援、適用所有 Apple silicon Mac mini 的「任意關閉單一 TB4 埠供電」命令。這是本次查證範圍內的未找到，不是證明所有硬體都不可能做到。

## 建議的下一步驗證

用同一顆 SSD／外接盒／port、相近室溫，分晚比較：A 正常 sleep；B deep-sleep unmount 後 sleep；C 正常卸載後斷開供電。先完成備份，關閉會使用目標 volumes 的工作；本次研究不自行觸發卸載或睡眠。

記錄睡前及醒後溫度、如能取得則量測功耗、睡眠期間活動燈、`pmset -g log` 的 DarkWake／Wake、醒後是否全部恢復掛載。醒後讀取的 SSD 溫度可能已受恢復 I/O 影響；外殼觸感不等於 SSD sensor 溫度，量測方法需保持一致。

若 B 明顯低於 A，即支持此硬體上減少活動的方案；若 B 仍熱而 C 冷，則下一步應研究外接盒待機與實際供電。本次僅完成文件查證、只讀本機電源設定及實作檢視，未量測溫度、功耗或完成真實卸載睡眠循環；研究也不改變本專案當前設計。
