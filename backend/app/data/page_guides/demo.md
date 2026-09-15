# Demo Console

Route: `/demo`

## What this page is for
Presenter mode. It walks through the full ten-beat story of the system, one beat at a time,
driven through the real API, so a panel sees real numbers on screen. It mirrors the
`scripts/demo.ps1` terminal script.

## The ten beats
1. **Agent-01's starting position**: where it stands now on real seed data.
2. **Build evidence**: run a simulation, then record human rulings on escalations.
3. **The trust evaluation**: raw accuracy against the Wilson lower bound, the number the
   ladder actually trusts, and the trust score (70 or more is needed for an increase).
4. **Generate a recommendation**: a live-earned INCREASE with four independent governance
   opinions.
5. **Human approval**: an admin approves it. This is the step that must happen before autonomy
   can go up.
6. **Autonomy rises**: the new limit and rung, with the new policy version chained to the
   one it replaced.
7. **Inject a critical error**: an APPROVE whose ground truth was REJECT.
8. **Drift detected**: a single critical error means immediate CRITICAL severity.
9. **Automatic clawback**: the limit drops straight away, with no approval call.
10. **Verify the audit chain**: every entry hash-linked, recomputed fresh.

## What you see and can do
- **LIVE / REPLAY** toggle. LIVE makes real API calls. REPLAY shows numbers captured from an
  earlier real run and makes no network calls (it is labelled "RECORDING — NOT LIVE").
- **RUN BEAT** runs the current beat and shows its result. **NEXT →** unlocks once it is
  done, and **← BACK** goes to the previous beat. The numbered dots jump to any beat.
- **RESET CONSOLE** clears the screen only. **It does not reset the database.** The arc
  changes real data (it moves agent-01 up, then claws it back), so reset the database from a
  terminal before running live again: `.\scripts\demo.ps1` or `make db-reset`.

## Common questions
- *Beat 5 says there is no recommendation.* Run beat 4 first. Beat 5 approves the
  recommendation beat 4 created.
- *Beat 4 did not give an INCREASE on a second run.* The database was not reset since the last
  live run. Reset it and try again.
- *Which mode should I use in front of an audience?* LIVE shows the real system. REPLAY is the
  safe fallback if the backend or the network is unreliable.
