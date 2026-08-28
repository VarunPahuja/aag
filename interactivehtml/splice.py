import re, pathlib, sys

root = pathlib.Path(".")
idx  = root / "index.html"

mock_path = next((p for p in [root/"briefing-mockups.html", root/"docs"/"briefing-mockups.html"] if p.exists()), None)
rev_path  = next((p for p in [root/"review-section.html", root/"review-sections.html"] if p.exists()), None)

for name, p in [("index.html", idx), ("briefing-mockups.html", mock_path), ("review-section(s).html", rev_path)]:
    if p is None or not p.exists():
        sys.exit(f"Missing: {name}")

html   = idx.read_text(encoding="utf-8")
m      = mock_path.read_text(encoding="utf-8")
review = rev_path.read_text(encoding="utf-8")

if 'id="fm-mockup-agents"' in html:
    sys.exit("Already spliced. Restore index.backup.html first if you want to redo it.")

# patch the mockups
m = m.replace("min-width: 700px;", "min-width: 0;")
m = m.replace("background-color: #F7F8F6;", "background-color: #F7F8F6; border: 1px solid #E2E8F0;")
m = m.replace("Promotion granted → ₹50,000", "Promotion granted → ₹15,000")
m = m.replace("Sustained performance earned HIGH autonomy tier.",
              "Sustained performance earned MEDIUM autonomy tier.")

FRAMING = """  <p>These are the administrator screens as they exist in the current build. They predate the contract freeze, so they still show the earlier three-tier authority model rather than the five-rung ladder described above, and the governance opinions and audit-chain verification are not yet surfaced. Migration onto the frozen contracts is scheduled for 2 September; what follows is what runs today.</p>
  <div class="note"><b>Reading these accurately.</b> Three tiers rather than five rungs. Accuracy and the Wilson lower bound drawn as two separate lines rather than a shaded confidence band. A single approve-or-reject flow without the four per-agent governance opinions. Each is a scheduled change rather than a design decision &mdash; the statistical engine underneath already produces all of it, and the screens are the last lane to migrate.</div>
"""

# locate the demo section by id, keep its eyebrow + h2, replace everything after
sec = re.search(r'<section id="demo">(.*?)</section>', html, re.S)
if not sec:
    sys.exit('Could not find <section id="demo">. Is this the right index.html?')

head = re.match(r'\s*<div class="eyebrow">.*?</div>\s*<h2>.*?</h2>', sec.group(1), re.S)
if not head:
    sys.exit("Demo section header not in the expected shape.")

new_section = '<section id="demo">\n' + head.group(0) + "\n" + FRAMING + "\n" + m + "\n</section>"
html = html[:sec.start()] + new_section + html[sec.end():]

# nav link
if 'href="#review"' not in html:
    html = html.replace('<a href="#questions">Open questions</a>',
                        '<a href="#questions">Open questions</a>\n  <a href="#review">Review notes</a>')

# review section
html = html.replace("</main>", review + "\n</main>", 1)

idx.write_text(html, encoding="utf-8")
print("Done — open index.html and check the five tabs, the Wilson slider, and the notes boxes.")