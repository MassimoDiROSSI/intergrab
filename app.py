from flask import Flask, request, jsonify
import requests
import re
import os

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# ==================== ING ENDPOINTS (existing) ====================

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Bank Mask API</title></head>
    <body style="font-family:Arial; padding:40px;">
        <h2>Mask Grab APIs</h2>
        <ul>
            <li><a href="/test-ing">ING Test</a></li>
            <li><a href="/test-bankinter">Bankinter Test</a></li>
        </ul>
    </body>
    </html>
    """

@app.route("/test-ing")
def test_ing():
    return """
    <!DOCTYPE html>
    <html>
    <head><title>ING Mask Test</title></head>
    <body style="font-family:Arial; padding:40px; background:#f5f5f5;">
        <div style="max-width:500px; margin:0 auto; background:white; padding:30px; border-radius:8px;">
            <h2 style="color:#ff6200;">ING Mask Grab</h2>
            <input type="text" id="username" placeholder="Enter username" style="width:100%; padding:12px; margin:10px 0;">
            <button onclick="getMask()" style="width:100%; padding:12px; background:#ff6200; color:white; border:none; cursor:pointer;">Get Mask</button>
            <pre id="result" style="margin-top:20px; background:#f8f8f8; padding:15px;"></pre>
        </div>
        <script>
        async function getMask() {
            const u = document.getElementById("username").value;
            document.getElementById("result").innerHTML = "Loading...";
            const r = await fetch("/get-mask?username=" + encodeURIComponent(u));
            const d = await r.json();
            document.getElementById("result").innerHTML = JSON.stringify(d, null, 2);
        }
        </script>
    </body>
    </html>
    """

@app.route("/get-mask")
def get_mask():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username required"}), 400

    session = requests.Session()

    try:
        app_resp = session.get(
            "https://login.ingbank.pl/mojeing/app/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "cs,fr;q=0.9,fr-FR;q=0.8,en-US;q=0.7,en;q=0.6",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1",
            },
            timeout=15
        )

        auth_resp = session.get(
            "https://login.ingbank.pl/oauth2/oauth2authorize",
            params={
                "response_type": "code",
                "client_id": "mojeing",
                "scope": "openid standard",
                "state": "test",
                "redirect_uri": "https://login.ingbank.pl/mojeing/rest/oauth2/code/nma",
                "nonce": "test",
                "code_challenge": "test",
                "code_challenge_method": "S256",
                "custom": "null"
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
            },
            allow_redirects=False,
            timeout=15
        )

        location = auth_resp.headers.get("Location", "")
        ref_match = re.search(r"ref=([a-zA-Z0-9]+)", location)
        ref = ref_match.group(1) if ref_match else None

        if not ref:
            return jsonify({"error": "No ref found", "location": location, "status": auth_resp.status_code}), 500

        init_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2init",
            json={"token": "", "trace": "", "data": {"ref": ref, "screenType": "D"}, "locale": "PL"},
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "application/json",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=15
        )

        init_data = init_resp.json()

        if init_data.get("status") != "OK":
            return jsonify({"error": "init failed", "init_response": init_data}), 500

        auth_ref = init_data["data"]["authorizationReference"]
        csrf = init_data["data"]["csrfToken"]

        getauth_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2getauthdata",
            json={"token": csrf, "trace": "", "data": {"ref": auth_ref}, "locale": "PL"},
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "application/json",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-Token": csrf,
            },
            timeout=15
        )

        getauth_data = getauth_resp.json()

        if getauth_data.get("status") != "OK":
            return jsonify({"error": "getauthdata failed", "getauth_response": getauth_data}), 500

        confirm_ref = getauth_data["data"]["ref"]

        confirm_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2confirm",
            json={"token": csrf, "trace": "", "data": {"factor": "LOGIN", "ref": confirm_ref, "credentials": username}, "locale": "PL"},
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "application/json",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-Token": csrf,
            },
            timeout=15
        )

        confirm_data = confirm_resp.json()

        if confirm_data.get("status") != "OK":
            return jsonify({"error": "confirm failed", "confirm_response": confirm_data}), 500

        challenge = confirm_data.get("data", {}).get("challenge", {})
        mask = challenge.get("mask")

        if mask:
            required_positions = [i for i, c in enumerate(mask) if c == "*"]
        else:
            required_positions = []

        return jsonify({
            "success": True,
            "username": username,
            "factor": confirm_data.get("data", {}).get("factor"),
            "mask": mask,
            "mask_length": len(mask) if mask else 0,
            "required_positions": required_positions,
            "required_count": len(required_positions),
            "salt": challenge.get("salt"),
            "key": challenge.get("key"),
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


# ==================== BANKINTER ENDPOINTS (new) ====================

@app.route("/test-bankinter")
def test_bankinter():
    return """
    <!DOCTYPE html>
    <html lang="pt">
    <head>
        <meta charset="UTF-8">
        <title>Bankinter Mask Test</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 40px; background: #f5f5f5; }
            .wrap { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h2 { color: #c41230; margin-top: 0; }
            input[type="text"] { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
            button { width: 100%; padding: 12px; background: #c41230; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-top: 10px; }
            button:hover { background: #a01028; }
            pre { margin-top: 20px; background: #f8f8f8; padding: 15px; border-radius: 4px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <div class="wrap">
            <h2>Bankinter Mask Grab</h2>
            <input type="text" id="username" placeholder="Enter username (e.g. rain2020)">
            <button onclick="getMask()">Get Mask</button>
            <pre id="result"></pre>
        </div>
        <script>
        async function getMask() {
            const u = document.getElementById("username").value;
            document.getElementById("result").innerHTML = "Loading...";
            const r = await fetch("/get-mask-bankinter?username=" + encodeURIComponent(u));
            const d = await r.json();
            document.getElementById("result").innerHTML = JSON.stringify(d, null, 2);
        }
        </script>
    </body>
    </html>
    """

@app.route("/get-mask-bankinter")
def get_mask_bankinter():
    """
    Bankinter Portugal mask grab.
    Flow:
      1. POST /particulares/waitLoginMC.jsp  (UserName=xxx)
      2. GET  /particulares/indexHomeCod.jsp  (response contains two masked forms)
      3. Parse HTML to find which idNif* and idMulti* inputs are NOT disabled
    """
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username required"}), 400

    session = requests.Session()

    try:
        # Step 1: POST waitLoginMC.jsp
        wait_resp = session.post(
            "https://banco.bankinter.pt/particulares/waitLoginMC.jsp",
            data={
                "location": "/particulares/indexHomeCod.jsp",
                "source": "/particulares/index.html",
                "UserName": username,
                "Origem": "null",
                "txtUserName": ""
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-PT,pt;q=0.9,en-US;q=0.7,en;q=0.5",
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://banco.bankinter.pt",
                "Referer": "https://banco.bankinter.pt/particulares/index.html",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Upgrade-Insecure-Requests": "1",
            },
            allow_redirects=True,
            timeout=20
        )

        # Step 2: We should now be on indexHomeCod.jsp (or follow redirect)
        html = wait_resp.text

        # If we got redirected, the HTML should contain the masks
        # Parse which inputs are disabled vs enabled

        # Find idNif inputs (Elemento de Identificação) — usually 9 positions
        nif_open = []
        for i in range(1, 10):
            # Look for idNif{i} — if NOT disabled, it's open
            pattern = rf'<input[^>]*id="idNif{i}"[^>]*>'
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                tag = match.group(0)
                if 'disabled' not in tag.lower():
                    nif_open.append(i)

        # Find idMulti inputs (Código Multicanal) — usually 7 positions
        multi_open = []
        for i in range(1, 8):
            pattern = rf'<input[^>]*id="idMulti{i}"[^>]*>'
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                tag = match.group(0)
                if 'disabled' not in tag.lower():
                    multi_open.append(i)

        # If parsing failed (e.g., site changed or blocked), return mock for debugging
        if not nif_open and not multi_open:
            # Fallback: try to extract from the text hints like "posições 2 - 7"
            hint_nif = re.search(r'posiÃ§Ãµes\s+<strong>([^<]+)</strong>\s+do elemento', html, re.IGNORECASE)
            hint_multi = re.search(r'posiÃ§Ãµes\s+<strong>([^<]+)</strong>\s+do c', html, re.IGNORECASE)

            if hint_nif:
                nums = re.findall(r'\d+', hint_nif.group(1))
                nif_open = [int(n) for n in nums]
            if hint_multi:
                nums = re.findall(r'\d+', hint_multi.group(1))
                multi_open = [int(n) for n in nums]

        # If still empty, return error with partial HTML for debugging
        if not nif_open and not multi_open:
            return jsonify({
                "error": "Could not parse masks from response",
                "status": wait_resp.status_code,
                "url": wait_resp.url,
                "html_snippet": html[:2000]
            }), 500

        return jsonify({
            "success": True,
            "username": username,
            "identification": {
                "label": "Elemento de Identificação",
                "total": 9,
                "open_positions": nif_open,
                "locked_char": "•"
            },
            "multichannel": {
                "label": "Código Multicanal",
                "total": 7,
                "open_positions": multi_open,
                "locked_char": "•"
            }
        })

    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
