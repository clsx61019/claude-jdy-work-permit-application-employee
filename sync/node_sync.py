"""
节点同步：把简道云流程的「当前节点 / 当前负责人 / 进入时间 / 停留天数」写进表单的普通字段，
这样仪表盘才能按节点统计（简道云仪表盘用不了系统字段「当前节点」「当前负责人」）。

数据来源是官方接口「查询流程实例信息」（/v6/workflow/instance/get），读的是真实待办，
不靠推测，所以回退、撤回、转交、手动结束都会在下一次同步时自动改对。

两种触发方式（同一个腾讯云事件函数）：
  1. 定时触发器：把所有需要同步的记录对一遍（兜底）。
  2. 函数 URL 收简道云「数据推送 → 流程变更时推送」（勾「流程待办变更时」「流程状态变更时」）：
     只同步推送过来的那一条（即时）。也兼容「表单变更时推送」。
只在值变了才写回，所以写回引起的那次推送不会再写，不会循环。

只用标准库。环境变量：
  JDY_API_KEY        简道云 API 密钥
  JDY_APP_ID         应用 ID
  JDY_ENTRY_ID       表单 ID
  SYNC_PUSH_SECRET   数据推送的签名密钥（配置后才校验签名，没配置时放行）
  FIELD_NODE         当前节点（单行文本）
  FIELD_ASSIGNEE     当前负责人（成员多选）
  FIELD_ENTERED      进入当前节点时间（日期时间）
  FIELD_DAYS         当前节点停留天数（数字）
  FIELD_SYNCED       节点同步时间（日期时间，节点信息最后一次变化的时间）
  LABEL_DONE / LABEL_ENDED / LABEL_WAITING   流程结束、手动结束、等子流程时写的文字（有默认值）
"""
import base64
import hashlib
import hmac
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

env = os.environ.get
BASE = env("JDY_API_BASE", "https://api.jiandaoyun.com/api")

LABEL_DONE = env("LABEL_DONE", "已完成")
LABEL_ENDED = env("LABEL_ENDED", "已手动结束")
# V9 里只有「第二轮通知」是「子流程结束后进入下一节点」，流程进行中却没有待办时就是在等它
LABEL_WAITING = env("LABEL_WAITING", "第二轮通知（子流程）")
FINAL_LABELS = {LABEL_DONE, LABEL_ENDED}


class JdyError(RuntimeError):
    pass


