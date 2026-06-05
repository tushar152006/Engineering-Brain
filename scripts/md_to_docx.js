const fs = require("fs");
const path = require("path");

const root = process.cwd();
const inputPath = path.join(root, "docs", "Engineering-Brain-Startup-Blueprint.md");
const outputDocx = path.join(root, "docs", "Engineering-Brain-Startup-Blueprint.docx");
const outputHtml = path.join(root, "docs", "Engineering-Brain-Startup-Blueprint.html");

const markdown = fs.readFileSync(inputPath, "utf8");

function escapeXml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function paragraph(text, style) {
  const styleXml = style ? `<w:pPr><w:pStyle w:val="${style}"/></w:pPr>` : "";
  const runStyle = style === "Code" ? '<w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/><w:sz w:val="18"/></w:rPr>' : "";
  const preserve = /^\s|\s$/.test(text) ? ' xml:space="preserve"' : "";
  return `<w:p>${styleXml}<w:r>${runStyle}<w:t${preserve}>${escapeXml(text)}</w:t></w:r></w:p>`;
}

function markdownToDocxBody(md) {
  const lines = md.split(/\r?\n/);
  const out = [];
  let inCode = false;
  for (const rawLine of lines) {
    const line = rawLine.replace(/\t/g, "    ");
    if (line.startsWith("```")) {
      inCode = !inCode;
      continue;
    }
    if (inCode) {
      out.push(paragraph(line.length ? line : " ", "Code"));
      continue;
    }
    if (line.trim() === "---") {
      out.push('<w:p><w:r><w:br w:type="page"/></w:r></w:p>');
      continue;
    }
    if (line.startsWith("# ")) {
      out.push(paragraph(line.slice(2).trim(), "Title"));
    } else if (line.startsWith("## ")) {
      out.push(paragraph(line.slice(3).trim(), "Heading1"));
    } else if (line.startsWith("### ")) {
      out.push(paragraph(line.slice(4).trim(), "Heading2"));
    } else if (line.startsWith("- ")) {
      out.push(paragraph("• " + line.slice(2).trim(), "ListParagraph"));
    } else if (/^\d+\.\s+/.test(line)) {
      out.push(paragraph(line.trim(), "ListParagraph"));
    } else if (line.trim() === "") {
      out.push(paragraph(" "));
    } else {
      out.push(paragraph(line.trim()));
    }
  }
  return out.join("");
}

