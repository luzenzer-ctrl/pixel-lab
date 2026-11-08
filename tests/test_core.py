from io import BytesIO
import math
from pathlib import Path
import numpy as np
import cv2
import pytest
from PIL import Image
from core import load_image, channels, histogram, parse_kernel, convolve, quality, detect_faces

@pytest.mark.parametrize('fmt',['PNG','JPEG','BMP'])
def test_load_formats(fmt):
    f=BytesIO();Image.new('RGB',(12,9),(21,83,146)).save(f,fmt)
    a,m=load_image(f.getvalue());assert a.shape==(9,12,3);assert m['format']==fmt;assert m['bytes']==len(f.getvalue())

def test_transparent_and_gray():
    f=BytesIO();Image.new('RGBA',(2,2),(255,0,0,0)).save(f,'PNG')
    assert np.all(load_image(f.getvalue())[0]==255)
    f=BytesIO();Image.new('L',(2,2),77).save(f,'BMP')
    a,m=load_image(f.getvalue());assert m['source_channels']==1;assert np.all(a==77)

@pytest.mark.parametrize('raw',[b'',b'not an image'])
def test_bad_files(raw):
    with pytest.raises(ValueError): load_image(raw)

def test_oversize_bytes():
    with pytest.raises(ValueError):load_image(b'0'*(20*1024*1024+1))

def test_hist_and_yuv():
    a=np.zeros((2,3,3),dtype='uint8');a[:,:,0]=255
    ch=channels(a)
    assert np.array_equal(ch['Y'],cv2.cvtColor(a,cv2.COLOR_RGB2YUV)[:,:,0])
    assert int(ch['Y'][0,0])==76
    for mode,v in ch.items():
        for hist in histogram(v).values():assert hist.shape==(256,);assert hist.sum()==6
    assert histogram(ch['R'])['Intensity'][255]==6

@pytest.mark.parametrize('text',['1 2\n3 4','1 2 3\n4 5','nan','inf','10001','[[1], [2]]','', '1e309'])
def test_invalid_kernels(text):
    with pytest.raises(ValueError):parse_kernel(text)

def test_extreme_valid():
    a=np.full((3,3,3),255,dtype='uint8')
    out,info=convolve(a,np.array([[10000.]]));assert np.all(out==255);assert info['clipped_fraction']==1

def test_normalization_zero():
    a=np.zeros((4,4,3),dtype='uint8')
    for norm,d in [('sum',1),('custom',0),('custom',float('nan'))]:
        with pytest.raises(ValueError):convolve(a,[[0]],norm,d)

def test_identity_and_psnr():
    a=np.arange(75,dtype='uint8').reshape(5,5,3)
    b,_=convolve(a,[[1]])
    assert np.array_equal(a,b);assert quality(a,b)==(0.,math.inf)
    mse,p=quality(np.zeros((1,1,3),dtype='uint8'),np.full((1,1,3),255,dtype='uint8'))
    assert mse==65025;assert p==0

def test_convolution_orientation():
    a=np.arange(25,dtype='uint8').reshape(5,5);a=np.repeat(a[:,:,None],3,2)
    k=np.array([[0,0,0],[0,0,1],[0,0,0]])
    b,_=convolve(a,k,border='zero')
    assert b[2,2,0]==a[2,1,0] # true convolution reads the left neighbor

def test_manual_reference():
    a=np.arange(75,dtype='uint8').reshape(5,5,3)
    k=np.array([[1.,2,3],[4,5,6],[7,8,9]])
    out,_=convolve(a,k,'sum',border='zero')
    pad=np.pad(a.astype(float),((1,1),(1,1),(0,0)))
    ref=np.zeros_like(a)
    for y in range(5):
        for x in range(5):
            ref[y,x]=np.clip(np.rint(np.sum(pad[y:y+3,x:x+3]*k[::-1,::-1,None]/45,axis=(0,1))),0,255)
    assert np.array_equal(out,ref)

def test_constant_normalized():
    a=np.full((7,7,3),80,dtype='uint8')
    out,_=convolve(a,np.ones((5,5)),'sum');assert np.array_equal(out,a)

def test_face_zero_one_two():
    root=Path(__file__).resolve().parents[1]
    for name,n in [('color.png',0),('face.png',1),('two_faces.png',2)]:
        rgb,_=load_image((root/'assets'/name).read_bytes())
        marked,faces=detect_faces(rgb)
        assert len(faces)==n;assert marked.shape==rgb.shape
        for f in faces:
            assert .8<=f['confidence']<=1
            assert 0<=f['x']<rgb.shape[1];assert f['x']+f['width']<=rgb.shape[1]

def test_face_downscale():
    root=Path(__file__).resolve().parents[1]
    rgb,_=load_image((root/'assets/face.png').read_bytes())
    rgb=cv2.resize(rgb,(1536,1536))
    _,faces=detect_faces(rgb)
    assert len(faces)==1
    assert faces[0]['x']>400
