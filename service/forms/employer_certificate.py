"""
Employer's certificate Wanhua（派出公司出具的雇主证明，匈英双语）—— 规则见 docs/rules/ICT声明和雇主证明.md

模板由 tools/build_ict_documents.py 从简道云原模板转换而来。目前只给 ICT 用。
"""
from ..docx_text import TextDoc
from ..model import hu_since
from .ict_common import common_values, name_title, require
from .labour_contract import address

DOC = TextDoc
TEMPLATE = "../hu/employer_certificate_wanhua.docx"

HIS_HER = {"Male 男": "his", "Female 女": "her"}


def fill(doc, p):
    require({"原派出公司": p.sending_company, "原派出公司入职日期": p.sending_start,
             "原派出公司工资": p.sending_salary, "岗位名称（英语）": p.job_title_en,
             "岗位名称（匈牙利语）": p.job_title_hu, "签字日期": p.sign_date, "详细地址": p.home_address,
             "性别": HIS_HER.get(p.gender)})
    values = common_values(p)
    values.update({
        "name": name_title(p),
        "address_en": address(p, p.home_country),
        "address_hu": address(p, p.home_country_hu),
        "sending_since_hu": hu_since(p.sending_start),   # 2011.08.12-től（和 9.10 同一写法）
        "his_her": HIS_HER[p.gender],
    })
    doc.fill(values)
