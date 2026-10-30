"""
生成文件：读取一条简道云记录（API 返回的格式），套用 Jinja 模板，输出 Word。

用法: python generate.py <记录.json> <模板.docx> <输出.docx>
正式部署时，记录来自简道云开放 API，生成的文件再通过 API 写回附件字段。
"""
import json
import sys

import jinja2
from docxtpl import DocxTemplate

import rules


def main(record_path, template_path, out_path):
    record = json.load(open(record_path, encoding="utf-8"))
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)  # 模板里写错字段名会直接报错，而不是悄悄留空
    env.filters.update(rules.FILTERS)
    env.globals.update(rules.GLOBALS)
    tpl = DocxTemplate(template_path)
    tpl.render({"p": rules.build_model(record)}, jinja_env=env)
    tpl.save(out_path)
    print("已生成", out_path)


if __name__ == "__main__":
    main(*sys.argv[1:4])
