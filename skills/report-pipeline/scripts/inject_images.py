#!/usr/bin/env python3
"""hwpx 이미지 주입 — [캡처 N 삽입] 마커 문단을 인라인 그림(hp:pic)으로 치환.

구조 근거: reports/260720_ict-portal_PIMS어드바이저/04_final.hwpx 실측
- BinData/imageN.PNG 파일 추가
- Contents/content.hpf 에 <opf:item ... isEmbeded="1"/> 등록
- section0.xml 의 <hp:t>마커</hp:t> 를 <hp:pic>...</hp:pic> 로 치환 (treatAsChar=1 인라인)

단위: HWPUNIT = 1/7200 inch. orgSz 는 px*100 (HWP 72dpi 관례).
"""
import json, os, re, shutil, struct, sys, zipfile

HWPUNIT_PER_MM = 7200.0 / 25.4


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(33)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    w, h = struct.unpack(">II", head[16:24])
    return w, h


def make_pic(item_id, px_w, px_h, target_mm_w, seq, name):
    org_w, org_h = px_w * 100, px_h * 100
    cur_w = int(round(target_mm_w * HWPUNIT_PER_MM))
    cur_h = int(round(cur_w * px_h / px_w))
    sx, sy = cur_w / org_w, cur_h / org_h
    pid = 1000000 + seq * 37
    iid = 2000000 + seq * 41
    return (
        f'<hp:pic id="{pid}" zOrder="{seq}" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM"'
        f' textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0"'
        f' instid="{iid}" reverse="0">'
        f'<hp:offset x="0" y="0"/>'
        f'<hp:orgSz width="{org_w}" height="{org_h}"/>'
        f'<hp:curSz width="{cur_w}" height="{cur_h}"/>'
        f'<hp:flip horizontal="0" vertical="0"/>'
        f'<hp:rotationInfo angle="0" centerX="{cur_w // 2}" centerY="{cur_h // 2}" rotateimage="1"/>'
        f'<hp:renderingInfo>'
        f'<hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        f'<hc:scaMatrix e1="{sx:.6f}" e2="0" e3="0" e4="0" e5="{sy:.6f}" e6="0"/>'
        f'<hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>'
        f'</hp:renderingInfo>'
        f'<hc:img binaryItemIDRef="{item_id}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>'
        f'<hp:imgRect><hc:pt0 x="0" y="0"/><hc:pt1 x="{org_w}" y="0"/>'
        f'<hc:pt2 x="{org_w}" y="{org_h}"/><hc:pt3 x="0" y="{org_h}"/></hp:imgRect>'
        f'<hp:imgClip left="0" right="{org_w}" top="0" bottom="{org_h}"/>'
        f'<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        f'<hp:imgDim dimwidth="{org_w}" dimheight="{org_h}"/>'
        f'<hp:effects/>'
        f'<hp:sz width="{cur_w}" widthRelTo="ABSOLUTE" height="{cur_h}" heightRelTo="ABSOLUTE" protect="0"/>'
        f'<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0"'
        f' holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP"'
        f' horzAlign="CENTER" vertOffset="0" horzOffset="0"/>'
        f'<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        f'<hp:shapeComment>그림입니다.\n원본 그림의 이름: {name}\n'
        f'원본 그림의 크기: 가로 {px_w}pixel, 세로 {px_h}pixel</hp:shapeComment>'
        f'</hp:pic>'
    )


def inject(hwpx, specs, workdir):
    """specs: [(marker_text, png_path, target_mm_width), ...]"""
    ext = os.path.join(workdir, "_hwpx")
    shutil.rmtree(ext, ignore_errors=True)
    with zipfile.ZipFile(hwpx) as z:
        names = z.namelist()
        z.extractall(ext)
    for root, dirs, files in os.walk(ext):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)
        for f in files:
            os.chmod(os.path.join(root, f), 0o644)

    sec = os.path.join(ext, "Contents/section0.xml")
    hpf = os.path.join(ext, "Contents/content.hpf")
    s = open(sec, encoding="utf-8").read()
    h = open(hpf, encoding="utf-8").read()
    os.makedirs(os.path.join(ext, "BinData"), exist_ok=True)

    # hc: 네임스페이스 미선언 시 루트에 추가 (kordoc 산출물은 hp:/hs:만 선언)
    if 'xmlns:hc=' not in s:
        s = s.replace(
            '<hs:sec ',
            '<hs:sec xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" ', 1)
        report_ns = True
    else:
        report_ns = False

    items, report = [], []
    if report_ns:
        report.append('NS  xmlns:hc 추가')
    for i, (marker, png, mm_w) in enumerate(specs, start=1):
        if marker not in s:
            report.append(f"MISS {marker}")
            continue
        item_id = f"image{i}"
        shutil.copy(png, os.path.join(ext, "BinData", f"{item_id}.png"))
        pw, ph = png_size(png)
        pic = make_pic(item_id, pw, ph, mm_w, i, os.path.basename(png))
        # <hp:t>마커</hp:t> 전체를 그림으로 치환
        pat = re.compile(r"<hp:t>" + re.escape(marker) + r"</hp:t>")
        s, n = pat.subn(pic, s, count=1)
        if n == 0:
            pat2 = re.compile(r"<hp:t>[^<]*" + re.escape(marker) + r"[^<]*</hp:t>")
            s, n = pat2.subn(pic, s, count=1)
        items.append(f'<opf:item id="{item_id}" href="BinData/{item_id}.png" media-type="image/png" isEmbeded="1"/>')
        report.append(f"OK  {marker} -> {item_id} ({pw}x{ph}px, {mm_w}mm)")

    if items:
        h = h.replace("</opf:manifest>", "".join(items) + "</opf:manifest>", 1)

    open(sec, "w", encoding="utf-8").write(s)
    open(hpf, "w", encoding="utf-8").write(h)

    # 재패킹: mimetype 무압축 선행 → 나머지 deflate (원본 엔트리 순서 유지)
    out = hwpx
    tmp = hwpx + ".tmp"
    with zipfile.ZipFile(tmp, "w") as z:
        if "mimetype" in names:
            z.write(os.path.join(ext, "mimetype"), "mimetype", zipfile.ZIP_STORED)
        for n in names:
            if n == "mimetype" or n.endswith("/"):
                continue
            z.write(os.path.join(ext, n), n, zipfile.ZIP_DEFLATED)
        for item_id in [it.split('"')[1] for it in items]:
            z.write(os.path.join(ext, "BinData", f"{item_id}.png"),
                    f"BinData/{item_id}.png", zipfile.ZIP_DEFLATED)
    os.replace(tmp, out)
    shutil.rmtree(ext, ignore_errors=True)
    return report


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(
        description="hwpx 이미지 주입 — [마커] 문단/셀을 인라인 그림으로 치환")
    ap.add_argument("hwpx", help="대상 hwpx (제자리 수정)")
    ap.add_argument("-i", "--image", action="append", required=True,
                    metavar="MARKER::PNG::MM",
                    help="마커::PNG경로::표시폭mm (반복 지정)")
    ap.add_argument("--workdir", default="/tmp", help="임시 전개 디렉토리")
    a = ap.parse_args()
    specs = []
    for spec in a.image:
        marker, png, mm = spec.split("::")
        specs.append((marker, png, float(mm)))
    lines = inject(a.hwpx, specs, a.workdir)
    print(json.dumps({"results": lines}, ensure_ascii=False, indent=1))
    sys.exit(1 if any(l.startswith("MISS") for l in lines) else 0)
