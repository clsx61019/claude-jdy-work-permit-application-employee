"""
9.6. Betétlap（就业 Foglalkoztatás）—— 规则见 docs/rules/09_6-就业附件.md

官方匈牙利语 Word 表单，按编号填写，并校验旁边的文字。
很多格子由几个连续的空域拼成（例如电话 #2#3#4），只填第一个，其余留空。
与 9.5 / 9.10 相同的规则（雇主、学历、工作地点、语言、前任雇主等）沿用已确认的决定。
"""
from ..model import COMPANY, EMPLOYERS, hu_date, hu_money

TEMPLATE = "09_6_Foglalkoztatas_HU.docx"

# 学历 -> 勾选框（同 9.5 Q7：9.6 没有大专、大学选项，都不勾）
EDUCATION = {
    "Primary School 小学": 60,
    "Specialised School 专业学校": 61,
    "Vocational School 职业学校": 62,
    "Secondary Grammar School 普通高中": 63,
    "Vocational Secondary School 中等职业学校": 64,
    "Technician Education Establishment 技术教育机构": 65,
    "Finished Less Than 8 School Years In Primary School 未完成小学8个学年": 66,
}
EDUCATION_LABELS = {60: "általános iskola", 61: "szakiskola", 62: "szakmunkásképző", 63: "gimnázium",
                    64: "szakközépiskola", 65: "technikum", 66: "8 általánosnál kevesebb"}

BORSODCHEM = "BorsodChem Zrt."
BC_SITE = "3700 Kazincbarcika, Bolyai tér 1."


def fill(f, p):
    def yes_no(yes_no_nos, yes):
        y, n = yes_no_nos
        f.check(y, "igen", yes)
        f.check(n, "nem", not yes)

    emp = p.employer_info

    # 页眉：证件领取方式（Q1：邮寄，同旧模板；电话、邮箱用公司联系人）
    f.check(1, "kiállító hatóságnál", False)
    f.check(5, "postai úton")
    f.text(2, "Telefonszám", COMPANY["contact_phone"])
    f.text(6, "E-mail cím", COMPANY["contact_email"])

    # 1. 就业依据（Q2：与匈牙利雇主的劳动关系）
    f.check(9, "belföldi foglalkoztatóval fennálló munkaviszony")
    f.check(10, "megállapodás teljesítése érdekében", False)

    # 2. 生活来源：工资，福林不要小数（同 9.5）；上一年度在匈纳税收入见 Q4
    f.text(21, "munkaviszonyból származó várható jövedelem", f"HUF {hu_money(p.salary)}" if p.salary != "" else "")

    # 3. 匈牙利雇主
    f.text(33, "név", p.employer)
    f.text(35, "irányítószám", emp.zip)
    f.text(37, "település", emp.city)
    f.text(41, "közterület neve", emp.street)
    f.text(45, "közterület jellege", emp.street_type)
    f.text(46, "házszám", emp.house_no)
    f.text(53, "adószáma", emp.tax_no)
    f.text(55, "KSH-szám", emp.ksh)
    f.text(57, "TEÁOR száma", emp.teaor)

    # 4、5、6
    f.text(59, None, p.qualification_hu)
    box = EDUCATION.get(p.education)
    for no, label in EDUCATION_LABELS.items():
        f.check(no, label, no == box)
    f.text(67, None, p.prev_position_hu)

    # 7. 工作地点（同 9.5 / 9.10）
    is_bc = p.employer == BORSODCHEM
    yes_no((69, 70), not is_bc)
    if not is_bc:
        f.text(71, "címe(i)", emp.workplace_hu)
    yes_no((82, 83), is_bc)
    if is_bc:
        f.text(84, "munkavégzés megkezdésének helye", BC_SITE)
    yes_no((85, 86), is_bc)

    # 8. 预协议日期（同 9.5）
    d = p.sign_date
    f.text(87, None, f"{d:%Y}" if d else "")
    f.text(88, "év", f"{d:%m}" if d else "")
    f.text(89, "hó", f"{d:%d}" if d else "")

    # 9. 岗位（同 9.10 Q5：一个格子写岗位和 FEOR）
    feor = f" (FEOR: {p.feor})" if p.feor != "" else ""
    f.text(90, None, f"{p.job_title_hu}{feor}")

    # 10. 技能（专业经验年限留空，同 9.5 Q11）
    f.text(96, "speciális ismerete", p.special_skills)
    f.text(99, "Anyanyelve", p.native_language)
    f.text(102, "Egyéb nyelvismerete", p.other_languages)
    f.check(103, "igen", False)
    f.check(104, "nem", True)

    # 之前在匈牙利工作（Q3）
    second = p.second_entry == "Yes 是"
    renewing = p.app_type in ("extension", "change")
    worked = second or renewing
    f.check(105, "igen", worked)
    f.check(106, "nem", not worked)
    if worked:
        f.text(107, "érvényességi ideje", hu_date(p.prev_permit_expiry))
        if renewing:  # 延期 / 变更：之前的雇主就是现在的雇主
            name, addr = p.employer, emp.address
        else:         # 二次入职只有万华员工，前任雇主一定是 BC（同 9.5 Q13）
            name, addr = BORSODCHEM, EMPLOYERS[BORSODCHEM]["address"]
        f.text(113, "Neve", name)
        f.text(116, "Címe", addr)

    # 11、12. 豁免：都勾「Nem」（Q5，同旧模板）
    f.check(119, "Igen", False)
    f.check(121, "Nem", True)
    f.check(122, "Igen", False)
    f.check(124, "Nem", True)
    # 13. 免劳动力市场审查（Q5，同旧模板）：BorsodChem → Igen，第 3 点（445/2013 第 9 条第 (1) 款第 3 点：外资控股公司）；其他雇主 → Nem
    f.check(125, "Igen", is_bc)
    f.text(126, None, COMPANY["labour_market_exemption_point"] if is_bc else "")
    f.check(127, "Nem", not is_bc)
