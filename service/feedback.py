"""
点按钮后写回简道云「生成结果」字段的反馈：先英语，空两行，再中文。

跳过原因在模板代码里是中文；英语部分按下面的对照表翻译，
对照表里没有的原因，英语部分写「see Chinese note below」，不会丢信息。
"""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Budapest")

# 文件（选项文字）-> 英语名，和英文模板一览表一致
DOC_EN = {
    "9 居留许可申请表": "Form 9 – Residence permit application",
    "9.5 投资类附件": "Annex 9.5 – Investment",
    "9.6 就业类附件": "Annex 9.6 – Employment",
    "9.8 匈牙利卡附件": "Annex 9.8 – Hungarian Card",
    "9.9 欧盟蓝卡附件": "Annex 9.9 – EU Blue Card",
    "9.10 ICT附件": "Annex 9.10 – Intra-corporate transfer",
    "预协议": "Preliminary Agreement",
    "劳动合同（普通员工）": "Employment Agreement – Ordinary",
    "劳动合同（高管）": "Employment Agreement – Executive",
    "ICT声明": "Declaration on Intra-Corporate Transfer",
    "万华雇主证明": "Employer's Certificate (Wanhua)",
    "IMO授权书": "Authorization for the Immigration Office",
    "NAV授权书": "NAV Authorization",
    "TAJ授权书": "TAJ Authorization",
    "住宿证明": "Confirmation of Accommodation",
    "雇主用工情况报告": "Employer's Notification",
    "沿用材料请求": "Request to Use Previously Submitted Documents",
    "通信和寄卡地址请求": "Request for Delivery Address",
    "住址未变声明": "Declaration – Address Unchanged",
    "员工同意雇主代为递交": "Employee Consent",
    "TAJ申请表": "TAJ Application Form",
    "TAJ订购单": "TAJ Order Form",
    "GDPR声明": "GDPR Declarations",
}

GROUP_EN = {"application": "Application forms", "contract": "Agreements and contracts",
            "authorization": "Authorizations", "declarations": "Declarations and certificates",
            "taj": "Social security card (TAJ)"}

# 「缺少：…」里的字段名 -> 英语（括号里的说明先去掉再查）
FIELD_EN = {
    "出生国": "country of birth", "出生地": "place of birth", "出生日期": "date of birth",
    "劳动关系实际起始日期": "actual start of employment", "劳动关系终止日期": "end of employment",
    "劳动关系起始日期": "start of employment", "原派出公司": "sending company",
    "原派出公司入职日期": "start date at sending company", "原派出公司工资": "salary at sending company",
    "国籍": "nationality", "城市": "city", "居留卡号": "residence card number", "岗位名称": "job title",
    "岗位名称（匈牙利语）": "job title (Hungarian)", "岗位名称（英语）": "job title (English)",
    "工作活动简要说明（匈牙利语）": "work description (Hungarian)",
    "工作活动简要说明（英语）": "work description (English)", "工资": "salary", "性别": "gender",
    "护照号": "passport number", "母亲出生时姓名": "mother's maiden name", "汇率日期": "exchange rate date",
    "直线上级岗位": "line manager's position", "税号": "tax number", "签字日期": "signing date",
    "职业资格/专业": "qualification", "街道名称": "street name", "被授权人住址": "authorized person's address",
    "被授权人公司": "authorized person's company", "被授权人出生地": "authorized person's place of birth",
    "被授权人出生日期": "authorized person's date of birth", "被授权人姓名": "authorized person's name",
    "被授权人岗位": "authorized person's position", "被授权人母亲姓名": "authorized person's mother's name",
    "被授权人税号": "authorized person's tax number", "被授权人证件号": "authorized person's ID number",
    "见证人1地址": "witness 1 address", "见证人1姓名": "witness 1 name", "见证人1母亲姓名": "witness 1 mother's name",
    "见证人1证件号": "witness 1 ID number", "见证人2地址": "witness 2 address", "见证人2姓名": "witness 2 name",
    "见证人2母亲姓名": "witness 2 mother's name", "见证人2证件号": "witness 2 ID number",
    "详细地址": "home address", "邮编": "postcode", "门牌号": "house number", "雇主": "employer",
    "雇主代表": "employer's representative", "雇主公司注册号": "employer's registration number",
    "雇主地址": "employer's address", "雇主税号": "employer's tax number",
    "雇主职权行使人岗位": "position of the person exercising employer's rights",
    "BC职级": "BC grade", "居留许可类型": "permit type", "递交地点": "place of submission",
}

