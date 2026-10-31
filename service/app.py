"""
打印服务（HTTP）：读简道云记录 -> 生成 Word + PDF -> 写回附件字段。
部署在腾讯云函数（Web 函数，镜像部署，监听 9000 端口），本地也能直接跑：

    python -m service.app            # http://localhost:9000

接口
- GET  /health                        检查服务是否在线
- GET|POST /generate                  生成文件
    参数（查询字符串或 JSON）：
      token      必填，等于环境变量 GEN_TOKEN
      data_id    必填，简道云记录 ID
      forms      可选，逗号分隔的选项文字或模块名，或 all（附件只出对应居留许可类型的那份，其余逐个尝试，不适用的跳过）。
                 不填时读记录里的多选框 FIELD_SELECT；它也为空时按 all。
      app_id / entry_id   可选，默认用环境变量 JDY_APP_ID / JDY_ENTRY_ID
      group      可选，按钮分组（见 config/groups.json），只生成这一组里适用的文件；优先于 forms
      format     attach（压缩包放进附件字段；带 group 时用该组的 FIELD_<分组>，给简道云智能助手用）/ json（默认，写回简道云）/ zip（不写回，直接下载压缩包）/ html（写回，返回网页，方便浏览器测试）
- POST /jdy-webhook                   简道云「数据推送」：多选框 FIELD_SELECT 有值时生成，生成后把它清空

环境变量
  JDY_API_KEY      简道云 API 密钥
  JDY_APP_ID / JDY_ENTRY_ID    默认的应用、表单 ID
  GEN_TOKEN        调用口令
  FIELD_WORD       写回 Word 的附件字段 _widget_ ID
  FIELD_APPLICATION / FIELD_CONTRACT / FIELD_AUTHORIZATION / FIELD_DECLARATIONS / FIELD_TAJ
                   各分组压缩包的附件字段（format=attach&group=…），没配就用 FIELD_WORD
  FIELD_PDF        写回 PDF 的附件字段 _widget_ ID（不填则 Word、PDF 都写到 FIELD_WORD）
  FIELD_SELECT     多选框「选择要生成的文件」的 _widget_ ID（可选）
  FIELD_RESULT     多行文本，写生成结果和跳过原因（可选）
  JDY_PUSH_SECRET  数据推送的签名密钥（用 /jdy-webhook 时必填）
"""
import hashlib
import hmac
import html
import io
import json
import os
import re
import tempfile
import traceback
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from . import jdy, model
from .generate import render, to_pdf_many

FORMS = {k: v for k, v in json.loads(
    (Path(__file__).parent / "config" / "forms.json").read_text(encoding="utf-8")).items()
    if not k.startswith("_")}
LABELS = {v: k for k, v in FORMS.items()}
GROUPS = {k: v for k, v in json.loads(
    (Path(__file__).parent / "config" / "groups.json").read_text(encoding="utf-8")).items()
    if not k.startswith("_")}

env = os.environ.get

# 自动模式（all）下，附件只生成与居留许可类型对应的那一份
ANNEX_FOR_PERMIT = {"Investment": "form09_5", "Employment": "form09_6", "Hungarian Card": "form09_8",
                    "EU Blue Card": "form09_9", "Intra-corporate Transfer": "form09_10"}
ICT_ONLY = {"ict_declaration", "employer_certificate"}  # ICT 声明、万华雇主证明只给 ICT


class BadRequest(ValueError):
    pass


def applicable(modules, record):
    """自动模式：9.x 附件只留与居留许可类型对应的那份，ICT 文件只给 ICT。其余不适用的生成时会报错跳过。"""
    permit = model.build(record).permit_type
    wanted = ANNEX_FOR_PERMIT.get(permit)
    return [m for m in modules
            if (m not in ANNEX_FOR_PERMIT.values() or m == wanted)
            and (m not in ICT_ONLY or permit == "Intra-corporate Transfer")]


def resolve_forms(spec, record, group=None):
    """返回模块名列表。"""
    if group:
        if group not in GROUPS:
            raise BadRequest(f"不认识的分组「{group}」，可选：{'、'.join(GROUPS)}")
        return applicable(GROUPS[group]["forms"], record)
    if not spec and env("FIELD_SELECT"):
        spec = record.get(env("FIELD_SELECT")) or []
    if isinstance(spec, str):
        spec = [s.strip() for s in spec.split(",") if s.strip()]
    if not spec or spec == ["all"]:
        return applicable(list(FORMS.values()), record)
    out = []
    for s in spec:
        mod = FORMS.get(s) or (s if s in LABELS else None)
        if not mod:
            raise BadRequest(f"不认识的文件「{s}」，可选：{'、'.join(FORMS)}")
        out.append(mod)
    return out


