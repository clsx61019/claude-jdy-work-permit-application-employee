"""
打印服务端到端测试：起一个假的简道云接口，调用 /generate，检查文件是否上传并写回。

运行: python tests/test_app.py            （需要 LibreOffice）
      docker run --rm -v $PWD/tests:/app/tests <镜像> python tests/test_app.py   （在镜像里测）
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = json.loads((ROOT / "tests" / "samples" / "employee_documents.json").read_text(encoding="utf-8"))
SAMPLE.update({"_id": "rec1", "appId": "app1", "entryId": "entry1"})

calls = {"uploads": [], "updates": [], "lists": [], "employers": [], "auth": []}


class FakeJdy(BaseHTTPRequestHandler):
    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if self.path.endswith("/data/list") and json.loads(raw)["entry_id"] == "69beb7dbd92ecd4fdced0420":
            calls["employers"].append(json.loads(raw)["filter"]["cond"][0]["value"])
            out = {"data": [{"_widget_1774106588505": "Rep EN", "_widget_1774106588506": "Rep HU"}]}
        elif self.path.endswith("/data/list") and json.loads(raw)["entry_id"] == "67501efb28e2adbc9a9d7bda":
            calls["auth"].append(json.loads(raw)["filter"]["cond"][0]["value"])
            out = {"data": [{"_widget_1793481372267": "Miskolc", "_widget_1793481372268": "3700 Kazincbarcika, Teszt u. 1.",
                             "_widget_1793481372269": "8000000000", "_widget_1793481372270": "000000AA"}]}
        elif self.path.endswith("/data/list"):
            cond = json.loads(raw)["filter"]["cond"][0]
            calls["lists"].append(cond)
            out = {"data": [{"_id": "rec1"}] if cond["value"] == ["SN-1"] else []}
        elif self.path.endswith("/data/get"):
            out = {"data": SAMPLE}
        elif self.path.endswith("/get_upload_token"):
            out = {"token_and_url_list": [{"url": f"http://127.0.0.1:{self.server.server_port}/upload",
                                           "token": f"t{i}"} for i in range(100)]}
        elif self.path == "/upload":
            calls["uploads"].append(len(raw))
            out = {"key": f"key{len(calls['uploads'])}"}
        elif self.path.endswith("/data/update"):
            calls["updates"].append(json.loads(raw))
            out = {"data": {}}
        else:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def call(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=600) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    fake = ThreadingHTTPServer(("0.0.0.0", 0), FakeJdy)
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    env = dict(os.environ, PORT="9123", JDY_API_BASE=f"http://127.0.0.1:{fake.server_port}/api",
               JDY_API_KEY="test", JDY_APP_ID="app1", JDY_ENTRY_ID="entry1", GEN_TOKEN="secret",
               FIELD_WORD="_widget_word", FIELD_PDF="_widget_pdf", FIELD_RESULT="_widget_result",
               FIELD_TAJ="_widget_taj")
    proc = subprocess.Popen([sys.executable, "-m", "service.app"], cwd=ROOT, env=env)
    base = "http://127.0.0.1:9123"
    for _ in range(50):
        try:
            call(base, "/health")
            break
        except OSError:
            time.sleep(0.2)

    try:
        assert call(base, "/generate?data_id=rec1&token=wrong")[0] == 403
        t = time.time()
        code, body = call(base, "/generate?data_id=rec1&token=secret&forms=all")
        print(f"/generate {code}，用时 {time.time() - t:.1f}s")
        res = json.loads(body)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        assert code == 200, body
        n = len(res["generated"])
        assert n >= 2 and n % 2 == 0
        assert len(calls["uploads"]) == n and all(x > 1000 for x in calls["uploads"])
        upd = calls["updates"][-1]
        assert len(upd["data"]["_widget_word"]["value"]) == n // 2
        assert len(upd["data"]["_widget_pdf"]["value"]) == n // 2
        assert upd["transaction_id"]
        code, body = call(base, "/generate?data_id=rec1&token=secret&format=zip&forms="
                          + urllib.parse.quote("GDPR声明"))
        assert code == 200 and body[:2] == b"PK", body[:200]
        code, body = call(base, "/generate?data_id=rec1&token=secret&format=zip&group=taj")
        assert code == 200 and body[:2] == b"PK", body[:200]
        import io, zipfile
        names = zipfile.ZipFile(io.BytesIO(body)).namelist()
        assert all(n.startswith(("TAJ", "GDPR")) or n == "结果.txt" for n in names), names
        assert call(base, "/generate?data_id=rec1&token=secret&format=zip&group=nope")[0] == 400
        # 智能助手：一个压缩包，按分组分文件夹，放进附件字段
        code, body = call(base, "/generate?data_id=rec1&token=secret&format=attach")
        assert code == 200, body
        assert json.loads(body)["attached"][0].startswith("申请材料"), body  # 超过 10 个：打包
        value = calls["updates"][-1]["data"]["_widget_word"]["value"]
        assert len(value) == 1, value
        # 按分组：写进该组自己的附件字段
        code, body = call(base, "/generate?data_id=rec1&token=secret&format=attach&group=taj")
        attached = json.loads(body)["attached"]
        assert code == 200 and attached and all(n.endswith((".docx", ".pdf")) for n in attached), body
        assert list(calls["updates"][-1]["data"]) == ["_widget_taj"], calls["updates"][-1]
        # 没有数据 ID 时按字段值找记录
        code, body = call(base, "/generate?key=SN-1&key_field=_widget_sn&key_type=sn&token=secret&format=attach&group=taj")
        assert code == 200, body
        assert calls["lists"][-1] == {"field": "_widget_sn", "type": "sn", "method": "eq", "value": ["SN-1"]}
        assert call(base, "/generate?key=NOPE&key_field=_widget_sn&token=secret&format=attach&group=taj")[0] == 400
        assert call(base, "/generate?token=secret&format=attach&group=taj")[0] == 400
        code, body = call(base, "/generate?data_id=rec1&token=secret&format=zip")
        names = zipfile.ZipFile(io.BytesIO(body)).namelist()
        assert "申请表/" in names and "TAJ/" in names and any(n.startswith("授权书/IMO") for n in names), names
        assert calls["employers"] and calls["employers"][0] == [SAMPLE["_widget_1732604018708"]], calls["employers"]
        assert calls["auth"], "没有按被授权人姓名查辅助表"
        print("通过")
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
