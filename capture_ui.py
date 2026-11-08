"""Capture the actual Streamlit UI; start a local test server if needed."""
from pathlib import Path
import subprocess,sys,time,urllib.request
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
out=ROOT/'evidence';out.mkdir(exist_ok=True)
server=None

def healthy():
    try:
        with urllib.request.urlopen('http://localhost:8501/_stcore/health',timeout=2) as r:return r.status==200
    except Exception:return False

try:
    if not healthy():
        server=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.port=8501','--server.headless=true','--browser.gatherUsageStats=false'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
        for _ in range(60):
            if healthy():break
            if server.poll() is not None:raise RuntimeError('Streamlit server stopped')
            time.sleep(.5)
        else:raise RuntimeError('Streamlit startup timed out')
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True,args=['--no-sandbox'])
        page=b.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
        page.goto('http://localhost:8501')
        page.get_by_text('PIXEL LAB · 影像處理實驗室',exact=False).wait_for(timeout=30000)
        page.get_by_test_id('stImage').first.wait_for()
        page.get_by_role('tab',name='色彩與直方圖',exact=True).click()
        page.screenshot(path=str(out/'01_original.png'),full_page=True)
        page.get_by_text('U',exact=True).click()
        page.get_by_text('U｜通道強度圖',exact=True).wait_for()
        page.screenshot(path=str(out/'02_yuv.png'),full_page=True)
        page.get_by_role('tab',name='自訂卷積與 PSNR',exact=True).click()
        page.get_by_test_id('stSelectbox').filter(has_text='矩陣範例').get_by_role('combobox').click()
        page.get_by_role('option',name='高斯平滑',exact=True).click()
        page.get_by_text('36.694 dB',exact=True).wait_for()
        page.screenshot(path=str(out/'03_filter.png'),full_page=True)
        field=page.get_by_role('textbox',name='卷積核',exact=False)
        field.fill('1 2\n3 4');field.press('Tab')
        page.get_by_text('矩陣必須為 1～15 階的奇數方陣，例如 3×3 或 5×5。',exact=True).wait_for()
        page.screenshot(path=str(out/'04_validation.png'),full_page=True)
        page.get_by_test_id('stSelectbox').filter(has_text='或使用內建測試影像').get_by_role('combobox').click()
        page.get_by_role('option',name='雙人臉',exact=True).click()
        page.get_by_role('tab',name='人臉分析',exact=True).click()
        page.get_by_role('button',name='開始偵測',exact=True).click()
        page.get_by_text('YuNet｜2 faces',exact=True).wait_for()
        page.screenshot(path=str(out/'05_faces.png'),full_page=True)
        b.close()
    print('Saved five actual app screenshots in evidence/')
finally:
    if server:
        server.terminate()
        try:server.wait(timeout=5)
        except subprocess.TimeoutExpired:server.kill()