function markdownToHtml(md) {
  const lines = md.split(/\r?\n/);
  const out = [];
  let inCode = false;
  for (const raw of lines) {
    const line = raw;
    if (line.startsWith("```")) {
      if (inCode) out.push("</code></pre>");
      else out.push("<pre><code>");
      inCode = !inCode;
      continue;
    }
    if (inCode) {
      out.push(escapeXml(line));
      continue;
    }
    if (line.startsWith("# ")) out.push(`<h1>${escapeXml(line.slice(2))}</h1>`);
    else if (line.startsWith("## ")) out.push(`<h2>${escapeXml(line.slice(3))}</h2>`);
    else if (line.startsWith("### ")) out.push(`<h3>${escapeXml(line.slice(4))}</h3>`);
    else if (line.startsWith("- ")) out.push(`<p class="bullet">• ${escapeXml(line.slice(2))}</p>`);
    else if (/^\d+\.\s+/.test(line)) out.push(`<p class="bullet">${escapeXml(line)}</p>`);
    else if (line.trim() === "---") out.push("<hr>");
    else if (line.trim() === "") out.push("");
    else out.push(`<p>${escapeXml(line)}</p>`);
  }
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Engineering Brain Startup Blueprint</title>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.55; color: #1f2937; max-width: 980px; margin: 48px auto; padding: 0 28px; }
    h1 { color: #111827; font-size: 34px; margin-top: 42px; border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; }
    h2 { color: #111827; font-size: 25px; margin-top: 32px; }
    h3 { color: #374151; font-size: 19px; margin-top: 24px; }
    p { margin: 8px 0; }
    .bullet { margin-left: 20px; }
    pre { background: #111827; color: #f9fafb; padding: 16px; overflow: auto; border-radius: 8px; }
    code { font-family: Consolas, "Courier New", monospace; font-size: 13px; }
    hr { border: 0; border-top: 1px solid #e5e7eb; margin: 32px 0; }
  </style>
</head>
<body>
${out.join("\n")}
</body>
</html>`;
}

function crc32(buf) {
  let table = crc32.table;
  if (!table) {
    table = crc32.table = Array.from({ length: 256 }, (_, n) => {
      let c = n;
      for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      return c >>> 0;
    });
  }
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = table[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function dosDateTime(date) {
  const year = Math.max(date.getFullYear(), 1980);
  const time = (date.getHours() << 11) | (date.getMinutes() << 5) | Math.floor(date.getSeconds() / 2);
  const day = ((year - 1980) << 9) | ((date.getMonth() + 1) << 5) | date.getDate();
  return { time, day };
}

function makeZip(files) {
  const chunks = [];
  const central = [];
  let offset = 0;
  const now = dosDateTime(new Date());

  for (const file of files) {
    const name = Buffer.from(file.name, "utf8");
    const data = Buffer.from(file.content, "utf8");
    const crc = crc32(data);

    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0, 6);
    local.writeUInt16LE(0, 8);
    local.writeUInt16LE(now.time, 10);
    local.writeUInt16LE(now.day, 12);
    local.writeUInt32LE(crc, 14);
    local.writeUInt32LE(data.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(name.length, 26);
    local.writeUInt16LE(0, 28);
    chunks.push(local, name, data);

    const header = Buffer.alloc(46);
    header.writeUInt32LE(0x02014b50, 0);
    header.writeUInt16LE(20, 4);
    header.writeUInt16LE(20, 6);
    header.writeUInt16LE(0, 8);
    header.writeUInt16LE(0, 10);
    header.writeUInt16LE(now.time, 12);
    header.writeUInt16LE(now.day, 14);
    header.writeUInt32LE(crc, 16);
    header.writeUInt32LE(data.length, 20);
    header.writeUInt32LE(data.length, 24);
    header.writeUInt16LE(name.length, 28);
    header.writeUInt16LE(0, 30);
    header.writeUInt16LE(0, 32);
    header.writeUInt16LE(0, 34);
    header.writeUInt16LE(0, 36);
    header.writeUInt32LE(0, 38);
    header.writeUInt32LE(offset, 42);
    central.push(header, name);
    offset += local.length + name.length + data.length;
  }

  const centralSize = central.reduce((sum, part) => sum + part.length, 0);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(files.length, 8);
  end.writeUInt16LE(files.length, 10);
  end.writeUInt32LE(centralSize, 12);
  end.writeUInt32LE(offset, 16);
  end.writeUInt16LE(0, 20);

  return Buffer.concat([...chunks, ...central, end]);
}

const documentXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    ${markdownToDocxBody(markdown)}
    <w:sectPr>
      <w:pgSz w:w="12240" w:h="15840"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>
    </w:sectPr>
  </w:body>
</w:document>`;

const stylesXml = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:rPr><w:sz w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:rPr><w:b/><w:sz w:val="40"/><w:color w:val="111827"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="Heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="32"/><w:color w:val="111827"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="Heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="26"/><w:color w:val="374151"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph">
    <w:name w:val="List Paragraph"/>
    <w:pPr><w:ind w:left="720"/></w:pPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Code">
    <w:name w:val="Code"/>
    <w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/><w:sz w:val="18"/></w:rPr>
  </w:style>
</w:styles>`;

const files = [
  {
    name: "[Content_Types].xml",
    content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>`
  },
  {
    name: "_rels/.rels",
    content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>`
  },
  {
    name: "word/_rels/document.xml.rels",
    content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>`
  },
  { name: "word/document.xml", content: documentXml },
  { name: "word/styles.xml", content: stylesXml },
  {
    name: "docProps/core.xml",
    content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Engineering Brain Startup Blueprint</dc:title>
  <dc:creator>Codex</dc:creator>
  <cp:lastModifiedBy>Codex</cp:lastModifiedBy>
</cp:coreProperties>`
  },
  {
    name: "docProps/app.xml",
    content: `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Codex</Application></Properties>`
  }
];

fs.writeFileSync(outputHtml, markdownToHtml(markdown));
fs.writeFileSync(outputDocx, makeZip(files));

console.log(`Generated:
- ${outputDocx}
- ${outputHtml}
- ${inputPath}`);
