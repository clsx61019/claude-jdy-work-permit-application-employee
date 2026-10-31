"""Kérelem / Request：请移民局沿用以前交过的材料（员工签）—— 规则见 docs/rules/住宿证明雇主通知员工声明.md"""
from ..docx_text import TextDoc
from .employee_common import personal_required, personal_values
from .ict_common import require

DOC = TextDoc
TEMPLATE = "../hu/request_previous_documents.docx"


def fill(doc, p):
    if p.app_type != "extension":  # B7
        raise ValueError("沿用材料请求只用于延期")
    require(personal_required(p))
    doc.fill(personal_values(p))
