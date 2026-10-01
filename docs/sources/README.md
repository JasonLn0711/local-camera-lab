# 使用者提供資料：2026-10-01

此目錄保留啟動專案時使用者貼上的完整技術 passage，供日後對照來源、修正與實作決策。

- [原文全文](2026-10-01-user-passage.txt)：1,222 行，UTF-8。取自本次對話的使用者訊息；移除外層三引號與首尾空行，以 LF 結尾，內文不改寫。
- [SHA256SUMS](SHA256SUMS)：對 repo 中這份原文檔計算的 SHA-256；標準函式庫測試會驗證。
- 原文的 `chatgpt-content-reference` 與重複 index 是原始文字的一部分，沒有對應網址清單，不能當成已核實引用。新的 primary-source URLs 放在查證筆記各段。
- 原文中的範例 JSON、時間、事件描述與程式碼都是使用者提供的構想／範例，並非本 repo 執行或家庭觀測證據。
- 尚無實際 internal model、韌體、IP、Xiaomi token、家庭影像或測量結果。原文提及的硬體型號不是家庭實機驗收。

## 全文到查證筆記的對照

| 原文主題 | 正式筆記／執行介面 |
| --- | --- |
| 台灣 C400／MJSXJ23CM、原生 RTSP／ONVIF、官方 Home Assistant 限制 | [攝影機筆記](../c400-go2rtc.zh-TW.md)的硬體、介面與證據分層 |
| MIoT p2p-stream／Google Home interface、Xiaomi P2P／MISS／CS2 | 同一筆記的協定與 MIoT 章節，保留 model-specific service 差別 |
| go2rtc 版本、LAN／Internet、internal models、品質設定 | 同一筆記的版本與返家連線程序 |
| OpenCV／PyAV／FFmpeg、H.265、RTSP／WebRTC／HLS、audio | [攝影機筆記](../c400-go2rtc.zh-TW.md)與[framework 比較](../models-frameworks.zh-TW.md) |
| 039a04 解碼問題、039c04 推薦、Home Assistant 替代方案 | 攝影機筆記保留原回報日期、issue 狀態及實機不確定性 |
| YOLO26／YOLOE-26／SAM 3.1／RF-DETR | [模型研究](../models-frameworks.zh-TW.md)的 checkpoint、任務、授權與比較順序 |
| Qwen3-VL／MiniCPM-V 4.6／MiniCPM-o 4.5／Moondream 3.1／YOLO27 | 模型研究的 VLM／影音候選與尚未釋出模型 |
| Detector → event → VLM → agent、pre/post frames、event DB | 模型研究的後續接入 gate；目前 [README](../../README.md)僅啟動 detector／JSONL |
| accuracy／recall／false alarms／latency／VRAM／power／24-hour stability | 模型筆記 benchmark 設計及[驗收表](../verification.zh-TW.md) |

## 本次已確認的專案決策

1. 第一版包含完整研究筆記與可跑 POC，人物觀測優先；VLM 留待下一階段。
2. 建立公開 `JasonLn0711/local-camera-lab`，私人設定與家庭資料留在 ignored `.local/`。
3. 最後採用的拓樸是：回家後將 go2rtc 與 GPU 主機放在 C400 同一子網。本輪只準備及發布 repo；先前外地跨網段想法不屬於目前部署。
4. 新 repo 擁有研究、程式與詳細驗收；Planning 僅保留狀態、容量、locator 與下一 gate。

查證內容是對原文的有來源整理，不將使用者原文中的推論、範例或官方 benchmark 轉成實機成功宣告。
