#!/usr/bin/env python3
"""Browser check of the hosted page with a fake Firestore (tools/fakefirestore.js): no real Firebase,
rules or network. Run: python3 tools/check.py   (needs Python Playwright + Chromium)"""
import http.server, threading, functools, pathlib, json, sys
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
FAKE = (ROOT / "tools" / "fakefirestore.js").read_text()
DB = {"v": "{}"}
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/__fakefs"):
            b = DB["v"].encode(); self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        return super().do_GET()
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); DB["v"] = self.rfile.read(n).decode()
        self.send_response(204); self.end_headers()
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Q, directory=str(ROOT)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
fails = []
def ok(c, msg):
    print(("PASS " if c else "FAIL ") + msg)
    if not c: fails.append(msg)

with sync_playwright() as p:
    b = p.chromium.launch()
    def route(r):
        u = r.request.url
        r.fulfill(body=FAKE if "app-compat" in u else "", content_type="application/javascript")
    errs = []
    def page(hash_, name=None):
        ctx = b.new_context(viewport={"width": 1280, "height": 900})   # one browser per person
        ctx.route("https://www.gstatic.com/firebasejs/**", route)
        if name: ctx.add_init_script("localStorage.getItem('s8-me')||localStorage.setItem('s8-me',JSON.stringify({name:%r,pid:'p'+Math.random().toString(36).slice(2,12),room:%d}))" % (name, len(name)))
        pg = ctx.new_page()
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(URL + hash_); pg.wait_for_timeout(900)
        return pg
    host = page("#vote-host")
    ok(host.evaluate("!!window.S8DB && !!window.S8HOST"), "Firestore shim and host sign-in loaded")
    ok(host.locator('#tabs [data-tab="wording"]').count() == 0, "no Wording tab")
    ok(not host.locator("#editOn").is_visible(), "no Edit button on the web page")
    ok(host.evaluate("document.body.classList.contains('noedit')"), "body.noedit set")
    host.fill("#v-hp", "wrongpass"); host.click("#v-hpf button"); host.wait_for_timeout(300)
    ok("isn’t right" in host.inner_text("#v-hpn"), "wrong host passcode refused")
    host.fill("#v-hp", "TestPass1"); host.click("#v-hpf button"); host.wait_for_timeout(500)
    ok(host.locator("[data-go]").count() > 0, "right passcode (any case) opens host controls")
    host.locator("[data-go]").first.click(); host.wait_for_timeout(400)
    cfg = host.evaluate("window.__fakeload()['s8-config/main']")
    ok(bool(cfg) and cfg.get("phase") not in (None, "idle"), f"host opened the vote: config {cfg and cfg.get('phase')}")
    ok(set(cfg).issubset({'set','phase','endsAt','addOpen','pickPhase','pickEnds','showResults','stamp','paper'}), "config keys match the rules")

    members = [page("#vote-drivers", n) for n in ("Amara", "Ben", "Chi")]
    for i, m in enumerate(members):
        m.wait_for_timeout(300)
        n = m.locator("#vv-drivers [data-pick]").count()
        if i == 0:
            ok(n >= 2, f"member sees a pair to vote on ({n} buttons)")
        for k in range(6):
            if m.locator("#vv-drivers [data-pick]").count() < 2: break
            m.locator("#vv-drivers [data-pick]").nth(k % 2).click(); m.wait_for_timeout(120)
    members[0].wait_for_timeout(500)
    db = host.evaluate("window.__fakeload()")
    votes = {k: v for k, v in db.items() if k.startswith("s8-votes/")}
    ok(len(votes) == 18, f"18 votes stored in s8-votes ({len(votes)})")
    allowed = {'set','a','b','w','r','by','name','room','at'}
    ok(all(set(v) <= allowed and {'set','a','b','w','by','name','room','at'} <= set(v) and v['w'] in (v['a'], v['b'], None) and isinstance(v['at'], int) for v in votes.values()), "every vote has the shape the rules accept")
    ok(len({v['by'] for v in votes.values()}) == 3, "three different voters")
    ok(not any(k.startswith(("votes/", "config/", "picks/", "ideas/", "edits/")) for k in db), "nothing written outside s8- collections")
    # undo
    members[0].evaluate("1"); und = members[0].locator("text=Undo my last choice")
    if und.count():
        und.first.click(); members[0].wait_for_timeout(300)
        n2 = len([k for k in host.evaluate("Object.keys(window.__fakeload())") if k.startswith("s8-votes/")])
        ok(n2 == 17, f"undo removes one vote ({n2})")
    lis = [m.evaluate("window.__listeners['col:s8-votes']||0") for m in members]
    ok(lis == [0, 0, 0], f"members voting don't listen to all votes {lis}")
    ok(host.evaluate("window.__listeners['col:s8-votes']||0") == 1, "host listens to all votes")
    members[1].goto(URL + "#vote-results"); members[1].wait_for_timeout(700)
    ok(members[1].evaluate("window.__listeners['col:s8-votes']||0") == 0, "a member's results screen doesn't read every vote")
    ok("appear" in members[1].inner_text("#vv-results").lower(), "members see 'results will appear' before the host shows them")
    host.locator('[data-sr="1"]').first.click(); host.wait_for_timeout(900)
    cfg = host.evaluate("window.__fakeload()['s8-config/main']")
    ok(cfg.get("showResults") and len(cfg.get("snap", {}).get("v", [])) == 17, f"showing results publishes a copy of the 17 votes ({len((cfg.get('snap') or {}).get('v', []))})")
    txt = members[1].inner_text("#vv-results")
    ok(__import__("re").search(r"17\s*choices", txt) is not None, "member's results show the House's 17 choices: " + txt[:80].replace("\n", " "))
    members[1].goto(URL + "#vote-drivers"); members[1].wait_for_timeout(300)
    # pick five
    host.goto(URL + "#vote-host"); host.wait_for_timeout(600)
    if host.locator("[data-pk5]").count(): host.locator("[data-pk5]").first.click(); host.wait_for_timeout(400)
    m = members[2]; m.goto(URL + "#vote-risks"); m.wait_for_timeout(800)
    m.evaluate("""['R01','N05','R12','N13','R07'].forEach(function(id){var b=document.createElement('button');b.setAttribute('data-pk',id);document.body.appendChild(b);b.click();b.remove();})""")
    m.wait_for_timeout(300)
    if m.locator("#pk-save").count(): m.locator("#pk-save").click(); m.wait_for_timeout(500)
    picks = {k: v for k, v in host.evaluate("window.__fakeload()").items() if k.startswith("s8-picks/")}
    ok(len(picks) == 1 and len(list(picks.values())[0]["ids"]) == 5 and set(list(picks.values())[0]) <= {"ids","name","room","at"}, f"five picks saved with the rules' shape {picks}")
    m.reload(); m.wait_for_timeout(1000)
    ok(m.evaluate("document.querySelectorAll('#pk-head [data-pk], .pkchips [data-pk]').length") >= 5 or "5 of 5" in m.inner_text("#vv-risks") or "Submitted" in m.inner_text("#vv-risks") or "sent" in m.inner_text("#vv-risks").lower(), "picks come back after a reload")
    m.screenshot(path="/tmp/picks.png")
    # a member whose clock is 3 minutes slow: Close now still closes voting for them
    slow = page("#vote-drivers", "Dee")
    host.goto(URL + "#vote-host"); host.wait_for_timeout(600)
    slow.evaluate("(function(){var r=Date.now;Date.now=function(){return r()-180000;};})()")
    host.locator("[data-go]").first.click(); host.wait_for_timeout(900)
    host.locator("#v-stop").click(); host.wait_for_timeout(900)
    ok("isn’t open" in slow.inner_text("#vv-drivers").lower() and slow.locator("#vv-drivers [data-pick]").count() == 0, "Close now closes voting for a member with a slow clock")
    # Download: the host's copy before clearing
    import csv, io
    host.goto(URL + "#vote-host"); host.wait_for_timeout(900)
    with host.expect_download() as d1: host.click("#v-dlv")
    rows = list(csv.reader(io.StringIO(open(d1.value.path(), encoding="utf-8-sig").read())))
    nv = len([k for k in host.evaluate("Object.keys(window.__fakeload())") if k.startswith("s8-votes/")])
    ok(len(rows) - 1 == nv and rows[0][0] == "Time" and all(r[10] or r[11] for r in rows[1:]), f"votes download has a row per vote ({len(rows)-1} of {nv}), each with a choice or a reason")
    with host.expect_download() as d2: host.click("#v-dlp")
    prow = list(csv.reader(io.StringIO(open(d2.value.path(), encoding="utf-8-sig").read())))
    ok(len(prow) == 2 and prow[1][1] == "Chi" and prow[1][4] and prow[1][9].count(" ") == 4, f"picks download has Chi's five picks {prow[1][:5] if len(prow)>1 else prow}")
    print("   sample vote row:", rows[1][:2], rows[1][5:11])
    # Clear: two clicks, everything emptied, members' screens reset
    host.locator("#v-reset").click(); host.wait_for_timeout(300); host.locator("#v-reset").click(); host.wait_for_timeout(1200)
    db = host.evaluate("window.__fakeload()")
    ok(not any(k.startswith(("s8-votes/", "s8-picks/", "s8-ideas/")) for k in db), "Clear empties votes, picks and ideas")
    c2 = db.get("s8-config/main", {})
    ok(not c2.get("showResults") and c2.get("pickPhase") == "idle" and not c2.get("snap"), "Clear also hides results and closes picking")
    m.goto(URL + "#vote-risks"); m.wait_for_timeout(900)
    ok("saved" not in m.inner_text("#vv-risks").lower(), "a cleared member's picks no longer say saved")
    ok(not errs, "no script errors" + ("" if not errs else ": " + "; ".join(errs[:3])))
    print("reads by host:", host.evaluate("window.__reads"), " by a member:", members[0].evaluate("window.__reads"))
    b.close()
srv.shutdown()
print("\nALL PASSED" if not fails else f"\n{len(fails)} FAILED"); sys.exit(1 if fails else 0)
