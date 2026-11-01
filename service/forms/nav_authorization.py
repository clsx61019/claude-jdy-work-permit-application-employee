"""NAV Authorization（税务局授权书：上一年收入证明）—— 规则见 docs/rules/授权书.md

模板 templates/hu/nav_authorization.docx 由 tools/build_authorizations.py 转换而来，
改自 NAV「Természetes személy, egyéni vállalkozó részére eseti meghatalmazásminta」（推荐样本，不强制）。
"""
from ..docx_text import TextDoc
from .authorization_common import common_values, require_common
from .preliminary import hu_long

DOC = TextDoc
TEMPLATE = "../hu/nav_authorization.docx"


def fill(doc, p):
    # B4：上一年收入证明只在变更、延期时需要（新申请的人在匈牙利还没有收入）
    if p.app_type not in ("change", "extension"):
        raise ValueError("NAV 授权书（上一年收入证明）只用于变更、延期")
    require_common(p, {"税号": p.tax_no, "出生地": p.birth_place_en,
                       "被授权人税号（辅助表「被授权人」里填）": p.auth_tax_no,
                       "被授权人出生地（辅助表「被授权人」里填）": p.auth_birth_place,
                       "被授权人住址（辅助表「被授权人」里填）": p.auth_address,
                       "见证人1母亲姓名": p.w1_mother, "见证人2母亲姓名": p.w2_mother})
    doc.fill({
        **common_values(p),
        "tax_no": p.tax_no,
        "birth_place": p.birth_place_en,
        "birth_country_hu": p.birth_country_hu,   # A5
        "birth_date_hu": hu_long(p.birth_date),
        "auth_tax_no": p.auth_tax_no,
        "auth_birth_place": p.auth_birth_place,
        "auth_birth_date_hu": hu_long(p.auth_birth_date),
        "auth_address": p.auth_address,
        "w1_name": p.w1_name, "w1_address": p.w1_address, "w1_mother": p.w1_mother,
        "w2_name": p.w2_name, "w2_address": p.w2_address, "w2_mother": p.w2_mother,
    })
