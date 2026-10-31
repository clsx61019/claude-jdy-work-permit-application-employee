"""
一次性工具：把简道云的两份 ICT 文件模板转换成本项目的模板。

- Declaration on Intra-Corporate Transfer（ICT 声明，派出公司 + BorsodChem + 员工三方签字）
- Employer's certificate Wanhua（派出公司出具的雇主证明）

${标签#_widget_xxx} 换成 {{名字}}（值由 service/forms/ict_declaration.py、employer_certificate.py 计算），
并做 docs/rules/ICT声明和雇主证明.md 里的 A 类修正。

用法: python tools/build_ict_documents.py
"""
import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from service.docx_text import para_text, paragraphs, replace_in_paragraph  # noqa: E402
from tools.bilingual import flip_labels, hungarian_left  # noqa: E402

W = r"\$\{[^}]*?#_widget_"  # 占位符开头


def fix(doc, old, new, regex=False, expect=1):
    pattern = old if regex else re.escape(old)
    n = sum(replace_in_paragraph(p, pattern, lambda m: new) for p in paragraphs(doc))
    if n != expect:
        raise ValueError(f"「{old[:50]}…」应命中 {expect} 处，实际 {n} 处")


def check_done(doc):
    left = [para_text(p) for p in paragraphs(doc) if "${" in para_text(p)]
    if left:
        raise ValueError(f"还有没换掉的字段：{left}")


