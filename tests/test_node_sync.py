"""
节点同步函数的单元测试：假的简道云接口，不联网。
运行: python tests/test_node_sync.py
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "sync"))
os.environ.update({
    "JDY_API_KEY": "k", "JDY_APP_ID": "app1", "JDY_ENTRY_ID": "entry1", "SYNC_PUSH_SECRET": "s3",
    "FIELD_NODE": "w_node", "FIELD_ASSIGNEE": "w_who", "FIELD_ENTERED": "w_in",
    "FIELD_DAYS": "w_days", "FIELD_SYNCED": "w_sync",
})
import node_sync as ns  # noqa: E402

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
RECORDS = {
    # 进行中，停在节点 6（三人或签，只算进行中的待办）
    "r1": {"_id": "r1", "flowState": 0},
    # 进行中，没有进行中的待办 → 等子流程
    "r2": {"_id": "r2", "flowState": 0},
    # 已结束，但字段还停在某个节点 → 要改成已完成
    "r3": {"_id": "r3", "flowState": 1, "w_node": "09 信息归档"},
    # 进行中，字段已经是对的 → 不写
    "r4": {"_id": "r4", "flowState": 0, "w_node": "01.1 HR确认", "w_who": [{"username": "jia"}],
           "w_in": "2026-10-30T08:00:00.000Z", "w_days": 3},
}
INSTANCES = {
    "r1": {"status": 0, "tasks": [
        {"status": 1, "flow_name": "5. 递交申请", "assignee": {"username": "wu"}, "create_time": "2026-10-20T08:00:00Z"},
        {"status": 0, "flow_name": "6. 确认抵达日期", "assignee": {"username": "wu"}, "create_time": "2026-10-28T07:13:31Z"},
        {"status": 0, "flow_name": "6. 确认抵达日期", "assignee": {"username": "jia"}, "create_time": "2026-10-28T07:13:31Z"},
    ]},
    "r2": {"status": 0, "tasks": [{"status": 1, "flow_name": "7. 文件签署"}]},
    "r3": {"status": 1, "tasks": []},
    "r4": {"status": 0, "tasks": [
        {"status": 0, "flow_name": "1.1. HR确认", "assignee": {"username": "jia"}, "create_time": "2026-10-30T08:00:00Z"}]},
}
updates = []


def fake_post(path, body):
    if path.endswith("/data/list"):
        st = body["filter"]["cond"][0]["value"]
        rows = [r for r in RECORDS.values() if r["flowState"] in st]
        if st != [0]:
            rows = [r for r in rows if r.get("w_node") and r["w_node"] not in ns.FINAL_LABELS]
        return {"data": rows}
    if path.endswith("/data/get"):
        return {"data": RECORDS[body["data_id"]]}
    if path.endswith("/workflow/instance/get"):
        assert body["tasks_type"] == 1
        return INSTANCES[body["instance_id"]]
    if path.endswith("/data/update"):
        updates.append(body)
        RECORDS[body["data_id"]].update({k: v["value"] for k, v in body["data"].items()})
        return {"data": {}}
    raise AssertionError(path)


ns.post = fake_post


def by_id(rid):
    return next(u["data"] for u in updates if u["data_id"] == rid)


def test_labels():
    assert ns.node_label("6. 确认抵达日期") == "06 确认抵达日期"
    assert ns.node_label("1.1. HR确认") == "01.1 HR确认"
    assert ns.node_label("10. 最终确认") == "10 最终确认"
    assert ns.node_label("1A HR确认") == "01A HR确认"
    assert ns.node_label("5B. 匈牙利递交") == "05B 匈牙利递交"
    assert ns.node_label("第一轮通知") == "第一轮通知"
    assert ns.node_label("HR确认完成") == "HR确认完成"


def test_sync_all():
    res = ns.sync_all(NOW)
    assert res["checked"] == 4 and not res["errors"], res
    assert set(res["changed"]) == {"r1", "r2", "r3"}, res
    d = by_id("r1")
    assert d["w_node"]["value"] == "06 确认抵达日期"
    assert d["w_who"]["value"] == ["jia", "wu"]
    assert d["w_in"]["value"] == "2026-10-28T07:13:31.000Z"
    assert d["w_days"]["value"] == 5
    assert d["w_sync"]["value"] == "2026-11-02T09:00:00.000Z"
    assert by_id("r2")["w_node"]["value"] == ns.LABEL_WAITING
    d = by_id("r3")
    assert d["w_node"]["value"] == "已完成" and d["w_who"]["value"] == [] and d["w_days"]["value"] is None


def test_second_run_writes_nothing():
    before = len(updates)
    res = ns.sync_all(NOW)
    assert res["changed"] == {} and len(updates) == before, res


def push(body, secret="s3"):
    raw = json.dumps(body, ensure_ascii=False)
    q = {"nonce": "n1", "timestamp": "1700000000"}
    sig = hashlib.sha1(f"n1:{raw}:{secret}:1700000000".encode()).hexdigest()
    event = {"httpMethod": "POST", "headers": {"X-JDY-Signature": sig}, "body": raw, "queryString": q}
    return ns.main_handler(event)


def test_push():
    INSTANCES["r4"]["tasks"].append(
        {"status": 0, "flow_name": "2. 收到证书", "assignee": {"username": "reka"}, "create_time": "2026-11-02T08:00:00Z"})
    INSTANCES["r4"]["tasks"][0]["status"] = 1
    # 官方「流程待办变更时」样例的格式
    out = push({"schema": "2.0", "header": {"event_type": "task_update", "created_at": 1761703465254},
                "event": {"app_id": "app1", "form_id": "entry1", "instance_id": "r4", "flow_id": 7,
                          "flow_name": "2. 收到证书", "completed_tasks": [], "created_tasks": []}})
    assert out["statusCode"] == 200, out
    assert RECORDS["r4"]["w_node"] == "02 收到证书" and RECORDS["r4"]["w_who"] == ["reka"]
    # 写回引起的再次推送：值没变，不写
    before = len(updates)
    push({"op": "data_update", "data": {"_id": "r4", "entryId": "entry1", "appId": "app1"}})
    assert len(updates) == before
    # 别的表单、签名不对
    assert json.loads(push({"data": {"_id": "x", "entryId": "other"}})["body"]) == {"ignored": True}
    assert json.loads(push({"schema": "2.0", "header": {"event_type": "process_update"},
                            "event": {"form_id": "other", "instance_id": "x", "status": 2}})["body"]) == {"ignored": True}
    assert push({"data": {"_id": "r4"}}, secret="wrong")["statusCode"] == 403
    os.environ.pop("SYNC_PUSH_SECRET")
    try:
        assert ns.check_signature({}, "{}", {})  # 没配置密钥时放行
    finally:
        os.environ["SYNC_PUSH_SECRET"] = "s3"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
