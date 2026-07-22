"""근거 이미지 1/3페이지 규격 판정 (spec §7-1: 170×90mm). stdlib-only — PNG IHDR/JPEG SOF 직접 파싱."""
import sys, json, struct, argparse

MM_PER_INCH = 25.4

def png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not png")
    if len(data) < 24:
        raise ValueError("truncated png")
    w, h = struct.unpack(">II", data[16:24])
    return w, h

def jpeg_size(data):
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1; continue
        marker = data[i + 1]
        # Skip consecutive 0xFF padding bytes
        while i + 1 < len(data) and data[i + 1] == 0xFF:
            i += 1
        if i + 1 < len(data):
            marker = data[i + 1]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    raise ValueError("no SOF")

def judge(w_px, h_px, dpi=96, max_w=170.0, max_h=90.0):
    w_mm, h_mm = w_px / dpi * MM_PER_INCH, h_px / dpi * MM_PER_INCH
    fits = w_mm <= max_w and h_mm <= max_h
    scale = min(max_w / w_mm, max_h / h_mm) if not fits else 1.0
    return {"w_mm": round(w_mm, 1), "h_mm": round(h_mm, 1), "fits": fits,
            "scale_to_fit": round(scale, 3)}

if __name__ == "__main__":
    try:
        ap = argparse.ArgumentParser()
        ap.add_argument("img"); ap.add_argument("--max-w-mm", type=float, default=170)
        ap.add_argument("--max-h-mm", type=float, default=90); ap.add_argument("--dpi", type=float, default=96)
        a = ap.parse_args()
        data = open(a.img, "rb").read()

        # Validate signature
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            w, h = png_size(data)
        elif data.startswith(b"\xff\xd8"):
            w, h = jpeg_size(data)
        else:
            raise ValueError("unsupported format")

        r = judge(w, h, a.dpi, a.max_w_mm, a.max_h_mm)
        print(json.dumps(r))
        sys.exit(0 if r["fits"] else 1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(2)
