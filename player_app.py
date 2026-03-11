#!/usr/bin/env python3
import os
import json
import time
import random
import threading
from functools import lru_cache

import requests
from flask import Flask, jsonify, render_template_string

AZURE_CONFIG = os.environ.get("AZURE_CONFIG", "/opt/soop-downloader/azure_config.json")
ONEDRIVE_FOLDER = os.environ.get("ONEDRIVE_FOLDER", "SOOP_VOD")
MAX_PAGES = int(os.environ.get("MAX_PAGES", "2"))
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "300"))
CACHE_TTL = int(os.environ.get("CACHE_TTL", "600"))
REFRESH_INTERVAL = int(os.environ.get("REFRESH_INTERVAL", "180"))  # 3 min

app = Flask(__name__)

HTML = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>🍑 韩国小姐姐</title>
  <style>
    :root{
      --bg:#0b0d12;
      --bg2:#121724;
      --card:#151b2a;
      --line:#2a3145;
      --text:#ecf1ff;
      --sub:#9fb0d7;
      --primary:#4d7cff;
      --primary2:#7b5cff;
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      color:var(--text);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"PingFang SC","Microsoft YaHei",sans-serif;
      background:radial-gradient(1200px 600px at 50% -10%, #233053 0%, var(--bg) 60%), linear-gradient(145deg,var(--bg2),var(--bg));
      min-height:100vh;
    }
    .wrap{max-width:1120px;margin:0 auto;padding:18px 16px 22px}
    .title{
      text-align:left;
      font-weight:700;
      font-size:26px;
      letter-spacing:.5px;
      margin:2px 0 12px;
      text-shadow:0 2px 20px rgba(88,124,255,.25);
    }
    .panel{
      background:linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.01));
      border:1px solid var(--line);
      border-radius:16px;
      padding:14px;
      text-align:center;
      box-shadow:0 14px 45px rgba(0,0,0,.25);
      backdrop-filter: blur(6px);
    }
    .video-wrap{
      border-radius:12px;
      overflow:hidden;
      background:#000;
      border:1px solid #20263a;
    }
    video{
      display:block;
      margin:0 auto;
      width:100%;
      max-height:74vh;
      background:#000;
    }
    .status{
      margin-top:10px;
      color:var(--sub);
      font-size:14px;
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
    }
    .controls{
      margin-top:12px;
      display:flex;
      gap:12px;
      align-items:center;
      justify-content:center;
      flex-wrap:wrap;
    }
    .btn{
      border:0;
      color:#fff;
      cursor:pointer;
      padding:9px 14px;
      border-radius:10px;
      font-weight:600;
      background:linear-gradient(135deg,var(--primary),var(--primary2));
      box-shadow:0 6px 18px rgba(77,124,255,.28);
    }
    .btn:active{transform:translateY(1px)}
    .switch{
      display:flex;align-items:center;gap:7px;
      color:#d2dcf5;font-size:14px;
      padding:7px 10px;border-radius:10px;
      border:1px solid var(--line);
      background:rgba(255,255,255,.03)
    }
    .switch input{accent-color:#6f86ff}
    @media (max-width:768px){
      .wrap{padding:8px 10px 14px;min-height:100vh;display:flex;flex-direction:column}
      .title{margin:0 0 8px;font-size:22px;text-align:left}
      .panel{margin:auto 0;padding:10px;border-radius:14px}
      video{max-height:62vh}
      .status{font-size:13px}
    }
  </style>
</head>
<body>
  <div class="wrap">
    <h1 class="title">🍑 韩国小姐姐</h1>
    <div class="panel">
      <div class="video-wrap">
        <video id="player" controls autoplay playsinline preload="auto"></video>
      </div>
      <div id="now" class="status">正在加载随机视频...</div>
      <div class="controls">
        <button class="btn" onclick="playRandom()">随机下一个</button>
        <label class="switch">
          <input id="autonext" type="checkbox" checked />
          连续播放
        </label>
      </div>
    </div>
  </div>
<script>
const player = document.getElementById('player');
const nowEl = document.getElementById('now');
const autoNextEl = document.getElementById('autonext');
let preloaded = null;





function preconnect(url){
  try{
    const u = new URL(url);
    const l = document.createElement('link');
    l.rel = 'preconnect';
    l.href = u.origin;
    l.crossOrigin = 'anonymous';
    document.head.appendChild(l);
  }catch(e){}
}

async function getRandomVideo(){
  const r = await fetch('/api/random');
  const d = await r.json();
  if(!d.ok) throw new Error(d.error || '没有可播放视频');
  if (!d.url && d.id) {
    const r2 = await fetch('/api/play/'+encodeURIComponent(d.id));
    const d2 = await r2.json();
    if(!d2.ok) throw new Error(d2.error || '无法播放');
    d.url = d2.url;
    d.name = d2.name || d.name;
  }
  return d;
}

async function preloadNext(){
  try{
    preloaded = await getRandomVideo();
    if (preloaded?.url) preconnect(preloaded.url);
  }catch(e){
    preloaded = null;
  }
}

async function playByUrl(url, name){
  if(!url) throw new Error('播放链接为空');
  preconnect(url);
  player.src = url;
  nowEl.textContent = '正在播放: ' + (name || '未知视频');

  // one quick retry if initial start stalls/fails
  try {
    await player.play();
  } catch (e) {
    await new Promise(r => setTimeout(r, 500));
    await player.play().catch(()=>{});
  }
}

async function playRandom(){
  nowEl.textContent = '正在加载随机视频...';
  const picked = preloaded || await getRandomVideo();
  preloaded = null;
  await playByUrl(picked.url, picked.name);
  preloadNext();
}

async function boot(){
  preloadNext();
  for (let i = 0; i < 3; i++) {
    try {
      await playRandom();
      return;
    } catch (e) {
      nowEl.textContent = `加载中（重试 ${i+1}/3）...`;
      await new Promise(r => setTimeout(r, 900));
    }
  }
  nowEl.textContent = '加载失败，请稍后再试';
}

player.addEventListener('ended', () => {
  if (autoNextEl && autoNextEl.checked) {
    playRandom();
  }
});

boot();
</script>
</body>
</html>
"""


def load_cfg():
    with open(AZURE_CONFIG, "r", encoding="utf-8") as f:
        c = json.load(f)
    required = ["tenant_id", "client_id", "client_secret", "drive_user"]
    miss = [k for k in required if not c.get(k)]
    if miss:
        raise RuntimeError(f"azure_config 缺少字段: {', '.join(miss)}")
    return c


_token_cache = {"token": None, "exp": 0}


def get_token():
    now = int(time.time())
    if _token_cache["token"] and now < _token_cache["exp"] - 120:
        return _token_cache["token"]

    cfg = load_cfg()
    url = f"https://login.microsoftonline.com/{cfg['tenant_id']}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "scope": "https://graph.microsoft.com/.default",
    }
    resp = requests.post(url, data=data, timeout=20)
    j = resp.json()
    if "access_token" not in j:
        raise RuntimeError(j.get("error_description") or str(j))

    _token_cache["token"] = j["access_token"]
    _token_cache["exp"] = now + int(j.get("expires_in", 3600))
    return _token_cache["token"]


def graph_get(path, params=None):
    cfg = load_cfg()
    token = get_token()
    url = f"https://graph.microsoft.com/v1.0/users/{cfg['drive_user']}{path}"
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
    if r.status_code >= 400:
        raise RuntimeError(f"Graph API {r.status_code}: {r.text[:400]}")
    return r.json()


@lru_cache(maxsize=1)
def folder_item_id():
    j = graph_get(f"/drive/root:/{ONEDRIVE_FOLDER}")
    return j["id"]


_video_cache = {"ts": 0, "items": []}
_recent_ids = []


def list_videos(force: bool = False):
    now = time.time()
    if (not force) and _video_cache["items"] and (now - _video_cache["ts"]) < CACHE_TTL:
        return _video_cache["items"]

    fid = folder_item_id()
    items = []
    next_url = f"https://graph.microsoft.com/v1.0/users/{load_cfg()['drive_user']}/drive/items/{fid}/children?$top=200"
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    page_count = 0

    while next_url and page_count < MAX_PAGES and len(items) < MAX_ITEMS:
        page_count += 1
        r = requests.get(next_url, headers=headers, timeout=20)
        if r.status_code >= 400:
            raise RuntimeError(f"Graph list error {r.status_code}: {r.text[:300]}")
        j = r.json()
        for it in j.get("value", []):
            name = it.get("name", "")
            if "file" not in it:
                continue
            if not name.lower().endswith((".mp4", ".mkv", ".webm", ".mov", ".m4v")):
                continue
            items.append({
                "id": it["id"],
                "name": name,
                "size": it.get("size", 0),
                "lastModifiedDateTime": it.get("lastModifiedDateTime", ""),
                "downloadUrl": it.get("@microsoft.graph.downloadUrl", ""),
            })
            if len(items) >= MAX_ITEMS:
                break
        next_url = j.get("@odata.nextLink")

    items.sort(key=lambda x: x.get("lastModifiedDateTime", ""), reverse=True)
    _video_cache["items"] = items
    _video_cache["ts"] = now
    return items


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/videos")
def api_videos():
    try:
        return jsonify({"ok": True, "items": list_videos()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "items": []}), 500


@app.route("/api/random")
def api_random():
    try:
        items = list_videos()
        if not items:
            return jsonify({"ok": False, "error": "没有可播放视频"}), 404

        # avoid recent repeats (better UX, less same-file rebuffer)
        global _recent_ids
        pool = [x for x in items if x["id"] not in _recent_ids]
        if not pool:
            _recent_ids = []
            pool = items

        pick = random.choice(pool)
        _recent_ids.append(pick["id"])
        if len(_recent_ids) > 20:
            _recent_ids = _recent_ids[-20:]

        # return url directly to reduce one extra API round-trip
        durl = pick.get("downloadUrl")
        if not durl:
            token = get_token()
            cfg = load_cfg()
            url = f"https://graph.microsoft.com/v1.0/users/{cfg['drive_user']}/drive/items/{pick['id']}"
            r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=15)
            j = r.json()
            durl = j.get("@microsoft.graph.downloadUrl", "")

        return jsonify({"ok": True, "id": pick["id"], "name": pick["name"], "url": durl})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/play/<item_id>")
def api_play(item_id):
    try:
        token = get_token()
        cfg = load_cfg()
        url = f"https://graph.microsoft.com/v1.0/users/{cfg['drive_user']}/drive/items/{item_id}"
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        j = r.json()
        durl = j.get("@microsoft.graph.downloadUrl")
        if not durl:
            return jsonify({"ok": False, "error": "未获取到播放链接"}), 400
        return jsonify({"ok": True, "url": durl, "name": j.get("name", "")})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/healthz")
def healthz():
    return "ok", 200


def warmup_cache():
    try:
        list_videos(force=True)
        app.logger.info("Cache warmup done")
    except Exception as e:
        app.logger.warning(f"Cache warmup failed: {e}")


def refresh_loop():
    while True:
        try:
            list_videos(force=True)
            app.logger.info("Cache refresh done")
        except Exception as e:
            app.logger.warning(f"Cache refresh failed: {e}")
        time.sleep(REFRESH_INTERVAL)


if __name__ == "__main__":
    threading.Thread(target=warmup_cache, daemon=True).start()
    threading.Thread(target=refresh_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=8090)
