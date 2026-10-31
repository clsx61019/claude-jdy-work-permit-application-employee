"""
9.5. Betétlap（投资项目用工附件）—— 规则见 docs/rules/09_5-投资类附件.md

模板里的域都有名字（tools/build_form_9_5.py 生成），按名字填写。
"""
from ..model import COMPANY, EMPLOYERS, hu_money

TEMPLATE = "../hu/09_5_Betetlap_HU.docx"

# 学历 -> 勾选框（Q7：大专、大学在 9.5 没有对应选项，都不勾）
EDUCATION = {
    "Primary School 小学": "isk_altalanos",
    "Specialised School 专业学校": "isk_szakiskola",
    "Vocational School 职业学校": "isk_szakmunkas",
    "Secondary Grammar School 普通高中": "isk_gimnazium",
    "Vocational Secondary School 中等职业学校": "isk_szakkozep",
    "Technician Education Establishment 技术教育机构": "isk_technikum",
    "Finished Less Than 8 School Years In Primary School 未完成小学8个学年": "isk_8_alatt",
}

BORSODCHEM = "BorsodChem Zrt."


def fill(f, p):
    def t(name, value):
        f.text(f.no(name), None, value)

    def c(name, on=True):
        f.check(f.no(name), None, on)

    def yes_no(prefix, yes):
        c(f"{prefix}_igen", yes)
        c(f"{prefix}_nem", not yes)

    def ymd(prefix, d):
        t(f"{prefix}_ev", f"{d:%Y}" if d else "")
        t(f"{prefix}_ho", f"{d:%m}" if d else "")
        t(f"{prefix}_nap", f"{d:%d}" if d else "")

    emp = p.employer_info
    by_employer = p.submitted_by_employer

    # 页眉
    c("benyujt_ugyfel", not by_employer)
    c("benyujt_foglalk", by_employer)
    if by_employer:                                             # Q1、Q2：只在雇主递交时填
        t("kapcs_cim", COMPANY["delivery_address"])
        t("szekhely", emp.address)
        t("vizum_orszag", COMPANY["visa_pickup_country"])       # Q3
        t("vizum_varos", COMPANY["visa_pickup_city"])
    t("telefon", COMPANY["contact_phone"])
    t("email", COMPANY["contact_email"])

    # 1. 生活来源
    t("jov_varhato", f"HUF {hu_money(p.salary)}" if p.salary != "" else "")

    # 2. 住处（Q4、Q5：数据在 config/accommodation.json，空着就不填）
    acc = p.accommodation_info
    t("szallas_fo", acc.capacity)
    yes_no("szallas_elkul", True)
    t("szallas_eng_kiallito", acc.permit_issuer)
    t("szallas_eng_szam", acc.permit_no)
    if acc.permit_date:
        y, m, d = acc.permit_date.split("-")
        t("szallas_eng_ev", y), t("szallas_eng_ho", m), t("szallas_eng_nap", d)

    # 3. 雇主
    t("munkaltato_nev", p.employer)
    t("munkaltato_irsz", emp.zip)
    t("munkaltato_telepules", emp.city)
    t("munkaltato_kozter", emp.street)
    t("munkaltato_jelleg", emp.street_type)
    t("munkaltato_hazszam", emp.house_no)
    t("munkaltato_adoszam", emp.tax_no)
    t("munkaltato_ksh", emp.ksh)
    t("munkaltato_teaor", emp.teaor)

    # 4、5
    yes_no("miniszter_megall", True)
    t("csop_jovahagyas_a", COMPANY["group_permit_a"])           # Q6
    t("csop_jovahagyas_b", COMPANY["group_permit_b"])

    # 6、7、8
    t("szakkepzettseg", p.qualification_hu)
    box = EDUCATION.get(p.education)
    if box:
        c(box)
    t("elozo_foglalkozas", p.prev_position_hu)                  # Q8

    # 9. 工作地点（Q9：用辅助表里的工作地点，不用注册地址）
    is_bc = p.employer == BORSODCHEM
    yes_no("egy_hely", not is_bc)
    if not is_bc:
        t("egy_hely_cim", emp.workplace_hu)
    yes_no("tobb_megye", is_bc)
    if is_bc:
        t("tobb_megye_cim", "3700 Kazincbarcika, Bolyai tér 1.")
    yes_no("tobb_telephely", is_bc)

    # 10、11
    ymd("megall_kelte", p.sign_date)
    t("munkakor", p.job_title_hu)                               # Q10
    t("feor", str(p.feor) if p.feor != "" else "")

    # 12. 技能（Q11：专业经验年限留空）
    t("specialis_ismeret", p.special_skills)
    t("anyanyelv", p.native_language)                           # Q12
    t("egyeb_nyelv", p.other_languages_no_hu)
    yes_no("magyarul", p.speaks_hungarian)
    second = p.second_entry == "Yes 是"
    yes_no("korabban_mo", second)
    if second:                                                  # Q13：二次入职只有万华员工，前任雇主一定是 BC
        ymd("elozo_eng", p.prev_permit_expiry)
        bc = EMPLOYERS[BORSODCHEM]
        t("elozo_foglalk_nev", BORSODCHEM)
        t("elozo_foglalk_cim", bc["address"])
