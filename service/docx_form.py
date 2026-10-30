"""
填写官方 Word 表单里的旧式表单域（FORMTEXT / FORMCHECKBOX）。

官方表单的域名大多重复，没法按名字找，所以按文档顺序编号（从 1 开始），
编号可用 tools/list_form_fields.py 查看。每次填写都要同时给出该位置旁边应有的文字，
对不上就报错。这样官方模板一旦换版，会立刻发现，而不是悄悄填错位置。
"""
import copy
import re

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def _norm(s):
    return re.sub(r"[ \s]+", " ", s).strip()


class FormDoc:
    def __init__(self, path):
        self.doc = Document(path)
        self.fields = []  # (kind, begin fldChar)
        for fc in self.doc.element.body.iter(qn("w:fldChar")):
            if fc.get(qn("w:fldCharType")) != "begin":
                continue
            ff = fc.find(qn("w:ffData"))
            if ff is not None:
                kind = "check" if ff.find(qn("w:checkBox")) is not None else "text"
                self.fields.append((kind, fc))
        self._labels = self._collect_labels()

    def _collect_labels(self):
        """文本域取前面的文字，勾选框取后面的文字（与 tools/list_form_fields.py 相同）。"""
        begins = {id(fc): i for i, (_, fc) in enumerate(self.fields)}
        before, after, text, last = [""] * len(self.fields), [""] * len(self.fields), "", None
        for el in self.doc.element.body.iter(qn("w:t"), qn("w:fldChar"), qn("w:p"), qn("w:tc")):
            if el.tag == qn("w:t"):
                text += el.text or ""
            elif el.tag == qn("w:fldChar"):
                i = begins.get(id(el))
                if i is not None:
                    before[i] = text
                    if last is not None:
                        after[last] = text
                    text, last = "", i
            else:
                text += " | "
        if last is not None:
            after[last] = text
        labels = []
        for i, (kind, _) in enumerate(self.fields):
            if kind == "check":
                s = after[i].split("|")[0]
            else:  # 往前找最近一段非空文字（说明文字可能在上一段）
                s = next((seg for seg in reversed(before[i].split("|")) if _norm(seg)), "")
            labels.append(_norm(s))
        return labels

    def _get(self, no, kind, expect):
        k, fc = self.fields[no - 1]
        if kind is not None and k != kind:
            raise ValueError(f"第 {no} 个域应为 {kind}，实际为 {k}")
        if expect is not None and expect not in self.labels(no):
            raise ValueError(f"第 {no} 个域旁边应为「{expect}」，实际为「{self.labels(no)}」")
        return fc

    def labels(self, no):
        return self._labels[no - 1]

    def check(self, no, expect, on=True):
        cb = self._get(no, "check", expect).find(qn("w:ffData")).find(qn("w:checkBox"))
        for old in cb.findall(qn("w:checked")):
            cb.remove(old)
        if on:
            cb.append(OxmlElement("w:checked"))

    def text(self, no, expect, value):
        run = self._get(no, "text", expect).getparent()
        ts, state, sib = [], None, run.getnext()
        while sib is not None:
            f = sib.find(qn("w:fldChar"))
            if f is not None and f.get(qn("w:fldCharType")) == "separate":
                state = "result"
            elif f is not None and f.get(qn("w:fldCharType")) == "end":
                break
            elif state == "result":
                ts += sib.findall(qn("w:t"))
            sib = sib.getnext()
        if not ts:
            raise ValueError(f"第 {no} 个域没有可写入的结果区")
        ts[0].text = "" if value is None else str(value)
        ts[0].set(XML_SPACE, "preserve")
        for t in ts[1:]:
            t.text = ""

    def append_after(self, no, expect, lines):
        """在某个域所在段落末尾追加几行文字（不是表单域）。lines: [(文字, 加粗, 字号pt)]"""
        para = self._get(no, None, expect)
        while para is not None and para.tag != qn("w:p"):
            para = para.getparent()
        template_rpr = None
        for r in para.findall(qn("w:r")):
            if r.find(qn("w:t")) is not None and r.find(qn("w:rPr")) is not None:
                template_rpr = r.find(qn("w:rPr"))
        for text, bold, size in lines:
            r = OxmlElement("w:r")
            rpr = copy.deepcopy(template_rpr) if template_rpr is not None else OxmlElement("w:rPr")
            for tag in ("w:b", "w:sz", "w:szCs"):
                for old in rpr.findall(qn(tag)):
                    rpr.remove(old)
            if bold:
                rpr.append(OxmlElement("w:b"))
            if size:
                for tag in ("w:sz", "w:szCs"):
                    el = OxmlElement(tag)
                    el.set(qn("w:val"), str(int(size * 2)))
                    rpr.append(el)
            r.append(rpr)
            r.append(OxmlElement("w:br"))
            t = OxmlElement("w:t")
            t.text = text
            t.set(XML_SPACE, "preserve")
            r.append(t)
            para.append(r)

    def snapshot(self):
        """所有已填写的域：{编号: 文字 或 True}，用于测试对比。"""
        out = {}
        for i, (kind, fc) in enumerate(self.fields, 1):
            if kind == "check":
                # 官方模板里未勾选的框可能带 <w:checked w:val="0"/>，要看值而不是看有没有
                c = fc.find(qn("w:ffData")).find(qn("w:checkBox")).find(qn("w:checked"))
                if c is not None and c.get(qn("w:val"), "1") not in ("0", "false"):
                    out[str(i)] = True
            else:
                run, state, value, sib = fc.getparent(), None, "", fc.getparent().getnext()
                while sib is not None:
                    f = sib.find(qn("w:fldChar"))
                    if f is not None and f.get(qn("w:fldCharType")) == "separate":
                        state = "result"
                    elif f is not None and f.get(qn("w:fldCharType")) == "end":
                        break
                    elif state == "result":
                        value += "".join(t.text or "" for t in sib.findall(qn("w:t")))
                    sib = sib.getnext()
                if value.strip("  "):
                    out[str(i)] = value
        return out

    def save(self, path):
        self.doc.save(path)
