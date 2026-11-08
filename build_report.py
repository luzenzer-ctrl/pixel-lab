"""Rebuild the report; does not invent deployment status or screenshot evidence."""
from pathlib import Path
import argparse,json,sys,platform,math
from xml.sax.saxutils import escape
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image as PILImage
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
from core import load_image,channels,histogram

ROOT=Path(__file__).parent
E=ROOT/'evidence';E.mkdir(exist_ok=True)
P=argparse.ArgumentParser()
P.add_argument('--student-id',default='待填學號');P.add_argument('--name',default='待填姓名')
P.add_argument('--demo',default='');P.add_argument('--repo',default='');P.add_argument('--output',default='')
a=P.parse_args()
font_path=ROOT/'fonts/NotoSansTC-Regular.ttf'
if font_path.exists():
    pdfmetrics.registerFont(TTFont('NotoTC',str(font_path)))
    FONT='NotoTC'
else:
    import reportlab.pdfbase._cidfontdata as cid
    cid.defaultUnicodeEncodings['MSung-Light']=('cht','UniCNS-UCS2-H')
    pdfmetrics.registerFont(UnicodeCIDFont('MSung-Light'))
    FONT='MSung-Light'
navy=colors.HexColor('#172b45'); teal=colors.HexColor('#167d9a')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='CBody',fontName=FONT,fontSize=10.5,leading=17,textColor=navy,spaceAfter=8,wordWrap='CJK'))
styles.add(ParagraphStyle(name='CTitle',parent=styles['CBody'],fontSize=27,leading=38,spaceAfter=18))
styles.add(ParagraphStyle(name='CH1',parent=styles['CBody'],fontSize=20,leading=28,spaceAfter=16,textColor=teal))
styles.add(ParagraphStyle(name='CH2',parent=styles['CBody'],fontSize=13,leading=20,spaceBefore=8,spaceAfter=10,textColor=teal))
styles.add(ParagraphStyle(name='SmallC',parent=styles['CBody'],fontSize=8.5,leading=13))
styles.add(ParagraphStyle(name='CodeC',parent=styles['SmallC'],backColor=colors.HexColor('#edf3f7'),borderPadding=8,spaceAfter=12))
story=[]
def p(s,style='CBody'):
    return Paragraph(s,styles[style])
def add(s,style='CBody'):
    story.append(p(s,style))
def title(ch,t):
    add(ch,'SmallC');add(t,'CH1')
def br():story.append(PageBreak())
def table(rows,widths=None):
    t=Table([[p(str(v),'SmallC') for v in row] for row in rows],colWidths=widths or [120,365],repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dfedf3')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.7,teal),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f5f8fb')]),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.append(t);story.append(Spacer(1,10))
def image(path,width=485,caption=''):
    with PILImage.open(path) as im:w,h=im.size
    story.append(Image(str(path),width=width,height=width*h/w))
    if caption:add(caption,'SmallC')

def diagram():
    d=Drawing(485,210)
    def node(x,y,w,h,t):
        d.add(Rect(x,y,w,h,rx=7,fillColor=colors.HexColor('#edf3f7'),strokeColor=teal))
        d.add(String(x+w/2,y+h/2-4,t,fontName=FONT,fontSize=10,textAnchor='middle',fillColor=navy))
    def arrow(x,y,xx,yy):
        d.add(Line(x,y,xx,yy,strokeColor=teal));d.add(Polygon([xx,yy,xx-4,yy+6,xx+4,yy+6],fillColor=teal,strokeColor=teal))
    node(120,166,245,30,'上傳檔案／內建測試圖')
    node(120,115,245,30,'驗證、EXIF、白底合成 → RGB uint8')
    arrow(242,166,242,145)
    for x,t in [(0,'RGB／YUV／直方圖'),(166,'自訂卷積／PSNR'),(332,'YuNet／框與分數')]:
        node(x,48,153,35,t)
        d.add(Line(242,115,242,99,strokeColor=teal));d.add(Line(76,99,409,99,strokeColor=teal))
        arrow(x+76,99,x+76,83)
    node(120,0,245,27,'即時顯示／PNG 與 JSON 下載')
    for x in [76,242,409]:
        d.add(Line(x,48,x,38,strokeColor=teal));d.add(Line(x,38,242,38,strokeColor=teal))
    arrow(242,38,242,27)
    return d

