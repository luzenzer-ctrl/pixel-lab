---
title: Pixel Lab Image Processing
emoji: 🔬
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8501
license: mit
---

# Pixel Lab｜互動式影像處理與人臉分析

原始碼：https://github.com/luzenzer-ctrl/pixel-lab

GitHub Actions 會執行演算法測試與真實介面截圖；結果見儲存庫 Actions 的 pixel-lab-ui-evidence。

## 快速開始（建議 Python 3.12）

Windows 安裝 Python 3.12 後，解壓縮，雙擊 `start_windows.bat`。
或在專案目錄執行：

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

開啟終端機顯示的 Local URL（通常 http://localhost:8501）。不需要 OpenAI API Key。
如電腦有多個 Python，Windows 建議將上述 `python` 改成 `py -3.12`。
不要使用 Python 3.14 安裝這份固定版本環境；驗證環境是 Python 3.12.14。

## 功能

- PNG/JPEG/BMP 解碼、檔案大小、解析度、來源模式/通道與 RGB 處理維度。
- Original/R/G/B/Y/U/V 切換，0–255、256 bins、像素數量直方圖。
- 1–15 階奇數方陣，空白/逗號/JSON 輸入；實際卷積、正規化、偏移、三種邊界模式。
- 浮點運算後四捨五入並裁切到 uint8；MSE、PSNR 與裁切比例；影像/參數下載。
- 已隨附 YuNet 2023mar 模型：多張人臉框、原始座標、信心分數、NMS、JSON 下載。

## 架構

`app.py` 是 Streamlit 介面；`core.py` 是可獨立測試的演算法；`models/` 為模型與授權；
`assets/` 為測試圖；`tests/` 為單元及 Streamlit 操作測試；`evidence/` 為實測結果。
PSNR = 10 log10(255² / MSE)，MSE 對 H×W×3 計算；MSE = 0 時 PSNR = ∞。
`cv2.filter2D` 預設為相關運算，因此先將核旋轉 180° 才達成卷積。
U/V 為 OpenCV 8-bit YUV 編碼，含 128 色度偏移；不是 YCbCr 或原始 signed U/V。

## 執行測試

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## 產生真實介面截圖

本次環境可執行 Streamlit 與 AppTest，但截圖瀏覽器無法連線本機服務；目前報告未將運算圖冒充介面截圖。
請先保持應用程式執行，再開另一個終端機：

```bash
python -m pip install playwright==1.60.0
python -m playwright install chromium
python capture_ui.py
```

會產生 `evidence/01_original.png` 至 `05_faces.png`。腳本僅使用內建範例，不含你的私人照片。
若要更新 PDF，安裝 `reportlab` 後執行 `python build_report.py --student-id 學號 --name 姓名 --demo 公開網址 --repo GitHub網址`。
PDF 生成器會自動納入已存在的介面截圖。未填姓名／網址時明示「待補」。

## 公開部署（尚未代為登入或發佈）

### GitHub 原始碼

1. 在 GitHub 建立 Public 儲存庫，例如 `pixel-lab`。
2. 將本資料夾**內容**上傳到根目錄，包含 `.streamlit`、`models`、`assets`；不要只上傳 ZIP。
3. 用無痕視窗開啟該儲存庫，確認不登入也能查看原始碼。

### Streamlit Community Cloud

1. 登入 https://share.streamlit.io/ ，建立 App，連結上述 Public GitHub repo。
2. 主程式選 `app.py`，Python 選 3.12；部署相依性來自 requirements.txt。
3. 確認應用的分享設定為公開。將真實部署後網址填入報告 Chapter 2。
4. 使用無痕視窗測試讀檔、切換 U、執行高斯核、雙人臉偵測與下載。

### Hugging Face Spaces 備選

1. 建立 Public Docker Space。
2. 上傳本資料夾內容；保留 README 頂端的 `sdk: docker` 與 `app_port: 8501`。
3. Dockerfile 已指定 Python 3.12 與 0.0.0.0:8501。等待建置後測試公開 App 頁面。

上述兩平台擇一提供 Live Demo 即可，GitHub 原始碼連結仍須另外填入。網址未建立前不能宣稱已完成公開驗收。

## 驗收與限制

- 20 MiB、1,200 萬像素上限；核絕對值 ≤10000、奇數方陣最大15×15，是防止資源耗盡的合理限制。
- 灰階轉三通道，透明圖以白底合成，EXIF 方向校正；計算以轉換後的 RGB 原圖為基準。
- 大圖人臉推論長邊縮到1280；小臉、側臉、遮擋與低照度可能漏檢；不能保證真實場景找出所有人臉。
- 內建雙人臉是同一公開領域照片的拼接，僅驗證多框流程，未證明對多人多樣性的準確率。
- Confidence 是模型分數，不是經校準的機率；未進行人臉身分識別。
- 本程式不主動將上傳圖寫入磁碟；雲端部署時圖像會傳到部署主機處理。

## 資料與模型授權

`assets/face.png` 來自 scikit-image astronaut 範例（NASA Eileen Collins，公開領域），`two_faces.png` 為並排複製；
https://scikit-image.org/docs/0.24.x/api/skimage.data.html#skimage.data.astronaut
`color.png` 是本次程式生成的合成色彩圖。
YuNet 模型來源與 SHA-256 見 `models/MODEL_CARD.md`；隨附來源授權。
程式碼（不含第三方資產）以 MIT 授權提供，見 LICENSE。

## AI 協作紀錄

`audit/original_prompt.txt` 保留本次使用者完整原始題目；`audit/AI_AUDIT.md` 記錄真實工具輸出與修正。
此次僅有一輪使用者需求，未虛構多輪使用者 refinement。最終回覆與後續真人操作請另外匯出完整對話留存。
