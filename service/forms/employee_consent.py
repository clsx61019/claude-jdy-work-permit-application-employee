"""Nyilatkozat / Declaration：员工同意雇主在 Enter Hungary 上代为递交申请 —— 规则见 docs/rules/住宿证明雇主通知员工声明.md"""
from ..docx_text import TextDoc
from .employee_common import personal_required, personal_values, with_article
from .ict_common import require

DOC = TextDoc
TEMPLATE = "../hu/employee_consent.docx"

# B8：居留许可类型。匈语用 9 号申请表第 9 部分的写法
PERMITS = {
    "Intra-corporate Transfer": ("vállalaton belüli áthelyezés célú tartózkodási engedély",
                                 "an intra-corporate transfer residence permit"),
    "Investment": ("beruházás megvalósítása céljából munkavállalás célú tartózkodási engedély",
                   "a residence permit for employment for the implementation of an investment"),
    "Employment": ("foglalkoztatás célú tartózkodási engedély", "a residence permit for employment"),
    "Hungarian Card": ("Magyar Kártya", "a Hungarian Card"),
    "EU Blue Card": ("EU Kék Kártya", "an EU Blue Card"),
}


def fill(doc, p):
    if p.submit_place != "Hungary 匈牙利":  # B8
        raise ValueError("员工同意书只在雇主于匈牙利递交（递交地点 = 匈牙利）时用")
    if p.permit_type not in PERMITS:
        raise ValueError(f"居留许可类型「{p.permit_type}」没有对应的写法")
    require(personal_required(p))
    hu, en = PERMITS[p.permit_type]
    doc.fill({**personal_values(p), "permit_hu": with_article(hu), "permit_en": en})
