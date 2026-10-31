"""劳动合同 Ordinary（with CBA，普通员工）—— 规则见 docs/rules/劳动合同.md，逻辑在 labour_contract.py"""
from . import labour_contract as lc

DOC = lc.DOC
TEMPLATE = "../hu/labour_contract_ordinary.docx"


def fill(doc, p):
    lc.fill(doc, p, executive=False)
