# -*- coding: utf-8 -*-
"""
寿司云 Web App 版本（云端部署版）
Flask 后端 + H5 移动端界面
"""
import json
import random
import string
import os
import urllib.request
import urllib.error
from datetime import datetime
from flask import Flask, render_template, jsonify, request

# ============ 寿司云 API 核心函数 ============
SUSHI_BASE = "https://get.sushi2.cloud"
SUSHI_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
SUSHI_SUFFIXES = ["qq.com", "163.com", "gmail.com", "139.com", "outlook.com", "icloud.com"]

def gen_random_email():
    """生成邮箱：字母数字字母 (9位)"""
    chars = []
    for i in range(5):
        chars.append(random.choice(string.ascii_lowercase))
        chars.append(str(random.randint(0, 9)))
    local = ''.join(chars)[:9]
    domain = random.choice(SUSHI_SUFFIXES)
    return f"{local}@{domain}"

def _sushi_http(url, data=None, headers_extra=None, method=None):
    h = {"Accept": "application/json, text/plain, */*", "Origin": SUSHI_BASE,
         "Referer": SUSHI_BASE + "/#/", "User-Agent": SUSHI_UA}
    if headers_extra:
        h.update(headers_extra)
    if data is not None:
        body = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=h, method=(method or "POST"))
    else:
        req = urllib.request.Request(url, headers=h, method=(method or "GET"))
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, str(e)

def sushi_register(email, password):
    _, body = _sushi_http(SUSHI_BASE + "/api/v1/passport/auth/register",
        {"email_ssyun": email, "password_ssyun": password,
         "invite_code_ssyun": "", "email_code_ssyun": "", "recaptcha_data_ssyun": ""})
    try:
        j = json.loads(body)
        return j.get("status") == "success", j.get("data", {}), body
    except Exception:
        return False, {}, body

def sushi_login(email, password):
    _, body = _sushi_http(SUSHI_BASE + "/api/v1/passport/auth/login",
        {"email": email, "password": password})
    try:
        j = json.loads(body)
        return j.get("status") == "success", j.get("data", {}), body
    except Exception:
        return False, {}, body

def sushi_get_subscribe(bearer):
    _, body = _sushi_http(SUSHI_BASE + "/api/v1/user/getSubscribe",
        headers_extra={"Authorization": "***" + bearer})
    try:
        return json.loads(body)
    except Exception:
        return {}

def sushi_fetch_vmess(sub_url):
    req = urllib.request.Request(sub_url, headers={"User-Agent": "v2rayng/1.8.16", "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return None, str(e)

# ============ Flask App ============
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def api_register():
    """单账号注册"""
    try:
        email = gen_random_email()
        password = "nuosen666"
        
        ok1, data1, _ = sushi_register(email, password)
        if not ok1:
            return jsonify({"success": False, "error": "注册失败，请重试"})
        
        ok2, data2, _ = sushi_login(email, password)
        if not ok2:
            return jsonify({"success": False, "error": "登录失败"})
        
        auth = data2.get("auth_data", "") or ("Bearer " + data1.get("token", ""))
        bearer = auth.split("Bearer ", 1)[1] if auth.startswith("Bearer ") else auth
        
        sub_j = sushi_get_subscribe(bearer)
        if not isinstance(sub_j, dict) or sub_j.get("status") != "success":
            return jsonify({"success": False, "error": "获取订阅失败"})
        
        sub_url = sub_j.get("data", {}).get("subscribe_url", "")
        if not sub_url:
            return jsonify({"success": False, "error": "订阅 URL 为空"})
        
        _, vmess = sushi_fetch_vmess(sub_url)
        
        return jsonify({
            "success": True,
            "email": email,
            "password": password,
            "subscribe_url": sub_url,
            "vmess_length": len(vmess)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/batch', methods=['POST'])
def api_batch():
    """批量注册 10 个账号"""
    try:
        accounts = []
        ok_count = 0
        
        for i in range(10):
            email = gen_random_email()
            password = "nuosen666"
            
            ok1, data1, _ = sushi_register(email, password)
            if not ok1:
                continue
            
            ok2, data2, _ = sushi_login(email, password)
            if not ok2:
                continue
            
            auth = data2.get("auth_data", "") or ("Bearer " + data1.get("token", ""))
            bearer = auth.split("Bearer ", 1)[1] if auth.startswith("Bearer ") else auth
            
            sub_j = sushi_get_subscribe(bearer)
            if not isinstance(sub_j, dict) or sub_j.get("status") != "success":
                continue
            
            sub_url = sub_j.get("data", {}).get("subscribe_url", "")
            if not sub_url:
                continue
            
            accounts.append({
                "email": email,
                "password": password,
                "subscribe_url": sub_url
            })
            ok_count += 1
        
        return jsonify({
            "success": True,
            "total": 10,
            "success_count": ok_count,
            "accounts": accounts
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/health')
def health():
    return jsonify({"status": "ok", "service": "sushi-cloud-register"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
