# 规则清单：TAJ 申请表、TAJ 订购单、GDPR 声明

- **模板：** 都由 `tools/build_taj_gdpr.py` 从简道云原模板转换而来。

| 简道云原模板 | 仓库模板（templates/hu/） | 官方表格 | 谁签 |
|---|---|---|---|
| TAJ Application Form | taj_application.docx | NEAK NYT.53 Igénylőlap（TAJ 申请表） | 员工或被授权人 |
| TAJ Card Application | taj_order.docx | NEAK NYT.52 Megrendelő（TAJ 订购单，只能由雇主填） | 雇主（盖章） |
| GDPR | gdpr_declarations.docx | 无（公司自己的告知确认和同意书，英语） | 员工 |

- 第一次办 TAJ 要交三份：订购单、申请表、授权书（NYT.159，见 `docs/rules/授权书.md`）。
- **和官方版对过：** 简道云的两份 TAJ 表格和 NEAK 现行的 NYT.52.G / NYT.53.G（2020）逐字对过，只有申请表脚注的法条不同，已改成官方写法（见 A10）。
- **原模板入库前已脱敏：** 申请表里写死的递交人姓名和家庭住址已换成 `[NÉV]`、`[TELEPÜLÉS]` 之类的标记。
- **实现：** `service/forms/taj_application.py`、`taj_order.py`（共用 `taj_common.py`）、`gdpr_declarations.py`；测试样例 `tests/samples/employee_documents.json`（女性，有楼层和室，在匈牙利递交）、`taj_male.json`（男性，有曾用名，有楼号，承包商雇主）、`authorization_china.json`（GDPR，在中国递交）
- **复选框：** 原模板的复选框叫 Jelölő2…8，而且有重名。转换时按顺序改成 first_issue、male、female、employee、egt_no 这类名字，代码用 `doc.check(名字)` 勾选
- **检查文档（2026-10-31）：** https://claude.ai/artifact/JhEerHgAuzRru7jhyp3zZi

## 什么时候能生成

| 模板 | 条件（不满足就报错） |
|---|---|
| TAJ 申请表 | 有被授权人姓名和住址（住址待办 J15）；性别是男或女 |
| TAJ 订购单 | 有「劳动关系实际起始日期」（B3）；雇主在 `config/employers.json` 里有地址、税号、雇主代表（雇主代表待办 J13） |
| GDPR | 有出生日期、签字日期、国内详细地址 |

## A. 修正（2026-10-31 确认）

| # | 模板 | 原来 | 现在 |
|---|---|---|---|
| A1 | 订购单 | 出生日期的「日」用了「月」的字段（5 月 7 日印成 5 月 5 日） | 代码生成年、月、日 |
| A2 | 申请表 | 递交人写死一名员工和她的家庭住址 | 取「选择被授权人」（和 TAJ 授权书同一人）。被授权人住址是一个字段（待办 J15），原来分成邮编、城市、街道、门牌号的两行合成一行 |
| A3 | 两份 | 「emelet, ajtó」写死「-」 | 按「楼」「室」：2., 3.；都没有才写「-」。有楼号、单元的写在街道那格（Ipari út, B ép.） |
| A4 | 两份 | 性别、申请类型的勾选框空着 | 按「性别」勾；申请表勾「első kiadás」 |
| A5 | 订购单 | 雇主地址、税号用辅助字段 | 取 `config/employers.json` |
| A6 | GDPR | 地址写成「China, Shandong Province, Yantai City, …」 | 和劳动合同同一种写法：详细地址, 区/县, 城市, 省份, 邮编, 国家 |
| A7 | GDPR | 「give my consent my personal data processing」「family union – and other visa types」「renting contracts」「family child allowance」 | 「consent to the processing of my personal data … for the following purposes」「family reunification and other visa applications」「rental contracts」「family allowance」 |
| A9 | 全部 | 出生时姓名、出生地、国籍、日期等用辅助字段 | 代码生成 |
| A10 | 申请表 | 脚注「a Tbj. 16.§ alá tartozó」 | 官方现行写法「az új Tbj. 22.§ alá tartozó」 |
| — | 申请表 | 官方要求印刷体大写填写 | 填进去的内容都转成大写 |
| — | 两份 | 性别、日期等处有黄色高亮 | 去掉 |

## B. 内容（2026-10-31 确认）

| # | 问题 | 结论 |
|---|---|---|
| B1 | 用哪个版本 | 简道云现在的模板（和官方版只差 A10 一处） |
| B2 | 「Lakóhelye」和「Tartózkodási helye」都填同一个匈牙利住址 | 保持（一直这样填，没被退回过） |
| B3 | 订购单「Biztosítási jogviszony kezdete」 | 取「劳动关系实际起始日期」，没有就报错 |
| B4 | 订购单的申请人类型和三个问题 | 勾「külföldi munkavállalónk」；三个问题都勾「nem」 |
| B5 | 日期 | GDPR 用「签字日期」，签字地点和其他员工声明一样按递交地点（Beijing / Kazincbarcika）。TAJ 两份是入境、开始工作后才办，用生成当天 |
| B6 | 订购单签字人 | 「foglalkoztató」下面印雇主代表（`employers.json` 的 representative_hu，待办 J13） |
| B7 | GDPR 只有英语 | 保持英语 |
| B8 | GDPR 数据控制者 | 保持 BorsodChem Zrt.（承包商员工也一样） |
| B9 | 个人信息表（Personal Datasheet，Excel） | 先不做 |

## C. 法务、操作人员（2026-10-31）

- GDPR 同意书里的 √ 是预先打好的：保持
- 「CARINVISA shares my sensitive data」是笔误：改成 BorsodChem Zrt.
- 「notarial sustain declaration」没改（是不是「公证的抵养声明」没确认）
- TAJ 申请表「在国外没有医保」的声明：一般不会有例外，保持

## 需要和操作人员核对

- 申请表的落款地点写死 KAZINCBARCIKA，订购单写死 Kazincbarcika
- 申请表的递交人现在是被授权人。如果实际是员工本人去递交，这一栏要改成员工
- GDPR 引用了「数据处理告知书」的章节（Chpt. 1、6、7、Article 8），告知书改版时要一起对
- 订购单「házszám」那格很窄，「9-11.」这种门牌号会折成两行（原模板也一样）
