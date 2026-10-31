"""TAJ 订购单（NEAK NYT.52 Megrendelő，雇主填）—— 规则见 docs/rules/TAJ申请和GDPR声明.md

模板 templates/hu/taj_order.docx 由 tools/build_taj_gdpr.py 转换而来。
"""
from ..docx_text import TextDoc
from . import taj_common
from .authorization_common import official_date
from .ict_common import require
from .taj_common import check_person, person_values, ymd

DOC = TextDoc
TEMPLATE = "../hu/taj_order.docx"


def fill(doc, p):
    emp = p.employer_info
    require({"雇主": p.employer, "雇主地址（config/employers.json）": emp.zip,
             "雇主税号（config/employers.json）": emp.tax_no,
             "雇主代表（辅助表「雇主相关信息」）": emp.representative_hu,
             "劳动关系实际起始日期": p.actual_start})  # B3
    check_person(doc, p)
    # B4：外籍员工；三个问题都是「nem」
    doc.check("employee")
    for q in ("egt", "commuter", "simplified"):
        doc.check(f"{q}_no")
    doc.fill({
        **person_values(p),
        "employer": p.employer,
        "employer_zip": emp.zip,
        "employer_city": emp.city,
        "employer_street": f"{emp.street} {emp.street_type}",
        "employer_house_no": emp.house_no,
        "employer_tax_no": emp.tax_no,
        **ymd("start", p.actual_start),
        "today": official_date(taj_common.today()),  # B5
        "representative": emp.representative_hu,      # B6
    })
