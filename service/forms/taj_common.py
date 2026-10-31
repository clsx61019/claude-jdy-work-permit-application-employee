"""TAJ 申请表（NYT.53）和订购单（NYT.52）共用 —— 规则见 docs/rules/TAJ申请和GDPR声明.md"""
from datetime import date

from .employee_common import ordinal, require_hu_address
from .ict_common import require

GENDER = {"Male 男": "male", "Female 女": "female"}


def today():
    """落款日期 = 生成当天（B5：TAJ 是入境后才办）。测试里会换成固定日期"""
    return date.today()


def ymd(prefix, d):
    return {f"{prefix}_y": str(d.year), f"{prefix}_m": f"{d.month:02d}", f"{prefix}_d": f"{d.day:02d}"}


def street(p):
    """街道名称 + 类型；有楼号、单元也写在这里（表格里没有单独的格子）"""
    parts = [f"{p.hu_street} {p.hu_street_type}".strip()]
    if p.hu_building:
        parts.append(f"{ordinal(p.hu_building)} ép.")
    if p.hu_staircase:
        parts.append(f"{ordinal(p.hu_staircase)} lph.")
    return ", ".join(parts)


def floor_door(p):
    """「emelet, ajtó」一格：2., 3.；都没有写 -（A3）"""
    if not p.hu_floor and not p.hu_door:
        return "-"
    return f"{ordinal(p.hu_floor) if p.hu_floor else '-'}, {ordinal(p.hu_door) if p.hu_door else '-'}"


def person_values(p):
    return {
        "surname": p.surname,
        "given_name": p.given_name,
        "birth_surname": p.birth_surname,
        "birth_given_name": p.birth_given_name,
        "mother_surname": p.mother_surname,
        "mother_given_name": p.mother_given_name,
        "birth_place": p.birth_place_en,
        "birth_country_hu": p.birth_country_hu,
        **ymd("birth", p.birth_date),
        "nationality_hu": p.nationality_hu,
        "hu_zip": p.hu_zip,
        "hu_city": p.hu_city,
        "hu_street": street(p),
        "hu_house_no": ordinal(p.hu_house_no),
        "hu_floor_door": floor_door(p),
    }


def check_person(doc, p):
    require({"出生日期": p.birth_date, "出生地": p.birth_place_en, "出生国": p.birth_country,
             "母亲出生时姓名": p.mother_surname, "国籍": p.nationality_hu, **require_hu_address(p)})
    if p.gender not in GENDER:
        raise ValueError(f"性别「{p.gender}」无法勾选")
    doc.check("male", GENDER[p.gender] == "male")      # A4
    doc.check("female", GENDER[p.gender] == "female")
