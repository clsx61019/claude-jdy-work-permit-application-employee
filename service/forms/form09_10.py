"""
9.10. Betétlap（公司内部调动 ICT）—— 规则见 docs/rules/09_10-ICT附件.md

官方匈牙利语 Word 表单，按编号填写，并校验旁边的文字。
与 9.5 相同的规则（递交方、签证领取地、工作地点、语言、前任雇主等）沿用 9.5 的决定。
"""
from ..model import COMPANY, EMPLOYERS, SENDING_COMPANIES, hu_date, hu_money_cents, hu_since

TEMPLATE = "09_10_Betetlap_ICT_HU.docx"

POSITION = {"Manager 经理": 99, "Expert 专家": 100, "Intern 实习生": 101}

EDUCATION = {  # 9.10 有大专、大学选项
    "Primary School 小学": 108,
    "Specialised School 专业学校": 109,
    "Vocational School 职业学校": 110,
    "Vocational Secondary School 中等职业学校": 111,
    "Secondary Grammar School 普通高中": 112,
    "Technician Education Establishment 技术教育机构": 113,
    "College 学院 / 大专": 114,
    "University 大学": 115,
    "Finished Less Than 8 School Years In Primary School 未完成小学8个学年": 116,
}
EDUCATION_LABELS = {108: "általános iskola", 109: "szakiskola", 110: "szakmunkásképző", 111: "szakközépiskola",
                    112: "gimnázium", 113: "technikum", 114: "főiskola", 115: "egyetem",
                    116: "8 általánosnál kevesebb"}

BORSODCHEM = "BorsodChem Zrt."
BC_SITE_ZIP, BC_SITE = "3700", "Kazincbarcika, Bolyai tér 1."


def fill(f, p):
    def yes_no(yes_no_nos, yes):
        y, n = yes_no_nos
        f.check(y, "igen", yes)
        f.check(n, "nem", not yes)

    emp = p.employer_info
    by_employer = p.submitted_by_employer

    # 页眉
    f.check(1, "Vállalaton belüli áthelyezés célú")
    f.check(3, "ügyfél által", not by_employer)
    f.check(4, "foglalkoztató által", by_employer)
    if by_employer:
        f.text(5, "kapcsolattartási címe", COMPANY["delivery_address"])
        f.text(9, "foglalkoztató székhelye", emp.address)
        f.text(13, "ország", COMPANY["visa_pickup_country"])
        f.text(17, "város", COMPANY["visa_pickup_city"])
    f.text(22, "Telefonszám", COMPANY["contact_phone"])
    f.text(26, "E-mail cím", COMPANY["contact_email"])

    # 1. 生活来源（Q1：原派出公司工资，CNY，保留两位小数；不换行空格让币种和金额不分开）
    salary = f"CNY\u00a0{hu_money_cents(p.sending_salary)}" if p.sending_salary != "" else ""
    f.text(30, "várható jövedelem összege", salary)

    # 2. 匈牙利接收单位 = 雇主（Q2）
    f.text(46, "név", p.employer)
    f.text(57, "irányítószám", emp.zip)
    f.text(58, "település", emp.city)
    f.text(61, "közterület neve", emp.street)
    f.text(64, "közterület jellege", emp.street_type)
    f.text(65, "házszám", emp.house_no)
    f.text(70, "adóazonosító jele", emp.tax_no)
    f.text(76, "KSH-szám", emp.ksh)
    f.text(82, "TEÁOR száma", emp.teaor)

    # 3. 第三国派出公司
    f.text(88, "név", p.sending_company)
    f.text(93, "Székhely (ország, város)", SENDING_COMPANIES.get(p.sending_company, ""))

    # 4. 岗位类型
    for label, no in POSITION.items():
        f.check(no, ["Vezető", "Szakértő", "Gyakornok"][no - 99], p.ict_position == label)

    # 5. 在欧盟的停留（Q3）
    period = f"{hu_date(p.contract_start)} – {hu_date(p.contract_end)}" if p.contract_end else ""
    f.text(102, "Első tagállam", f"Magyarország, {period}" if period else "Magyarország")

    # 6、7、8、9、10
    f.text(105, "szakképzettsége", p.qualification_hu)
    box = EDUCATION.get(p.education)
    for no, label in EDUCATION_LABELS.items():
        f.check(no, label, no == box)
    f.text(117, "érkezést megelőző foglalkozása", p.prev_position_hu)
    f.text(122, "munkaviszony időtartama", hu_since(p.sending_start))          # Q4
    feor = f" (FEOR: {p.feor})" if p.feor != "" else ""
    f.text(127, "Munkakör (FEOR szám)", f"{p.job_title_hu}{feor}")

    # 11. 工作地点（与 9.5 相同：用辅助表的工作地点）
    is_bc = p.employer == BORSODCHEM
    yes_no((130, 131), not is_bc)
    if not is_bc and emp.workplace_hu:
        zip_, _, addr = emp.workplace_hu.partition(" ")
        f.text(132, "irányítószám", zip_)
        f.text(133, "cím", addr)
    yes_no((137, 138), is_bc)
    if is_bc:
        f.text(139, "irányítószám", BC_SITE_ZIP)
        f.text(140, "cím", BC_SITE)
    yes_no((145, 146), is_bc)

    # 12. 技能
    f.text(150, "speciális ismerete", p.special_skills)
    f.text(153, "Anyanyelve", p.native_language)
    f.text(156, "Egyéb nyelvismerete", COMPANY["other_language"])
    yes_no((159, 160), False)
    second = p.second_entry == "Yes 是"
    yes_no((161, 162), second)
    if second:
        f.text(163, "előző magyarországi foglalkoztatója", f"{BORSODCHEM}, {EMPLOYERS[BORSODCHEM]['address']}")
