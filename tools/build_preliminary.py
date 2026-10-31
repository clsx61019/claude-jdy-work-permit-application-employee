"""
一次性工具：把简道云的预协议打印模板转换成本项目的模板。

- ${标签#_widget_xxx} 换成 {{名字}}（值由 service/forms/preliminary.py 计算）
- 修正法律依据（Harmtv. → Btátv.，期限按 Flt. 7. § (7)–(7a) 现行条文）和英文译文错误

用法: python tools/build_preliminary.py
输入: templates/jdy/preliminary_agreement_jdy_original.docx
输出: templates/hu/preliminary_agreement.docx
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from service.docx_text import para_text, paragraphs, replace_in_paragraph  # noqa: E402

SRC = ROOT / "templates/jdy/preliminary_agreement_jdy_original.docx"
OUT = ROOT / "templates/hu/preliminary_agreement.docx"

WIDGETS = {
    "_widget_1732604018729": "employer_rep_hu",
    "_widget_1732604018770": "employer_rep_en",
    "_widget_1732604018708": "employer",
    "_widget_1732604018771": "employer_address",
    "_widget_1732604018791": "tax_no",
    "_widget_1732604018811": "teaor",
    "_widget_1728475331386": "surname",
    "_widget_1728475331387": "given_name",
    "_widget_1732527942838": "birth_place",
    "_widget_1732527942947": "birth_country_hu",
    "_widget_1728480011250": "birth_country_en",
    "_widget_1773645284571": "birth_date_hu",
    "_widget_1773645284570": "birth_date_en",
    "_widget_1728480011304": "passport_no",
    "_widget_1732527942807": "gender_hu",
    "_widget_1732527942805": "gender_en",
    "_widget_1732550878139": "nationality_hu",
    "_widget_1728480011238": "nationality_en",
    "_widget_1773645284790": "start_hu",
    "_widget_1773645284789": "start_en",
    "_widget_1773645284793": "end_hu",
    "_widget_1773645284792": "end_en",
    "_widget_1732541277156": "job_title_hu",
    "_widget_1730212322930": "job_title_en",
    "_widget_1732527943206": "feor",
    "_widget_1732527943129": "qualification_hu",
    "_widget_1728480011277": "qualification_en",
    "_widget_1732541277107": "salary",
    "_widget_1730212322963": "salary",
    "_widget_1732541277293": "workplace_hu",
    "_widget_1732541277231": "workplace_en",
    "_widget_1773645284868": "sign_date_hu",
    "_widget_1773645284867": "sign_date_en",
}

# 文字修正：(旧, 新)。每条都必须找到，否则报错（防止模板改过后悄悄漏改）
FIXES = [
    # A1：Harmtv.（2007. évi II.）2024-01-01 起由 Btátv.（2023. évi XC.）取代
    ("a harmadik országbeli állampolgárok beutazásáról és tartózkodásáról szóló 2007. évi II. törvény "
     "(továbbiakban: Harmtv.)",
     "a harmadik országbeli állampolgárok beutazására és tartózkodására vonatkozó általános szabályokról "
     "szóló 2023. évi XC. törvény (továbbiakban: Btátv.)"),
    ("Act II of 2007 on the admission and right of residence of third-country nationals (hereinafter: TCN)",
     "Act XC of 2023 on the general rules for the entry and residence of third-country nationals "
     "(hereinafter: Btátv.)"),
    # A1：期限按 Flt. 7. § (7)：一般最长 2 年；(7a) 的例外只保留我们会用到的 b) f) h)
    ("legfeljebb hároméves, határozott időtartamú jogviszony létesítésére szólhat. Kivéve:",
     "legfeljebb kétéves, határozott időtartamú jogviszony létesítésére szólhat. Kivéve:"),
    ("may not be longer than 3 years with the exception of the following:",
     "may not be longer than 2 years with the exception of the following:"),
    # A3：英文把「申请前不超过 60 天」译成了「之后 60 天内」
    ("before or at the same time the single permit application is submitted but no later 60 days thereafter",
     "at the same time as, or not more than 60 days before, the submission of the single permit application"),
    # A4
    ("may involve more than one country or labour centre", "may involve more than one county or labour centre"),
    # A6
    ("as third-party national", "as third-country national"),
    ("Third- country citizen", "Third-country national"),
    # B2：英文工资也用匈牙利格式，并写明每月
    ("HUF {{salary}}.", "HUF {{salary}}/month."),
]

# A1：(7a) 例外清单，替换原来的 5 条（家庭团聚、人道许可等与我们无关）
EXCEPTIONS_HU = [
    "az EU Kék Kártya iránt benyújtott kérelem esetén legfeljebb négyéves,",
    "a Btátv. 24. § (1) bekezdése szerinti beruházás megvalósítása céljából kiállított munkavállalási célú "
    "tartózkodási engedély esetén legfeljebb hároméves,",
    "a Btátv. 36. § (3) bekezdés a) pontja szerinti célból kiállított Magyar Kártya esetén legfeljebb hároméves",
]
EXCEPTIONS_EN = [
    "up to 4 years if an application is submitted for the EU Blue Card,",
    "up to 3 years for a work-purpose residence permit issued for the implementation of an investment "
    "under Article 24 (1) of the Btátv.,",
    "up to 3 years for a Hungarian Card issued for the purpose under Article 36 (3) (a) of the Btátv.,",
]
OLD_FIRST_HU = "a családi együttélés biztosítása céljából"
OLD_FIRST_EN = "up to 5 years if a residency permit is issued to provide for family cohabitation"


def set_text(p, text):
    ts = list(p.iter(qn("w:t")))
    ts[0].text = text
    ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in ts[1:]:
        t.text = ""


def replace_list(doc, first, new_items):
    """找到以 first 开头的那条，连同后面同一列表的几条，换成 new_items（多余的删除）"""
    ps = [p for p in paragraphs(doc) if para_text(p).strip().startswith(first)]
    if len(ps) != 1:
        raise ValueError(f"找不到例外清单：{first}")
    start = ps[0]
    items = [start]
    nxt = start.getnext()
    while nxt is not None and nxt.tag == qn("w:p") and nxt.find(".//" + qn("w:numPr")) is not None:
        items.append(nxt)
        nxt = nxt.getnext()
    if len(items) != 5:
        raise ValueError(f"例外清单应有 5 条，实际 {len(items)} 条")
    for p, text in zip(items, new_items):
        set_text(p, text)
    for p in items[len(new_items):]:
        p.getparent().remove(p)


def main():
    doc = Document(SRC)
    widget = re.compile(r"\$\{[^}]*?#(_widget_\d+)\}")
    unknown = set()

    def repl(m):
        if m.group(1) not in WIDGETS:
            unknown.add(m.group(1))
            return m.group(0)
        return "{{" + WIDGETS[m.group(1)] + "}}"

    for p in paragraphs(doc):
        replace_in_paragraph(p, widget, repl)
    if unknown:
        raise ValueError(f"未映射的字段：{unknown}")

    # B1：第 10 点「开始工作地点」不用注册地址，单独一个值
    for p in paragraphs(doc):
        t = para_text(p)
        if "megkezdésének helye" in t or "starting place of work" in t:
            replace_in_paragraph(p, r"\{\{employer_address\}\}", lambda m: "{{start_site}}")

    for old, new in FIXES:
        n = sum(replace_in_paragraph(p, re.escape(old), lambda m, new=new: new) for p in paragraphs(doc))
        if n != 1:
            raise ValueError(f"修正「{old[:40]}…」应命中 1 处，实际 {n} 处")

    replace_list(doc, OLD_FIRST_HU, EXCEPTIONS_HU)
    replace_list(doc, OLD_FIRST_EN, EXCEPTIONS_EN)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print("已生成", OUT)


if __name__ == "__main__":
    main()