# Generate exact algorithm figures, never label as UI captures.
rgb,_=load_image((ROOT/'assets/color.png').read_bytes());ch=channels(rgb)
fig,axs=plt.subplots(2,4,figsize=(11,5.2))
for ax,(name,arr) in zip(axs.ravel(),ch.items()):
    ax.imshow(arr,cmap='gray',vmin=0,vmax=255);ax.set_title(name);ax.axis('off')
axs.ravel()[-1].axis('off');fig.tight_layout();fig.savefig(E/'channels_grid.png',dpi=180);plt.close(fig)
fig,axs=plt.subplots(1,3,figsize=(11,3))
for ax,name in zip(axs,'YUV'):
    counts=histogram(ch[name])['Intensity'];ax.plot(np.arange(256),counts,color='#167d9a');ax.set(xlim=(0,255),xlabel='Intensity (0-255)',ylabel='Pixel count',title=f'{name} histogram');ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(E/'histograms.png',dpi=180);plt.close(fig)
fig,axs=plt.subplots(2,2,figsize=(10,6.4))
for ax,name in zip(axs.ravel(),['identity','gaussian','sharpen','emboss']):
    ax.imshow(PILImage.open(E/f'result_{name}.png'));ax.set_title(name);ax.axis('off')
fig.tight_layout();fig.savefig(E/'filters_grid.png',dpi=180);plt.close(fig)
m=json.loads((E/'metrics.json').read_text())

story.append(Spacer(1,48));add('GENERATIVE AI × COMPUTER VISION','CH2')
add('Pixel Lab<br/>互動式影像處理<br/>與人臉分析工具','CTitle')
add('期中專題報告','CH1')
add(f'學號：{escape(a.student_id)}　　姓名：{escape(a.name)}')
add('製作日期：2026 年 11 月 8 日')
add('Python · Streamlit · OpenCV · YuNet','CH2')
story.append(Spacer(1,16))
table([['本版狀態','程式與實測已完成；提交資料尚待補齊'],['演算法與介面測試','27 項通過；數值及人臉框資料附於專案'],['公開連結','已填寫，請依 Chapter 2 驗證' if a.demo and a.repo else ('原始碼已公開；Live Demo 尚待部署' if a.repo else '尚未部署／填入；目前無可供老師公開檢閱的網址')],['介面截圖','已偵測到本機截圖檔' if (E/'01_original.png').exists() else '尚待本機擷取；本報告先呈現真實運算結果圖'],['提交前必做',('核對姓名學號' if a.student_id!='待填學號' and a.name!='待填姓名' else '填入姓名學號')+'、補公開連結與操作截圖、確認 AI 模型標示及完整對話']])
add('閱讀導覽：Chapter 1 環境與專案範圍；Chapter 2 部署與連結；Chapter 3 架構、操作、演算法與測試；Chapter 4 AI 協作紀錄；附錄為原始 Prompt。','SmallC')
br()
title('CHAPTER 1','專案概述與環境建置')
add('1.1 專案目標','CH2')
add('將影像讀取、通道探索、自訂卷積、PSNR 評估與人臉偵測整合於繁體中文互動網頁。使用者可以在同一介面調整參數並查看結果，並匯出濾波圖、人臉框圖及 JSON 數值。')
add('1.2 開發與相依性','CH2')
add('實測環境為 Linux、Python 3.12.14、CPU 推論。Windows 建議使用 Python 3.12；應用本身不依賴 GPU、API 金鑰或付費服務。以下是 requirements.txt 的直接相依性。')
table([['套件／版本','用途'],['streamlit 1.40.2','上傳、參數控制、分頁、圖片與下載介面'],['numpy 2.1.3','矩陣驗證、直方圖計數、浮點 MSE'],['opencv-python-headless 4.10.0.84','RGB→YUV、filter2D、YuNet DNN 與框線'],['Pillow 11.3.0','點陣影像解碼、EXIF 校正、透明合成與 PNG 匯出'],['matplotlib 3.9.2','256 bins 強度直方圖']])
add('開發測試另用 pytest 8.3.4 與 Streamlit AppTest。報告重建另需 ReportLab；自動截圖另需 Playwright 和 Chromium，兩者不屬於部署 App 的必要相依性。NASA 範例圖已隨專案提供，執行 App 無須安裝 scikit-image。')
add('1.3 本機啟動','CH2')
add('python -m pip install -r requirements.txt<br/>python -m streamlit run app.py','CodeC')
add('請在解壓縮後的 image_lab 目錄執行。Windows 也可雙擊 start_windows.bat；啟動器使用 py -3.12。開啟終端機提供的 Local URL，首次無須上傳照片即可使用內建圖。')
br()
title('CHAPTER 2','可執行連結與部署驗收')
add('2.1 公開連結登錄','CH2')
for label,url in [('Live Demo',a.demo),('GitHub / GitLab',a.repo)]:
    add(f'{label}：'+(f'<link href="{escape(url)}" color="#167d9a">{escape(url)}</link>' if url else '待部署後填入（本版沒有可驗證的公開連結）'))
