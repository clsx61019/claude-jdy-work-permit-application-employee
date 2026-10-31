"""
9. Tartózkodási engedély iránti kérelem —— 规则见 docs/rules/09-申请表.md

每一行：域编号、表单上旁边应有的文字（用于校验位置）、填写内容。
"""
from ..model import COMPANY

TEMPLATE = "09_Tartozkodasi_engedely_iranti_kerelem.docx"

# 居留许可类型 -> 第 9 部分的勾选框编号、第 10 部分的附件号
PURPOSE = {
    "Investment": (367, "9.5 SZÁMÚ"),
    "Employment": (368, "9.6 SZÁMÚ"),
    "Hungarian Card": (370, "9.8 SZÁMÚ"),
    "EU Blue Card": (371, "9.9 SZÁMÚ"),
    "Intra-corporate Transfer": (372, "9.10 SZÁMÚ"),
}

# 合法居留权 -> 第 3 部分勾选框（Q3）
LEGAL_TITLE = {"Tulajdonos": 122, "Bérlő": 123, "Családtag": 124,
               "Szívességi Lakáshasználó": 125, "Egyéb": 126}

# 第 12 部分只适用于这些类型（Q6）
SECTION12_TYPES = {"Investment", "Employment"}


def ymd(f, nos, d):
    """日期分三格填写，月、日补零（Q7）"""
    y, m, dd = nos  # 前后各留一个空格，和表单上的「év / hó / nap」隔开
    f.text(y, None, f" {d:%Y} " if d else "")
    f.text(m, "év", f" {d:%m} " if d else "")
    f.text(dd, "hó", f" {d:%d} " if d else "")


def fill(f, p):
    # 页眉：申请类型。变更（换许可类型）也勾首次申请（已确认）
    extension = p.app_type == "extension"
    f.check(1, "kiadása első alkalommal", not extension)
    f.check(8, "meghosszabbítása", extension)
    if extension:  # 正在延期的那张卡：原居留卡号、原居留卡有效期（新卡另存在「居留卡号」「居留卡有效期」）
        f.text(9, "Az engedély száma", p.prev_card_no)
        ymd(f, (12, 13, 14), p.prev_permit_expiry)

    # 页眉：联系方式、领取方式
    f.text(15, "Telefonszám", COMPANY["contact_phone"])
    f.text(17, "E-mail cím", COMPANY["contact_email"])
    f.check(19, "postai úton")
    f.check(21, "meghatalmazott kapcsolattartási címe")
    f.append_after(21, "meghatalmazott kapcsolattartási címe", [   # Q1
        (COMPANY["delivery_address"], True, None),
        (COMPANY["delivery_note"], True, 7),
    ])

    # 1. 个人信息
    f.text(23, "családi név (útlevél szerint)", p.surname)
    f.text(28, "utónév (útlevél szerint)", p.given_name)
    f.text(33, "születési családi név", p.birth_surname)
    f.text(39, "születési utónév", p.birth_given_name)
    f.text(45, "anyja születési családi neve", p.mother_surname)
    f.text(50, "anyja születési utóneve", p.mother_given_name)
    f.check(55, "férfi", p.gender == "Male 男")
    f.check(56, "nő", p.gender == "Female 女")
    f.check(57, "nőtlen/hajadon", p.marital_status == "Single 未婚")
    f.check(58, "özvegy", p.marital_status == "Widowed 丧偶")
    f.check(59, "házas", p.marital_status == "Married 已婚")
    f.check(60, "elvált", p.marital_status == "Divorced 离异")
    f.text(61, "születési idő", "")  # 校验位置，下面再写入
    ymd(f, (61, 62, 63), p.birth_date)
    f.text(64, "születési hely (település)", f" {p.birth_place_en}")  # 官方冒号后没有空格
    f.text(68, "ország", p.birth_country_hu)
    f.text(71, "állampolgársága", p.nationality_hu)
    f.check(82, "alapfokú", p.education_level == "Primary Education 基础教育")
    f.check(83, "középfokú", p.education_level == "Secondary Education 中等教育")
    f.check(84, "felsőfokú", p.education_level == "Higher Education 高等教育")
    f.text(78, "szakképzettsége", p.qualification_hu)
    f.text(85, "megelőző foglalkozás", p.prev_position_hu)        # Q2

    # 2. 护照
    f.text(88, "útlevél száma", p.passport_no)
    f.text(91, "kiállításának ideje, helye", "")
    ymd(f, (91, 92, 93), p.passport_issued)
    f.text(94, "nap,", p.passport_place_en)
    f.check(98, "magánútlevél")
    f.text(102, "érvényességi ideje", "")
    ymd(f, (102, 103, 104), p.passport_expiry)

    # 3. 匈牙利住处
    f.text(105, "helyrajzi szám", p.hu_lot_no)
    f.text(106, "irányítószám", p.hu_zip)
    f.text(107, "település", p.hu_city)
    f.text(111, "közterület neve", p.hu_street)
    f.text(115, "közterület jellege", p.hu_street_type)
    f.text(116, "házszám", p.hu_house_no)
    f.text(117, "épület", p.hu_building)
    f.text(119, "lépcsőház", p.hu_staircase)
    f.text(120, "emelet", p.hu_floor)
    f.text(121, "ajtó", p.hu_door)
    labels = {122: "tulajdonos", 123: "bérlő", 124: "családtag", 125: "szívességi lakáshasználó", 126: "egyéb"}
    for no, label in labels.items():
        f.check(no, label, LEGAL_TITLE.get(p.hu_legal_title) == no)

    # 4. 医疗保险
    f.check(129, "foglalkoztatási jogviszony alapján")

    # 5. 返回或继续前往
    f.text(140, "mely országba utazik vissza", p.nationality_country_hu)  # Q4
    f.text(144, "Milyen közlekedési eszközzel", COMPANY["return_transport"])
    f.check(148, "igen")   # útlevéllel
    f.check(150, "igen")   # vízummal
    f.check(152, "igen")   # menetjeggyel
    f.check(154, "igen, összege")
    f.text(155, "igen, összege", COMPANY["financial_means"])

    # 6. 家属：留空

    # 7. 其他信息
    f.text(326, "Ország", p.home_country_hu)                              # Q5
    f.text(331, "Település", f"{p.home_province} Province, {p.home_city} City")
    f.text(336, "Közterület neve", f"{p.home_district}, {p.home_address}, {p.home_zip}")
    for no in (342, 347, 349, 351, 356, 358):                             # Q8：全部 nem
        f.check(no, "nem")

    # 8. 未成年子女
    f.check(360, "nem")

    # 9. 期限与目的
    f.text(361, "Meddig kérelmezi", "")
    ymd(f, (361, 362, 363), p.contract_end)
    box, attachment = PURPOSE.get(p.permit_type, (None, ""))
    if box:
        f.check(box, "betétlap")

    # 10. 附件号
    f.text(386, "ahhoz csatolt", attachment)

    # 12. 只适用于部分类型（Q6）
    if p.permit_type in SECTION12_TYPES:
        f.check(398, "az állampolgárságom szerinti állam")
