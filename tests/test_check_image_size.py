import sys, pathlib, struct, zlib, subprocess, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts"))
from check_image_size import png_size, judge
import pytest

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

def minimal_jpeg(w, h):
    sof = struct.pack(">BBHBHHB", 0xFF, 0xC0, 11, 8, h, w, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + sof + b"\xff\xd9"

def test_jpeg_size_parsed():
    from check_image_size import jpeg_size
    assert jpeg_size(minimal_jpeg(800, 600)) == (800, 600)

def test_non_image_rejected_cli(tmp_path):
    SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts/check_image_size.py"
    p = tmp_path / "fake.bin"
    p.write_bytes(b"\x00\x01" + bytes(100))
    r = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)
    assert r.returncode == 2
    assert "error" in json.loads(r.stdout)

def test_missing_file_cli():
    SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "skills/report-pipeline/scripts/check_image_size.py"
    r = subprocess.run([sys.executable, str(SCRIPT), "/nonexistent/x.png"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "error" in json.loads(r.stdout)

def test_truncated_png_raises_valueerror():
    with pytest.raises(ValueError):
        png_size(b"\x89PNG\r\n\x1a\n" + b"\x00" * 4)
