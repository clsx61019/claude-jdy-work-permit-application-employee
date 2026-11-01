"""
部署节点同步函数（sync/node_sync.py）：普通 Python 事件函数，代码打 zip 上传，不用镜像。
由 .github/workflows/deploy-node-sync.yml 调用。

函数不存在时先试着用接口创建；这个账号用接口 CreateFunction 曾报 InternalError，
失败的话按提示去控制台手动建一个空函数，再重新运行即可（之后的更新走接口没问题）。

需要的环境变量：
  TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY
  TENCENT_REGION    默认 eu-frankfurt
  SYNC_FUNCTION     函数名，默认 jdy-node-sync
  SYNC_CRON         定时兜底的 cron（腾讯云 7 位格式），默认每小时一次
函数自己的环境变量：见 FUNCTION_ENV，原样传进函数。
"""
import base64
import io
import json
import os
import sys
import time
import zipfile
from pathlib import Path

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf.v20180416 import models, scf_client

FUNCTION_ENV = ["JDY_API_KEY", "JDY_APP_ID", "JDY_ENTRY_ID", "SYNC_PUSH_SECRET",
                "FIELD_NODE", "FIELD_ASSIGNEE", "FIELD_ENTERED", "FIELD_DAYS", "FIELD_SYNCED",
                "FIELD_SUBMITTED", "FIELD_APPROVED", "FIELD_SINCE_SUBMIT", "FIELD_TOTAL"]
env = os.environ.get
NAME = env("SYNC_FUNCTION") or "jdy-node-sync"
HANDLER = "node_sync.main_handler"
CRON = env("SYNC_CRON") or "0 0 * * * * *"
client = scf_client.ScfClient(
    credential.Credential(env("TENCENTCLOUD_SECRET_ID"), env("TENCENTCLOUD_SECRET_KEY")),
    env("TENCENT_REGION") or "eu-frankfurt")


def call(action, params):
    req = getattr(models, f"{action}Request")()
    req.from_json_string(json.dumps(params))
    return json.loads(getattr(client, action)(req).to_json_string())


def zip_code():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(Path(__file__).resolve().parent.parent / "sync" / "node_sync.py", "node_sync.py")
    return base64.b64encode(buf.getvalue()).decode()


def get_function():
    try:
        return call("GetFunction", {"FunctionName": NAME})
    except TencentCloudSDKException as e:
        if "ResourceNotFound" in (e.code or ""):
            return None
        raise


def wait_active():
    for _ in range(60):
        f = get_function()
        if f and f.get("Status") == "Active":
            return
        if f and "Failed" in (f.get("Status") or ""):
            sys.exit(f"函数状态 {f['Status']}：{f.get('StatusDesc')}")
        time.sleep(3)
    sys.exit("等了 3 分钟函数还没就绪")


def main():
    variables = {"Variables": [{"Key": k, "Value": env(k)} for k in FUNCTION_ENV if env(k)]}
    settings = {"MemorySize": 128, "Timeout": 120}
    if get_function() is None:
        print(f"创建函数 {NAME}")
        try:
            call("CreateFunction", {"FunctionName": NAME, "Type": "Event", "Runtime": "Python3.10",
                                    "Handler": HANDLER, "Code": {"ZipFile": zip_code()},
                                    "Environment": variables, "Description": "简道云流程节点同步", **settings})
        except TencentCloudSDKException as e:
            sys.exit(f"接口创建失败（{e.code}）。请在控制台「{env('TENCENT_REGION') or 'eu-frankfurt'}」新建事件函数："
                     f"名称 {NAME}，运行环境 Python 3.10，从空白模板创建；建好后重新运行本工作流。")
        wait_active()
    else:
        print(f"更新函数 {NAME}")
        wait_active()
        call("UpdateFunctionCode", {"FunctionName": NAME, "Handler": HANDLER, "Code": {"ZipFile": zip_code()}})
        wait_active()
        call("UpdateFunctionConfiguration", {"FunctionName": NAME, "Environment": variables, **settings})
        wait_active()

    triggers = call("ListTriggers", {"FunctionName": NAME}).get("Triggers", [])
    if not any(t.get("Type") == "timer" for t in triggers):
        print(f"创建定时触发器（{CRON}）")
        try:
            call("CreateTrigger", {"FunctionName": NAME, "TriggerName": "hourly", "Type": "timer",
                                   "TriggerDesc": CRON, "Enable": "OPEN"})
        except TencentCloudSDKException as e:
            print(f"定时触发器创建失败（{e.code}），请在控制台「触发管理」手动添加：定时触发，Cron 表达式 {CRON}")
    url_trigger = next((t for t in triggers if t.get("Type") == "http"), None)
    if not url_trigger:
        print("创建函数 URL")
        try:
            call("CreateTrigger", {
                "FunctionName": NAME, "TriggerName": "url", "Type": "http", "Enable": "OPEN",
                "TriggerDesc": json.dumps({"AuthType": "NONE",
                                           "NetConfig": {"EnableIntranet": False, "EnableExtranet": True}})})
        except TencentCloudSDKException as e:
            print(f"函数 URL 创建失败（{e.code}），请在控制台「函数 URL」手动创建并开启公网访问")
    triggers = call("ListTriggers", {"FunctionName": NAME}).get("Triggers", [])
    url_trigger = next((t for t in triggers if t.get("Type") == "http"), None)
    url = json.loads((url_trigger or {}).get("TriggerDesc") or "{}").get("NetConfig", {}).get("ExtranetUrl")
    print("推送地址（填到简道云数据推送）：", url or "（没拿到，去控制台「函数 URL」看，记得开公网访问）")

    print("试跑一次全量同步：")
    out = call("Invoke", {"FunctionName": NAME, "InvocationType": "RequestResponse", "Event": "{}"})
    print(json.dumps(out.get("Result", {}), ensure_ascii=False)[:3000])


if __name__ == "__main__":
    main()
