"""TAJ Authorization（TAJ 卡授权书）—— 规则见 docs/rules/授权书.md

模板 templates/hu/taj_authorization.docx 由 tools/build_authorizations.py 转换而来，改自 NEAK NYT.159 表格。
"""
from ..docx_text import TextDoc
from .authorization_common import common_values, official_date, require_common

DOC = TextDoc
TEMPLATE = "../hu/taj_authorization.docx"


def ordinal(v):
    """匈语序数写法：数字结尾加句点（21 -> 21.，9-11. 不变，A 不变）"""
    v = str(v).strip()
    return v + "." if v[-1:].isdigit() else v


def street(p):
    """A1：街道 + 门牌号 + 楼号、单元、楼层、室：Ipari út 9-11. hsz, A ép., 2. lph., 3. em., 4. ajtó"""
    parts = [f"{p.hu_street} {p.hu_street_type} {ordinal(p.hu_house_no)} hsz".replace("  ", " ")]
    for value, label in ((p.hu_building, "ép."), (p.hu_staircase, "lph."), (p.hu_floor, "em."), (p.hu_door, "ajtó")):
        if value:
            parts.append(f"{ordinal(value)} {label}")
    return ", ".join(parts)


def fill(doc, p):
    require_common(p, {"出生地": p.birth_place_en, "护照号": p.passport_no,
                       "邮编（匈牙利）": p.hu_zip, "城市（匈牙利）": p.hu_city, "街道名称": p.hu_street,
                       "门牌号": p.hu_house_no,
                       "被授权人出生地（简道云待办 J15）": p.auth_birth_place,
                       "被授权人住址（简道云待办 J15）": p.auth_address,
                       "被授权人证件号（简道云待办 J15）": p.auth_id_no})
    doc.fill({
        **common_values(p),
        "birth_place": p.birth_place_en,
        "birth_country_hu": p.birth_country_hu,
        "birth_date": official_date(p.birth_date),
        "hu_zip": p.hu_zip,
        "hu_city": p.hu_city,
        "hu_street": street(p),
        "passport_no": p.passport_no,                 # A2
        "sign_date": official_date(p.sign_date),      # A3
        "auth_birth_place": p.auth_birth_place,
        "auth_birth_date": official_date(p.auth_birth_date),
        "auth_address": p.auth_address,
        "auth_id_no": p.auth_id_no,
        "w1_name": p.w1_name, "w1_address": p.w1_address,
        "w2_name": p.w2_name, "w2_address": p.w2_address,
    })
