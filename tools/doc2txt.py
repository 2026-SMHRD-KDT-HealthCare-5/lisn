"""
산출물 본문 추출 — PDF · PPTX -> docs/extracted/*.txt

hwp2txt.ps1 은 HWP 를 직접 파싱하지만 표 구조가 무너집니다.
한글에서 PDF 로 내보낸 뒤 이 스크립트를 쓰면 표를 표 형태로 뽑을 수 있어
버전 간 diff 비교와 문안 대조가 훨씬 정확합니다.

사용법:
    pip install pypdf pdfplumber
    python tools/doc2txt.py

출력:
    docs/extracted/<파일명>.txt

원본(documents/)에 PDF 와 PPTX 가 있어야 합니다. HWP 만 있고 PDF 가 없으면
해당 문서는 건너뜁니다. 그 경우 tools/hwp2txt.ps1 을 쓰세요.
"""

import glob
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "documents")
OUT = os.path.join(ROOT, "docs", "extracted")


def extract_pdf(path):
    import pdfplumber

    lines = []
    img_pages = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            lines.append(f"\n===== [page {i}] =====")
            lines.append(page.extract_text() or "")
            for tbl in page.extract_tables() or []:
                lines.append(f"--- table (page {i}) ---")
                for row in tbl:
                    cells = ["" if c is None else " ".join(c.split()) for c in row]
                    lines.append(" | ".join(cells))
            if page.images:
                img_pages.append((i, len(page.images)))
        total = len(pdf.pages)

    header = [
        f"# {os.path.basename(path)}",
        f"# pages={total}  images={sum(n for _, n in img_pages)}",
    ]
    if img_pages:
        header.append(
            "# 이미지 포함 페이지: "
            + ", ".join(f"p{p}({n})" for p, n in img_pages)
        )
    return "\n".join(header + lines), f"pages={total} images={sum(n for _, n in img_pages)}"


def extract_pptx(path):
    lines = [f"# {os.path.basename(path)}"]
    with zipfile.ZipFile(path) as z:
        slides = sorted(
            (n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
            key=lambda n: int(re.search(r"slide(\d+)", n).group(1)),
        )
        media = [n for n in z.namelist() if n.startswith("ppt/media/")]
        lines.append(f"# slides={len(slides)}  media={len(media)}")
        for n in slides:
            num = int(re.search(r"slide(\d+)", n).group(1))
            xml = z.read(n).decode("utf-8", "ignore")
            texts = re.findall(r"<a:t>(.*?)</a:t>", xml, re.S)
            body = re.sub(r"\s+", " ", " ".join(t.strip() for t in texts if t.strip()))
            lines.append(f"\n===== [slide {num}] =====")
            lines.append(body)
    return "\n".join(lines), f"slides={len(slides)} media={len(media)}"


def main():
    if not os.path.isdir(SRC):
        sys.exit(f"원본 폴더가 없습니다: {SRC}")
    os.makedirs(OUT, exist_ok=True)

    targets = sorted(glob.glob(os.path.join(SRC, "*.pdf"))) + sorted(
        glob.glob(os.path.join(SRC, "*.pptx"))
    )
    if not targets:
        sys.exit("documents/ 에 PDF·PPTX 가 없습니다.")

    for path in targets:
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            text, info = (
                extract_pdf(path) if path.lower().endswith(".pdf") else extract_pptx(path)
            )
        except Exception as e:
            print(f"[실패] {name}  {e}")
            continue
        with open(os.path.join(OUT, name + ".txt"), "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[완료] {name}  {info}")


if __name__ == "__main__":
    main()
