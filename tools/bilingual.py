"""
双语模板统一版式：左栏匈牙利语，右栏英语（2026-10-31 János 定）。

简道云的部分双语模板是英语在左。这里把两栏表格行的内容左右对调：
只换单元格里的段落，单元格本身（宽度、边框、底纹）留在原位。
"""
import re

from docx.oxml.ns import qn

from service.docx_text import para_text, paragraphs, replace_in_paragraph


def _content(tc):
    return [el for el in tc if el.tag != qn("w:tcPr")]


def hungarian_left(doc, keep=()):
    """把所有两格的表格行左右对调。keep：行里含这些文字的不动（例如左右是两方签字栏，不是两种语言）。
    返回对调的行数。"""
    n = 0
    for tbl in doc.element.body.iter(qn("w:tbl")):
        for tr in tbl.findall(qn("w:tr")):
            tcs = tr.findall(qn("w:tc"))
            if len(tcs) != 2:
                continue
            text = para_text(tr)
            if any(k in text for k in keep):
                continue
            left, right = tcs
            a, b = _content(left), _content(right)
            for el in a + b:
                el.getparent().remove(el)
            for el in b:
                left.append(el)
            for el in a:
                right.append(el)
            # 段前分页原来在左栏第一段（例如附件标题），换过去后要留在左栏第一段
            moved = [p for p in right.iter(qn("w:p")) if p.find(qn("w:pPr")) is not None
                     and p.find(qn("w:pPr")).find(qn("w:pageBreakBefore")) is not None]
            if moved:
                pbb = moved[0].find(qn("w:pPr")).find(qn("w:pageBreakBefore"))
                first = left.find(qn("w:p"))
                ppr = first.find(qn("w:pPr"))
                if ppr is None:
                    ppr = first.makeelement(qn("w:pPr"), {})
                    first.insert(0, ppr)
                pbb.getparent().remove(pbb)
                ppr.insert(0, pbb)
            n += 1
    return n


def flip_labels(doc, pairs):
    """「English / Magyar」这类标签改成「Magyar / English」。pairs: [(英语, 匈语)]，每对至少命中 1 处"""
    for en, hu in pairs:
        pattern = re.escape(en) + r"(\s*/\s*)" + re.escape(hu)
        n = sum(replace_in_paragraph(p, pattern, lambda m: hu + m.group(1) + en) for p in paragraphs(doc))
        if not n:
            raise ValueError(f"找不到标签「{en}/{hu}」")