def build_declaration():
    doc = Document(ROOT / "templates/jdy/ict_declaration_jdy_original.docx")
    # A5：派出公司取「原派出公司」+ 配置
    fix(doc, r"^Wanhua Chemical Group Co\., Ltd\.$", "{{sending_company}}", regex=True, expect=2)  # 只换当事人栏（整段就是公司名）
    fix(doc, "(address: No.59, Chongqing Rd, YEDA, Yantai, 264006, China)", "(address: {{sending_address_en}})")
    fix(doc, "(székhelye: No.59, Chongqing Rd, YEDA, Yantai, 264006, Kína)", "(székhelye: {{sending_address_hu}})")
    # 第 1 点「同一集团」仍写 Wanhua Chemical Group：ICT 的派出公司都属于万华集团
    # A11：引号统一
    fix(doc, '"Sending Company"', "“Sending Company”")
    fix(doc, '"Host Company"', "“Host Company”")
    fix(doc, '"Employee"', "“Employee”")
    fix(doc, 'a továbbiakban "Küldő Vállalat"', "a továbbiakban „Küldő Vállalat”")
    fix(doc, '„Fogadó Vállalat"', "„Fogadó Vállalat”")
    fix(doc, '„Munkavállaló"', "„Munkavállaló”")
    # 当事人
    fix(doc, W + r"1728475331388\}", "{{name}}", regex=True, expect=4)   # 两处当事人 + 两处简述（简述下面再换）
    fix(doc, W + r"1728480011238\}", "{{nationality_en}}", regex=True)
    fix(doc, W + r"1732550878139\}", "{{nationality_hu}}", regex=True)
    fix(doc, W + r"1732527942838\}, " + W + r"1728480011250\}, " + W + r"1773645284570\}",
        "{{birth_place}}, {{birth_country_en}}, {{birth_date_en}}", regex=True)
    fix(doc, W + r"1732527942838\}, " + W + r"1732527942947\}, " + W + r"1773645284571\}",
        "{{birth_place}}, {{birth_country_hu}}, {{birth_date_hu}}", regex=True)
    fix(doc, W + r"1728480011304\}", "{{passport_no}}", regex=True, expect=2)
    # A1：岗位类型
    fix(doc, W + r"1774114982916\}", "{{position_en}}", regex=True)
    fix(doc, "a Fogadó Vállalat vezetői pozícióban", "a Fogadó Vállalat {{position_hu}} pozícióban")
    # A6：简述由代码拼（姓名 + 简要说明 + 主要职责）
    fix(doc, r"\{\{name\}\} ?" + W + r"1770019996877\} " + W + r"1770019996879\}", "{{activity_en}}", regex=True)
    fix(doc, r"\{\{name\}\} ?" + W + r"1770019996876\} " + W + r"1770019996878\}", "{{activity_hu}}", regex=True)
    # A7：学历按字段
    fix(doc, "college education (" + "${职业资格/专业（英语）#_widget_1728480011277})",
        "{{education_en}} ({{qualification_en}})")
    fix(doc, "felsőfokú végzettség (" + "${职业资格/专业（匈牙利语）#_widget_1732527943129})",
        "{{education_hu}} ({{qualification_hu}}).")
    fix(doc, r"Sending Company: " + W + r"1768200681561\}", "Sending Company: {{sending_start_en}}", regex=True)
    fix(doc, r"Küldő Vállalatnál: " + W + r"1768200681561\}\.", "Küldő Vállalatnál: {{sending_start_hu}}", regex=True)  # 匈语日期自带句点
    fix(doc, W + r"1730212322930\}", "{{job_title_en}}", regex=True)
    fix(doc, W + r"1732541277156\}", "{{job_title_hu}}", regex=True)
    fix(doc, W + r"1732527943206\}", "{{feor}}", regex=True, expect=2)
    # A3：金额格式
    fix(doc, "CNY " + "${Salary at Sending Company#_widget_1773148604476}", "CNY {{sending_salary}}")
    fix(doc, W + r"1773148604476\} kínai jüan", "{{sending_salary}} kínai jüan", regex=True)
    fix(doc, "HUF " + "${Salary#_widget_1730212322963}", "HUF {{salary}}")
    fix(doc, W + r"1730212322963\} Ft", "{{salary}} Ft", regex=True)
    # A2：脚注的汇率日期
    fix(doc, "13:00, 02 April 2026", "13:00, {{rate_date_en}}")
    fix(doc, "2026. április 02. 13:00", "{{rate_date_hu}} 13:00")
    # 日期
    fix(doc, W + r"1773645284789\}", "{{start_en}}", regex=True)
    fix(doc, W + r"1773645284790\}", "{{start_hu}}", regex=True)
    fix(doc, W + r"1773645284792\}", "{{end_en}}", regex=True)
    fix(doc, W + r"1773645284793\}", "{{end_hu}}", regex=True)
    fix(doc, "China, Yantai, " + "${辅助_签字日期1（英语）#_widget_1773645284867}.", "{{sending_city_en}}, {{sign_date_en}}")
    fix(doc, W + r"1773645284868\}", "{{sign_date_hu}}", regex=True)
    # C1：法条引用。445/2013. 20/A. § 是旧条款号；现行依据是 35/2024. (II. 29.) Korm. rendelet 27. §
    fix(doc, "The Host Company declares, as per the 445/2013. 20/A.§ (1) a) and c) section, that:",
        "The Host Company declares, in accordance with Section 27 of Government Decree No. 35/2024 (II. 29.), that:")
    fix(doc, "A Fogadó Vállalat a 445/2013. (XI.28) Korm. rendelet 20/A.§ (1) bekezdés a) és c) pontja szerint "
             "továbbá nyilatkozik arról, hogy:",
        "A Fogadó Vállalat a 35/2024. (II. 29.) Korm. rendelet 27. §-a szerint továbbá nyilatkozik arról, hogy:")
    # A8、A9、A10：笔误
    fix(doc, "regulations and/for sectoral", "regulations and/or sectoral")
    fix(doc, "the employee have had an at least 3 months", "the Employee has had at least 3 months of")
    fix(doc, "hasonló helyzetben tévő", "hasonló helyzetben lévő")
    fix(doc, "duly executed this preliminary agreement", "duly executed this Declaration")
    fix(doc, "a felek a jelen megállapodást", "a felek a jelen nyilatkozatot")
    # 统一版式：左匈右英。日期和签字两行左右是派出公司和接收公司两方，不动
    hungarian_left(doc, keep=("Date/Dátum", "Sending Company/"))
    flip_labels(doc, [("Date", "Dátum"), ("Sending Company", "Küldő Vállalat"), ("Host Company", "Fogadó Vállalat"),
                      ("Employee", "Munkavállaló"),
                      ("I accept and agree with the above terms", "a fentiekkel egyetértek és elfogadom")])
    fix(doc, "a fentiekkel egyetértek és elfogadom / I accept", "A fentiekkel egyetértek és elfogadom / I accept")
    fix(doc, "HU National Bank exchange rate, 13:00, {{rate_date_en}} / Magyar Nemzeti Bank árfolyama alapján, {{rate_date_hu}} 13:00",
        "Magyar Nemzeti Bank árfolyama alapján, {{rate_date_hu}} 13:00 / HU National Bank exchange rate, 13:00, {{rate_date_en}}")
    # 脚注原来有黄色高亮，打印出来有底色
    for par in paragraphs(doc):
        if "Magyar Nemzeti Bank árfolyama" in para_text(par):
            for h in list(par.iter(qn("w:highlight"))):
                h.getparent().remove(h)
    check_done(doc)
    doc.save(ROOT / "templates/hu/ict_declaration.docx")


