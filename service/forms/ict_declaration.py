"""
Declaration on Intra-Corporate Transfer（ICT 声明，匈英双语）—— 规则见 docs/rules/ICT声明和雇主证明.md

模板由 tools/build_ict_documents.py 从简道云原模板转换而来。只用于 ICT，接收单位固定是 BorsodChem。
"""
import re

from ..docx_text import TextDoc
from ..model import hu_money
from .ict_common import BORSODCHEM, common_values, name_title, require
from .preliminary import en_long, hu_long

DOC = TextDoc
TEMPLATE = "../hu/ict_declaration.docx"

# A1：岗位类型（ICT），和 9.10 同一套选项
POSITION = {"Manager 经理": ("manager", "vezetői"),
            "Expert 专家": ("expert", "szakértői"),
            "Intern 实习生": ("trainee", "gyakornoki")}
# A7：学历（和 9.10 同一套选项）
EDUCATION = {
    "University 大学": ("university education", "egyetemi végzettség"),
    "College 学院 / 大专": ("college education", "főiskolai végzettség"),
    "Technician Education Establishment 技术教育机构": ("technician qualification", "technikusi végzettség"),
    "Vocational Secondary School 中等职业学校": ("vocational secondary education", "szakközépiskolai végzettség"),
    "Secondary Grammar School 普通高中": ("secondary education", "gimnáziumi érettségi"),
    "Vocational School 职业学校": ("vocational qualification", "szakmunkás végzettség"),
    "Specialised School 专业学校": ("vocational school education", "szakiskolai végzettség"),
    "Primary School 小学": ("primary education", "általános iskolai végzettség"),
}


def _months_before(d, n):
    y, m = divmod(d.month - 1 - n, 12)
    return d.replace(year=d.year + y, month=m + 1, day=min(d.day, 28))


def sentence(*parts):
    """把姓名、简要说明、主要职责接成一段，空格只留一个"""
    return re.sub(r"\s+", " ", " ".join(x for x in parts if x)).strip()


def check(p):
    if p.employer != BORSODCHEM:
        raise ValueError(f"ICT 声明的接收单位固定是 {BORSODCHEM}，现在雇主是「{p.employer}」")
    if p.ict_position not in POSITION:
        raise ValueError(f"「岗位类型（ICT）」不认识：「{p.ict_position}」")
    if p.education not in EDUCATION:
        raise ValueError(f"「学历」不适用于 ICT 声明：「{p.education}」")
    if p.ict_position == "Intern 实习生" and p.education != "University 大学":
        raise ValueError("ICT 实习生必须有大学学历（35/2024. Korm. rendelet 27. § (2) b)）")
    require({"原派出公司入职日期": p.sending_start, "劳动关系起始日期": p.contract_start,
             "劳动关系终止日期": p.contract_end, "原派出公司工资": p.sending_salary, "工资": p.salary,
             "汇率日期": p.rate_date, "工作活动简要说明（英语）": p.activity_en,
             "工作活动简要说明（匈牙利语）": p.activity_hu, "岗位名称（英语）": p.job_title_en,
             "岗位名称（匈牙利语）": p.job_title_hu, "签字日期": p.sign_date, "护照号": p.passport_no})
    # A12：派遣前须在派出公司连续工作至少 3 个月
    if p.sending_start > _months_before(p.contract_start, 3):
        raise ValueError(f"派出公司入职日期 {p.sending_start} 距派遣开始 {p.contract_start} 不足 3 个月")


def fill(doc, p):
    check(p)
    pos_en, pos_hu = POSITION[p.ict_position]
    edu_en, edu_hu = EDUCATION[p.education]
    name = name_title(p)
    values = common_values(p)
    values.update({
        "name": f"{p.surname} {p.given_name}",                       # B1：当事人栏用护照写法
        "nationality_en": p.nationality,
        "nationality_hu": p.nationality_hu,
        "passport_no": p.passport_no,
        "position_en": pos_en,
        "position_hu": pos_hu,
        "activity_en": sentence(name, p.activity_en, p.duties_en),   # B1：简述里用 Zeng Ying
        "activity_hu": sentence(name, p.activity_hu, p.duties_hu),
        "education_en": edu_en,
        "education_hu": edu_hu,
        "qualification_en": p.qualification_en,
        "qualification_hu": p.qualification_hu,
        "feor": p.feor,
        "salary": hu_money(p.salary),
        "rate_date_en": en_long(p.rate_date),
        "rate_date_hu": hu_long(p.rate_date),
        "start_en": en_long(p.contract_start),
        "start_hu": hu_long(p.contract_start),
        "end_en": en_long(p.contract_end),
        "end_hu": hu_long(p.contract_end),
    })
    doc.fill(values)
