"""
格式规则：替代简道云表单里的「辅助_」字段和公式。

简道云 API 返回的一条记录（按 _widget_ ID 存值）
  -> build_model() 变成有含义的数据模型
  -> Word 模板里用 {{ 模型.字段 | 过滤器 }} 直接取值、格式化。

主表只需要保留真实信息；所有"为了打印"的东西都在这里。
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REF = Path(__file__).parent / "reference"
TZ = ZoneInfo("Europe/Budapest")  # 简道云 API 返回 UTC 时间，日期要换回布达佩斯时区，否则会差一天

COUNTRIES = json.loads((REF / "countries.json").read_text(encoding="utf-8"))
ACCOMMODATION = json.loads((REF / "accommodation.json").read_text(encoding="utf-8"))

# 简道云字段 ID -> 模型字段名（只列这次模板用到的）
FIELDS = {
    "_widget_1732634740106": "permit_type",        # 居留许可类型
    "_widget_1728475331386": "surname",            # 姓氏（拼音）
    "_widget_1728475331387": "given_name",         # 名字（拼音）
    "_widget_1728475331399": "has_former_name",    # 曾用名
    "_widget_1728475331405": "birth_surname",      # 出生时姓氏（拼音）
    "_widget_1728475331406": "birth_given_name",   # 出生时名字（拼音）
    "_widget_1728475331411": "mother_surname",     # 母亲出生时姓氏（拼音）
    "_widget_1728475331412": "mother_given_name",  # 母亲出生时名字（拼音）
    "_widget_1728475331415": "gender",             # 性别
    "_widget_1728475331428": "birth_date",         # 出生日期
    "_widget_1728475331430": "birth_place",        # 出生地
    "_widget_1728480011250": "birth_country",      # 出生国
    "_widget_1728475331421": "marital_status",     # 婚姻状况
    "_widget_1728480011238": "nationality",        # 国籍
    "_widget_1728480011267": "education_level",    # 最高学历
    "_widget_1732527943129": "qualification_hu",   # 职业资格/专业（匈牙利语）
    "_widget_1770019996916": "prev_position_en",   # 原派出公司岗位（英语）
    "_widget_1728480011304": "passport_no",        # 护照号
    "_widget_1728480011313": "passport_issued",    # 签发日期
    "_widget_1728480011315": "passport_expiry",    # 有效期
    "_widget_1728480011305": "passport_place",     # 签发地点
    "_widget_1730202212741": "accommodation",      # 匈牙利居住地
    "_widget_1732527943146": "home_province",      # 省份
    "_widget_1732527943147": "home_city",          # 城市
    "_widget_1732527943148": "home_district",      # 区/县
    "_widget_1732527943149": "home_address",       # 详细地址
    "_widget_1743597826298": "home_zip",           # 邮编（国内）
    "_widget_1732527942981": "contract_end",       # 劳动关系终止日期
}

# 居留许可类型 -> 申请表附件号（原「辅助_申请表附件号」公式）
ATTACHMENT_NO = {
    "Employment": "9.6 SZÁMÚ",
    "Hungarian Card": "9.8 SZÁMÚ",
    "EU Blue Card": "9.9 SZÁMÚ",
    "Intra-corporate Transfer": "9.10 SZÁMÚ",
    "Investment": "9.5 SZÁMÚ",
}


class Model(dict):
    """允许模板里写 p.surname，而不是 p["surname"]；缺失字段返回空字符串。"""
    def __getattr__(self, k):
        return self.get(k, "")


def _date(v):
    if not v:
        return None
    return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(TZ).date()


def build_model(record):
    p = Model({name: record.get(wid, "") for wid, name in FIELDS.items()})
    for k in ("birth_date", "passport_issued", "passport_expiry", "contract_end"):
        p[k] = _date(p[k])

    # 原「辅助_出生时姓氏/名字」：没有曾用名就用现用名
    if p.has_former_name != "Yes 是":
        p["birth_surname"], p["birth_given_name"] = p.surname, p.given_name

    country = next((c for c in COUNTRIES if c["country_en"] == p.birth_country), {})
    nation = next((c for c in COUNTRIES if c["nationality_en"] == p.nationality), {})
    p["birth_country_hu"] = country.get("country_hu", "")
    p["nationality_hu"] = nation.get("nationality_hu", "")

    p["hu_address"] = Model(ACCOMMODATION.get(p.accommodation, {}))
    p["attachment_no"] = ATTACHMENT_NO.get(p.permit_type, "")
    return p


# ---------- 模板里可用的过滤器 / 函数 ----------

def cb(condition):
    """勾选框：替代所有「_单选框」公式"""
    return "☒" if condition else "☐"


def hu_full(d):
    """1990. év 05. hó 07. nap —— 原「_完整（匈牙利语）」公式"""
    return f"{d:%Y}. év {d:%m}. hó {d:%d}. nap" if d else ""


HU_MONTHS = ["január", "február", "március", "április", "május", "június",
             "július", "augusztus", "szeptember", "október", "november", "december"]


def hu_long(d):
    """1990. május 07. —— 原「（匈牙利语）」日期公式里那 12 段 IFS"""
    return f"{d:%Y}. {HU_MONTHS[d.month - 1]} {d:%d}." if d else ""


def en_long(d):
    """7 May 1990 —— 原「（英语）」日期公式"""
    return f"{d.day} {d:%B %Y}" if d else ""


def en_part(v):
    """「山东 Shandong」-> 「Shandong」 —— 原 RIGHT/LEN/SEARCH 公式"""
    return v.split(" ", 1)[1] if v and " " in v else (v or "")


def hu_money(n):
    """1234567 -> 1.234.567 —— 原多层嵌套 REPLACE 公式"""
    return f"{n:,.0f}".replace(",", ".") if n not in (None, "") else ""


FILTERS = {"hu_full": hu_full, "hu_long": hu_long, "en_long": en_long,
           "en_part": en_part, "hu_money": hu_money}
GLOBALS = {"cb": cb}
