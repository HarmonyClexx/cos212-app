# Ariadne: Changes and Tester Guide

This guide documents the fourteen implemented improvements and gives repeatable manual checks for testers and the project owner. It is a test script, not a record of tests performed by the reader.

All fourteen improvements have received individual developer checks. The separate integrated recheck is still pending. The scenarios below must start as **Not run** until somebody actually performs them against the build being evaluated. Software checks do not establish learning gains, motivation, mastery, lecture readiness or formal accessibility conformance.

## 1. Before testing

1. Obtain the URL and build/commit identifier from the project owner. Record the browser, operating system, viewport width and theme.
2. Confirm that both backend and frontend contain the latest changes. The final-bank, diagnostic and response-record changes need the updated backend as well as the frontend. Audio/confetti changes are frontend-only.
3. Refresh after an update. If old assets remain, use a hard refresh. The owner handles rebuilding/redeploying; testers should not change server configuration.
4. Use dedicated test accounts, not somebody's real learning account. Have two accounts for isolation checks and an account with unused reserved finals for L3.
5. Record whether navigation is open or sequential. In sequential mode, complete prerequisites or ask the owner for a suitably progressed test account. A locked page is not automatically a defect. Do not change access settings or reset/delete progress to make a test pass.
6. Use unfinished quick checks for audio/confetti tests: already-correct lesson answers are locked. Use a new formative attempt where needed.
7. Ensure browser sound is audible for A6. Identify the speaker and sparkle buttons beside the theme control. Sound and confetti have separate browser preferences.

**Safety:** starting reserved final A or B consumes that version for this account, even if you do not submit it. Use a separate QA account for exhaustion tests. Deliberately wrong QA answers and their scores must not be reported as student attainment. Do not publish reserved final questions, answer keys or unredacted final screenshots.

**Storage:** acknowledged quiz drafts are account-backed. Unfinished lesson recovery is per account in the current tab's session storage, not cross-device persistence. Sound/confetti preferences use this browser's local storage, with an in-memory fallback when storage is unavailable.

## 2. Where to find the pages

Paths are relative to the supplied site URL. For example, add `/profile` to that URL. Sign in first; direct paths do not bypass locks.

- Map: `/`
- Profile: `/profile`
- Leaderboard: `/leaderboard`
- Intro course / What is a graph?: `/learn/intro/l1-graphs`
- Intro course / Writing a graph down: `/learn/intro/l2-representation`
- Intro course / Depth-first search: `/learn/intro/l3-dfs`
- Intro course / Dead ends & backtracking: `/learn/intro/l4-backtracking`
- Intro course / DFS vs BFS: `/learn/intro/l5-bfs`
- The Labyrinth / Into the dark: `/learn/labyrinth/m0-maze`
- Anatomy of a Graph / Inspect the map: `/learn/anatomy/m1-inspect`
- Anatomy of a Graph / Name that part: `/learn/anatomy/m1-quiz`
- Mapping the Maze / Three views, one graph: `/learn/representation/m2-represent`
- Mapping the Maze / Cartographer: `/learn/representation/m2-build`
- Into the Depths / Watch Ariadne's rule: `/learn/dfs/m3-demo`
- Into the Depths / Warm-up: the tree: `/learn/dfs/m3-trace-1`
- Dead Ends & the Thread / Why we wind the thread: `/learn/backtracking/m4-demo`
- Dead Ends & the Thread / Corridors: `/learn/backtracking/m4-trace-1`
- Dead Ends & the Thread / Read the stack: `/learn/backtracking/m4-quiz`
- Deep vs Wide / The race: `/learn/dfs-vs-bfs/m5-compare`
- Deep vs Wide / Deep or wide?: `/learn/dfs-vs-bfs/m5-quiz`
- Face the Minotaur / The final trial: `/learn/minotaur/m6-final`

The Map offers the Intro course and game modules. Within a module, choose the named activity. Some checks below need a specific quiz question; use the question dots to reach it if that activity is available.

## 3. Change checklist

