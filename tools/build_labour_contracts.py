"""
一次性工具：把简道云的两份劳动合同打印模板转换成本项目的模板。

- Ordinary（with CBA，普通员工）和 Executive（without CBA，高管），都只给 BorsodChem 用
- ${标签#_widget_xxx} 换成 {{名字}}（值由 service/forms/labour_contract.py 计算）
- 修正语法、译文和结构问题（规则见 docs/rules/劳动合同.md 的 A 节）

用法: python tools/build_labour_contracts.py
输入: templates/jdy/labour_contract_{ordinary,executive}_jdy_original.docx
输出: templates/hu/labour_contract_{ordinary,executive}.docx
"""
import copy
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from service.docx_text import para_text, paragraphs, replace_in_paragraph  # noqa: E402

WIDGETS = {
    "_widget_1728475331388": "name",
    "_widget_1732527942838": "birth_place",
    "_widget_1728480011250": "birth_country_en",
    "_widget_1732527942947": "birth_country_hu",
    "_widget_1773645284570": "birth_date_en",
    "_widget_1773645284571": "birth_date_hu",
    "_widget_1728475331413": "mother_name",
    "_widget_1730212322930": "job_title_en",
    "_widget_1732541277156": "job_title_hu",
    "_widget_1730212322963": "salary",
    "_widget_1732541277107": "salary",
    "_widget_1730212322934": "rights_holder",
    "_widget_1730212322932": "line_manager",
}
# 地址的 6 个字段换成一个 {{address_en}} / {{address_hu}}（A1：两边同一种写法，由代码生成）
ADDRESS_EN = re.compile(r"\$\{详细地址#\w+\}, \$\{区/县#\w+\}, \$\{城市#\w+\}, \$\{省份#\w+\}, "
                        r"\$\{国家#\w+\}; \$\{邮编#\w+\}")
ADDRESS_HU = re.compile(r"\$\{国家#\w+\}, \$\{省份#\w+\}, \$\{城市#\w+\}, \$\{区/县#\w+\}, "
                        r"\$\{详细地址#\w+\}, \$\{邮编#\w+\}")
POLICIES_EN = re.compile(r"Remuneration Policy, \$\{辅助_奖金和Cafeteria福利（英语）#_widget_1780318748407\}")
POLICIES_HU = re.compile(r"továbbá a Juttatási Szabályzat, illetve a hatályos képzési szabályzat"
                         r"\$\{辅助_奖金和Cafeteria福利（匈牙利语）#_widget_1780315143575\}")

# 两份合同共用的修正：(旧, 新)，每条必须恰好命中 1 处
COMMON = [
    # A4：股东表述统一为 sole shareholder / egyedüli részvényese
    ("a Wanhua Chemical, mint a BorsodChem Zrt. fő részvényese", "a Wanhua Chemical, mint a BorsodChem Zrt. egyedüli részvényese"),
    # A5：附件 1 的 KSZ 清单（「A KSZ tartalmazza: …-val/-vel … összefüggő szabályokat.」）
    ("A napi munkaidővel (KSZ 31-35.§),", "a napi munkaidővel (KSZ 31-35.§),"),
    ("(KSZ 37-40.§, 43 §.)", "(KSZ 37-40.§, 43.§),"),
    ("a munkaviszony megszüntetésével összefüggő szabályok, különösen a felmondási idő megállapításának szabályaival",
     "a munkaviszony megszüntetésével, különösen a felmondási idő megállapításával"),
    # A5：附件 1 第 4 点从第三人称突然变成「你」
    ("which will be provided to you by", "which will be provided to the Employee by"),
    ("A munkaköri feladatokról a munkaköri leírásban kap részletes tájékoztatást",
     "Munkavállaló a munkaköri feladatokról a munkaköri leírásban kap részletes tájékoztatást"),
    ("ad át Önnek", "ad át Munkavállalónak"),
]

EXECUTIVE = [
    # A6
    ("a Társaság részvényese gyakorolják", "a Társaság részvényese gyakorolja"),
    # A7
    ("jogosult személygépkocsit igényelhet", "jogosult személygépkocsit igényelni"),
    # A8：匈语是 kötetlen munkaidő（不定时工作制），英文原来写成 flexible（弹性工作制）。英文优先，必须一致
    ("shall work under a flexible working time arrangement", "shall work under an unscheduled working time arrangement"),
    ("In view of the flexible working time arrangement", "In view of the unscheduled working time arrangement"),
]


def fix(doc, old, new):
    n = sum(replace_in_paragraph(p, re.escape(old), lambda m: new) for p in paragraphs(doc))
    if n != 1:
        raise ValueError(f"修正「{old[:40]}…」应命中 1 处，实际 {n} 处")


def sub(doc, pattern, new, expect=1):
    n = sum(replace_in_paragraph(p, pattern, lambda m: new) for p in paragraphs(doc))
    if n != expect:
        raise ValueError(f"「{pattern.pattern[:40]}…」应命中 {expect} 处，实际 {n} 处")


def set_text(p, text):
    ts = list(p.iter(qn("w:t")))
    ts[0].text = text
    ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for t in ts[1:]:
        t.text = ""


def row_with(doc, text):
    rows = [tr for tr in doc.element.body.iter(qn("w:tr"))
            if para_text(tr.findall(qn("w:tc"))[0]).strip().startswith(text)]
    if len(rows) != 1:
        raise ValueError(f"找不到以「{text}」开头的表格行")
    return rows[0]