add('本報告沒有以 localhost 或示意網址替代公開展示網址。要完成老師的 Chapter 2 驗收，必須使用持有者帳號建立公開原始碼儲存庫與線上應用，並以未登入視窗實際測試。','CodeC')
add('2.2 建議部署：GitHub + Streamlit Community Cloud','CH2')
for s in ['1. 建立 Public GitHub 儲存庫，將 image_lab 資料夾內的內容放到儲存庫根目錄。保留 models、assets、requirements.txt 與 app.py。','2. 登入 share.streamlit.io，建立應用並選擇儲存庫與 app.py，Python 選 3.12。套件由固定版 requirements.txt 安裝。','3. 設定應用為公開分享。使用無痕視窗分別開啟 App 與儲存庫，確認老師不登入也能操作及閱讀程式。','4. 測試載入 PNG/JPEG/BMP、U 通道、高斯卷積、雙人臉及下載，再填入本頁真實網址並重新產生報告。']:add(s)
add('2.3 備選：Hugging Face Docker Space','CH2')
add('建立 Public、Docker SDK 的 Space，上傳相同檔案；README 的 YAML 已指定 sdk: docker、app_port: 8501。Dockerfile 使用 Python 3.12-slim，以非 root 使用者執行，監聽 0.0.0.0:8501。模型已內附，避免首次推論時下載失敗。')
add('2.4 交付前檢查','CH2')
table([['項目','完成條件'],['Live Demo','Public；無痕視窗可實際推論；記下驗證日期'],['Source Code','Public；模型與範例資產完整；一鍵啟動說明可重現'],['PDF','填入學號／姓名，檔名符合「學號_姓名_期中專題.pdf」'],['截圖與 AI 紀錄','補真實介面截圖；核對實際模型名稱，保留完整對話匯出']])
br()
title('CHAPTER 3 · 3.1','系統架構與資料流')
story.append(diagram());story.append(Spacer(1,15))
add('輸入先通過檔案格式與資源上限檢查，再統一為 RGB uint8 陣列。色彩分析、濾波、人臉偵測皆以相同原始 RGB 為起點；切換色彩模式不會改變濾波或人臉偵測的輸入。')
table([['模組','責任與主要介面'],['app.py','Streamlit 呈現層：讀檔、三個頁籤、參數輸入、訊息與下載'],['core.load_image','解碼、格式驗證、EXIF 方向、白底透明合成；輸出 RGB 與 metadata'],['core.channels / histogram','RGB 拆分、YUV 轉換；每通道 256 bins 計數'],['core.parse_kernel / convolve','解析與驗證權重、計算除數、翻轉核、卷積、裁切'],['core.quality','float64 MSE 與 PSNR；處理相同影像'],['core.detect_faces','YuNet 推論、NMS、框座標還原、信心分數及繪圖']])
add('檔案與資料管理','CH2')
add('上傳影像在部署主機記憶體內處理，本程式不主動寫入使用者影像。模型每次偵測建立獨立 detector，避免共享可變 input size；點擊「開始偵測」才推論。模型檔隨附 SHA-256 與來源授權。')
br()
title('CHAPTER 3 · 3.2','影像載入與通道檢視')
add('操作：左側上傳 PNG、JPG/JPEG 或 BMP，或選擇內建色彩圖、單人臉、雙人臉。頂端顯示解析度、處理維度、檔案大小及來源格式；另顯示來源通道數，避免把灰階原始檔誤稱為三通道。')
add('EXIF 旋轉先校正再顯示；透明圖合成白底；灰階、調色盤等模式轉成 RGB。所有 PSNR 與濾波基準均為這張轉換後原圖。超過 20 MiB 或 1,200 萬像素會拒絕處理。')
image(E/'channels_grid.png',caption='圖 3-1｜真實演算法輸出，非介面截圖。上列 Original/R/G/B，下列 Y/U/V。輸入為 540×360 合成圖，含漸層、紅色與綠色區塊。')
add('RGB 分量是各自的強度圖','CH2')
add('例如 R 通道中紅色區塊為亮色，綠色區塊較暗。單通道以固定 0–255 灰階顯示，不隨每張圖自動拉伸對比，確保畫面明暗與直方圖數值一致。Original 仍顯示彩色圖。')
add('畫面切換會觸發 Streamlit 重新執行，以同一份 view 陣列同時更新圖片與直方圖，避免顯示模式與統計資料不一致。')
br()
title('CHAPTER 3 · 3.3','YUV 與同步直方圖')
add('採用 OpenCV COLOR_RGB2YUV 的 8-bit、三通道完整解析度編碼，與 YCbCr、I420、NV12 等格式不同。Y 代表亮度資訊，U/V 代表色度差；U/V 以 128 作為中性色偏移。')
add('Y = 0.299R + 0.587G + 0.114B<br/>U = 0.492(B - Y) + 128<br/>V = 0.877(R - Y) + 128','CodeC')
add('上述為公式說明；實作使用 cvtColor，輸出依 OpenCV 整數轉換規則量化及飽和至 0–255。RGB 已先轉為正確順序；人臉模組才另外轉 BGR。')
image(E/'histograms.png',caption='圖 3-2｜由圖 3-1 的 Y/U/V 實際計數；每張直方圖的總數均為 194,400。')
add('直方圖定義','CH2')
add('h(k) = 像素強度恰為 k 的像素數，k = 0,1,…,255。使用 numpy.bincount(..., minlength=256)，橫軸固定 0–255，縱軸為像素數量。單通道總數為 H×W，Original 三條曲線各自也為 H×W。')
add('測試以純紅色影像驗證 Y 約為 76；並逐通道檢查 bins 數量為 256、計數加總等於像素總數，確保沒有將機率密度誤當像素數量。')
br()
title('CHAPTER 3 · 3.4','自訂卷積與正規化')
add('操作：選擇「自訂卷積與 PSNR」頁籤，先挑範例核，再直接修改文字。支援每列換行的空白／逗號數字與 JSON 二維陣列。可選不正規化、除以權重總和、自訂除數，再指定偏移與邊界模式。')
table([['參數','規則與原因'],['矩陣形狀','1–15 階奇數方陣；拒絕不等長列、非方陣與偶數尺寸，明確固定中心錨點'],['權重','接受正負、小數；必須有限；絕對值 ≤10000'],['正規化','none：D=1；sum：D=ΣK；custom：D=使用者值。|D|&lt;10⁻¹² 或非有限值時拒絕'],['偏移 b','加在卷積結果上，範圍 ±10000；浮雕可設為128'],['邊界','reflect：BORDER_REFLECT_101；replicate：複製邊緣；zero：補零'],['輸出','float64 運算 → numpy.rint 四捨五入（半值取偶）→ 裁切0–255 → uint8']])
add('真正卷積的方向','CH2')
add('F(y,x,c) = sum_i sum_j [K(i,j)/D] · I(y-i,x-j,c) + b','CodeC')
add('OpenCV filter2D 預設實作相關運算；若直接使用不對稱浮雕核，方向會相反。本工具先 np.flip(kernel, axis=(0,1))，再交給 filter2D。以不對稱「右側為1」核測試，卷積結果應讀到左鄰像素；另以手寫 5×5 小圖參考計算逐點比對。')
add('高斯範例核為 [[1,2,1],[2,4,2],[1,2,1]]，D=16。零和邊緣核則保留 none；不可除以權重總和0。裁切分量比例統計浮點結果有多少 RGB 分量超出0–255，協助解讀過強權重造成的失真。')
br()
title('CHAPTER 3 · 3.5','PSNR 公式與客觀評估')
add('先定義誤差 e = I - F。H 為高、W 為寬、C=3，8-bit 最大值 MAX=255。MSE 是所有像素與通道誤差平方的平均；PSNR 是峰值功率與平均誤差功率之比取對數。')
add('MSE = [1 / (H × W × C)] sum_y sum_x sum_c (I(y,x,c) - F(y,x,c))²<br/>PSNR = 10 log₁₀(MAX² / MSE)<br/>= 20 log₁₀(255 / √MSE)　（MSE &gt; 0）','CodeC')
add('MSE=0 時回傳正無限大，不以任意大數代替。先轉 float64 再相減，避免 uint8 溢位。評估對象是最後供顯示及下載的量化、裁切結果，而非未裁切的浮點中間影像。')
rows=[['濾波／除數／偏移','MSE','PSNR dB','裁切比例']]
labels={'identity':'恆等 / 1 / 0','gaussian':'高斯 / 16 / 0','sharpen':'銳化 / 1 / 0','emboss':'浮雕 / 1 / 128'}
for r in m['filters']:rows.append([labels[r['name']],f"{r['mse']:.4f}",'正無限大' if r['psnr_db'] is None else f"{r['psnr_db']:.4f}",f"{r['clipped_fraction']*100:.2f}%"])
table(rows,[200,95,100,90])
image(E/'filters_grid.png',width=420,caption='圖 3-3｜同一合成原圖、反射邊界的實際輸出；左上恆等、右上高斯、左下銳化、右下浮雕。')
add('高斯會平滑邊緣；銳化放大局部差異，約1.29%分量被裁切；浮雕與128偏移大幅改變亮度，PSNR 較低。此處原圖不是無雜訊真值，因此數值表示與原圖的接近程度，不能單以 PSNR 高低判定濾波用途或主觀品質優劣。','SmallC')
br()
title('CHAPTER 3 · 3.6','人臉偵測與信心分數')
add('操作：「人臉分析」頁籤可調整信心門檻（預設0.80）與 NMS IoU 門檻（預設0.30），再點擊「開始偵測」。顯示框圖、人臉總數、原始圖座標及每張臉分數，可下載 PNG 和 JSON。')
add('使用 YuNet 2023mar ONNX 與 OpenCV FaceDetectorYN。偵測輸出每列包含框位置、五組特徵點與 confidence；本工具讀取第15欄（索引14）。NMS 移除高度重疊候選框，回傳所有通過目前門檻與 NMS 的結果，不只保留最大臉。')
image(E/'detected_two_faces.png',caption='圖 3-4｜實際推論輸出，非介面截圖。NASA 公開領域範例照片並排拼接，偵測2張臉。')
table([['場景','結果／座標／分數'],['無人臉合成圖','0張；回傳空清單，不產生虛構分數'],['單人臉 512×512','1張；(x=178, y=63, w=90, h=113)；0.932327'],['雙人臉 1024×512','2張；(178,63,90,113) 與 (690,63,90,113)；分數皆約0.932327']])
add('大圖長邊縮至1280推論後，依實際縮圖寬高比例還原座標並裁切到圖內。額外以1536×1536放大圖測試還原流程。Confidence 是模型分數，不是經校準的機率；未做人臉身分識別。')
add('雙人臉測試為同一照片複製，可證明多框與計數流程，無法代表多樣人臉準確率。小臉、側臉、遮擋、低照度可能漏檢，不能保證所有真實場景的人臉皆會被找出。','SmallC')
br()
title('CHAPTER 3 · 3.7','測試案例與邊界條件')
add('實際執行：python -m pytest image_lab -q。27 項通過，含參數化案例；完整輸出見 evidence/test_results.txt。測試不是僅檢查程式有無執行，也驗證卷積方向、參考值、框座標、數量與介面錯誤訊息。')
table([['類別','測試內容與預期'],['檔案載入','PNG/JPEG/BMP 都解碼；灰階來源維度保留；透明像素合成白底'],['輸入防呆','空檔、損壞檔、超過20 MiB均 ValueError，不進行後續運算'],['色彩／直方圖','純紅Y=76；各模式256 bins，計數總和=H×W'],['矩陣格式','拒絕偶數核、不等長列、空值、非方陣、NaN、Inf、超限權重'],['極端與除數','10000權重可運算並飽和255；零和、零除數、NaN除數明確拒絕'],['卷積正確性','不對稱核方向正確；逐像素對照手寫參考；5×5平均核保留常數影像'],['PSNR','恆等核 MSE=0、PSNR=正無限大；全黑對全白 MSE=65025、PSNR=0 dB'],['人臉','無臉0、單臉1、雙臉2；分數在範圍內，框在圖內；大圖座標還原'],['AppTest','全部顯示模式切換無例外；非法核出現 error；點擊雙人臉偵測顯示2']])
add('尚未執行的驗收，不列為通過','CH2')
add('公開主機部署、無痕訪問與真實瀏覽器上傳操作仍待帳號端執行；極暗、遮擋、密集自然多人臉場景亦尚未做準確率實驗。1200萬像素上限已有程式保護，但本版測試沒有配置最大圖進行記憶體壓力量測。')
add('測試資料來源：色彩圖為程式生成；人臉為 scikit-image astronaut 的 NASA 公開領域照片，雙臉由其拼接而成。無使用私人照片或任何身分資料。')
br()
title('CHAPTER 3 · 3.8','介面操作截圖補齊流程')
ui=[('01_original.png','影像載入／Original 與直方圖'),('02_yuv.png','U通道與同步直方圖'),('03_filter.png','高斯濾波／PSNR／前後並排'),('04_validation.png','非法矩陣防呆提示'),('05_faces.png','雙人臉總數／框／信心分數')]
existing=[x for x in ui if (E/x[0]).exists()]
if not existing:
    add('本版尚無真實 GUI 截圖。','CH2')
    add('本次程式主機能執行 Streamlit 與 AppTest，但可用瀏覽器無法連到該主機 localhost:8501。前頁圖3-1至3-4均為實際演算法輸出，沒有標示為介面截圖，也不以示意介面替代。')
    add('補齊方式','CH2')
    add('1. 本機先啟動 App，保持終端機開啟。<br/>2. 另一個終端機執行下列指令，capture_ui.py 會操作內建圖並產生5張截圖。<br/>3. 將公開網址與身分資料傳給 build_report.py，重建後 PDF 會自動插入截圖。')
    add('python -m pip install playwright==1.60.0 reportlab<br/>python -m playwright install chromium<br/>python capture_ui.py<br/>python build_report.py --student-id 學號 --name 姓名 --demo 公開網址 --repo GitHub網址','CodeC')
    table([['截圖檔','應出現的操作證據']]+[[f'data: {n}',c] for n,c in ui])
    add('自動截圖腳本已提供，但由於本次瀏覽器連線限制，尚未在真實瀏覽器完整走完；若平台介面結構改變，需依實際畫面調整定位。補圖後務必人工確認截圖中的參數與結果對應。','SmallC')
