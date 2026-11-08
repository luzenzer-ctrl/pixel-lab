# AI 協作開發紀錄

日期：2026-11-08（Asia/Taipei）。協作工具：ChatGPT Work 中的 Codex。
本環境自我識別為 GPT-6 系列，未提供可驗證的精確模型子版本 ID；不捏造 GPT-4o 或其他型號。
正式提交時請另附／保留 ChatGPT 介面實際顯示的模型名稱與匯出的完整對話。

## 原始 Prompt

完整原文見 original_prompt.txt；報告附錄也排版納入原始題目。此為唯一使用者開發需求。

## AI 初始回覆（原文）

「我會先製作可執行的影像處理程式、測試案例與 PDF 報告，並保留這次實際的 AI 協作紀錄。報告需要的學號、姓名，以及公開展示和原始碼連結，我會先留明確欄位，避免填入未確認的資料。」

## 產出與可驗證紀錄

以下為 AI 執行工具的工作紀錄，並非額外的使用者 Prompt，亦非隱藏思考過程。
原始碼完整收錄於專案。未虛構多輪對話，未宣稱已部署公開連結。

1. 相依套件檢查：環境原先缺少 cv2、streamlit、pytest；安裝 OpenCV 4.10.0.84、Streamlit 1.40.2、pytest 8.3.4，再固定 requirements 的 NumPy 2.1.3、Pillow 11.3.0、Matplotlib 3.9.2。
2. 文件查核：OpenCV 文件說明 filter2D 是 correlation，需要翻轉 kernel 才是 convolution。產出 core.py 的 np.flip(k / d, axis=(0,1)) 實作；另以不對稱核與手寫小影像參考運算驗證方向。
3. 人臉模型：下載 OpenCV Zoo YuNet 2023mar ONNX，232589 bytes；模型 SHA-256 寫入 MODEL_CARD。使用 face[14] 的模型分數，未將 Haar 的權重偽裝成機率。
4. 介面與演算法：產出 app.py、core.py、requirements.txt、Streamlit 設定；加入檔案解碼、EXIF、RGBA 白底、RGB/YUV、直方圖、卷積、PSNR、分數與下載。
5. 第一輪測試：`python -m pytest image_lab -q` 得到 26 passed、1 failed。
   錯誤訊息：`ValueError: '雙人臉' is not in list`。原因是測試用 at.selectbox[0] 選到「矩陣範例」，不是 sidebar 的影像來源。
   實際修正：把 `at.selectbox[0].select('雙人臉').run()` 改為
   `next(s for s in at.selectbox if s.label=='或使用內建測試影像').select('雙人臉').run()`。
   這是測試定位方式修正，沒有以改寫預期結果掩蓋演算法錯誤。
6. 第二輪測試：27 passed；包含每個顯示模式切換、非法矩陣 UI 提示、雙人臉按鈕操作。實際測試結果寫入 evidence/test_results.txt。
7. 數值實測：color.png 高斯核 PSNR 36.6935917627 dB；銳化 34.0675469982 dB；浮雕加128偏移 7.9670729056 dB。單臉 1、雙臉 2、合成圖 0；完整座標和分數寫入 evidence/metrics.json。
8. 介面截圖阻礙：本地 Chromium 啟動時系統禁止 socket；可用的遠端瀏覽器開啟 http://localhost:8501 回報 ERR_CONNECTION_REFUSED。未產生或偽造介面截圖。提供 capture_ui.py 讓使用者在自己的執行環境產生實際截圖；報告僅標示真實演算法輸出。
9. 部署封裝：產出 Dockerfile（Python 3.12 / port8501）、Windows 啟動器、GitHub / Streamlit / Hugging Face 公開部署說明。沒有可用的使用者 GitHub/Hugging Face 登入狀態，故公開連結與無痕驗收仍待完成。
10. 文件：以 ReportLab 生成可搜尋文字的繁體中文 PDF，含四章、公式、實測圖、測試摘要、完整原始 Prompt 附錄；保留 build_report.py 可填入姓名學號與真實網址並重新產生。

## 紀錄範圍限制

此紀錄保留本輪使用者需求、初始回覆與實際工具修正摘要；不是 ChatGPT 平台提供的完整對話匯出，
也未包含每一個工具呼叫的逐字輸出。若老師要求完全逐字歷程，應將本次完整對話另行匯出並附在 PDF 後，
後續使用者的調整指令與 AI 回覆也應照實追加。不可將建議 Prompt 當成已發生的互動。

## 後續補充
使用者補充原文與身分欄位修改結果見 followup.txt；未完成 GitHub 連接前不宣稱已公開發佈。
