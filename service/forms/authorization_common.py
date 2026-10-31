"""三份授权书（IMO / NAV / TAJ）共用的数据 —— 规则见 docs/rules/授权书.md

被授权人和证人三份都取简道云「选择被授权人」「选择见证人1/2」联动出来的字段（B1）。
NAV、TAJ 还要被授权人的出生地、住址、税号、证件号，简道云辅助表还没有这几列（待办 J15）。
"""
from .ict_common import require
from .preliminary import en_long, hu_long


def full_name(p):
    return f"{p.surname} {p.given_name}"


def mother_name(p):
    return f"{p.mother_surname} {p.mother_given_name}".strip()


def hu_article(word):
    """匈语定冠词：元音开头用 az"""
    return "az" if word[:1].upper() in "AÁEÉIÍOÓÖŐUÚÜŰ" else "a"


def official_date(d):
    """官方表格写法：2026. év 10. hó 25. nap"""
    return f"{d.year}. év {d.month:02d}. hó {d.day:02d}. nap" if d else ""


def common_values(p):
    return {
        "name": full_name(p),
        "mother_name": mother_name(p),
        "auth_name": p.auth_name,
        "auth_mother": p.auth_mother,
        "sign_date_en": en_long(p.sign_date),
        "sign_date_hu": hu_long(p.sign_date),
    }


def require_common(p, extra=None):
    fields = {"出生日期": p.birth_date, "母亲出生时姓名": p.mother_surname, "签字日期": p.sign_date,
              "被授权人姓名": p.auth_name, "被授权人母亲姓名": p.auth_mother, "被授权人出生日期": p.auth_birth_date,
              "见证人1姓名": p.w1_name, "见证人1地址": p.w1_address,
              "见证人2姓名": p.w2_name, "见证人2地址": p.w2_address}
    fields.update(extra or {})
    require(fields)
