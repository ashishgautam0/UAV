// Generate a clean PDF résumé from the stored LaTeX source, entirely in the
// browser (jsPDF). This does NOT run a TeX engine — it parses the known résumé
// template macros into a structured layout. Anything it doesn't recognise is
// cleaned of LaTeX markup and rendered as plain text, so edits degrade
// gracefully rather than breaking the download.
import { jsPDF } from "jspdf";

// ---- LaTeX inline cleanup ---------------------------------------------------
function clean(input: string): string {
  let s = input;
  // Strip comments
  s = s.replace(/(^|[^\\])%.*$/gm, "$1");
  // Common inline wrappers → their content
  s = s.replace(/\\(?:textbf|textit|emph|scshape|small|large|Huge|Large|underline|texttt)\s*\{([^{}]*)\}/g, "$1");
  // \href{url}{text} → text
  s = s.replace(/\\href\s*\{[^{}]*\}\s*\{([^{}]*)\}/g, "$1");
  // Math separators used as bullets/pipes
  s = s.replace(/\$\s*\|\s*\$/g, "|");
  s = s.replace(/\$[^$]*\$/g, ""); // drop any other inline math
  // Escaped specials
  s = s
    .replace(/\\&/g, "&")
    .replace(/\\%/g, "%")
    .replace(/\\\$/g, "$")
    .replace(/\\_/g, "_")
    .replace(/\\#/g, "#")
    .replace(/\\~\{\}/g, "~")
    .replace(/~/g, " ");
  // Quotes and dashes
  s = s.replace(/``/g, "“").replace(/''/g, "”");
  s = s.replace(/---/g, "—").replace(/--/g, "–");
  // Line breaks / spacing commands
  s = s.replace(/\\\\/g, " ").replace(/\\vspace\s*\{[^{}]*\}/g, "").replace(/\\ /g, " ");
  // Any leftover simple commands (\item, \scshape, …) and stray braces
  s = s.replace(/\\[a-zA-Z]+\*?/g, "").replace(/[{}]/g, "");
  return s.replace(/\s+/g, " ").trim();
}

// Read `count` balanced {…} arguments starting at `pos` (which must be at a "{").
function readArgs(str: string, pos: number, count: number): { args: string[]; end: number } {
  const args: string[] = [];
  let i = pos;
  for (let a = 0; a < count; a++) {
    while (i < str.length && /\s/.test(str[i])) i++;
    if (str[i] !== "{") break;
    let depth = 0;
    const start = i + 1;
    for (; i < str.length; i++) {
      if (str[i] === "{") depth++;
      else if (str[i] === "}") {
        depth--;
        if (depth === 0) break;
      }
    }
    args.push(str.slice(start, i));
    i++; // past closing }
  }
  return { args, end: i };
}

export type Block =
  | { t: "name"; text: string }
  | { t: "contact"; text: string }
  | { t: "section"; text: string }
  | { t: "subheading"; left: string; right: string; subLeft: string; subRight: string }
  | { t: "project"; left: string; right: string }
  | { t: "item"; text: string }
  | { t: "skill"; label: string; rest: string }
  | { t: "plain"; text: string };

export function parseResume(tex: string): Block[] {
  const blocks: Block[] = [];
  const docStart = tex.indexOf("\\begin{document}");
  const body = docStart >= 0 ? tex.slice(docStart + "\\begin{document}".length) : tex;

  // Heading (name + contact) from the \begin{center} … \end{center} block.
  const center = /\\begin\{center\}([\s\S]*?)\\end\{center\}/.exec(body);
  if (center) {
    const inner = center[1];
    // Name: first {\Huge \scshape NAME} group (or first non-empty cleaned line)
    const nameMatch = /\{\\Huge[^}]*?\\scshape\s*([^}\\]+)\}/.exec(inner);
    const name = clean(nameMatch ? nameMatch[1] : inner.split("\\\\")[0]);
    if (name) blocks.push({ t: "name", text: name });
    // Contact: the remainder after the name, cleaned
    const afterName = nameMatch ? inner.slice(nameMatch.index + nameMatch[0].length) : inner;
    const contact = clean(afterName);
    if (contact) blocks.push({ t: "contact", text: contact });
  }

  // Walk the rest, capturing known macros in order.
  const rest = center ? body.slice(center.index + center[0].length) : body;
  const macroRe = /\\(section|resumeSubheading|resumeProjectHeading|resumeItem)\b/g;
  let m: RegExpExecArray | null;
  while ((m = macroRe.exec(rest)) !== null) {
    const kind = m[1];
    const after = m.index + m[0].length;
    if (kind === "section") {
      const { args, end } = readArgs(rest, after, 1);
      if (args[0]) blocks.push({ t: "section", text: clean(args[0]) });
      macroRe.lastIndex = end;
    } else if (kind === "resumeSubheading") {
      const { args, end } = readArgs(rest, after, 4);
      blocks.push({
        t: "subheading",
        left: clean(args[0] || ""),
        right: clean(args[1] || ""),
        subLeft: clean(args[2] || ""),
        subRight: clean(args[3] || ""),
      });
      macroRe.lastIndex = end;
    } else if (kind === "resumeProjectHeading") {
      const { args, end } = readArgs(rest, after, 2);
      blocks.push({ t: "project", left: clean(args[0] || ""), right: clean(args[1] || "") });
      macroRe.lastIndex = end;
    } else if (kind === "resumeItem") {
      const { args, end } = readArgs(rest, after, 1);
      if (args[0]) blocks.push({ t: "item", text: clean(args[0]) });
      macroRe.lastIndex = end;
    }
  }

  // Skills: the Skills section stores raw \textbf{Label}{: values} lines rather
  // than \resumeItem. Capture them so they aren't lost.
  const skillsSec = /\\section\{Skills\}([\s\S]*?)(?:\\section|\\end\{document\}|$)/.exec(body);
  if (skillsSec) {
    const skillRe = /\\textbf\{([^{}]+)\}\s*\{:\s*([^{}]*)\}/g;
    let s: RegExpExecArray | null;
    // Insert skill blocks right after the Skills section header we already emitted.
    const skillBlocks: Block[] = [];
    while ((s = skillRe.exec(skillsSec[1])) !== null) {
      skillBlocks.push({ t: "skill", label: clean(s[1]), rest: clean(s[2]) });
    }
    if (skillBlocks.length) {
      const idx = blocks.findIndex((b) => b.t === "section" && b.text.toLowerCase() === "skills");
      if (idx >= 0) blocks.splice(idx + 1, 0, ...skillBlocks);
      else blocks.push(...skillBlocks);
    }
  }

  return blocks;
}