def safe(s):
    return re.sub(r'[\\/:*?"<>|\s]+', " ", s).strip()


def generate(record, modules):
    """生成所有文件。返回 ([(文件名, bytes)], [(选项文字, 原因)])。不适用的模板会报 ValueError，记为跳过。"""
    p = model.build(record)
    who = safe(f"{p.surname} {p.given_name}")
    skipped, docx = [], []
    tmp = Path(tempfile.mkdtemp(prefix="gen-"))
    for i, mod in enumerate(modules):
        label = LABELS[mod]
        try:
            doc = render(mod, record)
        except Exception as e:  # noqa: BLE001 —— 一个模板出错不影响其他模板
            skipped.append((label, f"{type(e).__name__}: {e}" if not isinstance(e, ValueError) else str(e)))
            continue
        path = tmp / f"{i:02d}.docx"
        doc.save(path)
        docx.append((label, path))
    pdfs = to_pdf_many([x for _, x in docx]) if docx else []
    files = []
    for (label, path), pdf in zip(docx, pdfs):
        name = safe(f"{label} {who}")
        files.append((f"{name}.docx", path.read_bytes()))
        files.append((f"{name}.pdf", pdf.read_bytes()))
    return files, skipped


def result_text(files, skipped):
    lines = [f"已生成 {len(files) // 2} 份（Word + PDF）"]
    lines += [f"跳过 {label}：{why}" for label, why in skipped]
    return "\n".join(lines)


def write_back(app_id, entry_id, data_id, files, skipped, clear_select=False):
    word_field, pdf_field = env("FIELD_WORD"), env("FIELD_PDF") or env("FIELD_WORD")
    data = {}
    tid = None
    if files:
        tid, keys = jdy.upload_files(app_id, entry_id, files)
        words = [k for (n, _), k in zip(files, keys) if n.endswith(".docx")]
        pdfs = [k for (n, _), k in zip(files, keys) if n.endswith(".pdf")]
        if word_field == pdf_field:  # 同一个字段：每份文件的 Word、PDF 挨在一起
            data[word_field] = {"value": keys}
        else:
            data[word_field] = {"value": words}
            data[pdf_field] = {"value": pdfs}
    if env("FIELD_RESULT"):
        data[env("FIELD_RESULT")] = {"value": result_text(files, skipped)}
    if clear_select and env("FIELD_SELECT"):
        data[env("FIELD_SELECT")] = {"value": []}
    if data:
        jdy.update_record(app_id, entry_id, data_id, data, tid)


GROUP_OF = {m: g["name"] for g in GROUPS.values() for m in g["forms"]}  # 模块 -> 文件夹名


