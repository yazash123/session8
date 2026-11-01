# Session 8: Our priorities

The House of the People's Session 8 page (Tuesday 3 November): Recap, Set up, Our room and Ranking.
Served by GitHub Pages at `https://yazash123.github.io/session8/` and framed into
`houseofthepeople.uk/session8` by `webflow-embed.html`.

## Files

| file | what it is |
|---|---|
| `src/session8.html` | The claude.ai artifact, exactly as published there. **This is the source of truth.** |
| `index.html` | The hosted page. Built from `src/` by `tools/build.py`; don't edit by hand. |
| `firebase-config.js` | The Firebase web config for project `session-5-activity` (display name “HotP activities”). Public by design: the rules protect the data. |
| `firestore.rules` | The complete rules to paste into the Firebase console. |
| `webflow-embed.html` | Paste into one Webflow Code Embed on the `/session8` page. |
| `tools/build.py` | Turns the artifact into `index.html` (adds Firebase, hides Edit, connects the votes). |
| `docs/rules-sessions-5-7-backup.rules` | The rules that were live before Session 8 (see the appendix). |
| `tools/check.py`, `tools/fakefirestore.js` | A browser test with a fake Firestore: host sign-in, voting by three people, undo, picks, listener counts. |

To update after the artifact changes: save the artifact's HTML over `src/session8.html`, run
`python3 tools/build.py && python3 tools/check.py`, commit, push. Pages takes a few minutes to update.

## How the votes are stored

The page writes to four collections in the shared project (ID `session-5-activity`, shown in the console as “HotP activities”; renaming the display name changes nothing), all starting `s8-`:

| collection | one document per | who writes |
|---|---|---|
| `s8-config` (`main`) | the session: which vote is open, timers, results shown | host only |
| `s8-votes` | pairwise choice `{set, a, b, w, r?, by, name, room, at}` | any member; they can undo their own for a few minutes |
| `s8-picks` | member (id = browser id): their five risks `{ids, name, room, at}` | the member |
| `s8-ideas` | driver a member added during the vote | any member; only the host hides or removes |

**Reads stay small.** Only the signed-in host's screen reads every vote and pick. When the host shows the
results, the host's browser puts a compact copy of the votes and picks into the settings document (and
refreshes it every ~12 seconds while results are on), so members see the results without reading every vote.
A member reads only the session settings, the added ideas and their own picks. With about 100
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

## Appendix: the rules before Session 8 (Sessions 5–7)

