"""
9.9. Betétlap（欧盟蓝卡 EU Kék Kártya）—— 规则见 docs/rules/09_9-欧盟蓝卡附件.md

官方匈牙利语 Word 表单，按编号填写，并校验旁边的文字。
页眉（递交方、雇主递交时的领取方式、签证领取地）沿用 9.5 / 9.10 的决定；
其余部分沿用 9.6 / 9.8 的决定。很多格子由几个连续的空域拼成，只填第一个，其余留空。
"""
from ..model import COMPANY, EMPLOYERS, hu_date, hu_money

TEMPLATE = "09_9_EU_Kek_Kartya_HU.docx"

EDUCATION = {  # 有大专、大学（同 9.8 / 9.10）
    "Primary School 小学": 86,
    "Specialised School 专业学校": 87,
    "Vocational School 职业学校": 88,
    "Secondary Grammar School 普通高中": 89,
    "Vocational Secondary School 中等职业学校": 90,
    "Technician Education Establishment 技术教育机构": 91,
    "College 学院 / 大专": 92,
    "University 大学": 93,
    "Finished Less Than 8 School Years In Primary School 未完成小学8个学年": 94,
}
EDUCATION_LABELS = {86: "általános iskola", 87: "szakiskola", 88: "szakmunkásképző", 89: "gimnázium",
                    90: "szakközépiskola", 91: "technikum", 92: "főiskola", 93: "egyetem",
                    94: "8 általánosnál kevesebb"}

BORSODCHEM = "BorsodChem Zrt."
BC_SITE = "3700 Kazincbarcika, Bolyai tér 1."


def fill(f, p):
    def yes_no(yes_no_nos, yes):
        y, n = yes_no_nos
        f.check(y, "igen", yes)
        f.check(n, "nem", not yes)

    def ymd(nos, d):
        y, m, dd = nos
        f.text(y, None, f"{d:%Y}" if d else "")
        f.text(m, "év", f"{d:%m}" if d else "")
        f.text(dd, "hó", f"{d:%d}" if d else "")

    emp = p.employer_info
    is_bc = p.employer == BORSODCHEM
    by_employer = p.submitted_by_employer

    # 页眉（同 9.5 / 9.10）
    f.check(1, "ügyfél által", not by_employer)
    f.check(2, "foglalkoztató által", by_employer)
    if by_employer:
        f.text(3, None, COMPANY["delivery_address"])
        f.text(7, None, emp.address)
        f.text(11, "ország", COMPANY["visa_pickup_country"])
        f.text(15, "város", COMPANY["visa_pickup_city"])
    f.text(20, "Telefonszám", COMPANY["contact_phone"])
    f.text(24, "E-mail cím", COMPANY["contact_email"])

    # 1. 生活来源：工资，福林不要小数；上一年度在匈纳税收入暂时留空（同 9.6 Q4）
    f.text(28, None, f"HUF {hu_money(p.salary)}" if p.salary != "" else "")

    # 2. 匈牙利雇主
    f.text(44, "név", p.employer)
    f.text(59, "irányítószám", emp.zip)
    f.text(61, "település", emp.city)
    f.text(66, "közterület neve", emp.street)
    f.text(70, None, emp.street_type)
    f.text(72, None, emp.house_no)
    f.text(82, "adóazonosító jele", emp.tax_no)
    f.text(83, None, emp.ksh)
    f.text(84, None, emp.teaor)

    # 3、4、5
    f.text(85, None, p.qualification_hu)
    box = EDUCATION.get(p.education)
    for no, label in EDUCATION_LABELS.items():
        f.check(no, label, no == box)
    f.text(95, None, p.prev_position_hu)

    # 6. 工作地点（同 9.5 / 9.6 / 9.8 / 9.10）
    yes_no((96, 97), not is_bc)
    if not is_bc:
        f.text(98, "Címe(i)", emp.workplace_hu)
    yes_no((109, 110), is_bc)
    if is_bc:
        f.text(111, "munkavégzés megkezdésének helye", BC_SITE)
    yes_no((115, 116), is_bc)

    # 7. 预协议日期；8. 岗位（同 9.10 Q5）
    ymd((117, 118, 119), p.sign_date)
    feor = f" (FEOR: {p.feor})" if p.feor != "" else ""
    f.text(120, "Munkakör (FEOR szám)", f"{p.job_title_hu}{feor}")

    # 9. 技能（专业经验年限留空）
    f.text(124, "speciális ismerete", p.special_skills)
    f.text(127, "Anyanyelve", p.native_language)
    f.text(129, "Egyéb nyelvismerete", COMPANY["other_language"])
    f.check(131, "igen", False)
    f.check(132, "nem", True)

    # 10. 之前在匈牙利工作（同 9.6 Q3）；有效期分年 / 月 / 日，前任雇主名称和地址写在一格
    second = p.second_entry == "Yes 是"
    renewing = p.app_type in ("extension", "change")
    worked = second or renewing
    f.check(133, "igen", worked)
    f.check(134, "nem", not worked)
    if worked:
        ymd((135, 136, 137), p.prev_permit_expiry)
        if renewing:
            name, addr = p.employer, emp.address
        else:
            name, addr = BORSODCHEM, EMPLOYERS[BORSODCHEM]["address"]
        f.text(138, "foglalkoztatójának neve, címe", f"{name}, {addr}")

    # 11、12. 豁免：都勾「Nem」（同 9.6）
    f.check(148, "Igen", False)
    f.check(150, "Nem", True)
    f.check(151, "Igen", False)
    f.check(153, "Nem", True)
    # 14. 免劳动力市场审查（同 9.6）：BorsodChem → Igen，第 3 点；其他雇主 → Nem
    f.check(154, "Igen", is_bc)
    f.text(155, None, COMPANY["labour_market_exemption_point"] if is_bc else "")
    f.check(156, "Nem", not is_bc)
