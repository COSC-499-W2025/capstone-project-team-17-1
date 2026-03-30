function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function renderInline(text) {
  let out = String(text ?? "");
  out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
  out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  out = out.replace(/_([^_]+)_/g, "<em>$1</em>");
  return out;
}

export function renderMarkdown(text) {
  const raw = String(text ?? "");
  const codeBlocks = [];
  const tokenized = raw.replace(/```([a-zA-Z0-9_-]+)?\n?([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    const safeCode = escapeHtml(String(code || "").replace(/\n$/, ""));
    const langClass = lang ? ` class="language-${escapeHtml(lang)}"` : "";
    codeBlocks.push(`<pre><code${langClass}>${safeCode}</code></pre>`);
    return `@@CODE_BLOCK_${idx}@@`;
  });

  const escaped = escapeHtml(tokenized).replace(/\r\n/g, "\n");
  const lines = escaped.split("\n");
  const chunks = [];
  let inUl = false;
  let inOl = false;
  let paragraph = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    chunks.push(`<p>${renderInline(paragraph.join("<br>"))}</p>`);
    paragraph = [];
  };
  const closeLists = () => {
    if (inUl) {
      chunks.push("</ul>");
      inUl = false;
    }
    if (inOl) {
      chunks.push("</ol>");
      inOl = false;
    }
  };

  for (const lineRaw of lines) {
    const line = lineRaw.trimEnd();
    const codeTokenMatch = line.match(/^@@CODE_BLOCK_(\d+)@@$/);
    if (codeTokenMatch) {
      flushParagraph();
      closeLists();
      chunks.push(codeBlocks[Number(codeTokenMatch[1])] || "");
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      closeLists();
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      flushParagraph();
      closeLists();
      const level = headingMatch[1].length;
      chunks.push(`<h${level}>${renderInline(headingMatch[2])}</h${level}>`);
      continue;
    }

    const ulMatch = line.match(/^[-*+]\s+(.+)$/);
    if (ulMatch) {
      flushParagraph();
      if (inOl) {
        chunks.push("</ol>");
        inOl = false;
      }
      if (!inUl) {
        chunks.push("<ul>");
        inUl = true;
      }
      chunks.push(`<li>${renderInline(ulMatch[1])}</li>`);
      continue;
    }

    const olMatch = line.match(/^\d+\.\s+(.+)$/);
    if (olMatch) {
      flushParagraph();
      if (inUl) {
        chunks.push("</ul>");
        inUl = false;
      }
      if (!inOl) {
        chunks.push("<ol>");
        inOl = true;
      }
      chunks.push(`<li>${renderInline(olMatch[1])}</li>`);
      continue;
    }

    closeLists();
    paragraph.push(line);
  }

  flushParagraph();
  closeLists();

  let html = chunks.join("");
  html = html.replace(/@@CODE_BLOCK_(\d+)@@/g, (_, index) => codeBlocks[Number(index)] || "");
  return html;
}
