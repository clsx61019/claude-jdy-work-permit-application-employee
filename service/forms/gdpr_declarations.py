"""GDPR 告知确认 + 数据处理同意书（英语）—— 规则见 docs/rules/TAJ申请和GDPR声明.md

模板 templates/hu/gdpr_declarations.docx 由 tools/build_taj_gdpr.py 转换而来。
同意书里的 √ 是模板里预先打好的（2026-10-31 确认保留）。
"""
from ..docx_text import TextDoc
from .authorization_common import full_name
from .employee_common import place
from .ict_common import require
from .labour_contract import address
from .preliminary import en_long

DOC = TextDoc
TEMPLATE = "../hu/gdpr_declarations.docx"


def fill(doc, p):
    require({"出生日期": p.birth_date, "签字日期": p.sign_date, "详细地址": p.home_address})
    place_en, _ = place(p)
    doc.fill({
        "name": full_name(p),
        "home_address": address(p, p.home_country),   # A6
        "birth_date": en_long(p.birth_date),
        "place": place_en,                            # 和员工签的其他声明一样按递交地点
        "sign_date": en_long(p.sign_date),            # B5
    })
