"""Authorization for IMO（移民局授权书，匈英双语）—— 规则见 docs/rules/授权书.md

模板 templates/hu/imo_authorization.docx 由 tools/build_authorizations.py 转换而来。
"""
from ..docx_text import TextDoc
from .authorization_common import common_values, hu_article, require_common
from .employee_common import place
from .preliminary import en_long, hu_long

DOC = TextDoc
TEMPLATE = "../hu/imo_authorization.docx"


def fill(doc, p):
    require_common(p, {"被授权人岗位": p.auth_position, "被授权人公司": p.auth_company,
                       "见证人1证件号": p.w1_id, "见证人2证件号": p.w2_id})
    place_en, place_hu = place(p)  # B2：签字地点按「递交地点」
    doc.fill({
        **common_values(p),
        "birth_date_en": en_long(p.birth_date),
        "birth_date_hu": hu_long(p.birth_date),
        "auth_birth_date_en": en_long(p.auth_birth_date),   # A8
        "auth_birth_date_hu": hu_long(p.auth_birth_date),
        "auth_position": p.auth_position,
        "auth_company": p.auth_company,
        "auth_company_hu": f"{hu_article(p.auth_company)} {p.auth_company}",
        "place_en": place_en,
        "place_hu": place_hu,
        "w1_name": p.w1_name, "w1_id": p.w1_id, "w1_address": p.w1_address,
        "w2_name": p.w2_name, "w2_id": p.w2_id, "w2_address": p.w2_address,
    })