- T1: prominent, plain-language learning goals.
- T2: story-first orientation connecting the Labyrinth to graph concepts.
- T3: explanation of specific representation mistakes.
- T4: skippable, ungraded predictions in game DFS/backtracking demonstrations.
- L1: targeted revision links, safe navigation and reachable lesson sections.
- L2: truthful practice reporting, task versions, original responses and support records.
- L3: two reserved final versions, safe allocation and explicit repeat practice.
- A1: nonvisual information about visible graph connections.
- A2: genuinely modal reward dialog with contained/restored focus.
- A3: reward headings based on the current result, not historical best stars.
- A4: available badge totals from the authoritative catalogue.
- A5: clearer Ariadne logo naming while keeping its Map destination.
- A6: supportive spoken answer feedback with a remembered mute control.
- A7: newly correct answer celebrations with a separate preference and reduced motion.

Grading formulas, question weights, pass thresholds, hint penalties, XP, stars, badge awards, historical scores and access settings were not intentionally redesigned.

## 4. Manual checks for each improvement

### T1. Learning goals are prominent

**Changed:** learning goals now appear below the module title, before story/navigation/activity content, in plain language.

**Where:** any lesson or game activity; also preview the final page without starting a version.

1. Open What is a graph? and locate the Learning goals heading before the activity.
2. Switch to Writing a graph down. Check that its goal concerns representations, not the previous lesson's topic.
3. Open Into the Depths and check that the goal concerns DFS first-visit order.
4. Open the final page. Check that all five objectives are listed. Merely previewing an unused final must not issue a version.
5. Check at 320px and 390px and in both themes. With a screen reader, find the learning-goals heading/section.

**Expected:** relevant goals are easy to find and readable; the final lists all five. The maze retains its own exploration goal. Goals do not disclose task answers or override locks.

**Record:** page, goal observed, viewport/theme, and status: Not run / Pass / Fail / Blocked.

### T2. Story-first orientation

**Changed:** the signed-in Map introduces the Labyrinth problem before connecting it to formal concepts and the course route. The public opening uses consistent framing.

1. Open the signed-in Map on a new test account.
2. Read the opening in order: story, concept connections, pre-lecture purpose and lessons/game route.
3. Check the connections: rooms are vertices; corridors are edges; thread is the current-path stack; chalk remembers visited vertices.
4. Confirm that the Intro course and existing Start/Continue controls remain findable.
5. Inspect the signed-out opening and a returning account's Map.

**Expected:** the story explains the concrete problem without replacing explicit lessons or promising guaranteed mastery. Returning users retain sensible continuation controls. Open navigation is not misleadingly described as mandatory sequential unlocking.

**Layout note:** a small public-page overflow at 320px was previously observed in an isolated fixture and was not fixed by T2. Record actual behaviour on the tested site rather than assuming it was repaired.

**Record:** account state, opening order and wording, controls available, status.

### T3. Specific representation diagnostics

**Changed:** adjacency errors receive row-level missing/extra/reverse/direction information; selected wrong representation options receive concept-specific explanations. Existing scores and help costs remain.

**Where:** Mapping the Maze / Cartographer.

1. In the undirected adjacency task, build from the visible diagram. For one real edge, deliberately include one endpoint's neighbour entry but omit its matching reverse entry. Check.
2. Read About your last checked answer. Check that it identifies the affected row and relevant missing/reverse-entry rule.
3. Add a non-neighbour to a row and check again. Look for extra-entry information. In the directed task, try an incoming-only neighbour in an outgoing row.
4. In the matrix-row question, select **B only**. Check that the explanation addresses an omitted marked column. In the sparse-graph storage question, select **Adjacency matrix** and inspect the storage explanation.
5. Edit the answer without checking again, then request a hint.

**Expected:** explanations match the submitted mistake. Missing neighbour names are not supplied as an early answer key. Retained diagnostics refer to the last checked answer; the hint is distinct. Ambiguous wrong answers may receive general feedback rather than an invented precise diagnosis.

