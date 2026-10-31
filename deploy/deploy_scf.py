"""
把已推送到腾讯云容器镜像服务（TCR）的镜像部署成云函数（Web 函数），并确保有一个公网「函数 URL」。
函数不存在就创建，存在就更新镜像和环境变量。由 .github/workflows/deploy-tencent.yml 调用。

需要的环境变量：
  TENCENTCLOUD_SECRET_ID / TENCENTCLOUD_SECRET_KEY   腾讯云 API 密钥（建议用只授权 SCF 的子账号）
  TENCENT_REGION     地域，如 eu-frankfurt
  SCF_FUNCTION       函数名
  IMAGE_URI          完整镜像地址，如 deccr.ccs.tencentyun.com/命名空间/jdy-print:abc123
  IMAGE_TYPE         personal（个人版，默认）/ enterprise
  TCR_REGISTRY_ID    企业版实例 ID（IMAGE_TYPE=enterprise 时必填）
函数自己的环境变量（原样传进函数）：见 FUNCTION_ENV。
"""
import json
import os
import sys
import time

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.scf.v20180416 import models, scf_client

FUNCTION_ENV = ["JDY_API_KEY", "GEN_TOKEN", "JDY_APP_ID", "JDY_ENTRY_ID",
                "FIELD_WORD", "FIELD_PDF", "FIELD_SELECT", "FIELD_RESULT", "JDY_PUSH_SECRET"]

env = os.environ.get
NAME = env("SCF_FUNCTION", "jdy-print")
client = scf_client.ScfClient(
    credential.Credential(env("TENCENTCLOUD_SECRET_ID"), env("TENCENTCLOUD_SECRET_KEY")),
    env("TENCENT_REGION", "eu-frankfurt"))


def call(action, params):
    req = getattr(models, f"{action}Request")()
    req.from_json_string(json.dumps(params))
    return json.loads(getattr(client, action)(req).to_json_string())


def image_config():
    cfg = {"ImageType": env("IMAGE_TYPE") or "personal", "ImageUri": env("IMAGE_URI"), "ImagePort": 9000}
    if env("TCR_REGISTRY_ID"):
        cfg["RegistryId"] = env("TCR_REGISTRY_ID")
    return cfg


def function_env():
    return {"Variables": [{"Key": k, "Value": env(k)} for k in FUNCTION_ENV if env(k)]}


def get_function():
    try:
        return call("GetFunction", {"FunctionName": NAME})
    except TencentCloudSDKException as e:
        if "ResourceNotFound" in (e.code or ""):
            return None
        raise


def wait_active():
    for _ in range(120):
        f = get_function()
        status = f and f.get("Status")
        if status == "Active":
            return
        if status and "Failed" in status:
            print(f"函数状态 {status}：{f.get('StatusDesc')}")
            print("原因：", json.dumps(f.get("StatusReasons"), ensure_ascii=False))
            print("镜像配置：", json.dumps((f.get("ImageConfig") or {}), ensure_ascii=False))
            if status == "CreateFailed":  # 创建失败的函数留着会挡住下次创建，删掉
                call("DeleteFunction", {"FunctionName": NAME})
                print("已删除创建失败的函数，修正后重新运行即可")
            sys.exit(1)
        time.sleep(5)
    sys.exit("等了 10 分钟函数还没就绪")


SETTINGS = {
    "MemorySize": 2048,   # LibreOffice 转 PDF 要内存；镜像越大内存也要越大
    "Timeout": 300,       # 一次生成二十来份文件，留足余量
    "InitTimeout": 90,
}


def main():
    existing = get_function()
    if existing and existing.get("Status") not in ("Active", "CreateFailed"):
        wait_active()  # 控制台刚建的函数可能还在创建中
        existing = get_function()
    if existing and existing.get("Status") == "CreateFailed":
        print("上次创建失败，先删除")
        call("DeleteFunction", {"FunctionName": NAME})
        time.sleep(10)
        existing = None
    if existing is None:
        print(f"创建函数 {NAME}")
        call("CreateFunction", {
            "FunctionName": NAME, "Type": "HTTP", "Description": "简道云居留许可文件生成（测试）",
            "Code": {"ImageConfig": image_config()}, "Environment": function_env(),
            "MemorySize": SETTINGS["MemorySize"], "Timeout": SETTINGS["Timeout"]})
        wait_active()
    else:
        print(f"更新函数 {NAME}")
        call("UpdateFunctionCode", {"FunctionName": NAME, "Code": {"ImageConfig": image_config()}})
        wait_active()
        call("UpdateFunctionConfiguration", {"FunctionName": NAME, "Environment": function_env(), **SETTINGS})
        wait_active()

    triggers = call("ListTriggers", {"FunctionName": NAME}).get("Triggers", [])
    url_trigger = next((t for t in triggers if t.get("Type") == "http"), None)
    if not url_trigger:
        print("创建函数 URL")
        call("CreateTrigger", {
            "FunctionName": NAME, "TriggerName": "url", "Type": "http", "Enable": "OPEN",
            "TriggerDesc": json.dumps({"AuthType": "NONE",
                                       "NetConfig": {"EnableIntranet": False, "EnableExtranet": True}})})
        triggers = call("ListTriggers", {"FunctionName": NAME}).get("Triggers", [])
        url_trigger = next((t for t in triggers if t.get("Type") == "http"), None)
    desc = json.loads(url_trigger.get("TriggerDesc") or "{}")
    if not desc.get("NetConfig", {}).get("EnableExtranet"):  # 控制台默认只开内网
        print("打开函数 URL 的公网访问")
        try:
            call("UpdateTrigger", {
                "FunctionName": NAME, "TriggerName": url_trigger["TriggerName"], "Type": "http",
                "Qualifier": url_trigger.get("Qualifier") or "$DEFAULT", "Enable": "OPEN",
                "TriggerDesc": json.dumps({"AuthType": desc.get("AuthType", "NONE"),
                                           "NetConfig": {"EnableIntranet": False, "EnableExtranet": True}})})
        except TencentCloudSDKException as e:
            print(f"打开公网访问失败（{e.code}），请在控制台「函数 URL」里手动开启公网访问")
        triggers = call("ListTriggers", {"FunctionName": NAME}).get("Triggers", [])
        url_trigger = next(t for t in triggers if t.get("Type") == "http")
        desc = json.loads(url_trigger.get("TriggerDesc") or "{}")
    url = desc.get("NetConfig", {}).get("ExtranetUrl") or ""
    print("公网地址：", url or "（没拿到，去控制台「函数 URL」看）")
    if env("GITHUB_OUTPUT") and url:
        with open(env("GITHUB_OUTPUT"), "a") as f:
            f.write(f"url={url}\n")


if __name__ == "__main__":
    main()