def post(path, body):
    key = env("JDY_API_KEY")
    if not key:
        raise JdyError("没有配置 JDY_API_KEY")
    req = urllib.request.Request(
        f"{BASE}{path}", data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise JdyError(f"简道云接口 {path} 返回 {e.code}：{e.read().decode('utf-8', 'replace')}") from e


def fields():
    names = ["FIELD_NODE", "FIELD_ASSIGNEE", "FIELD_ENTERED", "FIELD_DAYS", "FIELD_SYNCED"]
    missing = [n for n in names if not env(n)]
    if missing:
        raise JdyError("没有配置字段：" + "、".join(missing))
    return {n[6:].lower(): env(n) for n in names}


def node_label(flow_name):
    """「6. 确认抵达日期」→「06 确认抵达日期」，「1A HR确认」→「01A HR确认」，「5B. 匈牙利递交」→「05B 匈牙利递交」：
    补零后按文字排序就是流程顺序。不带编号的节点（如「第一轮通知」）原样写。"""
    m = re.match(r"^\s*(\d+)([A-Za-z]?(?:\.\d+)*)\.?\s*(.*)$", flow_name or "")
    if not m:
        return (flow_name or "").strip()
    return f"{int(m.group(1)):02d}{m.group(2).upper()} {m.group(3)}".strip()


def parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z") if dt else None


def desired_state(instance, now):
    """由流程实例算出应该写进表单的值。"""
    status = instance.get("status")
    if status == 1:
        return {"node": LABEL_DONE, "assignee": [], "entered": None, "days": None}
    if status == 2:
        return {"node": LABEL_ENDED, "assignee": [], "entered": None, "days": None}
    active = [t for t in instance.get("tasks") or [] if t.get("status") == 0]
    if not active:
        return {"node": LABEL_WAITING, "assignee": [], "entered": None, "days": None}
    names = []
    for t in active:
        n = node_label(t.get("flow_name"))
        if n not in names:
            names.append(n)
    people = []
    for t in active:
        u = (t.get("assignee") or {}).get("username")
        if u and u not in people:
            people.append(u)
    entered = min(parse_time(t.get("create_time")) for t in active if t.get("create_time")) \
        if any(t.get("create_time") for t in active) else None
    days = max(0, (now - entered).days) if entered else None
    return {"node": " / ".join(names), "assignee": sorted(people), "entered": entered, "days": days}


def current_state(record, f):
    people = record.get(f["assignee"]) or []
    return {
        "node": record.get(f["node"]) or "",
        "assignee": sorted(p.get("username") if isinstance(p, dict) else p for p in people),
        "entered": parse_time(record.get(f["entered"])),
        "days": record.get(f["days"]),
    }


def diff(want, have):
    out = {}
    for k in ("node", "assignee", "days"):
        if (want[k] if want[k] is not None else "") != (have[k] if have[k] is not None else ""):
            out[k] = want[k]
    w, h = want["entered"], have["entered"]
    if (w is None) != (h is None) or (w and h and abs((w - h).total_seconds()) >= 1):
        out["entered"] = w
    return out


def sync_record(app_id, entry_id, record, now, f):
    """同步一条记录，返回写了哪些键（没变就是空）。"""
    inst = post("/v6/workflow/instance/get", {"instance_id": record["_id"], "tasks_type": 1})
    want = desired_state(inst, now)
    changes = diff(want, current_state(record, f))
    if not changes:
        return []
    data = {}
    for k in ("node", "assignee", "entered", "days"):
        v = want[k]
        if k == "entered":
            v = iso(v)
        data[f[k]] = {"value": v if v not in (None, []) else ([] if k == "assignee" else None)}
    data[f["synced"]] = {"value": iso(now)}
    post("/v5/app/entry/data/update",
         {"app_id": app_id, "entry_id": entry_id, "data_id": record["_id"], "data": data})
    return sorted(changes)


def list_records(app_id, entry_id, f):
    """要同步的记录：流程进行中的，加上「当前节点」还停在某个节点但流程已结束的。"""
    wanted = ["_id", "flowState", *f.values()]
    seen, out = set(), []
    for flt in (
        {"rel": "and", "cond": [{"field": "flowState", "type": "flowstate", "method": "eq", "value": [0]}]},
        {"rel": "and", "cond": [
            {"field": "flowState", "type": "flowstate", "method": "in", "value": [1, 2]},
            {"field": f["node"], "type": "text", "method": "not_empty"},
            {"field": f["node"], "type": "text", "method": "nin", "value": sorted(FINAL_LABELS)}]},
    ):
        cursor = None
        while True:
            body = {"app_id": app_id, "entry_id": entry_id, "limit": 100, "fields": wanted, "filter": flt}
            if cursor:
                body["data_id"] = cursor
            page = post("/v5/app/entry/data/list", body).get("data") or []
            for r in page:
                if r["_id"] not in seen:
                    seen.add(r["_id"])
                    out.append(r)
            if len(page) < 100:
                break
            cursor = page[-1]["_id"]
    return out


def sync_all(now=None):
    now = now or datetime.now(timezone.utc)
    app_id, entry_id, f = env("JDY_APP_ID"), env("JDY_ENTRY_ID"), fields()
    records = list_records(app_id, entry_id, f)
    changed, errors = {}, {}
    for r in records:
        try:
            keys = sync_record(app_id, entry_id, r, now, f)
            if keys:
                changed[r["_id"]] = keys
        except Exception as e:  # 一条出错不影响其他
            errors[r["_id"]] = str(e)[:300]
    return {"checked": len(records), "changed": changed, "errors": errors}


def check_signature(headers, raw, query):
    secret = env("SYNC_PUSH_SECRET")
    if not secret:
        # 还没生成密钥时先放行（简道云要先填好地址才能生成密钥）。
        # 推送只会让函数去官方接口重读真实状态，伪造的推送写不进错误的值。
        print("还没配置 SYNC_PUSH_SECRET，暂不校验签名", file=sys.stderr)
        return True
    nonce, ts = query.get("nonce", ""), query.get("timestamp", "")
    expected = hashlib.sha1(f"{nonce}:{raw}:{secret}:{ts}".encode("utf-8")).hexdigest()
    got = {k.lower(): v for k, v in (headers or {}).items()}.get("x-jdy-signature", "")
    return hmac.compare_digest(expected, got)


def pushed_ids(body):
    """从推送内容里找出记录 ID（= 流程实例 ID）和表单 ID。
    表单推送（data_create/data_update）和流程推送（待办变更、流程状态变更）的格式不同，
    这里不依赖具体格式：在常见位置找 _id / data_id / instance_id 和 entryId / form_id / entry_id。"""
    # 流程推送（schema 2.0）：{"header": {"event_type": "task_update" | "process_update"},
    #                          "event": {"app_id", "form_id", "instance_id", ...}}
    # 表单推送：{"op": "data_update", "data": {"_id", "appId", "entryId", ...}}
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    event = body.get("event") if isinstance(body.get("event"), dict) else {}
    spots = [event, data, body]
    rid = next((s.get(k) for s in spots for k in ("instance_id", "data_id", "_id") if s.get(k)), None)
    eid = next((s.get(k) for s in spots for k in ("entryId", "form_id", "entry_id") if s.get(k)), None)
    return rid, eid


def handle_push(headers, raw, query, now=None):
    if not check_signature(headers, raw, query):
        print("签名不对。请求头：", sorted((headers or {}).keys()), "查询参数：", sorted(query.keys()), file=sys.stderr)
        return 403, {"error": "签名不对"}
    body = json.loads(raw)
    print("收到推送：", json.dumps(body, ensure_ascii=False)[:1000])  # 先把格式记进日志，便于核对
    rid, eid = pushed_ids(body)
    app_id, entry_id = env("JDY_APP_ID"), env("JDY_ENTRY_ID")
    if not rid or (eid and eid != entry_id):
        return 200, {"ignored": True}
    f = fields()
    record = post("/v5/app/entry/data/get", {"app_id": app_id, "entry_id": entry_id, "data_id": rid})["data"]
    keys = sync_record(app_id, entry_id, record, now or datetime.now(timezone.utc), f)
    return 200, {"changed": keys}


def http_response(code, body):
    return {"isBase64Encoded": False, "statusCode": code,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps(body, ensure_ascii=False)}


def main_handler(event, context=None):
    """腾讯云事件函数入口。定时触发器的 event 带 Type=Timer；函数 URL 的 event 带 httpMethod。"""
    event = event or {}
    if "httpMethod" in event or "requestContext" in event:
        raw = event.get("body") or ""
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode("utf-8")
        query = event.get("queryString") or event.get("queryStringParameters") or {}
        try:
            return http_response(*handle_push(event.get("headers") or {}, raw, query))
        except Exception as e:
            print("推送处理出错：", e, file=sys.stderr)
            return http_response(500, {"error": str(e)[:300]})
    result = sync_all()
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == "__main__":  # 本地手动跑一遍：python sync/node_sync.py
    print(json.dumps(sync_all(), ensure_ascii=False, indent=2))
