"""
一次性工具：把简道云打印模板里的 ${标签#_widget_xxx} 换成 Jinja 表达式。
转换后的模板就是普通 Word 文件，以后直接在 Word 里改。

用法: python convert_template.py <简道云模板.docx> <输出.docx>
"""
import re
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

# 简道云字段 ID -> 新模板里写的内容。
# 普通字段就是 {{ p.xxx }}；原来靠公式生成的辅助字段，在这里变成模板里的一小段文字。
CB_PERMIT = [  # 原「辅助_居留许可类型_单选框」6591 字符的公式：静态文字放回模板，只有勾选框是变量
    ("Vendég-önfoglalkoztatás (9.2. sz. betétlap)", None),
    ("Vendégbefektető (9.3. sz. betétlap)", None),
    ("Szezonális munkavállalás (9.4. sz. betétlap)", None),
    ("Beruházás megvalósítása céljából munkavállalás (9.5. sz. betétlap)", "Investment"),
    ("Foglalkoztatás (9.6. sz. betétlap)", "Employment"),
    ("Vendégmunkás-tartózkodási engedély (9.7. sz. betétlap)", None),
    ("Magyar Kártya (9.8. sz. betétlap)", "Hungarian Card"),
    ("EU Kék Kártya (9.9. sz. betétlap)", "EU Blue Card"),
    ("Vállalaton belüli áthelyezés (9.10 sz. betétlap)", "Intra-corporate Transfer"),
    ("Kutatás vagy kutatói mobilitás (hosszú távú) (9.11. betétlap)", None),
    ("Nemzeti Kártya (9.12. betétlap)", None),
    ("Tanulmányok folytatása vagy hallgatói mobilitás (9.13. sz. betétlap)", None),
    ("Álláskeresés vagy vállalkozás indítás (9.14. sz. betétlap)", None),
    ("Képzés (9.15. sz. betétlap)", None),
    ("Gyakornok (9.16. sz. betétlap)", None),
    ("Hivatalos (9.17. sz. betétlap)", None),
    ("Fehér Kártya (9.18. sz. betétlap)", None),
    ("Kiküldetés (9.19. sz. betétlap)", None),
    ("Gyógykezelés (9.20. sz. betétlap)", None),
    ("Önkéntes tevékenység folytatása (9.21. sz. betétlap)", None),
    ("Tartózkodási engedély nemzeti érdekből (9.22. sz. betétlap)", None),
    ("Családi együttélés biztosítása (9.23. sz. betétlap)", None),
]
PERMIT_BLOCK = "\n".join(
    f"{{{{ cb(p.permit_type == '{key}') }}}} {text}" if key else f"☐ {text}"
    for text, key in CB_PERMIT
)

EDU_INDENT = "\n" + " " * 33 + "\t"
EDU_BLOCK = "\t" + EDU_INDENT.join([
    "{{ cb(p.education_level == 'Primary Education 基础教育') }} alapfokú",
    "{{ cb(p.education_level == 'Secondary Education 中等教育') }} középfokú",
    "{{ cb(p.education_level == 'Higher Education 高等教育') }} felsőfokú",
])

