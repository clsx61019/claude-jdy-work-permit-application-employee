"""Szállásigazolás / Confirmation Letter（住宿证明，Polimer 经营的住处出具）—— 规则见 docs/rules/住宿证明雇主通知员工声明.md"""
from ..docx_text import TextDoc
from ..model import ACCOMMODATION
from .authorization_common import full_name
from .employee_common import his_her, hu_address, require_hu_address, with_article
from .ict_common import require
from .preliminary import en_long, hu_long

DOC = TextDoc
TEMPLATE = "../hu/accommodation_certificate.docx"
POLIMER = "Polimer Szolgáltató Kft."


def fill(doc, p):
    # B2：模板是 Polimer 的信头，只给 Polimer 经营的住处用
    operator = ACCOMMODATION.get(p.accommodation, {}).get("operator", "")
    if operator != POLIMER:
        raise ValueError(f"住宿证明是 {POLIMER} 的信头，只用于它经营的住处；现在的住处是「{p.accommodation}」")
    require({"出生日期": p.birth_date, "国籍": p.nationality, "签字日期": p.sign_date, **require_hu_address(p)})
    doc.fill({
        "name": full_name(p),
        "birth_date_hu": hu_long(p.birth_date),
        "birth_date_en": en_long(p.birth_date),
        "nationality_hu": p.nationality_hu,
        "nationality_en": p.nationality,
        "hotel": p.accommodation,
        "hotel_with_article": with_article(p.accommodation),
        "hu_address": hu_address(p),
        "his_her": his_her(p),
        "sign_date_hu": hu_long(p.sign_date),
        "sign_date_en": en_long(p.sign_date),
    })
