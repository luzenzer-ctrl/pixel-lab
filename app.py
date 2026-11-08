from pathlib import Path
import json
import math
import cv2
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from core import load_image, channels, histogram, parse_kernel, convolve, quality, detect_faces, png_bytes

ROOT=Path(__file__).parent
st.set_page_config(page_title='Pixel Lab｜影像處理實驗室',page_icon='🔬',layout='wide')
st.markdown('### PIXEL LAB · 影像處理實驗室')
st.caption('探索色彩分布、自訂卷積與人臉偵測｜Python + Streamlit + OpenCV')
with st.sidebar:
    st.header('01｜影像來源')
    upload=st.file_uploader('上傳 PNG / JPG / JPEG / BMP',type=['png','jpg','jpeg','bmp'])
    sample=st.selectbox('或使用內建測試影像',['色彩測試圖','單人臉','雙人臉'])
    st.caption('限制：20 MiB、1,200 萬像素。透明背景合成為白色；分析統一使用 8-bit RGB。')
    st.info('所有功能皆在執行程式的主機處理；本程式不主動儲存使用者上傳影像。')
files={'色彩測試圖':'color.png','單人臉':'face.png','雙人臉':'two_faces.png'}
try:
    raw=upload.getvalue() if upload else (ROOT/'assets'/files[sample]).read_bytes()
    rgb,meta=load_image(raw)
except (ValueError,OSError) as e:
    st.error(str(e)); st.stop()
cols=st.columns(4)
for col,label,value in zip(cols,['影像解析度','處理維度','檔案大小','來源格式'],
        [f"{meta['width']} × {meta['height']}",'3 channels / uint8',f"{meta['bytes']/1024:.1f} KiB",f"{meta['format']} / {meta['source_mode']}"]):
    col.metric(label,value)
st.caption(f"來源通道數：{meta['source_channels']}；目前陣列形狀：{rgb.shape}。解析度依 EXIF 方向校正後顯示。")
tab1,tab2,tab3=st.tabs(['色彩與直方圖','自訂卷積與 PSNR','人臉分析'])
with tab1:
    mode=st.radio('顯示模式',['Original','R','G','B','Y','U','V'],horizontal=True)
    view=channels(rgb)[mode]
    a,b=st.columns(2)
    a.image(view,caption=f'{mode}｜通道強度圖',clamp=True,use_container_width=True)
    fig,ax=plt.subplots(figsize=(6,3.7))
    for name,counts in histogram(view).items():
        ax.plot(np.arange(256),counts,label=name,color={'R':'#e45e61','G':'#269873','B':'#3b7acb'}.get(name,'#167d9a'))
    ax.set(xlim=(0,255),xlabel='Pixel intensity (0-255)',ylabel='Pixel count')
    ax.grid(alpha=.15); ax.legend(); fig.tight_layout(); b.pyplot(fig); plt.close(fig)
    st.caption('R/G/B 與 Y/U/V 皆以灰階顯示單一分量。U、V 為 OpenCV 8-bit YUV 編碼，128 附近代表中性色度。Original 同時顯示三通道直方圖。')
with tab2:
    presets={'恆等':'0 0 0\n0 1 0\n0 0 0','高斯平滑':'1 2 1\n2 4 2\n1 2 1',
             '銳化':'0 -1 0\n-1 5 -1\n0 -1 0','邊緣':'-1 -1 -1\n-1 8 -1\n-1 -1 -1',
             '浮雕':'-2 -1 0\n-1 1 1\n0 1 2','自訂':'1 1 1\n1 1 1\n1 1 1'}
    p=st.selectbox('矩陣範例',list(presets))
    text=st.text_area('卷積核：各列換行，數值以空白或逗號分隔；也接受 JSON 二維陣列',value=presets[p],key='kernel_'+p,height=125)
    c1,c2,c3,c4=st.columns(4)
    norm=c1.selectbox('正規化',['none','sum','custom'],index=1 if p=='高斯平滑' else 0,format_func=lambda x:{'none':'不正規化','sum':'除以權重總和','custom':'自訂除數'}[x],key='norm_'+p)
    divisor=c2.number_input('自訂除數',value=1.,disabled=norm!='custom')
    bias=c3.number_input('輸出偏移值',min_value=-10000.,max_value=10000.,value=0.,help='浮雕可設為 128')
    border=c4.selectbox('邊界模式',['reflect','replicate','zero'],format_func=lambda x:{'reflect':'反射','replicate':'複製','zero':'補零'}[x])
    try:
        kernel=parse_kernel(text)
        filtered,info=convolve(rgb,kernel,norm,divisor,bias,border)
        mse,psnr=quality(rgb,filtered)
        a,b,c=st.columns(3)
        a.metric('PSNR','∞ dB' if math.isinf(psnr) else f'{psnr:.3f} dB')
        b.metric('MSE',f'{mse:.6f}'); c.metric('裁切分量比例',f"{100*info['clipped_fraction']:.2f}%")
        a,b=st.columns(2); a.image(rgb,caption='原始影像',use_container_width=True); b.image(filtered,caption='卷積結果',use_container_width=True)
        st.caption(f"卷積核 {kernel.shape}｜實際除數 {info['divisor']:.6g}｜旋轉核 180° 後運算，四捨五入並裁切至 0–255。")
        st.download_button('下載濾波影像',png_bytes(filtered),'filtered.png','image/png')
        st.download_button('下載濾波參數',json.dumps({'kernel':kernel.tolist(),'normalization':norm,'divisor':info['divisor'],'bias':bias,'border':border,'mse':mse,'psnr_db':None if math.isinf(psnr) else psnr,'psnr_infinite':math.isinf(psnr)},ensure_ascii=False,indent=2),'filter_parameters.json','application/json')
    except (ValueError,cv2.error) as e:
        st.error(str(e))
    st.info('PSNR 衡量輸出與原圖的差異。平滑、銳化本來就會改變像素，PSNR 較低不代表視覺效果一定較差。')
    with st.expander('PSNR 與卷積公式'):
        st.latex(r'\mathrm{MSE}=\frac{1}{HWC}\sum_{y,x,c}(I_{yxc}-K_{yxc})^2')
        st.latex(r'\mathrm{PSNR}=10\log_{10}\left(\frac{255^2}{\mathrm{MSE}}\right)')
        st.write('MSE 為零時 PSNR = ∞；計算前轉為 float64，避免 uint8 減法溢位。')
with tab3:
    st.subheader('YuNet 人臉偵測')
    a,b=st.columns(2)
    threshold=a.slider('信心分數門檻',.1,.99,.8,.01)
    nms=b.slider('NMS IoU 門檻',.1,.9,.3,.05)
    st.caption('在原始影像上偵測。超過 1280 像素長邊時縮小推論，再將框座標還原；分數不是經校準的機率。')
    if st.button('開始偵測',type='primary'):
        try:
            with st.spinner('偵測中…'):
                marked,faces=detect_faces(rgb,threshold,nms)
            st.metric('偵測到的人臉數',len(faces))
            st.image(marked,caption=f'YuNet｜{len(faces)} faces',use_container_width=True)
            if faces: st.dataframe(faces,use_container_width=True,hide_index=True)
            else: st.info('目前門檻未偵測到人臉；可降低門檻或改用清晰正面照。')
            st.download_button('下載標記影像',png_bytes(marked),'faces.png','image/png')
            st.download_button('下載框座標與分數',json.dumps(faces,indent=2),'faces.json','application/json')
        except (ValueError,cv2.error) as e:
            st.error(f'偵測失敗：{e}')
