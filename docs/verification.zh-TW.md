# 驗證紀錄與回家驗收

## 2026-10-01：目前狀態

交付層：研究文件、原文保存、人物觀測 CLI、無憑證設定範例、標準函式庫測試與 CI。

| 驗證層 | 狀態 | 能支持的結論 |
| --- | --- | --- |
| Primary-source 查核 | 已整理 | 有可實作的 upstream 路線；來源與修正見[攝影機](c400-go2rtc.zh-TW.md)及[模型](models-frameworks.zh-TW.md)筆記 |
| 原文完整性 | SHA-256 已建立 | [來源檔](sources/2026-10-01-user-passage.txt)可與保存時位元組比對 |
| 合成資料單元檢查／CLI／語法 | 本機 12 項測試、CLI help 與 Python 語法檢查通過 | 不依賴 torch、攝影機、網路或權重；含 synthetic model 的 orchestration 檢查 |
| GitHub Actions | 待發布後核對 | 僅自動檢查程式與合成資料，不連線家庭 |
| go2rtc／C400 | 待回家 | 尚未取得真實串流，internal model 與韌體未知 |
| CUDA／YOLO26 | 待回家 | 尚未安裝候選環境、下載模型或執行推論 |
| accuracy／latency／power／24 小時穩定性 | 未測量 | 不將官方數據或合成測試當作本機結果 |

## 自動檢查

```bash
python3 -m unittest discover -s tests -v
python3 detect.py --help
python3 -m py_compile detect.py
git diff --check
```

涵蓋人物／無人物、confidence 邊界、類別過濾、冷卻邊界、JSONL 契約、無結果、非有限數值、非法參數、寫入失敗、錯誤退出與 Ctrl-C。資料全部是測試建立的合成值；不以 mock 結果宣稱模型 accuracy 或直播成功。

發布檢查另核對 Markdown 相對連結、shell 範例語法、原文 SHA-256、`.gitignore` 與實際 tracked file 列表。公開來源全文中的示範 token／位址屬原始引用，必須與真實憑證區分；任何真實秘密或家庭資料都不得被 stage。

## 回家後驗收 gate

依序完成；每一步失敗只保存該步證據與下一個排查動作。

1. **網路與裝置**：確認 C400、go2rtc、GPU 主機同子網，無 AP client isolation。由本人登入 local WebUI，選取實際帳號區域；在私人紀錄保存 internal model、韌體、go2rtc binary hash。MJSXJ23CM 與 `039c04` 不自動畫等號。
2. **解碼**：依[攝影機手冊](c400-go2rtc.zh-TW.md)執行 ffprobe，確認實際 codec、尺寸、FPS。設定 10 分鐘 smoke window，記錄首個可用畫面時間及持續錯誤；起始 keyframe 前錯誤與持續錯誤分開。逾時／沒有可用影格即未通過，不啟動 detector 測試。
3. **GPU**：在獨立環境記錄 torch／torchvision／CUDA／driver，跑 CUDA tensor 與固定圖片 YOLO smoke。確認 class 0 為 person，取得有效結果；只看到 `cuda.is_available()` 不足以通過。
4. **事件**：本人在鏡頭前出現，檢查有效 bbox、JSONL 欄位、UTC 觀測時間與冷卻。持續在畫面中時最多每個冷卻窗口一筆，空畫面不產生事件；真實模型誤報照實記錄，不依單次成功宣告 accuracy。
5. **中斷與恢復**：手動停止本次 go2rtc 後恢復，記錄 detector 是套件自行重連、退出，或需要 Ctrl-C／手動重啟。確認已寫入 JSONL 仍完整。這一步測量實際行為，不承諾 bounded reconnect 或 watchdog。
6. **收尾**：停止測試程序，保存私人環境快照、權重 hash 與簡短結果；公開報告只放去識別的條件、彙總結果、限制與下一 gate。

家用 smoke 的最小成功條件：取得可解碼串流，YOLO26 在指定 GPU 跑通，人物出現後寫出符合介面的事件；中斷後既有事件檔保持完整，恢復方式有實際紀錄。這不等同全天候服務驗收。

### GPU smoke 範例（回家、環境準備後才執行）

```bash
python3 - <<'PY'
import torch
import torchvision
print('torch', torch.__version__, 'torchvision', torchvision.__version__)
print('cuda', torch.version.cuda, 'architectures', torch.cuda.get_arch_list())
assert torch.cuda.is_available(), 'CUDA unavailable'
x = torch.ones((8, 8), device='cuda')
assert (x @ x).sum().item() == 512
print('CUDA tensor smoke passed; detector inference is a separate check')
PY
```

固定圖片或短影片由本人在 `.local/` 提供，並記錄來源與 hash；不把家庭影像上傳公開 CI。範例：

```bash
python3 detect.py --source .local/test.mp4 --device 0 \
  --cooldown-seconds 0 --output .local/smoke-events.jsonl
python3 -m pip freeze > .local/runtime-freeze.txt
nvidia-smi > .local/nvidia-smi.txt
sha256sum .local/models/yolo26s.pt > .local/model.sha256
```

## 後續測量

共同測試資料、event precision／recall、false alarms、處理 FPS、VRAM、功耗、斷線與長時間運作依[模型 benchmark 協定](models-frameworks.zh-TW.md)執行。另加 timestamp instrumentation 前，不從 JSONL `observed_at` 推算 sensor-to-event latency 或 frame age。

24 小時穩定性為後續另行啟動的測試，不建立排程、不預先占用 GPU，也不由本輪 publication 自動啟動。音訊、WebRTC、VLM、錄影與通知各自保留獨立驗收。