# 其他跳过原因：正则 -> 英语
REASON_EN = [
    (r"缺少劳动关系起始日期或终止日期", "Missing: start or end of employment."),
    (r"只用于延期", "Only for extensions."),
    (r"只用于变更、延期", "Only for changes and extensions."),
    (r"变更、延期用 contract modification", "Changes and extensions use the contract modification template."),
    (r"BC职级是「(.+)」，用高管版本", r"BC grade is \1, so the Executive version is used."),
    (r"BC职级是「(.+)」，用普通员工版本", r"BC grade is \1, so the Ordinary version is used."),
    (r"劳动合同模板只给 (.+) 用", r"Labour contract templates are only for \1."),
    (r"ICT 声明的接收单位固定是", "The ICT declaration is only for BorsodChem as host employer."),
    (r"「(.+)」不需要预协议", r"\1 does not need a Preliminary Agreement."),
    (r"预协议最长 (\d+) 年", r"Preliminary Agreement term is longer than the legal maximum of \1 years."),
    (r"员工同意书只在雇主于匈牙利递交", "Only when the application is submitted in Hungary."),
    (r"住宿证明是 .+ 的信头", "Only for accommodation run by Polimer Szolgáltató Kft."),
    (r"ICT 实习生必须有大学学历", "ICT trainees need a university degree."),
    (r"不足 3 个月", "Less than 3 months at the sending company before the transfer."),
    (r"派出公司「(.+)」没有地址配置", r"No address configured for sending company \1."),
    (r"「语言」里有不认识的选项", "Unknown option in Languages."),
    (r"模板可能改过|占位符|第 \d+ 个域|表单域", "Template structure problem. Please tell the developer."),
]


def _field_en(name):
    base = re.sub(r"（(辅助表|config).*?）$", "", name).strip()
    return FIELD_EN.get(base) or FIELD_EN.get(re.sub(r"（.*?）$", "", base)) or f"「{base}」"


def reason_en(zh):
    m = re.match(r"缺少[：:](.+?)(（.*）)?$", zh)
    if m and "N-1" not in zh:
        return "Missing: " + ", ".join(_field_en(x) for x in m.group(1).split("、")) + "."
    if zh.startswith("缺少：BC职级"):
        return "Missing: BC grade (N-1 = Executive, others = Ordinary)."
    for pattern, en in REASON_EN[:1]:
        if re.search(pattern, zh):
            return en
    if zh.startswith("缺少"):
        return "Missing: " + _field_en(zh[2:].lstrip("：")) + "."
    for pattern, en in REASON_EN:
        if re.search(pattern, zh):
            return re.search(pattern, zh).expand(en)
    return "Not generated (see Chinese note below)."


def text(group_key, group_zh, generated, skipped, error=None, now=None):
    """generated: [选项文字]；skipped: [(选项文字, 中文原因)]；error: 整体失败时的中文说明。"""
    stamp = (now or datetime.now(TZ)).strftime("%Y-%m-%d %H:%M")
    title_en = GROUP_EN.get(group_key, "All documents")
    en = [f"{title_en} – {stamp}"]
    zh = [f"{group_zh or '全部文件'} – {stamp}"]
    if error:
        en.append("FAILED. Nothing was generated. Please tell the developer.")
        zh += ["失败，没有生成文件。请联系开发人员。", f"原因：{error}"]
        return "\n".join(en) + "\n\n\n" + "\n".join(zh)
    if generated:
        en.append(f"Generated {len(generated)} (Word + PDF):")
        en += [f"  ✓ {DOC_EN.get(x, x)}" for x in generated]
        zh.append(f"已生成 {len(generated)} 份（Word + PDF）：")
        zh += [f"  ✓ {x}" for x in generated]
    else:
        en.append("No documents generated.")
        zh.append("没有生成任何文件。")
    if skipped:
        en.append(f"Skipped {len(skipped)}:")
        en += [f"  ✗ {DOC_EN.get(x, x)}: {reason_en(why)}" for x, why in skipped]
        zh.append(f"跳过 {len(skipped)} 份：")
        zh += [f"  ✗ {x}：{why}" for x, why in skipped]
    return "\n".join(en) + "\n\n\n" + "\n".join(zh)
