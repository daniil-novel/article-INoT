"""Create an editorial highlight copy of the frozen July PDF; never change its text."""

from __future__ import annotations

import argparse
import hashlib
import json
from importlib.metadata import version
from pathlib import Path

import pymupdf as fitz


SOURCE_SHA256 = "53b59452e63c89a65d1004bea295e78d899e1f83bb9545ada37e81e2b5d9d904"
SOURCE_COMMIT = "173a16c30488208db26acd51c20e2243430e54e0"
CANDIDATES = [
    {
        "id": "C1",
        "page": 2,
        "section": "1 Introduction, first paragraph",
        "priority": 2,
        "start": "A modern software-engineering agent",
        "end": "forced to reread the same long context.",
        "protected": ["This paper focuses precisely on that setting:"],
        "source_lines": [48, 48],
        "comment_ru": "Предложение при превышении лимита страниц: сжать вводный абзац, который частично повторяет §1.1. Сохранить инженерный контекст, репозиторий и внешние проверки. Сейчас текст не изменён.",
    },
    {
        "id": "C2",
        "page": 3,
        "section": "2.1, generic definition sentence only",
        "priority": 1,
        "start": "In this context,",
        "end": "final success of solving the target task.",
        "protected": [
            "improve solution quality on tasks that require several connected logical transitions.",
            "The Self-Refine approach",
        ],
        "source_lines": [84, 84],
        "comment_ru": "Предложение при превышении лимита: убрать общее определение промежуточных шагов и качества. Сохранить утверждение Wei et al. и его ссылку, а также дальнейшие сравнения и оговорку о достоверности рассуждений. Текст не изменён.",
    },
    {
        "id": "C3",
        "page": 10,
        "section": "5.4, first two explanatory sentences after inequality (2)",
        "priority": 1,
        "start": "The left-hand side of the inequality",
        "end": "a cheap preliminary check and a rerun of the large model.",
        "protected": ["Pilot measurements of"],
        "source_lines": [322, 322],
        "comment_ru": "Предложение при превышении лимита: сократить пересказ неравенства (2). Сохранить само условие, определения его величин и предложение с измерениями E4. Текст не изменён.",
    },
    {
        "id": "C4",
        "page": 11,
        "section": "6.2, first three rationale sentences; baseline sentence excluded",
        "priority": 3,
        "start": "The rationale for this construction is as follows.",
        "end": "of this effect.",
        "protected": ["The baseline uses"],
        "source_lines": [341, 341],
        "comment_ru": "Предложение при превышении лимита: сжать объяснение метрики до одной фразы, сохранив смысл Success, Verified и maintainability. Сохранить формулу, λ=0.5, семь инверсий и вторичный статус метрики. Текст не изменён.",
    },
    {
        "id": "C5",
        "page": 17,
        "section": "10, all seven future-work bullets; introduction and conclusion excluded",
        "priority": 1,
        "start": "1. run all 164 HumanEval tasks",
        "end": "storage, under a production context-length distribution.",
        "protected": ["The next study should remove", "11 Conclusion"],
        "source_lines": [544, 550],
        "comment_ru": "Предложение при превышении лимита: объединить семь пунктов в компактный абзац, сохранив все запланированные работы и численные условия. Ничего из списка не исключать. Текст не изменён.",
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordered_search(page: fitz.Page, text: str) -> list[fitz.Rect]:
    hits = page.search_for(text)
    if not hits:
        raise ValueError(f"Page {page.number + 1}: anchor not found: {text!r}")
    return sorted(hits, key=lambda r: (round(r.y0, 1), r.x0))


def selected_lines(page: fitz.Page, candidate: dict) -> tuple[list[fitz.Rect], str]:
    """Select only the range between exact textual anchors, including partial lines."""
    start = ordered_search(page, candidate["start"])[0]
    end = ordered_search(page, candidate["end"])[-1]
    if end.y1 < start.y0:
        raise ValueError(f"Reversed anchors for {candidate['id']}")
    boxes: list[fitz.Rect] = []
    selected_text: list[str] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            box = fitz.Rect(line["bbox"])
            if box.y1 < start.y0 - 0.5 or box.y0 > end.y1 + 0.5:
                continue
            if abs(box.y0 - start.y0) < 3:
                box.x0 = max(box.x0, start.x0)
            if abs(box.y1 - end.y1) < 3:
                box.x1 = min(box.x1, end.x1)
            if box.is_empty:
                continue
            boxes.append(box)
            selected_text.append(page.get_textbox(box))
    boxes.sort(key=lambda r: (round(r.y0, 1), r.x0))
    if not boxes:
        raise ValueError(f"No highlight geometry for {candidate['id']}")
    for protected in candidate["protected"]:
        for hit in ordered_search(page, protected):
            for box in boxes:
                intersection = hit & box
                if intersection.width > 0.5 and intersection.height > 0.5:
                    raise ValueError(f"{candidate['id']} overlaps protected text: {protected}")
    return boxes, "\n".join(selected_text)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repository = script_dir.parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=repository / "output/pdf/archive-2026-07-28/Hybrid-INoT-July-2026-en.pdf")
    parser.add_argument("--output", type=Path, default=script_dir / "Hybrid-INoT-July-2026-yellow-review.pdf")
    parser.add_argument("--manifest", type=Path, default=script_dir / "yellow-review-candidates.json")
    parser.add_argument("--render-dir", type=Path, default=script_dir / "rendered")
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    if source == output:
        raise ValueError("The original PDF may never be the output.")
    original_hash = sha256(source)
    if original_hash != SOURCE_SHA256:
        raise ValueError("Source differs from the selected frozen July PDF.")
    output.parent.mkdir(parents=True, exist_ok=True)
    document = fitz.open(source)
    original_text = [page.get_text(sort=False) for page in document]
    original_page_rects = [tuple(page.rect) for page in document]
    records = []
    for candidate in CANDIDATES:
        page = document[candidate["page"] - 1]
        boxes, selected_text = selected_lines(page, candidate)
        annotation = page.add_highlight_annot([fitz.Quad(box.tl, box.tr, box.bl, box.br) for box in boxes])
        annotation.set_colors(stroke=(1, 1, 0))
        annotation.set_opacity(0.35)
        annotation.set_info(
            title="Редакторское предложение",
            subject=f"{candidate['id']}: возможное сжатие, не применено",
            content=candidate["comment_ru"],
        )
        annotation.update()
        records.append({
            **candidate,
            "annotation_xref": annotation.xref,
            "line_quad_count": len(boxes),
            "highlight_rectangles": [list(box) for box in boxes],
            "highlighted_text_extracted": selected_text,
            "actual_text_change": False,
        })
    document.save(output, garbage=0, deflate=False)
    document.close()
    marked = fitz.open(output)
    marked_text = [page.get_text(sort=False) for page in marked]
    marked_page_rects = [tuple(page.rect) for page in marked]
    highlights = [
        (index + 1, annotation)
        for index, page in enumerate(marked)
        for annotation in (page.annots() or [])
        if annotation.type[0] == fitz.PDF_ANNOT_HIGHLIGHT
    ]
    if len(marked) != 20 or original_text != marked_text or original_page_rects != marked_page_rects:
        raise ValueError("Annotated PDF failed page/text/geometry parity.")
    if len(highlights) != len(CANDIDATES) or sha256(source) != original_hash:
        raise ValueError("Annotation count or original-file preservation failed.")
    args.render_dir.mkdir(parents=True, exist_ok=True)
    render_files = []
    for candidate in CANDIDATES:
        page = marked[candidate["page"] - 1]
        target = args.render_dir / f"page-{candidate['page']:02d}-yellow.png"
        page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False, annots=True).save(target)
        render_files.append(str(target))
    manifest = {
        "purpose": "Five optional compression proposals only; scientific text is unchanged.",
        "source_commit": SOURCE_COMMIT,
        "source_pdf": str(source),
        "source_sha256_before": original_hash,
        "source_sha256_after": sha256(source),
        "original_unchanged": True,
        "annotated_pdf": str(output),
        "annotated_pdf_sha256": sha256(output),
        "page_count_before": len(original_text),
        "page_count_after": len(marked),
        "all_page_text_exactly_equal": original_text == marked_text,
        "all_page_rectangles_exactly_equal": original_page_rects == marked_page_rects,
        "highlight_annotation_count": len(highlights),
        "highlighted_pages": [candidate["page"] for candidate in CANDIDATES],
        "pymupdf_version": version("PyMuPDF"),
        "candidates": records,
        "rendered_pages": render_files,
        "policy": "All scientific text stays in one main PDF. No compression is applied without actual overflow and separate user approval.",
    }
    args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    marked.close()
    print(json.dumps({key: manifest[key] for key in ["original_unchanged", "page_count_after", "all_page_text_exactly_equal", "highlight_annotation_count", "highlighted_pages"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
