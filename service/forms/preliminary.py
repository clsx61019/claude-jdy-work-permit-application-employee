"""
Előzetes megállapodás / Preliminary Agreement（劳动关系预协议，匈英双语）—— 规则见 docs/rules/预协议.md

模板 templates/hu/preliminary_agreement.docx 由 tools/build_preliminary.py 从简道云原模板转换而来，
里面的 {{名字}} 在这里计算。适用于 9.5 / 9.6 / 9.8 / 9.9（官方附件里有「预协议日期」的类型），ICT 不需要。
"""
from datetime import date

from ..docx_text import TextDoc
from ..model import hu_money

DOC = TextDoc
TEMPLATE = "../hu/preliminary_agreement.docx"

BORSODCHEM = "BorsodChem Zrt."
BC_SITE = "3700 Kazincbarcika, Bolyai tér 1."

# Flt. 7. § (7)–(7a)：预协议的最长期限（年）
MAX_YEARS = {"Employment": 2, "Investment": 3, "Hungarian Card": 3, "EU Blue Card": 4}

HU_MONTHS = ["január", "február", "március", "április", "május", "június", "július",
             "augusztus", "szeptember", "október", "november", "december"]
EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]
GENDER = {"Male 男": ("férfi", "male"), "Female 女": ("nő", "female")}


def hu_long(d):
    """2026. október 15."""
    return f"{d.year}. {HU_MONTHS[d.month - 1]} {d.day}." if d else ""


def en_long(d):
    """15 October 2026"""
    return f"{d.day} {EN_MONTHS[d.month - 1]} {d.year}" if d else ""


def _add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 2 月 29 日
        return date(d.year + n, 3, 1)


def check(p):
    """生成前检查：不合规或缺内容就报错，不出一份要手改的文件。"""
    if p.permit_type not in MAX_YEARS:
        raise ValueError(f"「{p.permit_type}」不需要预协议（只用于 {', '.join(MAX_YEARS)}）")
    if not p.contract_start or not p.contract_end:
        raise ValueError("缺少劳动关系起始日期或终止日期")
    years = MAX_YEARS[p.permit_type]
    if p.contract_end >= _add_years(p.contract_start, years):  # B5
        raise ValueError(f"{p.permit_type} 的预协议最长 {years} 年（Flt. 7. § (7)–(7a)），"
                         f"现在是 {p.contract_start} 至 {p.contract_end}")
    pairs = {"岗位名称": (p.job_title_hu, p.job_title_en),           # B7
             "职业资格/专业": (p.qualification_hu, p.qualification_en)}
    for name, (hu, en) in pairs.items():
        if not hu or not en:
            raise ValueError(f"「{name}」匈牙利语和英语都要填")
    emp = p.employer_info
    for key, name in (("representative_hu", "雇主代表（匈牙利语）"), ("representative_en", "雇主代表（英语）"),
                      ("address", "雇主地址")):
        if not emp.get(key):
            raise ValueError(f"雇主「{p.employer}」缺少{name}（config/employers.json）")
    if p.salary == "":
        raise ValueError("缺少工资")


def fill(doc, p):
    check(p)
    emp = p.employer_info
    is_bc = p.employer == BORSODCHEM
    gender_hu, gender_en = GENDER.get(p.gender, ("", ""))
    workplace_hu = emp.workplace_hu
    workplace_en = emp.workplace_en or workplace_hu.replace(" és ", " and ")

    # B1：跨州 / 多营业点只适用于 BorsodChem（同 9.x 的工作地点规则）；其他雇主是单一地点，整条删除
    if not is_bc:
        doc.remove_rows("Ha a munkavégzés")

    doc.fill({
        "employer": p.employer,
        "employer_address": emp.address,
        "employer_rep_hu": emp.representative_hu,
        "employer_rep_en": emp.representative_en,
        "tax_no": emp.tax_no,
        "teaor": emp.teaor,
        "surname": p.surname,
        "given_name": p.given_name,
        "birth_place": p.birth_place_en,
        "birth_country_hu": p.birth_country_hu,
        "birth_country_en": p.birth_country,
        "birth_date_hu": hu_long(p.birth_date),
        "birth_date_en": en_long(p.birth_date),
        "passport_no": p.passport_no,
        "gender_hu": gender_hu,
        "gender_en": gender_en,
        "nationality_hu": p.nationality_hu,
        "nationality_en": p.nationality,
        "start_hu": hu_long(p.contract_start),
        "start_en": en_long(p.contract_start),
        "end_hu": hu_long(p.contract_end),
        "end_en": en_long(p.contract_end),
        "job_title_hu": p.job_title_hu,
        "job_title_en": p.job_title_en,
        "feor": p.feor,
        "qualification_hu": p.qualification_hu,
        "qualification_en": p.qualification_en,
        "salary": hu_money(p.salary),                  # B2：两边都用 1.250.000
        "workplace_hu": workplace_hu,
        "workplace_en": workplace_en,
        "start_site": BC_SITE,
        "sign_date_hu": hu_long(p.sign_date),
        "sign_date_en": en_long(p.sign_date),
    })
