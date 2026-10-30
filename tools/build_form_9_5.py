"""
一次性工具：把负责人在简道云里做的 9.5 匈牙利语 Word 模板，重建成"干净的官方表单"。

背景：官方只提供 9.5 的英语 Word（旧版，没有 5/A、5/B）和匈牙利语 PDF（公报打印件，
没有文字层）。负责人的匈牙利语 Word 的固定文字已用 OCR 与 2025 年官方匈牙利语 PDF 比对，一致。

重建内容：
- 去掉简道云占位符和写死的公司数据，在需要填写的位置放 Word 表单域（有名字）
- ☐/☒ 字符换成 Word 原生勾选框
- 被公式代替的官方选项恢复成固定文字（学历 7 项、igen/nem、Neve/Címe 等）
- 去掉黄色高亮

用法: python tools/build_form_9_5.py <简道云 9.5 模板.docx> templates/hu/09_5_Betetlap_HU.docx
"""
import copy
import re
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
EMPTY = " " * 5  # Word 表单域默认显示的空白


def T(name):
    return ("T", name)


def C(name):
    return ("C", name)


NL, TAB = "\n", "\t"


def _run(rpr, *children):
    r = OxmlElement("w:r")
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    for c in children:
        r.append(c)
    return r


def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), v)
    return e


def _text(s):
    t = _el("w:t")
    t.text = s
    t.set(XML_SPACE, "preserve")
    return t


def _field_runs(kind, name, rpr):
    ff = _el("w:ffData")
    ff.append(_el("w:name", **{"w:val": name}))
    ff.append(_el("w:enabled"))
    ff.append(_el("w:calcOnExit", **{"w:val": "0"}))
    if kind == "C":
        cb = _el("w:checkBox")
        cb.append(_el("w:sizeAuto"))
        cb.append(_el("w:default", **{"w:val": "0"}))
        ff.append(cb)
    else:
        ff.append(_el("w:textInput"))
    begin = _el("w:fldChar", **{"w:fldCharType": "begin"})
    begin.append(ff)
    instr = _el("w:instrText")
    instr.text = " FORMCHECKBOX " if kind == "C" else " FORMTEXT "
    instr.set(XML_SPACE, "preserve")
    runs = [_run(rpr, begin), _run(rpr, instr)]
    if kind == "T":
        runs += [_run(rpr, _el("w:fldChar", **{"w:fldCharType": "separate"})), _run(rpr, _text(EMPTY))]
    runs.append(_run(rpr, _el("w:fldChar", **{"w:fldCharType": "end"})))
    return runs


def _rpr_without(rpr, *tags):
    rpr = copy.deepcopy(rpr) if rpr is not None else OxmlElement("w:rPr")
    for tag in tags:
        for e in rpr.findall(qn(tag)):
            rpr.remove(e)
    return rpr


def _ptext(p):
    return "".join(t.text or "" for t in p.iter(qn("w:t")))


class Builder:
    def __init__(self, path):
        self.doc = Document(path)
        self.ps = list(self.doc.element.body.iter(qn("w:p")))
        self.names = set()
        self.to_delete = []

    def p(self, i, expect):
        p = self.ps[i]
        if expect not in _ptext(p):
            raise ValueError(f"第 {i} 段应包含「{expect}」，实际为「{_ptext(p)}」")
        return p

    def put(self, i, expect, segments, cut=None, bold=None):
        """在第 i 段写入 segments。
        cut=None 清空整段；cut=True 保留整段；cut 是字符串时，保留它之前的文字。"""
        p = self.p(i, expect)
        runs = p.findall(qn("w:r"))
        rpr = next((r.find(qn("w:rPr")) for r in runs if r.find(qn("w:rPr")) is not None), None)
        text = _ptext(p)
        kept_len = 0 if cut is None else len(text) if cut is True else text.index(cut)
        pos = 0
        for r in runs:  # 截断：保留前 kept_len 个字符
            ts = r.findall(qn("w:t"))
            s = "".join(t.text or "" for t in ts)
            if pos >= kept_len:
                p.remove(r)
            elif pos + len(s) > kept_len:
                ts[0].text = s[: kept_len - pos]
                ts[0].set(XML_SPACE, "preserve")
                for t in ts[1:]:
                    r.remove(t)
                for br in r.findall(qn("w:br")):
                    r.remove(br)
            pos += len(s)
        base = _rpr_without(rpr, "w:highlight")
        if bold is False:
            base = _rpr_without(base, "w:b", "w:bCs")
        for seg in segments:
            if isinstance(seg, tuple):
                kind, name = seg
                if name in self.names:
                    raise ValueError(f"域名重复：{name}")
                self.names.add(name)
                for r in _field_runs(kind, name, base):
                    p.append(r)
            elif seg == NL:
                p.append(_run(base, _el("w:br")))
            elif seg == TAB:
                p.append(_run(base, _el("w:tab")))
            else:
                p.append(_run(base, _text(seg)))

    def append(self, i, expect, segments):
        """保留整段原文（含下划线等格式），在末尾追加。"""
        self.put(i, expect, segments, cut=True, bold=False)

    def delete(self, i, expect):
        self.to_delete.append(self.p(i, expect))

    def save(self, path):
        for p in self.to_delete:
            p.getparent().remove(p)
        for hl in list(self.doc.element.body.iter(qn("w:highlight"))):
            hl.getparent().remove(hl)
        self.doc.save(path)