def add_final_provisions(doc):
    """A3：生效、终止、适用法律、语言、份数原来都在「Invalidity / Érvénytelenség」下面，加一个标题"""
    heading = row_with(doc, "Invalidity")
    new = copy.deepcopy(heading)
    for tc, text in zip(new.findall(qn("w:tc")), ("Final Provisions", "Záró rendelkezések")):
        set_text(tc.find(qn("w:p")), text)
    row_with(doc, "The Parties agree that the present work contract").addprevious(new)


def merge_broken_item(doc):
    """A5：英文 KSZ 清单最后一条断成了两段"""
    ps = [p for p in paragraphs(doc) if para_text(p).strip() == "available to the employee."]
    if len(ps) != 1:
        raise ValueError("找不到断开的「available to the employee.」")
    prev = ps[0].getprevious()
    set_text(prev, para_text(prev).rstrip() + " available to the employee.")
    ps[0].getparent().remove(ps[0])


def number_hu_point3(doc):
    """Executive 原模板匈语附件第 3 点漏了编号，之后匈语都比英语少 1（英 4) = 匈 3)），补上"""
    p3 = next(p for p in paragraphs(doc) if para_text(p).startswith("Munkaviszony vonatkozásában"))
    if p3.find(".//" + qn("w:numPr")) is not None:
        return
    p4 = next(p for p in paragraphs(doc) if "a munkaköri leírásban kap" in para_text(p))
    ppr3, ppr4 = p3.find(qn("w:pPr")), p4.find(qn("w:pPr"))
    for tag in ("w:numPr", "w:ind"):
        old = ppr3.find(qn(tag))
        if old is not None:
            ppr3.remove(old)
    ppr3.find(qn("w:widowControl")).addnext(copy.deepcopy(ppr4.find(qn("w:numPr"))))
    ind = ppr4.find(qn("w:ind"))
    if ind is not None:
        ppr3.find(qn("w:numPr")).addnext(copy.deepcopy(ind))


def tidy_annex_break(doc):
    """合同正文和附件之间原来是空段 + 分页符段；正文刚好占满一页时会多出一张白纸。
    改成：一个 1 磅的空段（两个表格之间必须隔一段），附件第一段设「段前分页」"""
    body = doc.element.body
    tables = body.findall(qn("w:tbl"))
    between = [el for el in body if el.tag == qn("w:p")
               and tables[0].getparent() is body and body.index(tables[0]) < body.index(el) < body.index(tables[1])]
    for p in between[1:]:
        body.remove(p)
    sep = between[0]
    for r in sep.findall(qn("w:r")):
        sep.remove(r)
    ppr = sep.find(qn("w:pPr"))
    ppr.insert(0, OxmlElement("w:spacing"))
    ppr[0].set(qn("w:before"), "0")
    ppr[0].set(qn("w:after"), "0")
    ppr[0].set(qn("w:line"), "20")
    ppr[0].set(qn("w:lineRule"), "exact")
    # 签字栏最后的空行也会单独挤到下一页
    rows = tables[0].findall(qn("w:tr"))
    if not para_text(rows[-1]).strip():
        tables[0].remove(rows[-1])
    first = tables[1].find(".//" + qn("w:p"))
    fppr = first.find(qn("w:pPr"))
    if fppr is None:
        fppr = OxmlElement("w:pPr")
        first.insert(0, fppr)
    fppr.insert(0, OxmlElement("w:pageBreakBefore"))


def add_entitlement(doc):
    """C7：在附件 1 第 3 点后加一段（不编号，和编号文字对齐），写明有权享受 Cafeteria / 奖金；不适用时代码会删掉这段"""
    indent = next(p for p in paragraphs(doc) if para_text(p).strip() == "összefüggő szabályokat.")
    indent = indent.find(qn("w:pPr")).find(qn("w:ind"))
    for token in ("{{entitlement_en}}", "{{entitlement_hu}}"):
        key = "policies_en" if token.endswith("en}}") else "policies_hu"
        p = next(p for p in paragraphs(doc) if "{{" + key + "}}" in para_text(p))
        new = copy.deepcopy(p)
        num = new.find(".//" + qn("w:numPr"))
        if num is not None:
            num.getparent().remove(num)
        ppr = new.find(qn("w:pPr"))
        if ppr.find(qn("w:ind")) is not None:
            ppr.remove(ppr.find(qn("w:ind")))
        ppr.find(qn("w:widowControl")).addnext(copy.deepcopy(indent))
        set_text(new, token)
        p.addnext(new)


def build(kind):
    src = ROOT / f"templates/jdy/labour_contract_{kind}_jdy_original.docx"
    out = ROOT / f"templates/hu/labour_contract_{kind}.docx"
    doc = Document(src)

    sub(doc, ADDRESS_HU, "{{address_hu}}")
    sub(doc, ADDRESS_EN, "{{address_en}}")
    sub(doc, POLICIES_EN, "{{policies_en}}")
    sub(doc, POLICIES_HU, "továbbá {{policies_hu}}")

    widget = re.compile(r"\$\{[^}]*?#(_widget_\d+)\}")
    unknown = set()

    def repl(m):
        if m.group(1) not in WIDGETS:
            unknown.add(m.group(0))
            return m.group(0)
        return "{{" + WIDGETS[m.group(1)] + "}}"

    for p in paragraphs(doc):
        replace_in_paragraph(p, widget, repl)
    if unknown:
        raise ValueError(f"未映射的字段：{unknown}")

    for old, new in COMMON + (EXECUTIVE if kind == "executive" else []):
        fix(doc, old, new)
    add_final_provisions(doc)
    merge_broken_item(doc)
    number_hu_point3(doc)
    tidy_annex_break(doc)
    add_entitlement(doc)

    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    print("已生成", out)


if __name__ == "__main__":
    for kind in ("ordinary", "executive"):
        build(kind)
