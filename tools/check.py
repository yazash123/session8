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
    ok(members[1].evaluate("window.__listeners['col:s8-votes']||0") == 1, "results screen listens to all votes")
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
    ok(not errs, "no script errors" + ("" if not errs else ": " + "; ".join(errs[:3])))
    print("reads by host:", host.evaluate("window.__reads"), " by a member:", members[0].evaluate("window.__reads"))
    b.close()
srv.shutdown()
print("\nALL PASSED" if not fails else f"\n{len(fails)} FAILED"); sys.exit(1 if fails else 0)
