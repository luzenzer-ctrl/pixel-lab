from pathlib import Path
from streamlit.testing.v1 import AppTest

def app():
    return AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=30).run()

def test_initial_and_modes():
    at=app();assert not at.exception
    for mode in ['R','G','B','Y','U','V','Original']:
        at.radio[0].set_value(mode).run();assert not at.exception

def test_invalid_kernel_error():
    at=app();at.text_area[0].set_value('1 2\n3 4').run()
    assert not at.exception;assert len(at.error)==1

def test_face_button():
    at=app();next(s for s in at.selectbox if s.label=='或使用內建測試影像').select('雙人臉').run()
    next(b for b in at.button if b.label=='開始偵測').click().run()
    assert not at.exception
    assert any(m.label=='偵測到的人臉數' and m.value=='2' for m in at.metric)
