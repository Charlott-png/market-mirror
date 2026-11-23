import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const scriptDir = path.dirname(__filename);
const projectDir = path.dirname(scriptDir);
const htmlPath = path.join(scriptDir, "index.html");
const buildDir = path.join(projectDir, ".codex-build", "market-mirror-pptx");
const renderDir = path.join(buildDir, "rendered");
const outputPath = path.join(projectDir, "MarketMirror_Presentation.pptx");
const validatedOutputDir = path.join(projectDir, ".codex-output");

const SKILL_DIR = "C:\\Users\\Amaal\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.1105.12137\\skills\\presentations";
const RUNTIME_PYTHON = "C:\\Program Files\\WindowsApps\\OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt\\dependencies\\python\\python.exe";
const RUNTIME_NODE_MODULES = "C:\\Program Files\\WindowsApps\\OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt\\dependencies\\node\\node_modules";
process.env.RUNTIME_NODE_MODULES = RUNTIME_NODE_MODULES;
process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES = RUNTIME_NODE_MODULES;

const NAVY = "#0A1128";
const NAVY_2 = "#111B38";
const NAVY_3 = "#17213F";
const GOLD = "#D4AF37";
const GOLD_LIGHT = "#F4D76B";
const GOLD_DARK = "#6F5B24";
const OFF_WHITE = "#F4F0E6";
const MUTED = "#C9C2B4";
const ROSE = "#F29A9A";
const HEADING_FONT = "Georgia";
const BODY_FONT = "Arial";
const W = 1280;
const H = 720;