**Final check:** a final must withhold correctness/diagnostics until whole-trial submission.

**Record:** question, controlled wrong input, diagnostic text, score/help state, status. These QA inputs are not learner outcomes.

### T4. Predictions in game demonstrations

**Changed:** each of the two game demonstrations has three selected prediction pauses: a deeper visit, first backtrack and a visit after explored neighbours. Predictions are ungraded.

**Where:** Watch Ariadne's rule and Why we wind the thread.

1. Start Play. At a prediction, note the current graph, stack, visited marks and step counter.
2. Wait briefly: the next action must not appear before a prediction or Skip / reveal.
3. At the tree's first prompt from B, choose Backtrack (pop) as a deliberately wrong prediction.
4. Read the actual DFS transition, then resume with Play. At another prompt use Skip / reveal.
5. Try previous/next, left/right arrows, speed, restart and replay. Reach the empty-stack finish.
6. Repeat in Why we wind the thread. At a pop, check that visited marks and first-visit order remain unchanged.

**Expected:** prompts, feedback and all state displays agree. Wrong/skip choices impose no score penalty. Revealed checkpoints need not be answered again during backward/forward inspection; restart/replay restores prompts. I've got it becomes available after reaching the end.

**Exclusion:** introductory DFS/BFS figures have no new prediction gates.

**Record:** demonstration, checkpoint, action, before/after state, status.

### L1. Targeted revision and safe return

**Changed:** diagnosed concepts link to relevant existing lesson sections/practice instead of always sending users to a whole module.

**Where:** Cartographer feedback and submitted final reviews.

1. Use the matrix mistake from T3 and find Targeted revision.
2. Edit your quiz answer, then choose the **Read** link for the matrix explanation.
3. Check the lesson's section-review notice and relevant content. Your ordinary saved lesson position must not be replaced by this temporary review.
4. Use **Return to quiz**. Check the current question and saved edited answer.
5. Try the **Practise** link; it should reach Three views, one graph for representation topics.
6. On a suitable sequential-mode QA account, inspect a locked destination. If prerequisites prevent this case, record Blocked rather than changing access settings.

**Expected:** controlled navigation saves edits, records active-quiz support, then navigates. Locked/unreachable sections explain the limitation and offer a reachable alternative without skipping quick checks. Resume saved page leaves the temporary section review. Ambiguous/legacy feedback may show explicitly labelled general review.

**Recovery:** if saving/support navigation fails, the quiz stays open; retry the offered matching operation. See I3 for an offline exercise. Revision links in a submitted final are read-only navigation and must not rewrite its grade.

**Record:** diagnosis, link destination, draft restored, support record, gate behaviour, status.

### L2. Original responses, support and cautious reporting

**Changed:** new attempts pin task content and retain original and later answers plus disclosed/requested support. Practice progress, response counts and current scores are distinct.

**Where:** any formative quiz; Profile / Recorded quiz responses; submitted final reports.

1. Start a new formative attempt. Edit an answer but do not check it. Expand its recorded-response details.
2. Submit a wrong answer without requesting help first. Expand the details again.
3. Correct it and check again. Compare Original submitted answer with the latest recorded answer.
4. On another unanswered item, request Hint before its first check. Inspect the response category and recorded support after checking.
5. Visit a linked explanation/practice through controlled navigation, then return. Inspect recorded support.
6. Finish, reopen without starting another attempt, and inspect Profile.
7. Start an explicit repeat formative attempt and inspect its first-response classification.

**Expected:** draft edits are not submitted responses. The original wrong answer remains unchanged after correction; corrective feedback/hints/review requests are separate support events. First formative answers without recorded help remain **practice**, not fresh independent assessments. Repeat attempts are labelled as repeats.

**Reporting:** running practice scores can include guided/helped/repeated work. The 70% reference is not a validated mastery/readiness threshold. Fully correct / recorded response counts are separate from score/credit; a dash means no recorded responses, not assessed zero.

