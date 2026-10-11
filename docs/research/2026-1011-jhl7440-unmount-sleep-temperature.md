# JHL7440 外接 SSD：睡眠時卸載前後的社群溫度比較

查證日期：2026-10-11。承接 [睡眠供電與替代方案研究](2026-1011-thunderbolt-ssd-sleep.md)。本次集中搜尋 Apple silicon Mac mini／Mac Studio、JHL7440 外接盒，以及「保持掛載睡眠」對「先 unmount 再睡眠」的外部實測。

## 結論與證據缺口

**本次未找到完整符合上述條件、提供兩組溫度的社群 A/B 實測。不能引用現有資料宣稱 unmount 在這類配置可降低特定度數。**

找到的資料包括：JHL7440 型號外接盒的睡眠後溫度；Mac Studio 以 Jettison 睡前 eject 後仍溫暖；另一種晶片的外接盒 eject 半天後仍超過 50°C。這些是背景及邊界證據，沒有同時固定主機、外接盒、SSD、OS、室溫與睡眠條件來比較卸載前後。

## 搜尋時的硬體定義

JHL7440 是 Intel **Thunderbolt 3 Titan Ridge** peripheral controller，可以用在 TB4 主機埠。外接盒商品寫「Thunderbolt 3/4 相容」不代表它是原生 TB4 controller。[Intel 官方規格](https://www.intel.com/content/www/us/en/products/sku/97401/intel-jhl7440-thunderbolt-3-controller/specifications.html)

Acasis 官方將 TBU405 系列列為 JHL7440，部分型號另搭 RTL9210B；TBU405 Air 也有官方 JHL7440 商品資料。回報只寫「Acasis」而不提供型號時，不自行判定 controller。即使有型號，社群未拆機確認的硬體版本也應保留不確定性。[Acasis TBU405 官方資料](https://www.acasis.com/products/acasis-usb4-0-m-2-nvme-ssd-enclosure-40gbps-data-transfer-compatible-with-thunderbolt-3-4-usb3-2-3-1-3-0-2-0-type-c-tbu405)、[TBU405 Air](https://acasis.in/product/tbu405air/)

## 最接近目標的外部回報

### 1. Acasis 405 Air + WD SN770：閒置約 40°C，剛喚醒約 31–33°C

來源：r/macmini，2025-04-28 回覆，作者 `peirato_`，主題為 M4 Mac mini 的外接 SSD 選擇。[討論原文](https://www.reddit.com/r/macmini/comments/1jvwg13/acasis_tbu405_air_or_samsung_t7/)

| 狀態 | 回報值 |
| --- | --- |
| 清醒閒置 | 約 40°C |
| 複製檔案 | 約 50–53°C |
| 剛從 sleep 喚醒 | 約 31–33°C，接著很快升至約 40°C |

作者明確寫 Acasis 405 Air + SN770，另說關閉 Wake for network access 後外殼較冷，但仍不如拔線。沒有說先 unmount，也沒列睡眠時間、量測程式或室溫；回覆者未重新確認自己主機的具體型號。**這是 JHL7440 型號相關的睡眠讀值，不是 unmount 帶來 7–9°C 降溫的證據。**

同一討論中另一作者使用 P3 Plus，提供外殼及 SSD 本體讀值，不能與 SN770 作者拼接成同一組實驗。

### 2. Mac Studio + Acasis TB4 外接盒 + Samsung 990 PRO：Jettison eject 後 sleep，仍溫暖

來源：MacUser.de，2025-10-16，作者 `BeG261`，**#5**。[討論原文](https://www.macuser.de/threads/owc-express-1m2-ssd-gehause-dauerhaft-sehr-warm.962123/)

作者使用 Jettison 在 Mac Studio 睡眠前退出磁碟，回報外接盒 LED 仍亮、外殼溫暖但不燙；先前 Samsung T7 在相同使用情境下會完全停止、冷卻。

這是本次找到最直接描述「Mac Studio + 睡前 eject + sleep + 散熱結果」的回報，但沒有前後溫度，沒有 Acasis 型號、controller、Mac Studio 晶片與 OS 版本。只能說此配置 eject 後仍暖；無法判定有沒有較未 eject 時改善。T7 也不是同一顆 SSD／同一協定的控制組。

同作者 **#18** 另寫 990 PRO 清醒閒置 43°C；不能將它當作 #5 的睡眠後數值。**#19** 的另一位作者寫 unmounted 後仍顯示約 66°C，未提供符合本研究的主機及 sleep 條件，故不拿來計算前後差異。

### 3. M1 Mac mini + Acasis TBU405 外接開機碟：sleep 後保持溫暖

來源：r/macmini，2024-10-21 發文、2024-10-24 補充。[討論原文](https://www.reddit.com/r/macmini/comments/1g835mf/)

作者使用 2TB SSD／TBU405 作 M1 mini 的開機碟，DriveDx 的一般操作讀值約 mid-40s 至 low-50s °C，被問到 Mac sleep 時外接盒是否冷卻，回答仍溫暖。SSD 型號不明，也沒給睡眠後的 sensor 讀值。

這符合 Apple silicon 桌機及 JHL7440 型號背景，但作為開機碟無法直接採用本專案的卸載資料 volume 流程；不是 unmount A/B。

## 有溫度或比較，但條件不完全相符

| 回報／來源 | 觀察 | 缺少或不同的條件 |
| --- | --- | --- |
| [Mac Studio M2 Max + OWC Express 1M2](https://www.reddit.com/r/MacStudio/comments/1legxk1/)，2025-06-18 | 作者說 eject 半天後仍超過 50°C，室內空調設 27°C；同盒接 Intel MBP，idle／eject 時會冷卻 | 未確認這半天處於 Mac sleep；未給掛載前溫度；1M2 不作 JHL7440 證據 |
| [M4 Pro mini + OWC 1M2](https://www.reddit.com/r/macmini/comments/1ho6jrx/)，2024-12-28 起 | 修改網路喚醒與自動睡眠設定後，醒後從 51°C 降至 44°C；後續仍有發熱 | 不是 unmount；兩項設定同時改動；非 JHL7440 控制組 |
| [M4 mini + Qwiizlab USB4](https://forums.macrumors.com/threads/owc-express-1m2-versus-maiwo-40gbps-m-2-nvme.2441898/page-2)，2024-11-24 **#31** | 作者修正較早判斷：清醒 idle 4.5–5.6W，sleep 等待後約 1.0–1.5W；先前提到 SSD 可低於 30°C | 未測 unmount；SSD 型號在該段不明；不作 JHL7440 證據；作者說功率表不很精確 |
| [M1 Max Studio + Acasis JHL7440 + 990 EVO 2TB](https://missuo.me/posts/upgrade-mac-studio/)，2025-02-24 | 作者描述一般使用約 42°C，較先前 ASM2464PD 配置涼 | 同時更換 SSD 及外接盒；沒有 sleep／unmount 測試 |

## 旁證：相同 JHL7440 硬體，OS 更新後 sleep 行為改變

MacRumors 作者 `schmalen`，2026-09-08，**#40**，回報 JHL7440 + RTL9210B、40Gb/s、直連 TB4 的 Time Machine 外接盒，在 macOS 26.6.1 時 sleep 後風扇不持續運轉；升至 26.6.2 後，相同硬體及設定，`pmset -g log` 確認主機進入 sleep，風扇卻持續轉。作者未定論是 bug 或刻意修改。[原文](https://forums.macrumors.com/threads/external-drives-not-recognised-in-tahoe.2468852/page-2)

這是 OS 更新前後的 A/B，沒有溫度、SSD 型號或 unmount 對照；該則回報也未明列 Mac mini／Studio 型號。它提示比較時需固定 macOS 版本，不能拿別人的不同 OS 結果直接套用本機 27.0.1。

## 排除的資料與避免誤讀

- **iMac 27 + TBU405 Pro + SN850X** 的 [Reddit](https://www.reddit.com/r/mac/comments/17rxuwr/acasis_enclosure_ssd_running_hot_when_unmounted/) 與 [MacRumors](https://forums.macrumors.com/threads/is-this-normal-behavior-for-an-ssd-hard-drive.2412438/) 回報：卸載／睡眠後仍熱，但主機不是 Apple silicon，而且睡眠時同時關掉外接盒風扇；沒有數值。不能將「計畫買 Studio」讀成「已在 Studio 測過」，也不能把同作者跨站貼文當獨立樣本。
- Mac mini 發熱討論中，JHL7440 + 990 EVO Plus 的 **風扇開關、負載 40°C／52°C**，與另一位作者的 **未知 USB4 controller、idle 60°C** 是兩個不同人及配置，不能拼成 JHL7440 的數字比較。[原討論](https://www.reddit.com/r/macmini/comments/1iew0b2/mac_mini_m4external_ssd_extreme_heating_issue/)
- Jettison／Ejectify 解決不正常退出磁碟通知的成功回報，不等於提供降溫實測。
- Intel JHL7440 的 2.4W TDP 是規格資料，不是外接 SSD 在 sleep／unmount 時的實測功耗。

## 搜尋範圍與可重做的查詢

以英文及中文搜尋 Reddit、MacRumors、MacUser.de、個人實測文章及 Acasis／Intel 型號資料。代表查詢如下：

```text
"JHL7440" "Mac" "sleep" "temperature"
"JHL7440" "unmount"
"JHL7440" "eject" "sleep"
"Mac mini" "unmount" "SSD" "temperature" sleep
"Mac Studio" "eject" "SSD" "hot" sleep
"TBU405" "sleep" "temperature"
"TBU401" "sleep" "cool"
"Acasis" "eject" "cool" "Mac"
"JHL7440" "卸载" "温度"
"JHL7440" "睡眠" "溫度"
```

「未找到完整 A/B」只限本次可取得的公開資料，不代表社群完全不存在此實驗。沒有接觸發文者、購買工具、變更電源設定或進行本機 sleep／溫度量測。

## 對 deep-sleep 的影響

目前可把它定位為「按需要卸載資料 volumes、減少檔案系統活動並自動恢復」；**降低多少溫度仍是待驗證效果**。最關鍵的待補資料是同一台 Apple silicon mini／Studio、同一 JHL7440 外接盒及 SSD、相同 OS 與風扇設定，在正常 sleep 與 unmount 後 sleep 的整夜比較。

量測需區分 SSD sensor、外殼表面與 controller 溫度。剛喚醒讀值可能隨恢復活動快速上升，應固定醒來後取樣時間；持續的溫度監控也可能對裝置產生活動，不能預設完全不影響電源狀態。
