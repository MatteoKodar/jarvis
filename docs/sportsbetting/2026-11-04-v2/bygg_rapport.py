"""Bygg fristående HTML-bilagor och bädda in kopierbart uppdrag. Endast dokumentmappen skrivs."""
import html
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def inline(text):
    # Escape först; tillåt enbart enkla dokumentlänkar, fetstil och inlinekod.
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    def link(match):
        label, url = match.groups()
        if ":" in url and not url.startswith(("https://", "http://")):
            return label
        return f'<a href="{url}">{label}</a>'
    return re.sub(r"\[([^\]]+)\]\(([^\s)]+)\)", link, text)


def render(text):
    lines, blocks, index = text.splitlines(), [], 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("```"):
            code = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            blocks.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            index += 1
            continue
        if line.startswith("|") and index + 1 < len(lines) and re.fullmatch(r"[| :\-]+", lines[index + 1]):
            header = line.strip("|").split("|")
            cells = lambda values, tag: "".join(f"<{tag}>{inline(v.strip())}</{tag}>" for v in values)
            table = ["<div class=scroll><table><thead><tr>" + cells(header, "th") + "</tr></thead><tbody>"]
            index += 2
            while index < len(lines) and lines[index].startswith("|"):
                table.append("<tr>" + cells(lines[index].strip("|").split("|"), "td") + "</tr>")
                index += 1
            blocks.append("".join(table) + "</tbody></table></div>")
            continue
        heading = re.match(r"^(#{1,4}) (.*)", line)
        if heading:
            level = len(heading[1])
            blocks.append(f"<h{level}>" + inline(heading[2]) + f"</h{level}>")
        elif re.match(r"^(- |\d+\. )", line):
            ordered = not line.startswith("- ")
            tag = "ol" if ordered else "ul"
            items = []
            pattern = r"^\d+\. " if ordered else r"^- "
            while index < len(lines) and re.match(pattern, lines[index]):
                items.append("<li>" + inline(re.sub(pattern, "", lines[index])) + "</li>")
                index += 1
            blocks.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue
        else:
            blocks.append("<p>" + inline(line) + "</p>")
        index += 1
    return "\n".join(blocks)


def main():
    path = HERE / "plan.html"
    page = path.read_text(encoding="utf-8")
    css = re.search(r"<style>(.*?)</style>", page, re.S)[1]
    text = (HERE / "IMPLEMENTATIONSUPPDRAG.md").read_text(encoding="utf-8")
    page, count = re.subn(r'(<textarea id="implementation-text"[^>]*>).*?(</textarea>)',
                         lambda m: m[1] + html.escape(text) + m[2], page, count=1, flags=re.S)
    assert count == 1
    for stem in ("ekonomi", "statistik", "data-kallor", "kritikergranskning"):
        source = HERE / (stem + ".md")
        content = source.read_text(encoding="utf-8")
        title = content.splitlines()[0].lstrip("# ")
        document = ('<!doctype html><html lang="sv"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width,initial-scale=1">'
                    f'<title>{html.escape(title)}</title><style>{css}</style></head><body><main>'
                    '<a href="plan.html">← Till huvudplanen</a> · '
                    f'<a href="{source.name}">Källtext för kopiering</a>'
                    + render(content) + '<p><a href="plan.html">← Till huvudplanen</a></p></main></body></html>')
        (HERE / (stem + ".html")).write_text(document, encoding="utf-8")
        page = page.replace(f'href="{stem}.md"', f'href="{stem}.html"')
    path.write_text(page, encoding="utf-8")
    print("Plan och fyra fristående läsbara bilagor byggda.")


if __name__ == "__main__":
    main()
