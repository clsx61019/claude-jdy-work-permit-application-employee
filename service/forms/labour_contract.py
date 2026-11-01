"""
劳动合同（Munkaszerződés / Employment Agreement，匈英双语）两份共用的逻辑 —— 规则见 docs/rules/劳动合同.md

- labour_contract_ordinary：with CBA，普通员工（集体合同适用）
- labour_contract_executive：without CBA，高管（集体合同不适用；雇主权利由股东行使）

模板由 tools/build_labour_contracts.py 从简道云原模板转换而来。只给 BorsodChem 用（B5）。
新申请用；变更、延期另有 contract modification 模板，不用这份。
"""
import re

from ..docx_text import TextDoc
from ..model import hu_money
from .preliminary import en_long, hu_long

DOC = TextDoc
BORSODCHEM = "BorsodChem Zrt."

# C7：附件 1 第 3 点列出的公司制度，按「奖金系数」「Cafeteria福利」增加。
# 文字和旧辅助字段「辅助_奖金和Cafeteria福利（英语 / 匈牙利语）」的输出一致（2026-10-31 对照现有数据）
POLICIES_EN = ["Remuneration Policy", "Training Policy"]
BONUS_EN = "BorsodChem Comprehensive Performance Management and Incentive System Policy"
BONUS_HU = "a BorsodChem Átfogó Teljesítménymenedzsment és Ösztönzési rendszerre vonatkozó aktuális évi szabályzata"
CAFETERIA_EN = "Cafeteria Policy"
CAFETERIA_HU = "a Cafeteria Szabályzat"


def join(items, last_word):
    """[a, b, c] -> 'a, b and c'"""
    return ", ".join(items[:-1]) + f" {last_word} " + items[-1]


def benefits(p):
    """返回 (policies_en, policies_hu, entitlement_en, entitlement_hu)；没有福利时说明为空。
    匈语模板里固定写着「a Juttatási Szabályzat, illetve a hatályos képzési szabályzat」，policies_hu 接在后面"""
    has_bonus = float(p.bonus_factor or 0) > 0
    has_caf = p.cafeteria == "Yes 是"
    en, extra_hu, what_en, what_hu = list(POLICIES_EN), [], [], []
    if has_bonus:
        en.append(BONUS_EN)
        extra_hu.append(BONUS_HU)
    if has_caf:
        en.append(CAFETERIA_EN)
        extra_hu.append(CAFETERIA_HU)
        what_en.append("Cafeteria")
        what_hu.append("cafeteria-juttatásra")
    if has_bonus:
        what_en.append("bonus")
        what_hu.append("bónuszra")
    policies_hu = (", valamint " + " és ".join(extra_hu) if extra_hu else "") + "."
    ent_en = ent_hu = ""
    if what_en:
        ent_en = (f"The Employer informs the Employee that he/she is entitled to {' and '.join(what_en)} "
                  "according to the Policies stated in point 3).")
        ent_hu = (f"Munkáltató tájékoztatja Munkavállalót, hogy {' és '.join(what_hu)} jogosult "
                  "a 3) pontban meghatározott szabályzatok szerint.")
    return join(en, "and") + ".", policies_hu, ent_en, ent_hu


def address(p, country):
    """A1：两边同一种写法：详细地址, 区/县, 城市, 省份, 邮编, 国家"""
    parts = [p.home_address, p.home_district, p.home_city, p.home_province, p.home_zip, country]
    return ", ".join(x for x in parts if x)


def is_executive(grade):
    """BC职级是 N-1 的用高管版本，其他都用普通版本（János 2026-10-31）。"""
    return re.match(r"\s*N-1(?!\d)", grade or "", re.I) is not None


def check(p, executive):
    grade = getattr(p, "bc_grade", "") or ""
    if not grade.strip():
        raise ValueError("缺少：BC职级（N-1 用高管版，其他用普通版）")
    if is_executive(grade) != executive:
        raise ValueError(f"BC职级是「{grade}」，用{'高管' if is_executive(grade) else '普通员工'}版本")
    if p.employer != BORSODCHEM:
        raise ValueError(f"劳动合同模板只给 {BORSODCHEM} 用，现在雇主是「{p.employer}」")
    if p.app_type != "new":
        raise ValueError("变更、延期用 contract modification 模板，不用劳动合同")
    required = {"岗位名称（英语）": p.job_title_en, "岗位名称（匈牙利语）": p.job_title_hu, "工资": p.salary,
                "出生日期": p.birth_date, "母亲出生时姓名": p.mother_surname, "详细地址": p.home_address}
    if not executive:  # 高管的雇主权利由股东行使，模板里写死（B7）
        required.update({"雇主职权行使人岗位": p.rights_holder, "直线上级岗位": p.line_manager})
    missing = [k for k, v in required.items() if v in ("", None)]
    if missing:
        raise ValueError(f"缺少：{'、'.join(missing)}")


def fill(doc, p, executive):
    check(p, executive)
    policies_en, policies_hu, ent_en, ent_hu = benefits(p)
    if not ent_en:
        doc.remove_paragraphs("{{entitlement_en}}")
        doc.remove_paragraphs("{{entitlement_hu}}")
    values = {
        "name": f"{p.surname} {p.given_name}",
        "birth_place": p.birth_place_en,
        "birth_country_en": p.birth_country,
        "birth_country_hu": p.birth_country_hu,
        "birth_date_en": en_long(p.birth_date),
        "birth_date_hu": hu_long(p.birth_date),
        "address_en": address(p, p.home_country),
        "address_hu": address(p, p.home_country_hu),
        "mother_name": f"{p.mother_surname} {p.mother_given_name}".strip(),
        "job_title_en": p.job_title_en,
        "job_title_hu": p.job_title_hu,
        "salary": hu_money(p.salary),                  # A2：两边都用 1.250.000
        "policies_en": policies_en,
        "policies_hu": policies_hu,
        "entitlement_en": ent_en,
        "entitlement_hu": ent_hu,
    }
    if not executive:
        values.update({"rights_holder": p.rights_holder, "line_manager": p.line_manager})
    doc.fill(values)
