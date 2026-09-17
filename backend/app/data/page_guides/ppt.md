# Presentation

Route: `/ppt`

## What this page is for
A full-screen slide viewer for the project presentation. It shows seven slide images
exported from the deck, one at a time, with no editing and no live data — it is a
standalone viewer, not connected to the rest of the app.

## What you see
- The current slide filling the screen, with a thin progress bar across the top showing
  how far through the deck you are.
- A control bar: previous/next arrows, a "N / 7" counter, and a fullscreen toggle.
- A hint line at the bottom: `← → navigate · F fullscreen · ESC exit`.

## What you can do here
- **Keyboard**: Right arrow or Space for the next slide, Left arrow for the previous one,
  `F` to toggle fullscreen, Escape to exit (it exits fullscreen first if active, otherwise
  it leaves the page).
- **Mouse**: click the right half of the screen to advance, the left half to go back.
- **Touch**: swipe left for the next slide, right for the previous one.
- Navigation stops at the first and last slide — the prev/next buttons disable rather than
  wrap around.

## Common questions
- *Can I jump to a specific slide?* No. Only step forward or back one slide at a time.
- *Is this connected to the live simulation or agent data?* No. The slides are static
  images; nothing on this page reads from the backend.
- *Why does fullscreen not do anything?* Some browsers block fullscreen unless it is
  triggered by a direct user interaction — try clicking `F` or the fullscreen button again.
