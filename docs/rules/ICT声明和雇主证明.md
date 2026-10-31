# 规则清单：ICT 声明和万华雇主证明

- **模板：** 都由 `tools/build_ict_documents.py` 从简道云原模板转换而来：
  - `templates/hu/ict_declaration.docx` ← `templates/jdy/ict_declaration_jdy_original.docx`（Declaration on Intra-Corporate Transfer）
  - `templates/hu/employer_certificate_wanhua.docx` ← `templates/jdy/employer_certificate_wanhua_jdy_original.docx`（Employer's certificate Wanhua）
- **实现：** `service/forms/ict_declaration.py`、`employer_certificate.py`，共用 `ict_common.py`；测试样例 `tests/samples/ict_documents.json`
- **适用范围（2026-10-31 确认）：** 只用于 ICT。接收单位固定是 BorsodChem；派出公司取「原派出公司」，地址和签字城市在 `service/config/sending_company_details.json`（目前只有万华集团，其他派出公司缺配置会报错）。
- **检查过程：** 对照了一份已提交的真实 ICT 声明，看操作人员打印后手改了哪里（真实文件不进仓库）。

## Declaration on Intra-Corporate Transfer

| # | 原来 | 现在 |
|---|---|---|
| A1 | 岗位类型匈语写死 vezetői（管理岗），专家岗要手改 | 按「岗位类型（ICT）」：manager / expert / trainee，vezetői / szakértői / gyakornoki |
| A2 | 页脚汇率日期写死 02 April 2026 | 取「汇率日期」 |
| A3 | 金额、日期是原始值 | CNY 28.500,00；HUF 1.393.650；1 March 2015 / 2015. március 1. |
| A4 | 怀疑工作地点英文 Budapest 和 Gödöllő 连在一起 | 复查后是误判：原模板那里有换行，只是文字提取时看不出来。不改 |
| A5 | 派出公司名称、地址写死万华 | 取「原派出公司」+ 配置；签字地点用派出公司城市 |
| A6 | 简述前硬拼姓名，匈语少空格 | 代码拼：姓名 + 工作活动简要说明 + 主要职责，空格统一 |
| A7 | 学历写死 college education / felsőfokú végzettség | 按「学历」字段（大学 university education / egyetemi végzettség，大专 college education / főiskolai végzettség，等） |
| A8–A10 | 笔误；结尾写成「preliminary agreement / megállapodás」 | and/or、has had、lévő；this Declaration / jelen nyilatkozat |
| A11 | 引号混用 | 英文 “”，匈语 „” |
| A12 | — | 生成前检查：派出公司入职日期早于派遣开始至少 3 个月；实习生必须大学学历（35/2024. Korm. rendelet 27. § (2) b)） |
| B1 | — | 当事人栏用护照写法（ZENG YING），简述里用 Zeng Ying |
| B2 | — | 派遣开始/结束 = 劳动关系起始/终止日期 |
| B3 | — | 两边签字日期都用「劳动合同预协议&居留许可申请表签字日期」 |

### C1 法条引用

原来引用「445/2013. (XI.28) Korm. rendelet 20/A. § (1) a) 和 c)」。现行条文（2026-10-31 查 njt.hu）：

- 2024-03-01 起，ICT 居留许可的申请材料规定在 **35/2024. (II. 29.) Korm. rendelet（Btátv. 实施条例）27. §**：
  - (1) 派遣前须在同一企业或集团连续工作至少 3 个月；
  - (2) a) 同一集团的证明，b) 学历证明（实习生须大学学历），c) 接收单位关于员工具备所需经验的声明，d) 派出公司关于在欧盟各国停留时长的声明（匈牙利最长）。
- 在现行 445/2013 里没有找到 20/A. §。

所以改为引用 35/2024. Korm. rendelet 27. §。声明里「符合类似岗位派遣员工的法规和集体合同条件」这一条在 27. § 里没有对应的要求，但写上也无害，保留。

## Employer's certificate Wanhua

| # | 原来 | 现在 |
|---|---|---|
| W1 | **入职日期写死 2011.08.12 / 12 August, 2011** | 取「原派出公司入职日期」：2015.03.01-től / since 1 March 2015 |
| W2 | 派出公司写死 | 取「原派出公司」；签字城市取配置 |
| W3 | 地址「China, Shandong Province, Yantai City…」，匈语里也是英文 | 和劳动合同一样：详细地址, 区/县, 城市, 省份, 邮编, 国家 |
| W4 | 只用姓氏称呼 | 用全名（Zeng Ying） |
| W5 | during his stay | 按性别 his / her |
| W6 | Bolyai tér 少「1.」；neccessary；intracompany | 修正 |
| W7 | 金额原始值 | CNY 28.500,00 / 28.500,00 kínai jüan |
| W8 | 签字日期只有英文 | 「Yantai, Kína, 2026. október 25. / Yantai, China, 25 October 2026」 |
| W9 | 住宿和交通费用由万华承担 | 保留写死（2026-10-31 确认） |
| W10 | 是否其他外派也用 | 目前只有 ICT 用 |

## 需要和操作人员核对

- 「工作活动简要说明」「主要职责」现在怎么填：代码把姓名放在最前面，所以简要说明要以小写动词开头（possesses… / átfogó…），主要职责是完整的句子
- 「工资」对 ICT 是否就是「原派出公司工资 × 汇率」的福林金额
