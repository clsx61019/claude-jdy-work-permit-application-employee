"""Nyilatkozat / Declaration：匈牙利住址没变（员工签，延期用）—— 规则见 docs/rules/住宿证明雇主通知员工声明.md

简道云没有「住址是否变更」字段，住址变了的话由操作人员决定不打印这一份。
"""
from ..docx_text import TextDoc
from .employee_common import hu_address, personal_required, personal_values, require_hu_address, with_article
from .ict_common import require

DOC = TextDoc
TEMPLATE = "../hu/declaration_address_unchanged.docx"


def fill(doc, p):
    if p.app_type != "extension":  # B7
        raise ValueError("住址未变声明只用于延期")
    require({**personal_required(p), **require_hu_address(p)})
    doc.fill({
        **personal_values(p),
        "hu_address": hu_address(p),
        "hu_address_with_article": with_article(hu_address(p)),
    })
