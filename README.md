# Session 8: Our priorities

The House of the People's Session 8 page (Tuesday 3 November): Recap, Set up, Our room and Ranking.
Served by GitHub Pages at `https://yazash123.github.io/session8/` and framed into
`houseofthepeople.uk/session8` by `webflow-embed.html`.

## Files

| file | what it is |
|---|---|
| `src/session8.html` | The claude.ai artifact, exactly as published there. **This is the source of truth.** |
| `index.html` | The hosted page. Built from `src/` by `tools/build.py`; don't edit by hand. |
| `firebase-config.js` | The Firebase web config for project `session-5-activity`. Public by design: the rules protect the data. |
| `firestore.rules` | The complete rules to paste into the Firebase console. |
| `webflow-embed.html` | Paste into one Webflow Code Embed on the `/session8` page. |
| `tools/build.py` | Turns the artifact into `index.html` (adds Firebase, hides Edit, connects the votes). |
| `tools/check.py`, `tools/fakefirestore.js` | A browser test with a fake Firestore: host sign-in, voting by three people, undo, picks, listener counts. |

To update after the artifact changes: save the artifact's HTML over `src/session8.html`, run
`python3 tools/build.py && python3 tools/check.py`, commit, push. Pages takes a few minutes to update.

## How the votes are stored

The page writes to four collections in the shared `session-5-activity` project, all starting `s8-`:

| collection | one document per | who writes |
|---|---|---|
| `s8-config` (`main`) | the session: which vote is open, timers, results shown | host only |
| `s8-votes` | pairwise choice `{set, a, b, w, r?, by, name, room, at}` | any member; they can undo their own for a few minutes |
| `s8-picks` | member (id = browser id): their five risks `{ids, name, room, at}` | the member |
| `s8-ideas` | driver a member added during the vote | any member; only the host hides or removes |

**Reads stay small.** Only the host screen and the results screen listen to every vote and pick. A member
who is voting reads only the session settings, the added ideas and their own picks. With about 100
members that is roughly 15,000 to 25,000 reads for the evening instead of several hundred thousand,
well inside the free 50,000 a day.

**The host signs in.** The lock on Ranking → host controls asks for the passcode, and the page signs in
to Firebase as `host@houseofthepeople.uk` with that passcode as the password. The rules let only that
sign-in change settings, hide ideas or clear votes. The passcode is never in the page source.

## Before Tuesday (Yaz)

1. **Host user.** Firebase console → `session-5-activity` → Build → Authentication → Get started →
   Sign-in method → Email/Password → Enable → Save. Then Users → Add user: email
   `host@houseofthepeople.uk`, password = the host passcode, **all lower case**, at least 6 characters.
2. **Rules.** Firestore Database → Rules → select all → paste `firestore.rules` → Publish.
   If it shows a red error, screenshot it; the old rules stay live, so nothing breaks.
   These rules close Sessions 5–7's collections to the public (the data stays in the console).
3. **GitHub Pages.** This repo → Settings → Pages → Deploy from a branch → `main`, `/ (root)` → Save.
   After about 2 minutes, `https://yazash123.github.io/session8/` should load.
4. **Webflow.** New page `/session8` → full-width section (not a Container) → Code Embed → paste
   `webflow-embed.html` → Save & Close → Publish to houseofthepeople.uk.
5. **Test with two browsers** (Chrome Incognito plus Safari or Firefox private): one unlocks host
   controls and opens the drivers vote, the other enters a room and name and votes. In the console,
   `s8-config` and `s8-votes` appear. Then, on host controls, use "Clear" (or delete `s8-votes`,
   `s8-picks` and `s8-ideas` in the console) so Tuesday starts empty.

## Cleanup from Sessions 5–7

- The new rules close `subs`, `ice-s6`, `ice-s7`, `drv-s6`, `drv-s7`, `miss-s6`, `miss-s7` and `poll-s6`.
  The old activity pages then fall back to "only saved on this computer". Unpublish or archive those
  Webflow pages if members could still reach them.
- Once you're sure your downloads are complete, delete those collections in the console (Data → the
  collection → ⋮ → Delete collection). `poll-s6` holds names and preferences, so it's the first to go.
- Optional, 5 minutes: Google Cloud console → APIs & Services → Credentials → the Browser key →
  Application restrictions: Websites → add `https://yazash123.github.io/*` and
  `https://houseofthepeople.uk/*`. This stops casual reuse of the key from other sites.
- Optional: put the project on the Blaze plan with a £5 budget alert, so a busy evening can't hit the
  daily free limit and stop the votes.

## What the rules can't stop

Nobody but the host signs in, so a determined person with the page source could add junk votes under
made-up ids, or take back a vote they can guess the id of. Member names are first names only. The
links only go to members, which keeps the risk low.
