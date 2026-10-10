# 採用 ~/.deep-sleep/.env 設定檔

日期：2026-10-11（Asia/Taipei；依對話回填）。

## 決策

採用 `~/.deep-sleep/.env` 保存 volume 清單，每個 volume 使用一個 `DEEP_SLEEP_VOLUME_<正整數>` 設定項目。支援另選設定檔及命令列覆寫，設定作為字面資料解析。

## 對話依據

使用者要求：

> 追加設定檔的做法
> .env 或是 ~/.deep-sleep/config.toml 都可以
> 你選定一個做法給我

agent 提出 `.env` 方案後，使用者批准開始：

> ok, init git, 給我第一版

## 背景與影響

agent 提案的選型理由是方便以 shell 實作並避免額外 TOML 解析依賴；此理由來自提案。已批准方案包含 `--config` 選擇檔案、`--volume` 取代設定清單，以及不使用 `source`／`eval` 執行設定內容。