function decodeEntities(value) {
  const entities = {
    "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": "\"",
    "&#39;": "'", "&nbsp;": " ", "&mdash;": "—", "&ndash;": "–",
    "&rarr;": "→", "&middot;": "·", "&check;": "✓", "&ldquo;": "“",
    "&rdquo;": "”", "&rsquo;": "’",
  };
  return value.replace(/&(amp|lt|gt|quot|#39|nbsp|mdash|ndash|rarr|middot|check|ldquo|rdquo|rsquo);/g, match => entities[match] ?? match);
}

function plain(value = "") {
  return decodeEntities(value)
    .replace(/<br\s*\/?\s*>/gi, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/[ \t\r\f\v]+/g, " ")
    .replace(/ *\n */g, "\n")
    .trim();
}

function firstTag(html, tag) {
  const match = html.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i"));
  return plain(match?.[1]);
}

function firstClass(html, className, tag = "[a-z0-9]+") {
  const match = html.match(new RegExp(`<${tag}[^>]*class="[^"]*\\b${className}\\b[^"]*"[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i"));
  return plain(match?.[1]);
}

function allBlocks(html, pattern) {
  return Array.from(html.matchAll(pattern), match => match[1]);
}

function parseHtml(html) {
  const sections = Array.from(html.matchAll(/<section class="slide(?: is-active)?" id="slide-(\d+)"[\s\S]*?<\/section>/gi));
  if (sections.length !== 8) throw new Error(`Expected 8 HTML slides, found ${sections.length}.`);

  return sections.map(sectionMatch => {
    const section = sectionMatch[0];
    const main = section.split('<aside class="speaker-notes"')[0];
    const notesArea = section.match(/<aside class="speaker-notes"[\s\S]*?<ul>([\s\S]*?)<\/ul>[\s\S]*?<\/aside>/i)?.[1] ?? "";
    return {
      number: Number(sectionMatch[1]),
      main,
      label: firstClass(main, "slide-number", "p"),
      title: firstTag(main, sectionMatch[1] === "1" ? "h1" : "h2"),
      lead: firstClass(main, "lead", "p"),
      kicker: firstClass(main, "kicker", "p"),
      notes: allBlocks(notesArea, /<li>([\s\S]*?)<\/li>/gi).map(plain),
    };
  });
}

function addBox(slide, x, y, w, h, options = {}) {
  const geometry = options.geometry ?? "roundRect";
  const config = {
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill: options.fill ?? NAVY_2,
    line: { style: "solid", fill: options.line ?? GOLD_DARK, width: options.lineWidth ?? 1 },
    shadow: options.shadow ?? undefined,
  };
  if (geometry === "roundRect") config.borderRadius = "rounded-xl";
  return slide.shapes.add(config);
}

function addText(slide, text, x, y, w, h, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text ?? "";
  shape.text.style = {
    typeface: options.font ?? BODY_FONT,
    fontSize: options.size ?? 22,
    bold: options.bold ?? false,
    italic: options.italic ?? false,
    color: options.color ?? OFF_WHITE,
    alignment: options.align ?? "left",
    verticalAlignment: options.valign ?? "top",
    autoFit: options.autoFit ?? "shrinkText",
    wrap: "square",
    lineSpacing: options.lineSpacing ?? 1.05,
    insets: options.insets ?? 0,
  };
  return shape;
}

function addGoldRule(slide, x, y, w = 56, h = 2) {
  addBox(slide, x, y, w, h, { geometry: "rect", fill: GOLD, line: GOLD, lineWidth: 0 });
}

function addFrame(slide, index, timing, label) {
  slide.background.fill = NAVY;
  addBox(slide, 0, 0, W, 4, { geometry: "rect", fill: NAVY_3, line: NAVY_3, lineWidth: 0 });
  addBox(slide, 0, 0, W * (index / 8), 4, { geometry: "rect", fill: GOLD_LIGHT, line: GOLD_LIGHT, lineWidth: 0 });
  addGoldRule(slide, 38, 30, 26, 1);
  addText(slide, "MARKET MIRROR", 72, 20, 230, 24, { size: 13, bold: true, color: MUTED });
  addText(slide, timing, 1172, 19, 68, 28, { size: 13, bold: true, color: GOLD_LIGHT, align: "center", valign: "middle" });
  addText(slide, label.toUpperCase(), 64, 76, 560, 24, { size: 14, bold: true, color: GOLD_LIGHT });
  addGoldRule(slide, 64, 104, 70, 2);
  addText(slide, `SLIDE ${index} OF 8`, 570, 681, 140, 18, { size: 11, bold: true, color: GOLD_LIGHT, align: "center" });
}

function notesFor(slide, data) {
  slide.speakerNotes.text = [
    `Estimated time: ${["1:00", "1:00", "1:00", "1:30", "1:30", "1:30", "1:30", "1:00"][data.number - 1]}`,
    "",
    ...data.notes.map(note => `• ${note}`),
  ].join("\n");
  slide.speakerNotes.setVisible(true);
}

function buildSlide1(presentation, data) {
  const slide = presentation.slides.add();
  addFrame(slide, 1, "1:00", data.label);
  addText(slide, "AI-POWERED LUXURY MARKETPLACE", 64, 130, 520, 24, { size: 15, bold: true, color: GOLD });
  addText(slide, "Market", 64, 169, 335, 92, { size: 68, font: HEADING_FONT, bold: true });
  addText(slide, "Mirror", 347, 169, 315, 92, { size: 68, font: HEADING_FONT, bold: true, color: GOLD_LIGHT });
  addText(slide, data.lead, 64, 275, 620, 92, { size: 23, color: MUTED, lineSpacing: 1.1 });
  addBox(slide, 64, 410, 42, 42, { geometry: "ellipse", fill: NAVY, line: GOLD, lineWidth: 1 });
  addText(slide, "AM", 65, 410, 40, 42, { size: 13, font: HEADING_FONT, color: GOLD_LIGHT, align: "center", valign: "middle" });
  addText(slide, "Amaal (AzureMonarch)\nFull-Stack Developer & Student", 124, 405, 330, 58, { size: 17, bold: true });
  addText(slide, "Academic Committee\n10-minute pitch", 475, 405, 210, 58, { size: 16, color: MUTED });

  addBox(slide, 746, 164, 454, 340, { fill: NAVY_2, line: GOLD_DARK, lineWidth: 1, shadow: "shadow-sm" });
  addBox(slide, 746, 164, 4, 340, { geometry: "rect", fill: GOLD, line: GOLD, lineWidth: 0 });
  addText(slide, "THE VALUE PROPOSITION", 780, 197, 300, 24, { size: 14, bold: true, color: GOLD });
  addText(slide, "List faster. Discover smarter. Trade with confidence.", 780, 236, 365, 112, { size: 34, font: HEADING_FONT, bold: true, color: GOLD_LIGHT });
  const agenda = [
    ["Why", "The market gap"], ["How", "Product + architecture"], ["Proof", "Features + validation"],
  ];
  agenda.forEach(([head, body], i) => {
    const x = 780 + i * 122;
    addGoldRule(slide, x, 378, 100, 1);
    addText(slide, head, x, 393, 100, 22, { size: 15, bold: true });
    addText(slide, body, x, 420, 105, 48, { size: 14, color: MUTED });
  });
  notesFor(slide, data);
}

function buildSlide2(presentation, data) {
  const slide = presentation.slides.add();
  addFrame(slide, 2, "1:00", data.label);
  addText(slide, data.title, 64, 126, 930, 84, { size: 45, font: HEADING_FONT, bold: true });
  addText(slide, data.lead, 64, 218, 1020, 55, { size: 20, color: MUTED });
  const cards = allBlocks(data.main, /<article class="pain-card">([\s\S]*?)<\/article>/gi).map(block => ({
    index: firstClass(block, "pain-index", "span"), title: firstTag(block, "h3"), body: firstTag(block, "p"),
  }));
  cards.forEach((card, i) => {
    const x = 64 + i * 388;
    addBox(slide, x, 305, 360, 222, { fill: "#171126", line: "#6A3848", lineWidth: 1 });
    addBox(slide, x + 20, 326, 38, 38, { fill: "#21172E", line: ROSE, lineWidth: 1 });
    addText(slide, card.index, x + 20, 326, 38, 38, { size: 14, bold: true, color: ROSE, align: "center", valign: "middle" });
    addText(slide, card.title, x + 20, 386, 310, 38, { size: 25, font: HEADING_FONT, bold: true });
    addText(slide, card.body, x + 20, 432, 315, 72, { size: 17, color: MUTED });
  });
  addBox(slide, 64, 548, 1136, 52, { geometry: "rect", fill: NAVY_2, line: NAVY_2, lineWidth: 0 });
  addBox(slide, 64, 548, 3, 52, { geometry: "rect", fill: ROSE, line: ROSE, lineWidth: 0 });
  addText(slide, "THE GAP", 82, 563, 84, 21, { size: 14, bold: true });
  addText(slide, "Local simplicity should still provide a credible digital experience.", 170, 559, 690, 28, { size: 17, color: MUTED });
  addText(slide, "INTELLIGENT + TRUSTWORTHY", 914, 559, 260, 28, { size: 14, bold: true, color: GOLD_LIGHT, align: "right" });
  notesFor(slide, data);
}

function buildSlide3(presentation, data) {
  const slide = presentation.slides.add();
  addFrame(slide, 3, "1:00", data.label);
  addText(slide, data.kicker.toUpperCase(), 64, 130, 340, 22, { size: 14, bold: true, color: GOLD });
  addText(slide, data.title, 64, 166, 585, 150, { size: 43, font: HEADING_FONT, bold: true });
  addText(slide, data.lead, 64, 332, 575, 132, { size: 20, color: MUTED, lineSpacing: 1.1 });
  const pillars = allBlocks(data.main, /<div class="vision-pillar">([\s\S]*?)<\/div>/gi).map(block => {
    const spans = allBlocks(block, /<span>([\s\S]*?)<\/span>/gi);
    return { index: plain(spans[0]), title: firstTag(spans[1] ?? "", "strong"), body: firstTag(spans[1] ?? "", "small") };
  });
  pillars.forEach((pillar, i) => {
    const y = 126 + i * 112;
    addBox(slide, 720, y, 480, 88, { fill: NAVY_2, line: GOLD_DARK, lineWidth: 1 });
    addBox(slide, 744, y + 22, 42, 42, { geometry: "ellipse", fill: GOLD, line: GOLD, lineWidth: 0 });
    addText(slide, pillar.index, 744, y + 22, 42, 42, { size: 16, bold: true, color: NAVY, align: "center", valign: "middle" });
    addText(slide, pillar.title, 810, y + 17, 330, 26, { size: 19, bold: true });
    addText(slide, pillar.body, 810, y + 47, 340, 30, { size: 15, color: MUTED });
  });
  notesFor(slide, data);
}

function buildSlide4(presentation, data) {
  const slide = presentation.slides.add();
  addFrame(slide, 4, "1:30", data.label);
  addText(slide, data.title, 64, 124, 850, 66, { size: 42, font: HEADING_FONT, bold: true });
  addText(slide, data.lead, 64, 194, 1050, 48, { size: 18, color: MUTED });
  const nodes = allBlocks(data.main, /<div class="architecture-node">([\s\S]*?)<\/div>/gi).map(block => ({
    label: firstClass(block, "node-label", "span"), title: firstTag(block, "strong"), body: firstTag(block, "small"),
  }));
  nodes.forEach((node, i) => {
    const x = 64 + i * 392;
    addBox(slide, x, 278, 340, 160, { fill: NAVY_2, line: GOLD_DARK, lineWidth: 1 });
    addText(slide, node.label.toUpperCase(), x + 22, 300, 150, 20, { size: 12, bold: true, color: GOLD });
    addText(slide, node.title, x + 22, 333, 296, 32, { size: 22, bold: true });
    addText(slide, node.body, x + 22, 373, 296, 48, { size: 15, color: MUTED });
    if (i < 2) addText(slide, "→", x + 350, 330, 38, 42, { size: 29, bold: true, color: GOLD, align: "center" });
  });
  const integrations = allBlocks(data.main, /<div class="integration-card">([\s\S]*?)<\/div>/gi).map(block => ({
    title: firstTag(block, "strong"), body: firstTag(block, "span"),
  }));
  integrations.forEach((item, i) => {
    const x = 260 + i * 420;
    addBox(slide, x, 466, 360, 62, { fill: NAVY_3, line: GOLD_DARK, lineWidth: 1 });
    addText(slide, item.title, x + 18, 478, 190, 22, { size: 17, bold: true });
    addText(slide, item.body, x + 205, 478, 135, 22, { size: 14, color: GOLD_LIGHT, align: "right" });
  });
  const tech = allBlocks(data.main, /<span class="tech-badge">([\s\S]*?)<\/span>/gi).map(plain);
  addText(slide, tech.join("   ·   "), 64, 566, 1136, 30, { size: 15, bold: true, color: MUTED, align: "center" });
  notesFor(slide, data);
}

function buildSlide5(presentation, data) {
  const slide = presentation.slides.add();
  addFrame(slide, 5, "1:30", data.label);
  addText(slide, data.title, 64, 126, 780, 62, { size: 43, font: HEADING_FONT, bold: true });
  addText(slide, data.lead, 64, 193, 850, 35, { size: 19, color: MUTED });
  const steps = allBlocks(data.main, /<article class="demo-step">([\s\S]*?)<\/article>/gi).map(block => ({
    icon: firstClass(block, "feature-icon", "span"), title: firstTag(block, "h3"), body: firstTag(block, "p"),
  }));
  steps.forEach((step, i) => {
    const x = 64 + i * 228;
    addBox(slide, x, 270, 204, 260, { fill: NAVY_2, line: GOLD_DARK, lineWidth: 1 });
    addBox(slide, x + 68, 296, 68, 68, { geometry: "ellipse", fill: GOLD, line: GOLD, lineWidth: 0 });
    addText(slide, step.icon, x + 68, 296, 68, 68, { size: 20, bold: true, color: NAVY, align: "center", valign: "middle" });
    addText(slide, step.title, x + 18, 384, 168, 34, { size: 23, font: HEADING_FONT, bold: true, align: "center" });
    addText(slide, step.body, x + 20, 427, 164, 78, { size: 15, color: MUTED, align: "center" });
  });
  addText(slide, firstClass(data.main, "demo-note", "p"), 120, 564, 1040, 34, { size: 16, bold: true, color: GOLD_LIGHT, align: "center" });
  notesFor(slide, data);
}

function buildSlide6(presentation, data) {
  const slide = presentation.slides.add();
  addFrame(slide, 6, "1:30", data.label);
  addText(slide, data.title, 64, 126, 900, 68, { size: 44, font: HEADING_FONT, bold: true });
  const metrics = allBlocks(data.main, /<article class="metric-card">([\s\S]*?)<\/article>/gi).map(block => ({
    value: firstClass(block, "metric-value", "span"), label: firstClass(block, "metric-label", "span"), body: firstTag(block, "p"),
  }));
  metrics.forEach((metric, i) => {
    const x = 64 + i * 286;
    addBox(slide, x, 250, 260, 250, { fill: NAVY_2, line: GOLD_DARK, lineWidth: 1 });
    addText(slide, metric.value, x + 20, 273, 220, 72, { size: 52, font: HEADING_FONT, bold: true, color: GOLD_LIGHT, align: "center" });
    addText(slide, metric.label.toUpperCase(), x + 20, 356, 220, 25, { size: 14, bold: true, color: OFF_WHITE, align: "center" });
    addGoldRule(slide, x + 95, 395, 70, 1);
    addText(slide, metric.body, x + 24, 414, 212, 65, { size: 14, color: MUTED, align: "center" });
  });
  const validation = firstClass(data.main, "validation-band", "div");
  addBox(slide, 64, 538, 1136, 62, { geometry: "rect", fill: NAVY_3, line: NAVY_3, lineWidth: 0 });
  addText(slide, validation, 90, 553, 1080, 34, { size: 16, color: MUTED, align: "center" });
  notesFor(slide, data);
}

function buildSlide7(presentation, data) {
  const slide = presentation.slides.add();
  addFrame(slide, 7, "1:30", data.label);
  addBox(slide, 64, 126, 550, 486, { fill: NAVY_2, line: GOLD_DARK, lineWidth: 1 });
  addText(slide, "VALUE DELIVERED", 94, 154, 250, 22, { size: 14, bold: true, color: GOLD });
  addText(slide, data.title, 94, 192, 460, 150, { size: 38, font: HEADING_FONT, bold: true });
  const impacts = allBlocks(data.main, /<div class="impact-item">([\s\S]*?)<\/div>/gi).map(block => ({
    title: firstTag(block, "strong"), body: firstTag(block, "small"),
  }));
  impacts.forEach((impact, i) => {
    const y = 370 + i * 72;
    addText(slide, "◆", 106, y, 24, 24, { size: 14, color: GOLD_LIGHT, align: "center" });
    addText(slide, impact.title, 144, y - 2, 350, 24, { size: 17, bold: true });
    addText(slide, impact.body, 144, y + 23, 400, 34, { size: 13, color: MUTED });
  });
  addText(slide, "ROADMAP", 668, 130, 200, 24, { size: 14, bold: true, color: GOLD });
  const roadmap = allBlocks(data.main, /<article class="roadmap-card">([\s\S]*?)<\/article>/gi).map(block => ({
    index: firstClass(block, "roadmap-index", "span"), title: firstTag(block, "strong"), body: firstTag(block, "p"), status: firstClass(block, "status", "span"),
  }));
  roadmap.forEach((item, i) => {
    const y = 175 + i * 132;
    addBox(slide, 668, y, 532, 108, { fill: NAVY_2, line: GOLD_DARK, lineWidth: 1 });
    addBox(slide, 686, y + 30, 44, 44, { geometry: "ellipse", fill: GOLD, line: GOLD, lineWidth: 0 });
    addText(slide, item.index, 686, y + 30, 44, 44, { size: 16, bold: true, color: NAVY, align: "center", valign: "middle" });
    addText(slide, item.title, 750, y + 20, 270, 25, { size: 18, bold: true });
    addText(slide, item.body, 750, y + 48, 320, 45, { size: 15, color: MUTED });
    addText(slide, item.status.toUpperCase(), 1064, y + 38, 112, 20, { size: 12, bold: true, color: GOLD_LIGHT, align: "right" });
  });
  notesFor(slide, data);
}

function buildSlide8(presentation, data) {
  const slide = presentation.slides.add();
  addFrame(slide, 8, "1:00", data.label);
  addText(slide, data.kicker.toUpperCase(), 64, 128, 250, 22, { size: 14, bold: true, color: GOLD });
  addText(slide, data.title, 64, 164, 650, 184, { size: 46, font: HEADING_FONT, bold: true });
  addText(slide, data.lead, 64, 359, 685, 72, { size: 20, color: MUTED });
  const takeaways = allBlocks(data.main, /<div class="takeaway">([\s\S]*?)<\/div>/gi).map(plain);
  takeaways.forEach((item, i) => {
    const y = 458 + i * 34;
    addBox(slide, 66, y + 5, 10, 10, { geometry: "ellipse", fill: GOLD, line: GOLD, lineWidth: 0 });
    addText(slide, item, 88, y, 620, 24, { size: 16, color: MUTED });
  });
  addText(slide, firstClass(data.main, "contact-line", "p"), 64, 582, 680, 46, { size: 14, color: MUTED });
  addBox(slide, 808, 216, 392, 292, { fill: NAVY_2, line: GOLD_DARK, lineWidth: 1 });
  addText(slide, "?", 808, 245, 392, 126, { size: 92, font: HEADING_FONT, bold: true, color: GOLD_LIGHT, align: "center", valign: "middle" });
  addText(slide, "Questions & Discussion", 840, 385, 328, 44, { size: 28, font: HEADING_FONT, bold: true, align: "center" });
  addText(slide, "Thank you.", 840, 443, 328, 28, { size: 16, color: GOLD_LIGHT, align: "center" });
  notesFor(slide, data);
}

async function writeBlob(filePath, blob) {
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  const html = await fs.readFile(htmlPath, "utf8");
  const data = parseHtml(html);
  await fs.mkdir(renderDir, { recursive: true });
  await fs.mkdir(validatedOutputDir, { recursive: true });

  const presentation = Presentation.create({ slideSize: { width: W, height: H } });
  const builders = [buildSlide1, buildSlide2, buildSlide3, buildSlide4, buildSlide5, buildSlide6, buildSlide7, buildSlide8];
  data.forEach((slideData, index) => builders[index](presentation, slideData));

  for (const [index, slide] of presentation.slides.items.entries()) {
    const previewPath = path.join(renderDir, `slide-${String(index + 1).padStart(2, "0")}.png`);
    await writeBlob(previewPath, await presentation.export({ slide, format: "png", scale: 1 }));
  }
  await writeBlob(path.join(buildDir, "montage.webp"), await presentation.export({ format: "webp", montage: true }));

  const candidatePath = path.join(buildDir, "candidate.pptx");
  await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
  const validatedOutputPath = path.join(validatedOutputDir, `MarketMirror_Presentation-${Date.now()}.pptx`);

  const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href);
  const result = await finalizePresentation({
    workspaceDir: projectDir,
    candidatePath,
    finalPath: validatedOutputPath,
    pythonExecutable: RUNTIME_PYTHON,
    integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
    layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
    layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-heading-fit"],
    explicitTotalSlideCount: 8,
    requiredNativeTableOwnerSlides: [],
    requiredNativeChartOwnerSlides: [],
    fontPolicy: { basis: "design", families: [HEADING_FONT, BODY_FONT] },
    verifyArtifactToolImport: true,
    receiptPath: path.join(buildDir, "MarketMirror_Presentation.validation.json"),
  });

  await fs.copyFile(validatedOutputPath, outputPath);

  console.log(`Created ${outputPath}`);
  console.log(`Slides: ${presentation.slides.items.length}`);
  console.log(`Validation: ${JSON.stringify(result.summary ?? result, null, 2)}`);
}

main().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
