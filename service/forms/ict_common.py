"""ICT 声明和万华雇主证明共用的数据 —— 规则见 docs/rules/ICT声明和雇主证明.md"""
import json

from ..model import CONFIG, hu_money_cents
from .preliminary import en_long, hu_long

SENDING = json.loads((CONFIG / "sending_company_details.json").read_text(encoding="utf-8"))
BORSODCHEM = "BorsodChem Zrt."


def name_title(p):
    """ZENG YING -> Zeng Ying（正文里称呼员工用）"""
    return f"{p.surname} {p.given_name}".title()


def sending(p):
    info = SENDING.get(p.sending_company)
    if not info:
        raise ValueError(f"派出公司「{p.sending_company}」没有地址配置（config/sending_company_details.json）")
    return info


def common_values(p):
    s = sending(p)
    return {
        "sending_company": p.sending_company,
        "sending_address_en": s["address_en"],
        "sending_address_hu": s["address_hu"],
        "sending_city_en": s["city_en"],
        "sending_city_hu": s["city_hu"],
        "birth_place": p.birth_place_en,
        "birth_country_en": p.birth_country,
        "birth_country_hu": p.birth_country_hu,
        "birth_date_en": en_long(p.birth_date),
        "birth_date_hu": hu_long(p.birth_date),
        "job_title_en": p.job_title_en,
        "job_title_hu": p.job_title_hu,
        "sending_start_en": en_long(p.sending_start),
        "sending_start_hu": hu_long(p.sending_start),
        "sending_salary": hu_money_cents(p.sending_salary),
        "sign_date_en": en_long(p.sign_date),
        "sign_date_hu": hu_long(p.sign_date),
    }


def require(fields):
    missing = [k for k, v in fields.items() if v in ("", None)]
    if missing:
        raise ValueError(f"缺少：{'、'.join(missing)}")