Copied from the Firebase console on 1 November 2026, just before Session 8's rules replaced them.
They open `subs` (Session 5), `ice-s6`/`ice-s7` (Iceberg), `drv-s6`/`drv-s7` (Underlying drivers),
`miss-s6`/`miss-s7` (What's missing) and `poll-s6` (the poll). The same text is in
`docs/rules-sessions-5-7-backup.rules`.

To bring the old pages back: paste these into Firestore → Rules → Publish. That closes Session 8's
collections, so don't do it while Session 8's page is in use. To run both, the two files would need
merging into one.

```
rules_version = '2';
// Rules for the Firebase project "session-5-activity", which Sessions 5, 6 and 7 share.
// Paste the whole file into Firebase console → Firestore Database → Rules → Publish.
// Nobody signs in, so these rules check the shape of what is written, not who wrote it.
service cloud.firestore {
  match /databases/{database}/documents {

    // Session 5: one document per person, per group, per risk.
    match /subs/{id} {
      allow read: if true;

      allow create, update: if id.size() <= 160
        && request.resource.data.keys().hasOnly(['name', 'group', 'risk', 's', 'at'])
        && request.resource.data.keys().hasAll(['name', 'group', 'risk', 's', 'at'])
        && request.resource.data.name is string
        && request.resource.data.name.size() >= 1
        && request.resource.data.name.size() <= 80
        && request.resource.data.group is int
        && request.resource.data.group >= 1
        && request.resource.data.group <= 17
        && request.resource.data.risk is string
        && request.resource.data.risk.size() <= 12
        && request.resource.data.s is map
        && request.resource.data.s.size() <= 12
        && request.resource.data.at is int;

      // Nobody can delete from the page. Clear scores in the Firebase console.
      allow delete: if false;
    }

    // Sessions 6 and 7, the iceberg: one document per note.
    // ice-s6 is Session 6, ice-s7 is Session 7 (set by BOARD in index.html).
    // A note is "removed" by setting gone: true, so nothing is ever lost from the page.
    function iceNote(d) {
      return d.keys().hasOnly(['room', 'dir', 'layer', 't', 'k', 'name', 'pid', 'at', 'st', 'gone'])
        && d.keys().hasAll(['room', 'dir', 'layer', 't', 'k', 'name', 'pid', 'at', 'st', 'gone'])
        && d.room is int && d.room >= 1 && d.room <= 26
        && d.dir in ['dn', 'up']
        && d.layer in ['surface', 'under', 'core']
        && d.t is string && d.t.size() >= 1 && d.t.size() <= 600
        && d.k is string && d.k.size() <= 40
        && d.name is string && d.name.size() >= 1 && d.name.size() <= 40
        && d.pid is string && d.pid.size() >= 1 && d.pid.size() <= 40
        && d.at is int
        && d.st is map && d.st.size() <= 60
        && d.gone is bool;
    }

    // NEW. Underlying drivers, part 1: one document per person; its id is their pid.
    // str: drivers they linked to their room's risk ('big' main, 'subtle' plays a part, '' not decided).
    // eff: Drives ('amp') or Limits ('sup'). o1, o2: drivers they added themselves.
    // stars: other people's own drivers they hearted (keyed Ox_<pid>_O1).
    function drvPerson(d, docId) {
      return d.keys().hasOnly(['room', 'risk', 'name', 'pid', 'str', 'eff', 'o1', 'o2', 'stars', 'at'])
        && d.keys().hasAll(['room', 'risk', 'name', 'pid', 'str', 'eff', 'o1', 'o2', 'stars', 'at'])
        && d.room is int && d.room >= 1 && d.room <= 26
        && d.risk in ['R01', 'R02', 'R03', 'R05', 'R06', 'R07', 'R08', 'R09', 'R10', 'R11', 'R12', 'R14', 'R15']
        && d.name is string && d.name.size() >= 1 && d.name.size() <= 40
        && d.pid is string && d.pid == docId && d.pid.size() <= 40
        && d.str is map && d.str.keys().hasOnly(['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'O1', 'O2'])
        && d.str.values().hasOnly(['big', 'subtle', ''])
        && d.eff is map && d.eff.keys().hasOnly(['D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'O1', 'O2'])
        && d.eff.values().hasOnly(['amp', 'sup', ''])
        && d.o1 is string && d.o1.size() <= 90
        && d.o2 is string && d.o2.size() <= 90
        && d.stars is map && d.stars.size() <= 60 && d.stars.values().hasOnly([1, true])
        && d.at is int;
    }

    // NEW. What's missing: one document per thing someone adds.
    // kind 'word': their wording of a risk. 'gap': what it leaves out (k is the label).
    // 'new': a risk not on the map (t title, d a sentence or two). 'creep': a risk from
    // another cluster that kept coming up (t empty). st holds hearts {pid: name}.
    function missItem(d) {
      return d.keys().hasOnly(['room', 'kind', 'risk', 't', 'd', 'k', 'name', 'pid', 'at', 'st', 'gone'])
        && d.keys().hasAll(['room', 'kind', 'risk', 't', 'd', 'k', 'name', 'pid', 'at', 'st', 'gone'])
        && d.room is int && d.room >= 1 && d.room <= 26
        && d.kind in ['word', 'gap', 'new', 'creep']
        && d.risk in ['', 'R01', 'R02', 'R03', 'R05', 'R06', 'R07', 'R08', 'R09', 'R10', 'R11', 'R12', 'R14', 'R15']
        && d.t is string && d.t.size() <= 400 && (d.t.size() >= 1 || d.kind == 'creep')
        && d.d is string && d.d.size() <= 600
        && d.k in ['', 'who', 'day', 'narrow']
        && d.name is string && d.name.size() >= 1 && d.name.size() <= 40
        && d.pid is string && d.pid.size() >= 1 && d.pid.size() <= 40
        && d.at is int
        && d.st is map && d.st.size() <= 60
        && d.gone is bool;
    }

    // NEW. The poll: one document per person. Sending again replaces it.
    function pollVote(d) {
      return d.keys().hasOnly(['name', 'pid', 'clusters', 'risks', 'at'])
        && d.keys().hasAll(['name', 'pid', 'clusters', 'risks', 'at'])
        && d.name is string && d.name.size() >= 1 && d.name.size() <= 80
        && d.pid is string && d.pid.size() >= 1 && d.pid.size() <= 40
        && d.clusters is list && d.clusters.size() <= 6
        && d.clusters.hasOnly(['data', 'voters', 'kids', 'work', 'war', 'check'])
        && d.risks is list && d.risks.size() <= 13
        && d.risks.hasOnly(['R01', 'R02', 'R03', 'R05', 'R06', 'R07', 'R08', 'R09', 'R10', 'R11', 'R12', 'R14', 'R15'])
        && (d.at is int || d.at is timestamp);
    }

    // Every collection below is one of the lists named in its own lines.
    match /{board}/{id} {
      // The iceberg.
      allow read: if board in ['ice-s6', 'ice-s7'];

      allow create: if board in ['ice-s6', 'ice-s7']
        && id.size() <= 40
        && iceNote(request.resource.data)
        && request.resource.data.st.size() == 0
        && request.resource.data.gone == false;

      // Editing your note, liking someone's, or removing yours (gone: true).
      // Where it sits and who wrote it can never change.
      allow update: if board in ['ice-s6', 'ice-s7']
        && iceNote(request.resource.data)
        && request.resource.data.room == resource.data.room
        && request.resource.data.dir == resource.data.dir
        && request.resource.data.layer == resource.data.layer
        && request.resource.data.pid == resource.data.pid
        && request.resource.data.at == resource.data.at;

      // Nothing in any of these collections can be deleted from a page.
      allow delete: if false;

      // NEW. Underlying drivers, part 1. Each person writes only their own document.
      allow read: if board in ['drv-s6', 'drv-s7'];
      allow create, update: if board in ['drv-s6', 'drv-s7']
        && drvPerson(request.resource.data, id);

      // NEW. What's missing. Where a thing sits, what kind it is and who added it never change,
      // and one write can add or take away at most one heart.
      allow read: if board in ['miss-s6', 'miss-s7'];
      allow create: if board in ['miss-s6', 'miss-s7']
        && id.size() <= 60
        && missItem(request.resource.data)
        && request.resource.data.st.size() == 0
        && request.resource.data.gone == false;
      allow update: if board in ['miss-s6', 'miss-s7']
        && missItem(request.resource.data)
        && request.resource.data.room == resource.data.room
        && request.resource.data.kind == resource.data.kind
        && request.resource.data.risk == resource.data.risk
        && request.resource.data.pid == resource.data.pid
        && request.resource.data.at == resource.data.at
        && request.resource.data.st.diff(resource.data.st).affectedKeys().size() <= 1;

      // NEW. The poll.
      allow read: if board == 'poll-s6';
      allow create, update: if board == 'poll-s6'
        && id.size() <= 60
        && pollVote(request.resource.data);
    }

    // Everything else is closed.
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```
