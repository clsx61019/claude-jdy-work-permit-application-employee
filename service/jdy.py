"""
简道云开放接口（API v5）：读一条记录、上传文件、把文件写回附件字段。
只用标准库，密钥从环境变量 JDY_API_KEY 读取。
"""
import json
import mimetypes
import os
import urllib.request
import uuid

BASE = os.environ.get("JDY_API_BASE", "https://api.jiandaoyun.com/api")


class JdyError(RuntimeError):
    pass


def _post(path, body):
    key = os.environ.get("JDY_API_KEY")
    if not key:
        raise JdyError("没有配置 JDY_API_KEY")
    req = urllib.request.Request(
        f"{BASE}{path}", data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise JdyError(f"简道云接口 {path} 返回 {e.code}：{e.read().decode('utf-8', 'replace')}") from e


def get_record(app_id, entry_id, data_id):
    return _post("/v5/app/entry/data/get",
                 {"app_id": app_id, "entry_id": entry_id, "data_id": data_id})["data"]


def find_records(app_id, entry_id, field, value, field_type="text"):
    """按字段值等于 value 查记录，最多返回 2 条（够判断是否唯一）。"""
    return _post("/v5/app/entry/data/list", {
        "app_id": app_id, "entry_id": entry_id, "limit": 2, "fields": ["_id"],
        "filter": {"rel": "and", "cond": [{"field": field, "type": field_type, "method": "eq", "value": [value]}]},
    })["data"]


# 辅助表「雇主相关信息」：雇主代表（J13）在简道云里维护，生成时实时读取
EMPLOYER_ENTRY = os.environ.get("JDY_EMPLOYER_ENTRY_ID", "69beb7dbd92ecd4fdced0420")
EMPLOYER_FIELDS = {"employer": "_widget_1774106588504", "representative_en": "_widget_1774106588505",
                   "representative_hu": "_widget_1774106588506"}


def employer_representatives(app_id, employer):
    """返回 {"representative_hu": …, "representative_en": …}；查不到返回 {}。"""
    if not employer:
        return {}
    rows = _post("/v5/app/entry/data/list", {
        "app_id": app_id, "entry_id": EMPLOYER_ENTRY, "limit": 10,
        "fields": [EMPLOYER_FIELDS["representative_en"], EMPLOYER_FIELDS["representative_hu"]],
        "filter": {"rel": "and", "cond": [{"field": EMPLOYER_FIELDS["employer"], "type": "text",
                                           "method": "eq", "value": [employer]}]},
    })["data"]
    for row in rows:
        out = {k: (row.get(EMPLOYER_FIELDS[k]) or "").strip() for k in ("representative_hu", "representative_en")}
        if all(out.values()):
            return out
    return {}


# 辅助表「被授权人」（J15）：按姓名找出生地、住址、税号、证件号
AUTH_ENTRY = os.environ.get("JDY_AUTH_ENTRY_ID", "67501efb28e2adbc9a9d7bda")
AUTH_NAME = "_widget_1732624873034"
AUTH_FIELDS = {"auth_birth_place": "_widget_1793481372267", "auth_address": "_widget_1793481372268",
               "auth_tax_no": "_widget_1793481372269", "auth_id_no": "_widget_1793481372270"}


def authorized_person(app_id, name):
    if not name:
        return {}
    rows = _post("/v5/app/entry/data/list", {
        "app_id": app_id, "entry_id": AUTH_ENTRY, "limit": 2, "fields": list(AUTH_FIELDS.values()),
        "filter": {"rel": "and", "cond": [{"field": AUTH_NAME, "type": "text", "method": "eq", "value": [name]}]},
    })["data"]
    if len(rows) != 1:
        return {}
    return {k: (rows[0].get(w) or "").strip() for k, w in AUTH_FIELDS.items()}


def _upload_one(url, token, filename, content):
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts = [
        f'--{boundary}\r\nContent-Disposition: form-data; name="token"\r\n\r\n{token}\r\n'.encode(),
        (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
         f'filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n').encode("utf-8"),
        content, f"\r\n--{boundary}--\r\n".encode(),
    ]
    req = urllib.request.Request(url, data=b"".join(parts), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["key"]


def upload_files(app_id, entry_id, files):
    """files: [(文件名, bytes)]。返回 (transaction_id, [key])，写回记录时要带同一个 transaction_id。"""
    tid = str(uuid.uuid4())
    slots = []
    while len(slots) < len(files):  # 每次最多给 100 个上传凭证
        slots += _post("/v5/app/entry/file/get_upload_token",
                       {"app_id": app_id, "entry_id": entry_id, "transaction_id": tid})["token_and_url_list"]
    keys = [_upload_one(s["url"], s["token"], name, data) for s, (name, data) in zip(slots, files)]
    return tid, keys


def update_record(app_id, entry_id, data_id, data, transaction_id=None):
    body = {"app_id": app_id, "entry_id": entry_id, "data_id": data_id, "data": data}
    if transaction_id:
        body["transaction_id"] = transaction_id
    return _post("/v5/app/entry/data/update", body)