**Historical/blank cases:** where an owner-prepared legacy QA account exists, missing history stays labelled not recorded rather than backfilled. Blank final items retain zero credit but no invented submitted-answer record. Inspect these during L3 if applicable.

**Version check:** after refresh/reopening, the same attempt's public task version and content remain stable. Proving pinning across a server content update requires maintainer tooling; testers should not edit question banks.

**Record:** attempt/question, original and latest status, support/category, public task version, counts versus score, status.

### L3. Two reserved finals and explicit repeat practice

**Changed:** two private final versions, A and B, each have ten questions/two per objective. Issuance records exposure; exhaustion leads to revision and labelled repeats.

**Where:** Face the Minotaur / The final trial.

**Before:** use a QA account with final access and no reserved versions issued. Reserve this account for this scenario.

1. Preview the final page. Expect two unused versions and an explicit start button, not automatically issued questions.
2. Start reserved final A. Answer one item, wait for Saved to your account, refresh and return.
3. Confirm the same A, answer and current question return. B must not be consumed by this resume.
4. Submit A. For a quick software check, blanks are allowed but intentionally score zero. Reopen and compare the saved score.
5. Explicitly start B. Confirm that its tasks differ from A, not merely its version label. Do not distribute either bank's content.
6. Submit B and reopen. Inspect both-used status, revision links and Repeat practice.
7. Start Repeat practice and inspect the status/result/Profile category.

**Expected:** there is no third unused final. A/B availability changes on issuance, not correctness. Refresh/reopening does not silently create an attempt. Repeats are clearly labelled and do not supply new independent-final evidence. Incorrect submitted answers and unanswered items are distinguished.

**Interpretation:** reserved responses without recorded help are task-specific records, not proof of no outside help, equivalent difficulty, general mastery or lecture readiness. Helped/fixed-set/repeat records remain separate.

**Legacy:** if provided with an older QA result, verify its original score/version remains available. Do not create fake legacy history or reset the database. Concurrent starts and lost acknowledgements need the maintainer checks in section 7 for stronger assurance.

**Record:** versions remaining before/after each action, resumed draft, saved score, repeat/blank classifications, status. Do not attach private final answers.

### A1. Visible graph connections are available nonvisually

**Changed:** static visible edges have accessible endpoint/direction names; clickable edges retain controls. Hidden/fog information is not disclosed.

**Where:** Three views, one graph; Cartographer; Into the dark.

1. With a screen reader or maintainer accessibility-tree inspector, inspect the undirected static graph's connections.
2. Switch to a directed graph and compare each named connection with its displayed arrow.
3. Inspect a task graph without completing its answer. Edge access must not provide a completed adjacency solution.
4. In the fog-of-war maze, compare accessible connection information with what is actually visible.
5. Try keyboard/pointer activation on an interactive edge in Inspect the map.

**Expected:** static edges are named images describing their visible endpoints/direction, not extra keyboard buttons. Interactive edges remain usable buttons. Hidden connections stay hidden; unknown endpoints may be described as unexplored rather than exposing room identities.

**Note:** Tab alone does not inspect static image information. Record the screen reader/browser used; one successful combination is not formal accessibility certification.

**Record:** graph/mode, accessible name versus visible edge, fog limits, keyboard result, status.

### A2. Reward dialog contains and restores focus

**Changed:** rewards use a native modal dialog with contained focus and unavailable background controls.

1. Complete an available activity to open its reward dialog.
2. Check initial focus on Continue. Press Tab repeatedly, then Shift+Tab; focus must remain among the dialog's enabled actions.
3. Try background navigation while the dialog is open. It must not activate.
4. Test Continue and, where offered, Retry. Reopen a reward and test Escape.
5. Repeat at 320px/390px and in both themes.

**Expected:** Escape retains its Continue meaning. After dismissal, focus returns to a usable trigger or destination activity/page heading. During navigation/loading a usable main-page destination remains. Actions wrap without clipping; decorative confetti does not capture focus or clicks.

