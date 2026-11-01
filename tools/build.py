#!/usr/bin/env python3
"""Build index.html (the hosted page) from src/session8.html (the claude.ai artifact, unchanged).

The artifact talks to claude.ai's shared storage through window.claude.use('db'), which has the
same shape as Firestore's compat API. The hosted page swaps that for Firestore:
  * loads the Firebase SDK (app, firestore, auth) and firebase-config.js
  * window.S8DB   = Firestore with every collection prefixed "s8-" (votes -> s8-votes, ...)
  * window.S8HOST = host sign-in (Firebase email/password user HOST_EMAIL; password = the host passcode)
  * the page boots with no Edit button and connects only the Ranking votes (no shared wording edits)
Each change is an exact one-off replacement, so a changed artifact fails loudly instead of building wrong.

Usage: python3 tools/build.py            (writes index.html next to src/)
"""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SDK = "10.14.1"
HOST_EMAIL = "host@houseofthepeople.uk"

HEAD = f"""<script src="https://www.gstatic.com/firebasejs/{SDK}/firebase-app-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/{SDK}/firebase-firestore-compat.js"></script>
<script src="https://www.gstatic.com/firebasejs/{SDK}/firebase-auth-compat.js"></script>
<script src="firebase-config.js"></script>
<script>
/* Session 8 on Firestore: the artifact's storage calls, pointed at the "s8-" collections. */
(function(){{
  var P='s8-', HOST_EMAIL='{HOST_EMAIL}';
  try{{
    var C=window.FIREBASE_CONFIG;
    if(!(window.firebase&&C&&C.projectId))return;
    if(!firebase.apps.length)firebase.initializeApp(C);
    var fs=firebase.firestore();
    try{{fs.settings({{experimentalAutoDetectLongPolling:true,merge:true}});}}catch(e){{}}
    window.S8DB={{doc:function(p){{return fs.doc(P+p);}},collection:function(n){{return fs.collection(P+n);}}}};
    if(firebase.auth){{
      var au=firebase.auth();
      window.S8HOST={{
        signIn:function(pw){{return au.signInWithEmailAndPassword(HOST_EMAIL,pw).then(function(){{return true;}},function(e){{console.warn('[session8] host sign-in refused',e&&e.code);return false;}});}},
        watch:function(fn){{au.onAuthStateChanged(function(u){{fn(!!(u&&u.email===HOST_EMAIL));}});}}
      }};
    }}
  }}catch(e){{console.error('[session8] Firebase failed to start',e);}}
}})();
</script>
"""

def build():
    s = (ROOT / "src" / "session8.html").read_text(encoding="utf-8")
    def rep(old, new):
        nonlocal s
        n = s.count(old)
        if n != 1:
            sys.exit(f"build.py: expected exactly one of {old[:70]!r}, found {n}. Has the artifact changed?")
        s = s.replace(old, new)
    # 1. SDK, config and the shim, just before the app script
    rep("</script>\n<script>\n(function(){'use strict';", "</script>\n" + HEAD + "<script>\n(function(){'use strict';")
    # 2. the artifact's host passcode check is not used on the web (Firebase checks the passcode)
    rep("var HOSTHASH='740b21f9'; /* the passcode: lighthouse */", "var HOSTHASH=''; /* hosted: the passcode is checked by Firebase sign-in */")
    # 3. boot: words fixed (no Edit), votes on Firestore
    old_boot_start = "  if(!(window.claude&&window.claude.use))document.body.classList.add('noedit');"
    a = s.index(old_boot_start)
    b = s.index("}).catch(function(){});\n  }\n", a) + len("}).catch(function(){});\n  }\n")
    if s.count(old_boot_start) != 1:
        sys.exit("build.py: boot block not found exactly once")
    s = s[:a] + ("  document.body.classList.add('noedit'); /* hosted: words are fixed, no Edit */\n"
                 "  if(window.S8DB)VIEW.vote.connect(window.S8DB,null);\n") + s[b:]
    for bad in ("window.claude.use('db'),window.claude.use('user')", "lighthouse"):
        if bad in s:
            sys.exit(f"build.py: {bad!r} still in the hosted page")
    (ROOT / "index.html").write_text(s, encoding="utf-8")
    print(f"index.html: {len(s):,} bytes")

if __name__ == "__main__":
    build()
