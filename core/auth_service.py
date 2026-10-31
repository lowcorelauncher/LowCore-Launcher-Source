import os
import uuid
import hashlib
import time
import requests

# Xbox App for PC / Minecraft Java public Client ID
# Override with your own Azure app registration via LOWCORE_MS_CLIENT_ID if you distribute the launcher.
MS_CLIENT_ID = os.environ.get("LOWCORE_MS_CLIENT_ID", "00000000402b5328")

DEVICE_CODE_URL = "https://login.live.com/oauth20_connect.srf"
TOKEN_URL = "https://login.live.com/oauth20_token.srf"

XBL_AUTH_URL = "https://user.auth.xboxlive.com/user/authenticate"
XSTS_AUTH_URL = "https://xsts.auth.xboxlive.com/xsts/authorize"
MC_AUTH_URL = "https://api.minecraftservices.com/authentication/login_with_xbox"
MC_PROFILE_URL = "https://api.minecraftservices.com/minecraft/profile"

XSTS_ERRORS = {
    2148916227: "This Xbox account has been banned from Xbox Live.",
    2148916229: "This account is restricted by Xbox parental controls. Ask the family organizer to allow online play.",
    2148916233: "This Microsoft account has no Xbox profile yet. Sign in once at xbox.com (or the Minecraft Launcher) to create one, then try again.",
    2148916234: "This Xbox account must accept the Xbox Terms of Service before it can sign in.",
    2148916235: "Xbox Live is not available in your country/region.",
    2148916236: "This account needs adult verification on Xbox before it can sign in.",
    2148916237: "This account needs adult verification on Xbox before it can sign in.",
    2148916238: "This is a child account. An adult must add it to a Microsoft Family before it can play online.",
}


class AuthService:
    @staticmethod
    def create_offline_account(username: str) -> dict:
        raw_hash = hashlib.md5(f"OfflinePlayer:{username}".encode("utf-8")).digest()
        offline_uuid = str(uuid.UUID(bytes=raw_hash[:16]))

        return {
            "id": offline_uuid,
            "name": username,
            "type": "offline",
            "access_token": "0",
            "refresh_token": ""
        }

    @staticmethod
    def start_device_code_flow() -> dict:
        payload = {
            "client_id": MS_CLIENT_ID,
            "scope": "service::user.auth.xboxlive.com::MBI_SSL",
            "response_type": "device_code"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests.post(DEVICE_CODE_URL, data=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise RuntimeError(f"{resp.status_code} Error: {resp.text}")
        return resp.json()

    @staticmethod
    def poll_for_login(device_code: str, interval: int = 5, expires_in: int = 900, status_cb=None) -> dict:
        start_time = time.time()
        poll_interval = max(interval, 5)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        while time.time() - start_time < expires_in:
            time.sleep(poll_interval)
            payload = {
                "client_id": MS_CLIENT_ID,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code
            }
            res = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=15)
            data = res.json()

            if "access_token" in data:
                ms_token = data["access_token"]
                refresh_token = data.get("refresh_token", "")
                if status_cb:
                    status_cb("Microsoft token acquired. Authenticating with Xbox Live...")
                return AuthService._complete_mc_login(ms_token, refresh_token, status_cb)

            err = data.get("error")
            if err == "authorization_pending":
                continue
            elif err == "slow_down":
                poll_interval += 5
            elif err in ("expired_token", "access_denied"):
                raise RuntimeError(f"Sign-in cancelled or expired: {err}")
            else:
                raise RuntimeError(f"OAuth Error: {data.get('error_description', err)}")

        raise TimeoutError("Device authentication flow timed out.")

    @staticmethod
    def refresh_microsoft_token(refresh_token: str) -> dict:
        payload = {
            "client_id": MS_CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": "service::user.auth.xboxlive.com::MBI_SSL"
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        res = requests.post(TOKEN_URL, data=payload, headers=headers, timeout=15)
        if res.status_code != 200:
            raise RuntimeError(f"{res.status_code} Refresh Failed: {res.text}")
        data = res.json()
        new_ms_token = data["access_token"]
        new_refresh = data.get("refresh_token", refresh_token)
        return AuthService._complete_mc_login(new_ms_token, new_refresh)

    @staticmethod
    def _complete_mc_login(ms_token: str, refresh_token: str, status_cb=None) -> dict:
        # 1. Xbox Live Token (Live.com tokens require 't=' or raw token ticket)
        ticket_val = f"t={ms_token}" if not ms_token.startswith("t=") else ms_token
        xbl_payload = {
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": ticket_val
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT"
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        xbl_res = requests.post(XBL_AUTH_URL, json=xbl_payload, headers=headers, timeout=15)
        
        # If 't=' fails on specific configurations, retry raw token
        if xbl_res.status_code == 401 and "t=" in ticket_val:
            xbl_payload["Properties"]["RpsTicket"] = ms_token
            xbl_res = requests.post(XBL_AUTH_URL, json=xbl_payload, headers=headers, timeout=15)

        xbl_res.raise_for_status()
        xbl_data = xbl_res.json()
        xbl_token = xbl_data["Token"]
        user_hash = xbl_data["DisplayClaims"]["xui"][0]["uhs"]

        # 2. XSTS Token
        if status_cb:
            status_cb("Requesting XSTS authorization...")
        xsts_payload = {
            "Properties": {
                "SandboxId": "RETAIL",
                "UserTokens": [xbl_token]
            },
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT"
        }
        xsts_res = requests.post(XSTS_AUTH_URL, json=xsts_payload, headers=headers, timeout=15)
        if xsts_res.status_code == 401:
            try:
                xerr = int(xsts_res.json().get("XErr", 0))
            except Exception:
                xerr = 0
            if xerr in XSTS_ERRORS:
                raise RuntimeError(XSTS_ERRORS[xerr])
        xsts_res.raise_for_status()
        xsts_token = xsts_res.json()["Token"]

        # 3. Minecraft Service Token
        if status_cb:
            status_cb("Logging into Minecraft Services...")
        mc_payload = {
            "identityToken": f"XBL3.0 x={user_hash};{xsts_token}"
        }
        mc_res = requests.post(MC_AUTH_URL, json=mc_payload, headers=headers, timeout=15)
        if mc_res.status_code == 403:
            raise RuntimeError("Minecraft services rejected this sign-in (403). Try again in a few minutes.")
        mc_res.raise_for_status()
        mc_token = mc_res.json()["access_token"]

        # 4. Minecraft Profile
        prof_headers = {"Authorization": f"Bearer {mc_token}"}
        prof_res = requests.get(MC_PROFILE_URL, headers=prof_headers, timeout=15)
        if prof_res.status_code == 404:
            raise RuntimeError("This Microsoft account does not own Minecraft: Java Edition (no profile found).")
        prof_res.raise_for_status()
        prof = prof_res.json()

        raw_id = prof.get("id", "").strip().replace("-", "")
        if len(raw_id) == 32:
            formatted_uuid = f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"
        else:
            formatted_uuid = prof.get("id", "")

        return {
            "id": formatted_uuid,
            "name": prof.get("name", "Player"),
            "type": "ms",
            "access_token": mc_token,
            "refresh_token": refresh_token
        }