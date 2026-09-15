# Simulation

Route: `/simulation`

## What this page is for
A test environment. It feeds an agent a batch of synthetic invoices so you can watch how
earned autonomy responds: evidence building, drift being caught, and recovery.

## What you see
- **Simulation setup**, with four settings:
  - AGENT ID: which agent receives the invoices (shown with its rung and limit).
  - SIMULATION PHASE:
    - *Good*: normal, high-accuracy performance that builds evidence towards an increase.
    - *Degraded*: a deliberate performance drop. The trust engine detects drift and the
      system claws autonomy back automatically.
    - *Recovery*: performance returns to normal. After enough clean decisions an increase
      can be recommended again.
  - INVOICE COUNT: 50, 100 or 200.
  - REASON (MANDATORY): why you are running it. It is recorded.
- **LAUNCH SIMULATION** button.
- While a run is going: a progress panel with phase, invoice count, decisions submitted and
  status, polled every 2 seconds. When it completes, it shows the run's ACCURACY and WILSON
  LOWER BOUND.
- With no run active: a short "Simulation guide" describing the three phases.

## What you can do here
1. Choose an agent, a phase and an invoice count.
2. Type a reason. The button stays disabled until you do.
3. Click **LAUNCH SIMULATION**, then watch progress.
4. Open the agent's detail page to see its trust score, drift and limit update.

Runs use a fixed seed (42), so the same settings produce the same invoices every time.
Simulations write real decisions for the chosen agent. They change its evidence and can
trigger a clawback.

## Common questions
- *How do I trigger a clawback?* Run the Degraded phase against an agent.
- *Why did the agent not go up after a Good run?* An increase is a recommendation that an
  admin must approve on the Approvals page. It also needs enough decisions, a trust score of
  70 or more, and the cooldown to have passed.
- *Can the assistant start a run for me?* No. The assistant is read-only. Use LAUNCH
  SIMULATION.