**Record:** activity, initial focus, tab cycle, dismissal/action, destination focus, viewport, status.

### A3. Reward wording matches the current result

**Changed:** the default heading uses the current graded result rather than three stars or historical best stars.

1. On a formative quiz, use a hint before an answer, complete the questions and submit. Record the actual imperfect score and stars.
2. Check the reward heading: an imperfect two/three-star success says Great work!, never Flawless!.
3. Where feasible, submit a perfect first-try/no-help formative attempt. A current score of exactly 100% may say Flawless!.
4. Complete an ungraded demonstration. Expect ordinary completion wording. Explicit lesson/course-completion titles remain their existing named titles.
5. If a failed QA final is produced during L3, inspect its failed-result heading even when that account has a better historical result.

**Expected:** the current result controls the wording. A rounded display of 100% is not enough for Flawless! if the stored score is below 1. A one-star success may use Completed!; failure uses Not quite yet.

**Boundary:** do not consume reserved finals solely to force a particular score. Use formative activities or maintainer-prepared fixtures for difficult score boundaries. Mark an unavailable boundary case Not run/Blocked rather than guessing.

**Record:** current score/stars, relevant historical best, heading, status.

### A4. Badge totals agree with the catalogue

**Changed:** Leaderboard reports the authoritative available total and distinguishes earned from available badges.

1. Open Profile and count available badges and the earned total.
2. Open Leaderboard and compare your Badges earned tile.
3. Check an account with no earned badges and an account with at least one earned badge.
4. After earning a badge normally on a QA account, refresh both pages and compare again.

**Expected:** both pages agree on earned and available counts. The current catalogue has eleven badges, not ten; if the catalogue changes, the displayed available count should follow it. This change does not award extra badges or XP.

**Maintainer-only boundary:** checking a changed catalogue uses an isolated automated fixture, not manual edits to the deployed catalogue.

**Record:** account alias, earned/available on each page, before/after award, status.

### A5. Ariadne logo clearly means Map

**Changed:** the logo remains a Map link but has clearer accessible naming and a tooltip; no separate overview page was added.

1. From Profile, hover the Ariadne logo and inspect its tooltip.
2. With a screen reader/accessibility inspector, inspect its link name.
3. Activate the logo using keyboard Enter, then repeat using the Map navigation link.
4. Check navigation and visible focus at 320px and 390px.

**Expected:** tooltip says Ariadne - Map, accessible name says Ariadne map, and both links lead to `/`. Profile/Leaderboard, speaker, sparkle, theme and sign-out controls remain usable. The visible brand still says Ariadne where space permits.

**Record:** tooltip/name, destination, keyboard/focus, viewport, status.

### A6. Spoken feedback and mute

**Changed:** new lesson/formative answers can speak Well done! or Oops, let's try again! through browser speech. The speaker control remembers mute in this browser.

1. Ensure speaker feedback is enabled, system volume is audible, and an unanswered lesson quick check is available.
2. Choose a wrong answer, then correct it. Listen for the corresponding short phrases while reading the existing explanations.
3. In a formative quiz, use Check. Speech occurs on newly returned feedback, not just selecting an option.
4. Mute with the speaker button, answer another item, then refresh. Mute should persist where local storage works.
5. Unmute. Previous answers must not speak again. Navigate away while a phrase is playing; it should stop.
6. Inspect a restored quiz, request a hint/reveal, and inspect a final before/after submission.

**Expected:** initial loads, restored results, hints/reveals, failed requests, ordinary demonstration steps and final assessment feedback remain silent. A recovered check speaks only when its acknowledgement is disclosed, once. Visible feedback remains usable with sound off.

**Limit:** audible speech depends on the browser/system's voices and policies. If unavailable/inaccessible, the speaker control is labelled unavailable. If speech is blocked, record that environment and confirm written feedback still works. Developer spy checks verified triggering, not actual audible output on every platform.

**Record:** browser/OS, voice heard, mute before/after refresh, silent exclusions, status.

### A7. Correct-answer celebrations and reduced motion