// ---- Render to PDF ----------------------------------------------------------
export function buildResumePdf(latex: string): jsPDF {
  const blocks = parseResume(latex);
  const doc = new jsPDF({ unit: "pt", format: "letter" });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const margin = 50;
  const contentW = pageW - margin * 2;
  const rightX = pageW - margin;
  let y = margin;

  const ensure = (needed: number) => {
    if (y + needed > pageH - margin) {
      doc.addPage();
      y = margin;
    }
  };
  const wrapped = (text: string, size: number, fontStyle: "normal" | "bold" | "italic", lineH: number, indent = 0) => {
    doc.setFont("helvetica", fontStyle);
    doc.setFontSize(size);
    const lines = doc.splitTextToSize(text, contentW - indent) as string[];
    for (const ln of lines) {
      ensure(lineH);
      doc.text(ln, margin + indent, y);
      y += lineH;
    }
  };

  for (const b of blocks) {
    switch (b.t) {
      case "name":
        ensure(26);
        doc.setFont("helvetica", "bold");
        doc.setFontSize(20);
        doc.setTextColor(20);
        doc.text(b.text, pageW / 2, y + 4, { align: "center" });
        y += 24;
        break;
      case "contact": {
        doc.setFont("helvetica", "normal");
        doc.setFontSize(9);
        doc.setTextColor(90);
        const lines = doc.splitTextToSize(b.text, contentW) as string[];
        for (const ln of lines) {
          ensure(12);
          doc.text(ln, pageW / 2, y, { align: "center" });
          y += 12;
        }
        doc.setTextColor(20);
        y += 6;
        break;
      }
      case "section":
        ensure(22);
        y += 6;
        doc.setFont("helvetica", "bold");
        doc.setFontSize(11);
        doc.setTextColor(20);
        doc.text(b.text.toUpperCase(), margin, y);
        y += 4;
        doc.setDrawColor(180);
        doc.setLineWidth(0.6);
        doc.line(margin, y, rightX, y);
        y += 12;
        break;
      case "subheading":
        ensure(26);
        doc.setTextColor(20);
        doc.setFont("helvetica", "bold");
        doc.setFontSize(10.5);
        doc.text(b.left, margin, y);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(9.5);
        doc.setTextColor(90);
        if (b.right) doc.text(b.right, rightX, y, { align: "right" });
        y += 13;
        if (b.subLeft || b.subRight) {
          doc.setFont("helvetica", "italic");
          doc.setFontSize(9.5);
          doc.setTextColor(60);
          if (b.subLeft) doc.text(b.subLeft, margin, y);
          if (b.subRight) doc.text(b.subRight, rightX, y, { align: "right" });
          y += 13;
        }
        doc.setTextColor(20);
        break;
      case "project":
        ensure(15);
        doc.setFont("helvetica", "bold");
        doc.setFontSize(10);
        doc.setTextColor(20);
        doc.text(b.left, margin, y);
        if (b.right) {
          doc.setFont("helvetica", "normal");
          doc.setFontSize(9.5);
          doc.setTextColor(90);
          doc.text(b.right, rightX, y, { align: "right" });
        }
        doc.setTextColor(20);
        y += 13;
        break;
      case "item":
        doc.setTextColor(40);
        ensure(12);
        doc.setFont("helvetica", "normal");
        doc.setFontSize(9.5);
        doc.text("•", margin + 4, y);
        wrapped(b.text, 9.5, "normal", 12, 14);
        y += 2;
        doc.setTextColor(20);
        break;
      case "skill": {
        ensure(12);
        doc.setFont("helvetica", "bold");
        doc.setFontSize(9.5);
        doc.setTextColor(20);
        const label = b.label + ": ";
        const labelW = doc.getTextWidth(label);
        doc.text(label, margin, y);
        doc.setFont("helvetica", "normal");
        const restLines = doc.splitTextToSize(b.rest, contentW - labelW) as string[];
        doc.text(restLines[0] || "", margin + labelW, y);
        y += 12;
        for (let i = 1; i < restLines.length; i++) {
          ensure(12);
          doc.text(restLines[i], margin, y);
          y += 12;
        }
        y += 2;
        break;
      }
      case "plain":
        wrapped(b.text, 9.5, "normal", 12);
        break;
    }
  }

  return doc;
}

// Trigger a browser download of the résumé as a PDF.
export function downloadResumePdf(latex: string, filename = "Subidh Khanal Resume.pdf"): void {
  const doc = buildResumePdf(latex);
  doc.save(filename);
}
