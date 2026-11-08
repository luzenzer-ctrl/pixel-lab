"""Pure image operations. All public image arrays use uint8 RGB."""
from pathlib import Path
from io import BytesIO
import json
import math
import warnings
import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 12_000_000
MODEL = Path(__file__).parent / 'models/face_detection_yunet_2023mar.onnx'

def load_image(raw):
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('檔案必須非空且不超過 20 MiB。')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as im:
                if im.format not in {'PNG', 'JPEG', 'BMP'}:
                    raise ValueError('僅接受 PNG、JPG/JPEG、BMP。')
                if im.width * im.height > MAX_PIXELS:
                    raise ValueError('影像不得超過 1,200 萬像素。')
                meta = dict(format=im.format, source_mode=im.mode,
                            source_channels=len(im.getbands()), bytes=len(raw))
                im = ImageOps.exif_transpose(im)
                if 'A' in im.getbands() or 'transparency' in im.info:
                    fg = im.convert('RGBA')
                    bg = Image.new('RGBA', fg.size, 'white')
                    im = Image.alpha_composite(bg, fg)
                rgb = np.array(im.convert('RGB'), dtype=np.uint8)
                meta.update(width=rgb.shape[1], height=rgb.shape[0], channels=3, dtype='uint8')
                return rgb, meta
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning,
            Image.DecompressionBombError) as exc:
        raise ValueError('無法解碼此影像，請檢查檔案是否損壞。') from exc

def channels(rgb):
    yuv = cv2.cvtColor(rgb, cv2.COLOR_RGB2YUV)
    return {'Original': rgb, **{n: rgb[:,:,i] for i,n in enumerate('RGB')},
            **{n: yuv[:,:,i] for i,n in enumerate('YUV')}}

def histogram(arr):
    if arr.ndim == 2:
        return {'Intensity': np.bincount(arr.ravel(), minlength=256)}
    return {n:np.bincount(arr[:,:,i].ravel(), minlength=256) for i,n in enumerate('RGB')}

def parse_kernel(text):
    if len(text) > 30000:
        raise ValueError('矩陣文字過長。')
    try:
        if text.lstrip().startswith('['):
            values = json.loads(text)
        else:
            values = [[float(v) for v in line.replace(',', ' ').split()]
                      for line in text.strip().splitlines() if line.strip()]
        k = np.asarray(values, dtype=np.float64)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError('請輸入數值方陣，各列換行、各數值以空白或逗號分隔。') from exc
    if k.ndim != 2 or k.shape[0] != k.shape[1] or k.shape[0] % 2 != 1 or not 1 <= k.shape[0] <= 15:
        raise ValueError('矩陣必須為 1～15 階的奇數方陣，例如 3×3 或 5×5。')
    if not np.isfinite(k).all() or np.abs(k).max() > 10000:
        raise ValueError('權重必須為有限數值，絕對值不可超過 10000。')
    return k

def convolve(rgb, kernel, normalization='none', divisor=1., bias=0., border='reflect'):
    k = parse_kernel(json.dumps(np.asarray(kernel).tolist()))
    if normalization == 'sum':
        d = float(k.sum())
    elif normalization == 'custom':
        d = float(divisor)
    elif normalization == 'none':
        d = 1.
    else:
        raise ValueError('未知正規化模式。')
    if not math.isfinite(d) or abs(d) < 1e-12:
        raise ValueError('正規化除數不可為零或接近零；零和邊緣核請選不正規化。')
    if not math.isfinite(bias) or abs(bias) > 10000:
        raise ValueError('偏移值必須為有限數值，絕對值不可超過 10000。')
    borders = {'reflect':cv2.BORDER_REFLECT_101, 'replicate':cv2.BORDER_REPLICATE,
               'zero':cv2.BORDER_CONSTANT}
    if border not in borders:
        raise ValueError('未知邊界模式。')
    # filter2D is correlation; flip both axes to perform mathematical convolution.
    floating = cv2.filter2D(rgb.astype(np.float64), cv2.CV_64F,
                           np.flip(k / d, axis=(0,1)), delta=bias, borderType=borders[border])
    out = np.clip(np.rint(floating), 0, 255).astype(np.uint8)
    return out, {'divisor':d, 'clipped_fraction':float(np.mean((floating<0)|(floating>255)))}

def quality(original, result):
    if original.shape != result.shape or original.size == 0:
        raise ValueError('兩張影像尺寸必須相同且非空。')
    mse = float(np.mean((original.astype(np.float64)-result.astype(np.float64))**2))
    return mse, math.inf if mse == 0 else 10 * math.log10(255**2/mse)

def detect_faces(rgb, threshold=.8, nms=.3, max_side=1280):
    if not MODEL.exists():
        raise ValueError('缺少 YuNet 模型，請保留 models 資料夾。')
    h,w=rgb.shape[:2]
    scale=min(1.,max_side/max(w,h))
    small=cv2.resize(rgb,(max(1,round(w*scale)),max(1,round(h*scale))))
    sh,sw=small.shape[:2]
    detector=cv2.FaceDetectorYN.create(str(MODEL),'',(sw,sh),float(threshold),float(nms),5000)
    _, found=detector.detect(cv2.cvtColor(small,cv2.COLOR_RGB2BGR))
    rows=[]
    for face in ([] if found is None else found):
        x,y,bw,bh=face[:4]
        x1=max(0,min(w-1,round(float(x)*w/sw)))
        y1=max(0,min(h-1,round(float(y)*h/sh)))
        x2=max(x1+1,min(w,round(float(x+bw)*w/sw)))
        y2=max(y1+1,min(h,round(float(y+bh)*h/sh)))
        rows.append(dict(id=len(rows)+1,x=x1,y=y1,width=x2-x1,height=y2-y1,
                         confidence=float(face[14])))
    marked=rgb.copy()
    for r in rows:
        x,y=r['x'],r['y']
        cv2.rectangle(marked,(x,y),(x+r['width']-1,y+r['height']-1),(24,220,130),2)
        cv2.putText(marked,f"#{r['id']} {r['confidence']:.3f}",(x,max(14,y-6)),
                    cv2.FONT_HERSHEY_SIMPLEX,.5,(24,220,130),1,cv2.LINE_AA)
    return marked,rows

def png_bytes(rgb):
    out=BytesIO(); Image.fromarray(rgb).save(out,format='PNG'); return out.getvalue()
