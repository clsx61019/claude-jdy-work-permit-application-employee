"""
9.8. Betétlap（匈牙利卡 Magyar Kártya）—— 规则见 docs/rules/09_8-匈牙利卡附件.md

官方匈牙利语 Word 表单，按编号填写，并校验旁边的文字。
版面和 9.6 几乎一样（只多了「居留目的」，学历多了大专、大学），规则全部沿用 9.6 已确认的决定。
很多格子由几个连续的空域拼成，只填第一个，其余留空。
"""
from ..model import COMPANY, EMPLOYERS, hu_date, hu_money

TEMPLATE = "09_8_Magyar_Kartya_HU.docx"

# 学历 -> 勾选框（9.8 有大专、大学，同 9.10）
EDUCATION = {
    "Primary School 小学": 64,
    "Specialised School 专业学校": 65,
    "Vocational School 职业学校": 66,
    "Secondary Grammar School 普通高中": 67,
    "Vocational Secondary School 中等职业学校": 68,
    "Technician Education Establishment 技术教育机构": 69,
    "College 学院 / 大专": 70,
    "University 大学": 71,
    "Finished Less Than 8 School Years In Primary School 未完成小学8个学年": 72,
}
EDUCATION_LABELS = {64: "általános iskola", 65: "szakiskola", 66: "szakmunkásképző", 67: "gimnázium",
                    68: "szakközépiskola", 69: "technikum", 70: "főiskola", 71: "egyetem",
                    72: "8 általánosnál kevesebb"}

PURPOSE_LABELS = {9: "szakképesítést igénylő munkakörben", 10: "hivatásos sportolóként",
                  11: "előadóművészként", 12: "mozgókép törvény"}

BORSODCHEM = "BorsodChem Zrt."
BC_SITE = "3700 Kazincbarcika, Bolyai tér 1."


def fill(f, p):
    def yes_no(yes_no_nos, yes):
        y, n = yes_no_nos
        f.check(y, "igen", yes)
        f.check(n, "nem", not yes)

    emp = p.employer_info
    is_bc = p.employer == BORSODCHEM

    # 页眉：只有电话、邮箱（同 9.6）
    f.text(1, "Telefonszám", COMPANY["contact_phone"])
    f.text(5, "E-mail cím", COMPANY["contact_email"])

    # 1. 居留目的：需要高等教育部门规定资格的岗位（同旧模板）
    for no, label in PURPOSE_LABELS.items():
        f.check(no, label, no == 9)

    # 2. 就业依据：与匈牙利雇主的劳动关系（同 9.6 Q2）
    f.check(13, "belföldi foglalkoztatóval fennálló munkaviszony")
    f.check(14, "megállapodás teljesítése érdekében", False)

    # 3. 生活来源：工资，福林不要小数；上一年度在匈纳税收入暂时留空（同 9.6 Q4）
    f.text(25, None, f"HUF {hu_money(p.salary)}" if p.salary != "" else "")

    # 4. 匈牙利雇主
    f.text(37, "név", p.employer)
    f.text(39, "irányítószám", emp.zip)
    f.text(40, "település", emp.city)
    f.text(44, "közterület neve", emp.street)
    f.text(48, "közterület jellege", emp.street_type)
    f.text(49, "házszám", emp.house_no)
    f.text(57, "adószáma", emp.tax_no)
    f.text(59, "KSH-szám", emp.ksh)
    f.text(61, "TEÁOR száma", emp.teaor)

    # 5、6、7
    f.text(63, None, p.qualification_hu)
    box = EDUCATION.get(p.education)
    for no, label in EDUCATION_LABELS.items():
        f.check(no, label, no == box)
    f.text(73, None, p.prev_position_hu)

    # 8. 工作地点（同 9.5 / 9.6 / 9.10）
    yes_no((75, 76), not is_bc)
    if not is_bc:
        f.text(77, "címe(i)", emp.workplace_hu)
    yes_no((88, 89), is_bc)
    if is_bc:
        f.text(90, "munkavégzés megkezdésének helye", BC_SITE)
    yes_no((95, 96), is_bc)

    # 9. 预协议日期
    d = p.sign_date
    f.text(97, None, f"{d:%Y}" if d else "")
    f.text(98, "év", f"{d:%m}" if d else "")
    f.text(99, "hó", f"{d:%d}" if d else "")

    # 10. 岗位（同 9.10 Q5）
    feor = f" (FEOR: {p.feor})" if p.feor != "" else ""
    f.text(100, None, f"{p.job_title_hu}{feor}")

    # 11. 技能（专业经验年限留空）
    f.text(106, "speciális ismerete", p.special_skills)
    f.text(109, "Anyanyelve", p.native_language)
    f.text(112, "Egyéb nyelvismerete", p.other_languages)
    f.check(113, "igen", False)
    f.check(114, "nem", True)

    # 之前在匈牙利工作（同 9.6 Q3）
    second = p.second_entry == "Yes 是"
    renewing = p.app_type in ("extension", "change")
    worked = second or renewing
    f.check(115, "igen", worked)
    f.check(116, "nem", not worked)
    if worked:
        f.text(117, "érvényességi ideje", hu_date(p.prev_permit_expiry))
        if renewing:
            name, addr = p.employer, emp.address
        else:
            name, addr = BORSODCHEM, EMPLOYERS[BORSODCHEM]["address"]
        f.text(123, "Neve", name)
        f.text(126, "Címe", addr)

    # 12、13. 豁免：都勾「Nem」（同 9.6）
    f.check(129, "Igen", False)
    f.check(131, "Nem", True)
    f.check(132, "Igen", False)
    f.check(134, "Nem", True)
    # 14. 免劳动力市场审查（同 9.6）：BorsodChem → Igen，第 3 点；其他雇主 → Nem
    f.check(135, "Igen", is_bc)
    f.text(136, None, COMPANY["labour_market_exemption_point"] if is_bc else "")
    f.check(137, "Nem", not is_bc)
