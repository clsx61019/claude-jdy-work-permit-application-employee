"""TAJ 申请表（NEAK NYT.53 Igénylőlap）—— 规则见 docs/rules/TAJ申请和GDPR声明.md

模板 templates/hu/taj_application.docx 由 tools/build_taj_gdpr.py 转换而来。
官方要求用印刷体大写填写，所有填写的内容都转成大写。
"""
from ..docx_text import TextDoc
from . import taj_common
from .ict_common import require
from .taj_common import check_person, person_values, ymd

DOC = TextDoc
TEMPLATE = "../hu/taj_application.docx"


def fill(doc, p):
    require({"被授权人姓名": p.auth_name, "被授权人住址（辅助表「被授权人」里填）": p.auth_address})
    check_person(doc, p)
    doc.check("first_issue")  # A4：只办第一次
    values = {
        **person_values(p),
        "auth_name": p.auth_name,          # A2：递交人 = 被授权人
        "auth_address": p.auth_address,
        **ymd("today", taj_common.today()),
    }
    doc.fill({k: v.upper() for k, v in values.items()})