else:
    add('以下頁面納入執行 capture_ui.py 後產生的介面截圖；請在提交前確認畫面與參數。')
    for fn,cap in existing:
        br();add(cap,'CH1');image(E/fn,caption=f'介面截圖：{fn}')
br()
title('CHAPTER 4 · 4.1','AI 協作與真實 Prompt 歷程')
add('協作日期：2026-11-08。工具：ChatGPT Work / Codex。系統自我識別為 GPT-6 系列；本執行環境未提供可核驗的精確子版本 ID。提交前請依 ChatGPT 介面實際模型標示補記，不冒用題目舉例的 GPT-4o 或 Claude 名稱。')
add('4.1 原始 Prompt 與 AI 初始回覆','CH2')
add('使用者提供完整考題、四大功能、報告規範與評分表，最後詢問「可以幫我做嗎」。完整 Prompt 逐字文字收錄於附錄及 audit/original_prompt.txt，不只保留這句簡短請求。')
add('AI 初始回覆：我會先製作可執行的影像處理程式、測試案例與 PDF 報告，並保留這次實際的 AI 協作紀錄。報告需要的學號、姓名，以及公開展示和原始碼連結，我會先留明確欄位，避免填入未確認的資料。','CodeC')
add('4.2 AI 產出對照','CH2')
table([['需求上下文','本輪 AI 實際產出'],['四大功能與中文介面','app.py、core.py；上傳、通道、直方圖、卷積、PSNR、YuNet'],['相依性與可執行性','requirements.txt、Dockerfile、Streamlit設定、Windows啟動器'],['正確性與邊界測試','tests/test_core.py、tests/test_ui.py；27項通過'],['實測圖與品質分析','evidence/metrics.json、人臉框圖、通道及濾波圖'],['PDF與審計紀錄','build_report.py、AI_AUDIT.md、完整原始Prompt附錄']])
add('這次只有一輪使用者需求；下頁記錄 AI 實際發出的工具修正與驗證結果，不把工具工作紀錄寫成未發生的使用者 Refinement 對話。')
br()
title('CHAPTER 4 · 4.3','除錯、調整與紀錄限制')
add('實際除錯鏈：測試失敗 → 修正工具指令 → 重跑','CH2')
add('第一輪測試得到 26 passed、1 failed；錯誤為 ValueError: 雙人臉 is not in list。AppTest 的 selectbox[0] 實際指向「矩陣範例」，測試錯把影像來源選項設定到這個欄位。')
add('原測試：at.selectbox[0].select(雙人臉).run()<br/>實際修正：依 label「或使用內建測試影像」找出 selectbox，再 select(雙人臉).run()','CodeC')
add('這是可重現的介面測試定位錯誤；修正後維持預期人臉數=2，未刪除測試或改成容易通過的預期。第二輪得到27項通過。相同測試輸出保存於 evidence/test_results.txt。')
add('其他實際調整','CH2')
add('查閱 OpenCV 原始文件後，濾波實作明確旋轉核180度；用非對稱核與手寫參考驗證。人臉模組使用模型分數欄位；PSNR 先轉 float64；零和核禁止權重總和正規化。這些是本次 AI 實作選擇與工具驗證，並非後補假想使用者對話。')
add('遇到的外部限制','CH2')
add('本機瀏覽器啟動受系統 socket 限制，遠端瀏覽器則無法連線 localhost。保留實測數據，附上本機截圖腳本並標明未完成截圖。初版沒有可用登入狀態建立儲存庫，其後使用者完成 GitHub 授權並建立公開儲存庫；本版已補入原始碼連結。Live Demo 仍未部署，未聲稱通過線上應用 Public 驗收。')
add('完整性聲明','CH2')
add('本報告保留原始 Prompt、AI 初始回覆、成果對照與真實除錯摘要；不是平台提供的完整逐字對話匯出，也沒有逐字嵌入每個工具呼叫。老師若要求完全逐字的 AI Audit Trail，請將本次完整對話匯出並附在本報告後，後續修改亦照實追加。學號、姓名、精確模型名稱與公開連結須由使用者核對。')
add('建議後續提問應針對實際問題，並保留原文、AI回覆與修正驗證；不可把尚未提出的建議 Prompt 寫成過去已執行的紀錄。')
br()
title('REFERENCES','技術來源與提交前清單')
refs=[('OpenCV Image Filtering','https://docs.opencv.org/4.10.0/d4/d86/group__imgproc__filter.html'),('OpenCV Color Conversions','https://docs.opencv.org/4.11.0/de/d25/imgproc_color_conversions.html'),('OpenCV DNN Face Tutorial','https://docs.opencv.org/4.10.0/d0/dd4/tutorial_dnn_face.html'),('OpenCV Zoo YuNet','https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet'),('Streamlit App Dependencies','https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies'),('Streamlit Deploy Guide','https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy'),('scikit-image astronaut','https://scikit-image.org/docs/0.24.x/api/skimage.data.html#skimage.data.astronaut')]
for i,(label,url) in enumerate(refs,1):add(f'[{i}] {label}<br/><link href="{url}" color="#167d9a">{url}</link>','SmallC')
add('第三方資產','CH2')
add('NASA Eileen Collins 照片為公開領域範例；拼接雙臉圖用於多框流程驗證。YuNet 模型採來源附帶的 LICENSE-YuNet，OpenCV Zoo 授權亦隨附；自寫程式碼另採 MIT。模型 SHA-256：','SmallC')
add('8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4','SmallC')
add('提交前清單','CH2')
for s in [('已填入學號與姓名，正式檔名已設定；請核對正確性。' if a.student_id!='待填學號' and a.name!='待填姓名' else '填妥學號與姓名，檔名改成正式規定格式。'),'建立Public原始碼與Live Demo，無痕測試後填入真實網址。','執行自動截圖或手動拍攝介面，重建PDF並檢查圖表。','核對實際AI模型名稱，將完整對話匯出及後續調整附於報告。','只繳交老師要求的PDF；ZIP保留作為程式部署與查驗來源。']:add('□ '+s)
br()
title('APPENDIX A','本輪使用者完整原始 Prompt')
add('下文保留原始題目文字、Markdown記號與題目中重複的公式排版字串；以可搜尋的文字重新排版，未使用純文字截圖。','SmallC')
for line in (ROOT/'audit/original_prompt.txt').read_text().splitlines():
    if line.strip():add(escape(line),'SmallC')
    else:story.append(Spacer(1,5))

if (ROOT/'audit/followup.txt').exists():
    br();title('APPENDIX B','後續使用者補充紀錄')
    for line in (ROOT/'audit/followup.txt').read_text().splitlines():
        if line.strip():add(escape(line))

def footer(c,doc):
    w,h=doc.pagesize;c.setStrokeColor(teal);c.line(55,h-38,w-55,h-38)
    c.setFont(FONT,8);c.setFillColor(navy);c.drawString(55,h-29,'PIXEL LAB｜影像處理期中專題')
    c.drawString(55,26,'2026-11-08 · '+('待補公開部署與截圖' if not a.demo or not existing else '提交前請完成無痕驗收'))
    c.drawRightString(w-55,26,f'{doc.page}')
output=Path(a.output) if a.output else ROOT/f'{a.student_id}_{a.name}_期中專題.pdf'
output.parent.mkdir(parents=True,exist_ok=True)
doc=SimpleDocTemplate(str(output),pagesize=(595.28,841.89),rightMargin=55,leftMargin=55,topMargin=60,bottomMargin=48,title='Pixel Lab 互動式影像處理與人臉分析工具',author=a.name)
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(output.resolve())