**Changed:** new correct lesson/formative answers show Well done! plus a brief, faint full-screen burst. The sparkle control remembers a separate confetti preference.

1. Enable celebrations. On an unfinished quick check, submit a wrong answer and then a correct one.
2. Check a correct formative answer. Inspect written praise and the short burst; keep using the keyboard normally.
3. Refresh/reopen a solved answer, request a hint or reveal, and select a final answer without submitting.
4. Disable celebrations using the sparkle button. Answer another question and refresh. Written feedback remains; the off setting persists where storage works.
5. Enable browser/system reduced motion. Correct answers must not animate even with the sparkle preference enabled.
6. Complete a guided DFS trace. Its individual decisions must not burst; successful activity completion still celebrates when enabled.

**Expected:** only newly disclosed correct lesson/formative responses trigger answer bursts. No stacked/non-ending overlays or lost focus. Confetti is decorative and pointer-transparent, stops on navigation/disable, and respects reduced motion. Re-enabling does not replay prior answers. Muting sound does not automatically disable confetti, or vice versa.

**Completion:** existing reward-dialog bursts retain their completion role and accurate result wording. Disabling confetti/reduced motion also applies to those bursts.

**Record:** fresh/restore/help path, visible praise, burst duration/cleanup, preference, reduced motion, keyboard, status.

## 5. Integrated scenarios to run after individual checks

These are the pending combined-path checks, not completed tester results. Run them on the latest build using QA accounts.

### I1. Complete teaching-to-repeat journey

1. Begin on the Map, read the narrative/goals and follow the available Intro course.
2. Make a controlled lesson mistake, correct it, and check spoken/written feedback and confetti preferences.
3. Use Three views, one graph, then make a representation mistake in Cartographer.
4. Read the diagnostic, edit an answer, follow targeted revision and return to the saved quiz.
5. Correct it and inspect the immutable first answer and recorded support.
6. Use game demonstration predictions and complete a guided DFS challenge; distinguish prediction/trace practice from quiz response records.
7. Follow L3 to issue/submit A, issue/submit B, reach exhaustion and start explicit repeat practice.
8. Reopen results and Profile; compare response categories, practice scores, actual final score and rewards.

**Expected:** the entire route remains usable; saves/support/version allocation/feedback agree. Grades/rewards are not changed by prediction guesses or preference toggles. No missing-history or repeat record is represented as validated mastery.

### I2. Two-account and two-tab recovery

1. In one tab, let QA account A make unfinished lesson and quiz progress. Wait for quiz save acknowledgement.
2. Sign out and sign into QA account B in that same tab. B must not receive A's answers, page or counters.
3. Return to A in that tab. Its own lesson draft can restore while session storage remains; acknowledged quiz state must restore to A's account.
4. Open the same unfinished quiz for A in two tabs before editing.
5. Save a change in tab 1. Attempt a different edit from stale tab 2.

**Expected:** account ownership is preserved. Stale tab 2 reports conflict/reload instead of overwriting tab 1. Reload the canonical saved state. This is not a promise of cross-device recovery for unsaved browser-only edits or lesson session storage.

### I3. Connection failure and acknowledged recovery

**Optional owner/technical-tester check:** use browser developer tools to set the test tab's network offline, then restore it. Do not stop shared services or alter database contents.

1. Try opening a formative quiz offline, restore online access and use Retry.
2. Edit a quiz while offline. Check Not saved/pending input rather than a false Saved message. Restore online access and retry the save.
3. Fail a check or controlled review request, then recover with its offered matching retry. Confirm the response/support is not charged or recorded twice.
4. Reopen after recovery; compare acknowledged answers and feedback.

**Expected:** temporary failures retain input and do not invent grades, mistakes, speech or celebrations. Access/authentication errors remain distinct from a connection failure. Revision navigation does not leave before the save/support acknowledgement.

**Limit:** an offline failure alone does not prove handling of a request committed by the server whose response was lost. Lost-acknowledgement and concurrent-final guarantees need maintainer instrumentation/isolated PostgreSQL checks.

