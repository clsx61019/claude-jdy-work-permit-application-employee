"""员工个人信息的通用写法：匈牙利地址、签字地点、性别代词等（多份模板共用）"""
from ..model import COMPANY
from .authorization_common import full_name, hu_article
from .preliminary import en_long, hu_long

# 签字地点按「递交地点」（IMO 授权书 B2、员工声明 B9）
PLACES = {"China 中国": ("Beijing", "Peking"), "Hungary 匈牙利": ("Kazincbarcika", "Kazincbarcika")}
HIS_HER = {"Male 男": "his", "Female 女": "her"}


def ordinal(v):
    """匈语序数写法：数字结尾加句点（21 -> 21.，9-11. 不变，A 不变）"""
    v = str(v).strip()
    return v + "." if v[-1:].isdigit() else v


def street(p, hsz=" hsz"):
    """街道 + 门牌号 + 楼号、单元、楼层、室：Ipari út 9-11. hsz, A ép., 2. lph., 3. em., 4. ajtó"""
    parts = [f"{p.hu_street} {p.hu_street_type} {ordinal(p.hu_house_no)}{hsz}".replace("  ", " ")]
    for value, label in ((p.hu_building, "ép."), (p.hu_staircase, "lph."), (p.hu_floor, "em."), (p.hu_door, "ajtó")):
        if value:
            parts.append(f"{ordinal(value)} {label}")
    return ", ".join(parts)


def hu_address(p):
    """3704 Berente, Ipari út 9-11., 2. em., 3. ajtó"""
    return f"{p.hu_zip} {p.hu_city}, {street(p, hsz='')}"


def with_article(text):
    return f"{hu_article(text)} {text}"


def require_hu_address(p):
    return {"邮编（匈牙利）": p.hu_zip, "城市（匈牙利）": p.hu_city, "街道名称": p.hu_street, "门牌号": p.hu_house_no}


def place(p):
    if p.submit_place not in PLACES:
        raise ValueError(f"递交地点「{p.submit_place}」没有对应的签字地点")
    return PLACES[p.submit_place]


def his_her(p):
    if p.gender not in HIS_HER:
        raise ValueError(f"性别「{p.gender}」无法确定 his / her")
    return HIS_HER[p.gender]


def personal_values(p):
    """员工签的几份声明共用：姓名、出生地（按出生国）、出生日期、签字地点和日期"""
    place_en, place_hu = place(p)
    return {
        "name": full_name(p),
        "birth_place": p.birth_place_en,
        "birth_country_hu": p.birth_country_hu,
        "birth_country_en": p.birth_country,
        "birth_date_hu": hu_long(p.birth_date),
        "birth_date_en": en_long(p.birth_date),
        "place_hu": place_hu,
        "place_en": place_en,
        "sign_date_hu": hu_long(p.sign_date),
        "sign_date_en": en_long(p.sign_date),
    }


def personal_required(p):
    return {"出生日期": p.birth_date, "出生地": p.birth_place_en, "出生国": p.birth_country, "签字日期": p.sign_date}


def company():
    return COMPANY