MAP = {
    # 普通字段
    "_widget_1728475331386": "{{ p.surname }}",
    "_widget_1728475331387": "{{ p.given_name }}",
    "_widget_1728475331411": "{{ p.mother_surname }}",
    "_widget_1728475331412": "{{ p.mother_given_name }}",
    "_widget_1732527943129": "{{ p.qualification_hu }}",
    "_widget_1770019996916": "{{ p.prev_position_en }}",
    "_widget_1728480011304": "{{ p.passport_no }}",
    "_widget_1732527943146": "{{ p.home_province }}",
    "_widget_1732527943147": "{{ p.home_city }}",
    "_widget_1732527943148": "{{ p.home_district }}",
    "_widget_1732527943149": "{{ p.home_address }}",
    "_widget_1743597826298": "{{ p.home_zip }}",
    # 原来是 IFS 公式的匈牙利住址 -> 查住宿地点表
    "_widget_1728480011344": "{{ p.hu_address.lot_no }}",
    "_widget_1728549508506": "{{ p.hu_address.zip }}",
    "_widget_1728549508516": "{{ p.hu_address.city }}",
    "_widget_1728549508519": "{{ p.hu_address.street }}",
    "_widget_1728549508520": "{{ p.hu_address.street_type }}",
    "_widget_1728549508521": "{{ p.hu_address.house_no }}",
    # 原「辅助_」字段
    "_widget_1728562133650": "{{ p.birth_surname | upper }}",
    "_widget_1728562133651": "{{ p.birth_given_name | upper }}",
    "_widget_1772702315563": "{{ cb(p.gender == 'Male 男') }} férfi {{ cb(p.gender == 'Female 女') }} nő",
    "_widget_1772720689497": (
        "{{ cb(p.marital_status == 'Single 未婚') }} nőtlen/hajadon "
        "{{ cb(p.marital_status == 'Widowed 丧偶') }} özvegy "
        "{{ cb(p.marital_status == 'Married 已婚') }} házas "
        "{{ cb(p.marital_status == 'Divorced 离异') }} elvált"
    ),
    "_widget_1772720689277": "{{ p.birth_date | hu_full }}",
    "_widget_1732527942838": "{{ p.birth_place | en_part }}",
    "_widget_1732527942947": "{{ p.birth_country_hu }}",
    "_widget_1732550878139": "{{ p.nationality_hu }}",
    "_widget_1772725832151": EDU_BLOCK,
    "_widget_1772720689386": "{{ p.passport_issued | hu_full }}",
    "_widget_1732632872427": "{{ p.passport_place | en_part }}",
    "_widget_1772720689387": "{{ p.passport_expiry | hu_full }}",
    "_widget_1773645284791": "{{ p.contract_end | hu_full }}",
    "_widget_1772725832261": PERMIT_BLOCK,
    "_widget_1732692034020": "{{ p.attachment_no }}",
}

PLACEHOLDER = re.compile(r"\$\{[^#}]*#(_widget_\d+)\}")


def convert_paragraph(par, unknown):
    runs = par.runs
    if not runs:
        return
    text = "".join(r.text for r in runs)
    matches = list(PLACEHOLDER.finditer(text))
    if not matches:
        return
    # 每个 run 在整段文字里的起止位置
    bounds, pos = [], 0
    for r in runs:
        bounds.append((pos, pos + len(r.text)))
        pos += len(r.text)
    # 从后往前替换，前面的位置不受影响
    for m in reversed(matches):
        wid = m.group(1)
        repl = MAP.get(wid)
        if repl is None:
            unknown.add(wid)
            continue
        s, e = m.span()
        first = next(i for i, (a, b) in enumerate(bounds) if a <= s < b)
        last = next(i for i, (a, b) in enumerate(bounds) if a < e <= b)
        prefix = runs[first].text[: s - bounds[first][0]]
        suffix = runs[last].text[e - bounds[last][0]:]
        # Run.text 会把 \n、\t 写成 Word 的换行和制表符
        runs[first].text = prefix + repl + (suffix if first == last else "")
        for i in range(first + 1, last + 1):
            runs[i].text = suffix if i == last else ""


def main(src, dst):
    doc = Document(src)
    unknown = set()
    parts = [doc.element.body] + [s.header._element for s in doc.sections] + [s.footer._element for s in doc.sections]
    for root in parts:
        for p in root.iter(qn("w:p")):  # 也包括表格和文本框里的段落
            convert_paragraph(Paragraph(p, None), unknown)
    doc.save(dst)
    if unknown:
        print("未映射的字段:", ", ".join(sorted(unknown)))
    print("已生成", dst)


if __name__ == "__main__":
    main(*sys.argv[1:3])