def make_zip(files, skipped, folders=False):
    """folders=True：按分组放进文件夹（申请表/、授权书/……），没有文件的文件夹留空"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if folders:
            for g in GROUPS.values():
                z.writestr(g["name"] + "/", b"")
        for name, content in files:
            folder = next((GROUP_OF[m] + "/" for label, m in FORMS.items() if name.startswith(label + " ")), "") \
                if folders else ""
            z.writestr(folder + name, content)
        z.writestr("结果.txt", result_text(files, skipped))
    return buf.getvalue()


def attach_zip(app_id, entry_id, data_id, zipname, content, group):
    """压缩包放进附件字段，替换字段里原来的文件。
    每个分组可以有自己的附件字段（环境变量 FIELD_APPLICATION、FIELD_TAJ……），没配就用 FIELD_WORD。
    简道云接口没法在保留旧附件的同时追加新文件，所以各分组要分开放才不会互相覆盖。"""
    field = (group and env(f"FIELD_{group.upper()}")) or env("FIELD_WORD")
    if not field:
        raise BadRequest("没有配置附件字段（FIELD_WORD 或 FIELD_<分组>）")
    tid, (key,) = jdy.upload_files(app_id, entry_id, [(zipname, content)])
    jdy.update_record(app_id, entry_id, data_id, {field: {"value": [key]}}, tid)
    return field


def handle_generate(params):
    if not env("GEN_TOKEN") or not hmac.compare_digest(str(params.get("token", "")), env("GEN_TOKEN")):
        return 403, "application/json", {"error": "token 不对"}
    data_id = params.get("data_id")
    if not data_id:
        raise BadRequest("缺少 data_id")
    app_id = params.get("app_id") or env("JDY_APP_ID")
    entry_id = params.get("entry_id") or env("JDY_ENTRY_ID")
    fmt = params.get("format", "json")
    record = jdy.get_record(app_id, entry_id, data_id)
    group = params.get("group")
    files, skipped = generate(record, resolve_forms(params.get("forms"), record, group))

    p = model.build(record)
    zipname = safe(f"{GROUPS[group]['name'] if group else '申请材料'} {p.surname} {p.given_name}") + ".zip"

    if fmt == "zip":
        if not files:  # 浏览器里点按钮时，与其下载空压缩包不如直接显示原因
            body = "<br>".join(html.escape(x) for x in result_text(files, skipped).split("\n"))
            return 200, "text/html; charset=utf-8", f"<meta charset=utf-8><p>没有可生成的文件。</p><p>{body}</p>"
        return 200, "application/zip", make_zip(files, skipped, folders=not group), zipname

    if fmt == "attach":  # 压缩包放进附件字段（给简道云智能助手用）
        attach_zip(app_id, entry_id, data_id, zipname, make_zip(files, skipped, folders=not group), group)
        return 200, "application/json", {
            "zip": zipname if files else None,
            "generated": [n for n, _ in files], "skipped": [{"file": l, "reason": r} for l, r in skipped]}

    if not env("FIELD_WORD"):
        raise BadRequest("没有配置 FIELD_WORD（附件字段），只能用 format=zip")
    write_back(app_id, entry_id, data_id, files, skipped)
    summary = {"generated": [n for n, _ in files], "skipped": [{"file": l, "reason": r} for l, r in skipped]}
    if fmt == "html":
        body = "<br>".join(html.escape(x) for x in result_text(files, skipped).split("\n"))
        return 200, "text/html; charset=utf-8", f"<meta charset=utf-8><p>{body}</p><p>已写回简道云，刷新记录查看附件。</p>"
    return 200, "application/json", summary


def check_push_signature(headers, raw, query):
    secret = env("JDY_PUSH_SECRET")
    if not secret:
        return False
    nonce, ts = query.get("nonce", ""), query.get("timestamp", "")
    expected = hashlib.sha1(f"{nonce}:{raw.decode('utf-8')}:{secret}:{ts}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(expected, headers.get("X-JDY-Signature", ""))


def handle_webhook(headers, raw, query):
    if not check_push_signature(headers, raw, query):
        return 403, "application/json", {"error": "签名不对"}
    body = json.loads(raw)
    record = body.get("data") or {}
    if body.get("op") not in ("data_create", "data_update") or not env("FIELD_SELECT") \
            or not record.get(env("FIELD_SELECT")):
        return 200, "application/json", {"ignored": True}
    files, skipped = generate(record, resolve_forms(None, record))
    write_back(record["appId"], record["entryId"], record["_id"], files, skipped, clear_select=True)
    return 200, "application/json", {"generated": len(files), "skipped": len(skipped)}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, ctype, body, filename="files.zip"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if ctype == "application/zip":
            self.send_header("Content-Disposition",  # 中文文件名按 RFC 5987 编码
                             f"attachment; filename=\"files.zip\"; filename*=UTF-8''{quote(filename)}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _dispatch(self, raw=b""):
        url = urlparse(self.path)
        query = {k: v[-1] for k, v in parse_qs(url.query).items()}
        try:
            if url.path == "/health":
                return self._send(200, "application/json", {"ok": True})
            if url.path == "/generate":
                params = dict(query)
                ctype = self.headers.get("Content-Type") or ""
                if raw and "json" in ctype:
                    params.update(json.loads(raw))
                elif raw and "form-urlencoded" in ctype:
                    params.update({k: v[-1] for k, v in parse_qs(raw.decode("utf-8")).items()})
                return self._send(*handle_generate(params))
            if url.path == "/jdy-webhook" and self.command == "POST":
                return self._send(*handle_webhook(self.headers, raw, query))
            return self._send(404, "application/json", {"error": "not found"})
        except BadRequest as e:
            return self._send(400, "application/json", {"error": str(e)})
        except jdy.JdyError as e:
            return self._send(502, "application/json", {"error": str(e)})
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            return self._send(500, "application/json", {"error": f"{type(e).__name__}: {e}"})

    def do_GET(self):
        self._dispatch()

    def do_POST(self):
        self._dispatch(self.rfile.read(int(self.headers.get("Content-Length") or 0)))

    def log_message(self, fmt, *args):  # 不打印查询字符串，里面有 token
        print(f"{self.command} {urlparse(self.path).path} -> {args[1] if len(args) > 1 else ''}", flush=True)


def main():
    port = int(env("PORT", "9000"))
    print(f"listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
