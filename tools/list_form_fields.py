"""
列出官方 Word 表单（旧式表单域）里的所有可填写域，以及它们旁边的文字。
用于编写规则清单时确定"第几个域对应表单上哪个位置"。

文本域看它前面的文字，勾选框看它后面的文字。

用法: python tools/list_form_fields.py <官方表单.docx>
"""
import re
import sys
import zipfile


def main(path):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    tokens = re.finditer(
        r"<w:t[^>]*>([^<]*)</w:t>|<w:ffData>(.*?)</w:ffData>|(</w:p>|</w:tc>)", xml, flags=re.S
    )
    items, text = [], ""
    for m in tokens:
        if m.group(1) is not None:
            text += m.group(1)
        elif m.group(2) is not None:
            kind = "☐" if "checkBox" in m.group(2) else "T"
            items.append([kind, re.sub(r"[ \s]+", " ", text).strip()])
            text = ""
        else:
            text += " | "
    after = [items[i + 1][1] if i + 1 < len(items) else re.sub(r"[ \s]+", " ", text).strip()
             for i in range(len(items))]
    for i, (kind, before) in enumerate(items):
        label = after[i].split("|")[0] if kind == "☐" else before.split("|")[-1]
        print(f"{i + 1:>3} {kind} {label.strip()[:70]}")


if __name__ == "__main__":
    main(sys.argv[1])