def yes_no(prefix):
    return [C(f"{prefix}_igen"), " igen   ", C(f"{prefix}_nem"), " nem"]


def date(prefix):
    return [T(f"{prefix}_ev"), " év  ", T(f"{prefix}_ho"), " hó  ", T(f"{prefix}_nap"), " nap"]


def build(src, dst):
    b = Builder(src)

    # 页眉
    b.put(6, "${", [C("benyujt_ugyfel"), " ügyfél által", NL, C("benyujt_foglalk"), " foglalkoztató által"], bold=False)
    b.delete(10, "3700 Kazincbarcika")                       # 写死的地址，改由规则决定
    b.put(12, "3700 Kazincbarcika", [T("kapcs_cim")])
    b.put(14, "${", [T("szekhely")])
    b.put(16, "Telefonszám", [T("telefon")], cut="+36")
    b.put(18, "E-mail cím", [T("email")], cut="renata")
    b.put(20, "ország", ["ország: ", T("vizum_orszag"), TAB, TAB, "város: ", T("vizum_varos")])

    # 1. 生活来源
    b.put(23, "${", [T("jov_varhato")])
    b.put(26, "", [T("jov_elozo_evi")])
    b.put(28, "", [T("megtakaritas")])
    b.put(31, "", [T("egyeb_jov")])

    # 2. 住处
    b.put(35, "138", [T("szallas_fo")])
    b.put(37, "igen", yes_no("szallas_elkul"), bold=False)
    b.put(39, ",", [T("szallas_eng_kiallito"), ", ", T("szallas_eng_szam"), ", "])
    b.put(40, "év", [TAB] + date("szallas_eng"))

    # 3. 雇主
    b.put(43, "név", [T("munkaltato_nev")], cut="${")
    b.put(46, "${", [T("munkaltato_irsz")])
    b.put(48, "${", [T("munkaltato_telepules")])
    b.put(50, "${", [T("munkaltato_kozter")])
    b.put(51, "közterület jellege", [T("munkaltato_jelleg")], cut="${")
    b.put(52, "házszám", [T("munkaltato_hazszam")], cut="${")
    b.put(53, "épület", ["épület: ", T("munkaltato_epulet")])
    b.put(54, "lépcsőház", ["lépcsőház: ", T("munkaltato_lepcsohaz")])
    b.put(55, "emelet", ["emelet: ", T("munkaltato_emelet")])
    b.put(56, "ajtó", ["ajtó: ", T("munkaltato_ajto")])
    b.put(57, "adószáma", [T("munkaltato_adoszam")], cut="${")
    b.put(58, "KSH-szám", [T("munkaltato_ksh")], cut="${")
    b.put(59, "TEÁOR", [T("munkaltato_teaor")], cut="${")

    # 4、5
    b.put(61, "igen", yes_no("miniszter_megall"), bold=False)
    b.put(63, "NGM", [T("csop_jovahagyas_a")])
    b.put(65, "", [T("csop_jovahagyas_b")])

    # 6、7、8
    b.put(68, "${", [T("szakkepzettseg")])
    edu = [
        NL, C("isk_altalanos"), " általános iskola", TAB, C("isk_szakiskola"), " szakiskola",
        NL, C("isk_szakmunkas"), " szakmunkásképző", TAB, C("isk_gimnazium"), " gimnázium",
        NL, C("isk_szakkozep"), " szakközépiskola", TAB, C("isk_technikum"), " technikum",
        NL, NL, C("isk_8_alatt"), " 8 általánosnál kevesebb",
    ]
    b.put(69, "Iskolai végzettsége", edu, cut="${", bold=False)
    b.put(72, "${", [T("elozo_foglalkozas")])

    # 9. 工作地点
    b.put(75, "${", yes_no("egy_hely") + [NL, NL, "cím(e)i: ", T("egy_hely_cim")], bold=False)
    b.put(77, "${", yes_no("tobb_megye") + [NL, NL, "Ha igen, a munkavégzés megkezdésének helye (címe):", NL,
                                             T("tobb_megye_cim")], bold=False)
    b.put(80, "${", yes_no("tobb_telephely"), bold=False)

    # 10、11
    b.put(83, "${", date("megall_kelte"))
    b.put(85, "${", [T("munkakor")])
    b.put(86, "FEOR", [T("feor")], cut="${")

    # 12. 技能
    b.append(88, "gyakorlati ideje", [" ", T("gyakorlat_ideje")])
    b.put(89, "speciális ismerete", [T("specialis_ismeret")], cut="${")
    b.put(91, "Anyanyelve", [T("anyanyelv")], cut="kínai")
    b.put(92, "Egyéb nyelvismerete", [T("egyeb_nyelv")], cut="angol")
    b.put(93, "Beszél magyarul", yes_no("magyarul"), cut="☐", bold=False)
    b.put(94, "Korábban dolgozott", yes_no("korabban_mo"), cut="${", bold=False)
    b.put(95, "érvényességi ideje", date("elozo_eng"), cut="${")
    b.put(97, "${", ["Neve: ", T("elozo_foglalk_nev"), NL, "Címe: ", T("elozo_foglalk_cim")], bold=False)

    b.save(dst)
    print(f"已生成 {dst}，共 {len(b.names)} 个表单域")


if __name__ == "__main__":
    build(*sys.argv[1:3])
