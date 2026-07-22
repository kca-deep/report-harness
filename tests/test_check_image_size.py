import sys, pathlib, struct, zlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts"))
from check_image_size import png_size, judge

def minimal_png(w, h):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    chunk = struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    return sig + chunk

def test_png_size_parsed():
    assert png_size(minimal_png(640, 480)) == (640, 480)

def test_judge_fits():
    r = judge(640, 300, dpi=96, max_w=170, max_h=90)   # 640px@96dpi ≈ 169mm
    assert r["fits"] is True

def test_judge_exceeds_height():
    r = judge(640, 640, dpi=96, max_w=170, max_h=90)   # 높이 ≈ 169mm > 90mm
    assert r["fits"] is False and 0 < r["scale_to_fit"] < 1
