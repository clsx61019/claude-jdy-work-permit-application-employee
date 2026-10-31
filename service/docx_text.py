"""
填写普通 Word 文档（不是表单域）：把段落里的 {{名字}} 换成内容。

Word 常把一段文字拆成好几个 run（拼写检查、格式变化都会拆），占位符可能横跨几个 run。
这里按整段文字找，替换后的内容放进占位符开头所在的 run，沿用那里的格式。
"""
import re

from docx import Document
from docx.oxml.ns import qn

TOKEN = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def paragraphs(doc):
    """正文、表格、页眉页脚里的所有段落（w:p 元素）"""
    parts = [doc.element.body]
    for s in doc.sections:
        parts += [s.header._element, s.footer._element]
    for part in parts:
        yield from part.iter(qn("w:p"))


def _texts(p):
    return [t for t in p.iter(qn("w:t"))]


def para_text(p):
    return "".join(t.text or "" for t in _texts(p))


def replace_in_paragraph(p, pattern, repl):
    """在一段里按正则替换，可横跨多个 run。repl: match -> 字符串。返回替换次数。"""
    ts = _texts(p)
    full = "".join(t.text or "" for t in ts)
    matches = list(re.finditer(pattern, full))
    if not matches:
        return 0
    # 每个字符属于哪个 w:t
    owner, offset = [], []
    for i, t in enumerate(ts):
        for j in range(len(t.text or "")):
            owner.append(i)
            offset.append(j)
    texts = [t.text or "" for t in ts]
    for m in reversed(matches):
        s, e = m.start(), m.end()
        a, b = owner[s], owner[e - 1]
        value = repl(m)
        if a == b:
            texts[a] = texts[a][:offset[s]] + value + texts[a][offset[e - 1] + 1:]
        else:
            texts[a] = texts[a][:offset[s]] + value
            for k in range(a + 1, b):
                texts[k] = ""
            texts[b] = texts[b][offset[e - 1] + 1:]
    for t, v in zip(ts, texts):
        t.text = v
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    return len(matches)


class TextDoc:
    """普通 Word 模板：fill(values) 替换所有 {{名字}}；缺值报错，避免漏填。"""

    def __init__(self, path):
        self.doc = Document(path)

    def fill(self, values):
        missing = set()

        def repl(m):
            if m.group(1) not in values:
                missing.add(m.group(1))
                return m.group(0)
            v = values[m.group(1)]
            return "" if v is None else str(v)

        for p in paragraphs(self.doc):
            replace_in_paragraph(p, TOKEN, repl)
        if missing:
            raise ValueError(f"模板里有没提供值的占位符：{', '.join(sorted(missing))}")

    def remove_rows(self, contains):
        """删除第一列含某段文字的表格行（例如不适用的条款，左右两栏一起删）"""
        n = 0
        for tr in list(self.doc.element.body.iter(qn("w:tr"))):
            tcs = tr.findall(qn("w:tc"))
            if tcs and contains in "".join(para_text(p) for p in tcs[0].iter(qn("w:p"))):
                tr.getparent().remove(tr)
                n += 1
        if not n:
            raise ValueError(f"找不到含「{contains}」的表格行，模板可能改过")

    def remove_paragraphs(self, contains):
        """删除含某段文字的段落（例如不适用时的整段说明）"""
        ps = [p for p in paragraphs(self.doc) if contains in para_text(p)]
        if not ps:
            raise ValueError(f"找不到含「{contains}」的段落，模板可能改过")
        for p in ps:
            p.getparent().remove(p)

    def labels(self, no):
        return ""

    def snapshot(self):
        """所有非空段落的文字：{序号: 文字}，用于测试对比。"""
        out, i = {}, 0
        for p in paragraphs(self.doc):
            t = para_text(p).strip()
            if t:
                i += 1
                out[str(i)] = t
        return out

    def save(self, path):
        self.doc.save(path)
