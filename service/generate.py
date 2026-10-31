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
import tempfile
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
    return to_pdf_many([docx_path])[0]


def to_pdf_many(docx_paths):
    """一次启动 LibreOffice 转多个文件（每次启动要几秒）。配置目录放 /tmp，云函数里只有 /tmp 可写。"""
    paths = [Path(x) for x in docx_paths]
    if not paths:
        return []
    profile = Path(tempfile.gettempdir()) / "lo-profile"
    subprocess.run(["soffice", f"-env:UserInstallation=file://{profile}", "--headless",
                    "--convert-to", "pdf", "--outdir", str(paths[0].parent), *map(str, paths)],
                   check=True, capture_output=True, timeout=600)
    return [x.with_suffix(".pdf") for x in paths]


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
