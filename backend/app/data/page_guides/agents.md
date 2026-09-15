# Agents

Route: `/agents`

## What this page is for
The list of every AI agent under governance: how much authority each one has right now
and whether any needs attention. It is the starting point of the dashboard.

## What you see
- **Summary block (top right)**:
  - ACTIVE AGENTS: how many agents are registered.
  - TOTAL AUTHORITY: the sum of every agent's current spending limit.
  - REQUIRES ATTENTION: how many agents are restricted or suspended.
- **One card per agent**:
  - a RUNG tag (0–4) and a STATE badge (probation, active, restricted, suspended)
  - the agent's name and id
  - a compact autonomy ladder showing its position (on wide screens)
  - CURRENT AUTHORITY (its spending limit), RUNG (out of 4) and STATE

This page deliberately shows only identity, limit, rung and state. Trust scores, accuracy
and drift are on each agent's detail page.

## What you can do here
- Click **VIEW AGENT →** on a card to open that agent's detail page, with its trust score,
  evidence, history and decisions.
- Open the assistant on an agent's detail page to ask about that specific agent.

## Common questions
- *Why is there no trust score here?* It is computed per agent on the detail page. The
  list stays fast by not computing it for every agent.
- *What does "requires attention" mean?* The agent is restricted or suspended, so every one
  of its decisions goes to a human, whatever the amount.
- *How does an agent move up a rung?* Evidence builds up, governance recommends an increase,
  and an admin approves it on the Approvals page.
