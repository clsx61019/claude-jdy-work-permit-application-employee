"""Kérelem / Request：通信发公司邮箱、居留卡寄到公司（员工签）—— 规则见 docs/rules/住宿证明雇主通知员工声明.md

邮箱、地址、收件人取 config/company.json（和 9 号申请表同一来源）。
"""
from ..docx_text import TextDoc
from ..model import COMPANY
from .employee_common import personal_required, personal_values, with_article
from .ict_common import require

DOC = TextDoc
TEMPLATE = "../hu/request_delivery_address.docx"


def fill(doc, p):
    require(personal_required(p))  # B7：所有申请都可以用
    doc.fill({
        **personal_values(p),
        "contact_email": COMPANY["contact_email"],
        "contact_email_with_article": with_article(COMPANY["contact_email"]),
        "delivery_address": COMPANY["delivery_address"],
        "delivery_address_with_article": with_article(COMPANY["delivery_address"]),
        "contact_name_hu": COMPANY["contact_name_hu"],
        "contact_name_en": COMPANY["contact_name_en"],
    })
