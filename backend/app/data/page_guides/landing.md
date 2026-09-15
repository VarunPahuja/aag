# Landing page

Route: `/`

## What this page is for
A scrolling introduction to the Earned Autonomy Engine: the problem it solves, how it works,
and why it can be trusted. It shows no live data. Everything on it is explanatory.

## What you see, top to bottom
- **Hero**: "Would you let AI approve a ₹10,000 invoice on day one?" The problem: today's
  choice is full autonomy with no safety, or approving everything by hand with no benefit.
- **Concept**: the five-rung ladder (₹500 → ₹10,000). An agent starts at ₹500 and escalates
  anything larger. A statistics engine watches it, four AI governance agents write the case
  for an increase, and a human approves every increase. A drop in performance takes authority
  back automatically.
- **Architecture**: four layers. The dashboard (Next.js), the backend API (FastAPI and
  PostgreSQL), the trust engine (pure Python, no libraries), and the governance panel of four
  AI agents. All four share one contracts package.
- **Key insight, "100% accurate. Refused."**: 22 of 22 correct proves only 85.1% (Wilson
  lower bound), 44 of 44 proves 92.0%, and 87 decisions at 98.9% proves 93.8%. The system uses the
  proven number, never the observed one.
- **Trust score**: the four weighted components (accuracy 0.50, human agreement 0.25,
  critical-error penalty 0.15, utilisation 0.10).
- **The numbers**: 1,550 decisions in one simulation run with zero lost, the same seed
  giving a byte-for-byte identical run, and review burden falling from 100% to 5% from the
  floor rung to the top.

## What you can do here
- Use the top navigation (Concept, Architecture, Insight, Numbers) to jump to a section.
- Click **Enter Dashboard** or **Dashboard →** to go to the Agents page, where the live
  system is.

## Common questions
- *Where is the real data?* On the dashboard. Click Enter Dashboard.
- *Why not just use the accuracy percentage?* On a small sample a perfect record proves very
  little. See the "100% accurate. Refused." section.