def build_certificate():
    doc = Document(ROOT / "templates/jdy/employer_certificate_wanhua_jdy_original.docx")
    fix(doc, W + r"1728475331388\}", "{{name}}", regex=True, expect=2)
    # W3：地址和劳动合同同一种写法
    addr = (W + r"1732527943145\}, " + W + r"1732527943146\} Province, " + W + r"1732527943147\} City, "
            + W + r"1732527943148\}, " + W + r"1732527943149\}, " + W + r"1743597826298\}")
    fix(doc, "állandó lakóhely: " + addr, "állandó lakóhely: {{address_hu}}", regex=True)
    fix(doc, "CHN address: " + addr, "address: {{address_en}}", regex=True)
    fix(doc, W + r"1732527942838\}, " + W + r"1732527942947\}, " + W + r"1773645284571\}",
        "{{birth_place}}, {{birth_country_hu}}, {{birth_date_hu}}", regex=True)
    fix(doc, W + r"1732527942838\}, " + W + r"1728480011250\}, " + W + r"1773645284570\}",
        "{{birth_place}}, {{birth_country_en}}, {{birth_date_en}}", regex=True)
    fix(doc, W + r"1732541277156\}", "{{job_title_hu}}", regex=True)
    fix(doc, W + r"1730212322930\}", "{{job_title_en}}", regex=True)
    # W2：派出公司取字段
    fix(doc, "a Wanhua Chemical Group Co. Ltd. által kiküldött", "a {{sending_company}} által kiküldött")
    fix(doc, "is employee of Wanhua Chemical Group Co. Ltd. transferred", "is an employee of {{sending_company}} transferred")
    # W6
    fix(doc, "3700 Kazincbarcika, Bolyai tér in the position", "3700 Kazincbarcika, Bolyai tér 1. in the position")
    # W1、W4：入职日期写死 2011；只用姓氏称呼 → 全名
    fix(doc, W + r"1728475331386\} a Wanhua Chemical Group Co. Ltd munkavállalója 2011.08.12-től",
        "{{name}} a {{sending_company}} munkavállalója {{sending_since_hu}}", regex=True)
    fix(doc, W + r"1728475331386\} is employee of Wanhua Chemical Group as of 12 August, 2011",
        "{{name}} has been an employee of {{sending_company}} since {{sending_start_en}}", regex=True)
    fix(doc, "neccessary", "necessary")
    fix(doc, "being transferred to BorsodChem Zrt., Hungary as part of Wanhua Chemical Group",
        "is being transferred to BorsodChem Zrt., Hungary, as part of Wanhua Chemical Group")
    # W7：金额
    fix(doc, W + r"1773148604476\} kínai jüan", "{{sending_salary}} kínai jüan", regex=True)
    fix(doc, "CNY " + "${Salary at Sending Company#_widget_1773148604476}", "CNY {{sending_salary}}")
    fix(doc, W + r"1728475331386\} első tervezett", "{{name}} első tervezett", regex=True)
    fix(doc, W + r"1728475331386\} first planned transfer duration to Hungary is expected to be in line with the duration "
             r"defined in declaration on intracompany transfer",
        "{{name}}’s first planned transfer duration to Hungary is in line with the duration defined in the Declaration "
        "on Intra-Corporate Transfer.", regex=True)
    # W5
    fix(doc, "during his stay in Hungary", "during {{his_her}} stay in Hungary")
    # W8：签字地点、日期
    fix(doc, "Yantai, China, " + "${辅助_签字日期1（英语）#_widget_1773645284867}",
        "{{sending_city_hu}}, {{sign_date_hu}} / {{sending_city_en}}, {{sign_date_en}}")
    check_done(doc)
    doc.save(ROOT / "templates/hu/employer_certificate_wanhua.docx")


if __name__ == "__main__":
    build_declaration()
    build_certificate()
    print("已生成 templates/hu/ict_declaration.docx、employer_certificate_wanhua.docx")
