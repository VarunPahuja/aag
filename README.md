# Adaptive AI Governance Platform (AAGP)

An AI agent approves invoices, starting with a small autonomy limit that it
earns the right to increase through statistical evidence, with automatic
clawback if its performance degrades. The design rule: **LLM reasons.
Statistics provide evidence. Policy Engine enforces. Humans authorize.**

## Get running

```
make setup && make up
```

No `make`? Use `.\scripts\setup.ps1; .\scripts\up.ps1` in PowerShell instead —
same two steps, no GNU make required. See `make help` (or
`.\scripts\help.ps1`) for every other target.

## Where to go next

- **[docs/CONTEXT.md](docs/CONTEXT.md)** — what this system is, the four lanes,
  the request flow, the shared contracts, current status. Start here.
- **[docs/DEADLINES.md](docs/DEADLINES.md)** — the schedule and what's due when.
- **[docs/lanes/](docs/lanes/)** — one primer per lane, written to hand to an
  AI assistant or a new contributor with zero other context.
- **[docs/adr/](docs/adr/)** — why the architecture is the way it is, one
  decision per file.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — review rules, in particular: any
  change to `shared/` needs all four lane owners' approval.
