"""Munkáltatói bejelentés（雇主用工情况报告）—— 规则见 docs/rules/住宿证明雇主通知员工声明.md

a) 已开始工作 / b) 未开始工作 / c) 劳动关系终止：有「劳动关系实际起始日期」时填 a)，删掉 b)、c)；
没有时三行都留着手填（b、c 现在没有对应字段）。
"""
from datetime import date

from ..docx_text import TextDoc
from ..model import COMPANY
from .authorization_common import full_name
from .ict_common import require
from .preliminary import hu_long

DOC = TextDoc
TEMPLATE = "../hu/employer_notification.docx"


def today():
    """落款日期 = 生成当天（B5）。测试里会换成固定日期"""
    return date.today()


def fill(doc, p):
    emp = p.employer_info
    require({"雇主": p.employer, "雇主地址（config/employers.json）": emp.address,
             "雇主税号（config/employers.json）": emp.tax_no,
             "雇主公司注册号（config/employers.json）": emp.registration_no,
             "雇主代表（config/employers.json，待办 J13）": emp.representative_hu,
             "出生日期": p.birth_date, "出生地": p.birth_place_en, "国籍": p.nationality_hu})
    if p.actual_start:  # B4
        require({"居留卡号": p.card_no})
        doc.remove_rows("b) munkáját")
        doc.remove_rows("c) munkaviszonya")
    doc.fill({
        "employer": p.employer,
        "contact": f"{COMPANY['contact_phone']}, {COMPANY['contact_email']}",
        "employer_address": emp.address,
        "employer_tax_no": emp.tax_no,
        "employer_registration_no": emp.registration_no,
        "name": full_name(p),
        "birth": f"{p.birth_place_en}, {p.birth_country_hu}, {hu_long(p.birth_date)}",
        "nationality_hu": p.nationality_hu,
        "card_no": p.card_no,
        "start_date": hu_long(p.actual_start),
        "today": hu_long(today()),
        "representative": emp.representative_hu,
    })
