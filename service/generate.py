"""
生成文件：读取一条简道云记录（API 返回格式），填写官方表单，输出 Word，可选转 PDF。

用法: python -m service.generate <表单> <记录.json> <输出.docx> [--no-pdf]
默认同时输出 Word 和 PDF。
例如: python -m service.generate form09 tests/samples/ict.json out/ict.docx
"""
import importlib
import json
import subprocess
import sys
from pathlib import Path

from . import model
from .docx_form import FormDoc

ROOT = Path(__file__).resolve().parent.parent
OFFICIAL = ROOT / "templates" / "official"


def render(form_name, record):
    form = importlib.import_module(f"service.forms.{form_name}")
    doc = getattr(form, "DOC", FormDoc)(OFFICIAL / form.TEMPLATE)  # 普通 Word 模板用 TextDoc
    form.fill(doc, model.build(record))
    return doc


def to_pdf(docx_path):
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir",
                    str(Path(docx_path).parent), str(docx_path)],
                   check=True, capture_output=True, timeout=180)
    return Path(docx_path).with_suffix(".pdf")


def main(argv):
    form_name, record_path, out = argv[:3]
    record = json.loads(Path(record_path).read_text(encoding="utf-8"))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    render(form_name, record).save(out)
    print("已生成", out)
    if "--no-pdf" not in argv:
        print("已生成", to_pdf(out))


if __name__ == "__main__":
    main(sys.argv[1:])