### I4. Keyboard, screen reader, viewport and preferences

1. Repeat representative Map, lesson, Cartographer, Profile, prediction and reward-dialog paths using keyboard only.
2. Include existing adjacency Add/remove controls, static graph information through a screen reader, and modal Tab/Shift+Tab/Escape.
3. Check 320px, 390px, a tablet width and desktop, in light/dark themes.
4. Repeat with sound muted, confetti disabled and reduced motion enabled. Confirm that explanation text and essential controls remain usable.

**Expected:** no new clipping/page overflow on the changed authenticated screens; controls/focus remain visible and labels readable. Static edges are information, not additional Tab stops. Record any browser/screen-reader limitations and the known public-page 320px caveat separately.

## 6. Recording results and reporting issues

Start every case as **Not run**. Use **Pass** only when its stated behaviour was observed; **Fail** when behaviour contradicts it; **Blocked** for a missing prerequisite/environment; **Not applicable** only with an explanation, such as no legacy QA record supplied.

Copy this record for each case/subcase:

- Test ID and title:
- Build/commit and site URL:
- Date of test:
- Tester alias and QA account alias:
- Browser/version, OS, screen reader if used:
- Viewport and light/dark theme:
- Navigation mode; sound/confetti/reduced-motion settings:
- Preconditions and steps actually performed:
- Expected behaviour:
- Actual behaviour:
- Status: Not run / Pass / Fail / Blocked / Not applicable
- Screenshot or other evidence reference:
- Issue ID / severity: blocking / major / minor / observation
- Retest build, steps and outcome:

For a bug, provide the shortest reproduction and expected versus actual behaviour. Note whether it repeats. Remove passwords, tokens, personal account data and private final question/answer content from evidence shared outside the authorised project team. Use a private, redacted report when assessment content is involved.

**Stop and escalate:** any cross-account answer disclosure, overwritten acknowledged work, early final answer leakage, duplicate reward/support mutation, incorrect reserved-version consumption, essential inaccessible control or broken completion path. Do not repair data or bypass gates as a tester.

**Suggested summary:** list test IDs passed/failed/blocked/not run; environment coverage; reproducible issues; unresolved limitations; and whether I1-I4 were actually completed. Do not turn scripted scores or tester impressions into research learning-effectiveness claims.

## 7. Optional maintainer checks

These are instructions for later verification, not checks run by creating this guide. Ordinary testers do not need source-code access.

**Frontend:** from the `cos212-app` repository:

```bash
cd frontend
npm run build
```

The existing build includes TypeScript checking. There is no added frontend testing framework.

**Backend isolated SQLite:** on the owner's machine, activate the existing environment first. Other maintainers should activate their own project environment instead of assuming this absolute path.

```bash
source /home/thinkpad/venv/bin/activate
cd cos212-app/backend
env -u ARIADNE_TEST_DATABASE_URL \
  ARIADNE_DATABASE_URL=sqlite:// ARIADNE_UNLOCK_ALL=false \
  pytest tests/test_engine.py tests/test_api.py --tb=short
```

Run the backend command from the COS750 parent directory, not after the frontend `cd` above. PostgreSQL-only checks are skipped in the SQLite run. They do not prove row-locking/concurrent allocation.

**Isolated PostgreSQL:** use the existing backend test configuration against a newly created, explicitly owned disposable test database. Never point it at the learner database. Verify concurrent final starts, start/finish replay receipts, stale drafts and evidence/reward preservation. Database creation/drop is maintainer work, not tester work.

**Content/privacy:** independently verify reserved keys/traces, objective coverage, private graph separation and supported legacy snapshots through existing engine/API tests; check that private keys/diagnostic maps are absent from public payloads. This guide deliberately supplies no reserved-final solutions.

**Scope:** do not reset learner data, regrade history, create commits, deploy, rewrite the research reports or perform a learner study merely because this guide exists. The integrated recheck should record observed software behaviour separately from participant research.
