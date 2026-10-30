"""
把简道云 API 返回的一条记录（按 _widget_ ID 存值）转换成有含义的数据模型。
字段 ID 以「居留许可申请流程（员工）_测试」表为准（模板用到的字段与正式表一致）。
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

CONFIG = Path(__file__).parent / "config"
TZ = ZoneInfo("Europe/Budapest")  # API 返回 UTC，日期要换回布达佩斯时区，否则会差一天

COUNTRIES = json.loads((CONFIG / "countries.json").read_text(encoding="utf-8"))
COMPANY = json.loads((CONFIG / "company.json").read_text(encoding="utf-8"))

FIELDS = {
    "_widget_1732634740106": "permit_type",          # 居留许可类型
    "_widget_1728475331386": "surname",              # 姓氏（拼音）
    "_widget_1728475331387": "given_name",           # 名字（拼音）
    "_widget_1728475331399": "has_former_name",      # 曾用名
    "_widget_1728475331405": "birth_surname",        # 出生时姓氏（拼音）
    "_widget_1728475331406": "birth_given_name",     # 出生时名字（拼音）
    "_widget_1728475331411": "mother_surname",       # 母亲出生时姓氏（拼音）
    "_widget_1728475331412": "mother_given_name",    # 母亲出生时名字（拼音）
    "_widget_1728475331415": "gender",               # 性别
    "_widget_1728475331428": "birth_date",           # 出生日期
    "_widget_1728475331430": "birth_place",          # 出生地
    "_widget_1728480011250": "birth_country",        # 出生国
    "_widget_1728475331421": "marital_status",       # 婚姻状况
    "_widget_1728480011238": "nationality",          # 国籍
    "_widget_1728480011267": "education_level",      # 最高学历
    "_widget_1732527943129": "qualification_hu",     # 职业资格/专业（匈牙利语）
    "_widget_1778569357541": "prev_position_hu",     # 原派出公司岗位（匈牙利语）
    "_widget_1728480011304": "passport_no",          # 护照号
    "_widget_1728480011313": "passport_issued",      # 签发日期
    "_widget_1728480011315": "passport_expiry",      # 有效期
    "_widget_1728480011305": "passport_place",       # 签发地点
    "_widget_1728480011344": "hu_lot_no",            # 房屋注册号
    "_widget_1728549508506": "hu_zip",               # 邮编（匈牙利）
    "_widget_1728549508516": "hu_city",              # 城市（匈牙利）
    "_widget_1728549508519": "hu_street",            # 街道名称
    "_widget_1728549508520": "hu_street_type",       # 街道类型
    "_widget_1728549508521": "hu_house_no",          # 门牌号
    "_widget_1728549508522": "hu_building",          # 楼号
    "_widget_1728549508523": "hu_staircase",         # 单元
    "_widget_1728549508524": "hu_floor",             # 楼
    "_widget_1728549508525": "hu_door",              # 室
    "_widget_1728549508526": "hu_legal_title",       # 合法居留权
    "_widget_1732527943145": "home_country",         # 国家（原居住地）
    "_widget_1732527943146": "home_province",        # 省份
    "_widget_1732527943147": "home_city",            # 城市
    "_widget_1732527943148": "home_district",        # 区/县
    "_widget_1732527943149": "home_address",         # 详细地址
    "_widget_1743597826298": "home_zip",             # 邮编（国内）
    "_widget_1732527942981": "contract_end",         # 劳动关系终止日期
}

DATE_FIELDS = ("birth_date", "passport_issued", "passport_expiry", "contract_end")


class Model(dict):
    """模板里可以写 p.surname；缺失字段返回空字符串。"""
    def __getattr__(self, k):
        return self.get(k, "")


def _date(v):
    if not v:
        return None
    return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(TZ).date()


def en_part(v):
    """「山东 Shandong」->「Shandong」"""
    return v.split(" ", 1)[1] if v and " " in v else (v or "")


def country_hu(country_en):
    row = next((c for c in COUNTRIES if c["country_en"] == country_en), {})
    return row.get("country_hu", "")


def build(record):
    p = Model({name: record.get(wid) or "" for wid, name in FIELDS.items()})
    for k in DATE_FIELDS:
        p[k] = _date(p[k])

    if p.has_former_name != "Yes 是":
        p["birth_surname"], p["birth_given_name"] = p.surname, p.given_name
    p["birth_surname"] = p.birth_surname.upper()
    p["birth_given_name"] = p.birth_given_name.upper()

    nation = next((c for c in COUNTRIES if c["nationality_en"] == p.nationality), {})
    p["nationality_hu"] = nation.get("nationality_hu", "").lower()  # Q10：国籍形容词小写
    p["nationality_country_hu"] = nation.get("country_hu", "")      # Q4：国籍所属国家
    p["birth_country_hu"] = country_hu(p.birth_country)
    p["home_country_hu"] = country_hu(p.home_country)               # Q5
    p["birth_place_en"] = en_part(p.birth_place)
    p["passport_place_en"] = en_part(p.passport_place)
    return p
