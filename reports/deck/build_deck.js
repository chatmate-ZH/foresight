const pptxgen = require("pptxgenjs");

const NAVY = "1B1A3B";
const NAVY_DARK = "141330";
const ICE = "CADCFC";
const PURPLE = "6C5CE7";
const CORAL = "E0575B";
const GREEN = "22A06B";
const WHITE = "FFFFFF";
const MUTED = "9AA3C0";
const LIGHT_BG = "F7F8FC";
const INK = "1E2130";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.3 x 7.5

function titleSlideBg(slide) {
  slide.background = { color: NAVY };
}

function footer(slide, pageNum) {
  slide.addText("FORESIGHT · NorthBay Living · Confidential", {
    x: 0.5, y: 7.15, w: 8, h: 0.3, fontSize: 9, color: MUTED, fontFace: "Calibri",
  });
  slide.addText(String(pageNum), {
    x: 12.5, y: 7.15, w: 0.5, h: 0.3, fontSize: 9, color: MUTED, fontFace: "Calibri", align: "right",
  });
}

function sectionHeader(slide, kicker, title, opts = {}) {
  const color = opts.dark ? WHITE : INK;
  const kickerColor = opts.dark ? ICE : PURPLE;
  slide.addText(kicker.toUpperCase(), {
    x: 0.6, y: 0.42, w: 10, h: 0.35, fontSize: 12, color: kickerColor, bold: true,
    fontFace: "Calibri", charSpacing: 2, isTextBox: true,
  });
  slide.addText(title, {
    x: 0.6, y: 0.72, w: 11.8, h: 0.8, fontSize: 30, color, bold: true,
    fontFace: "Cambria", isTextBox: true,
  });
}

// ---------- Slide 1: Title ----------
{
  const slide = pres.addSlide();
  titleSlideBg(slide);
  slide.addShape(pres.ShapeType.ellipse, { x: 9.6, y: -2.2, w: 6, h: 6, fill: { color: PURPLE, transparency: 82 }, line: { type: "none" } });
  slide.addShape(pres.ShapeType.ellipse, { x: -2, y: 4.8, w: 5, h: 5, fill: { color: ICE, transparency: 90 }, line: { type: "none" } });

  slide.addText("DATA SCIENCE & ANALYTICS  ·  EXECUTIVE READOUT", {
    x: 0.7, y: 1.55, w: 10, h: 0.4, fontSize: 13, color: ICE, bold: true, charSpacing: 2,
    fontFace: "Calibri", isTextBox: true,
  });
  slide.addText("Project FORESIGHT", {
    x: 0.7, y: 2.0, w: 11.5, h: 1.3, fontSize: 54, color: WHITE, bold: true,
    fontFace: "Cambria", isTextBox: true,
  });
  slide.addText("Demand & Inventory Intelligence for NorthBay Living", {
    x: 0.7, y: 3.15, w: 10.5, h: 0.6, fontSize: 20, color: ICE, fontFace: "Calibri", isTextBox: true,
  });

  slide.addShape(pres.ShapeType.rect, { x: 0.7, y: 4.05, w: 11.2, h: 0.02, fill: { color: PURPLE }, line: { type: "none" } });

  const kv = [
    ["Prepared for", "Head of Operations & Finance, NorthBay Living"],
    ["Prepared by", "Data Science & Analytics — Zidio Development Internship"],
    ["Engagement", "4-Week Client Engagement · Python, pandas, LightGBM, Streamlit"],
  ];
  let y = 4.4;
  kv.forEach(([k, v]) => {
    slide.addText(k.toUpperCase(), { x: 0.7, y, w: 3, h: 0.35, fontSize: 10, color: MUTED, bold: true, charSpacing: 1, fontFace: "Calibri", isTextBox: true, margin: 0 });
    slide.addText(v, { x: 0.7, y: y + 0.28, w: 10, h: 0.4, fontSize: 14, color: WHITE, fontFace: "Calibri", isTextBox: true, margin: 0 });
    y += 0.78;
  });
}

// ---------- Slide 2: Executive summary (rupee impact up front) ----------
{
  const slide = pres.addSlide();
  slide.background = { color: LIGHT_BG };
  sectionHeader(slide, "Executive Summary", "The bottom line, in rupees");

  const stats = [
    { big: "₹2.32 Cr", label: "Sales at risk from projected stockouts", color: CORAL },
    { big: "₹1.95 Cr", label: "Working capital locked in overstock", color: PURPLE },
    { big: "18.8%", label: "Forecast accuracy improvement vs. naive planning", color: GREEN },
  ];
  let x = 0.6;
  stats.forEach((s) => {
    slide.addShape(pres.ShapeType.roundRect, {
      x, y: 1.85, w: 3.9, h: 2.05, rectRadius: 0.12,
      fill: { color: WHITE }, line: { color: "E3E6F0", width: 1 },
      shadow: { type: "outer", color: "1B1A3B", opacity: 0.12, blur: 8, offset: 3, angle: 90 },
    });
    slide.addText(s.big, { x: x + 0.25, y: 2.05, w: 3.4, h: 0.85, fontSize: 38, bold: true, color: s.color, fontFace: "Cambria", isTextBox: true, margin: 0 });
    slide.addText(s.label, { x: x + 0.25, y: 2.9, w: 3.4, h: 0.85, fontSize: 13, color: INK, fontFace: "Calibri", isTextBox: true, margin: 0 });
    x += 4.15;
  });

  slide.addShape(pres.ShapeType.roundRect, {
    x: 0.6, y: 4.25, w: 12.1, h: 2.35, rectRadius: 0.12,
    fill: { color: NAVY }, line: { type: "none" },
  });
  slide.addText("What this means for NorthBay", {
    x: 1.0, y: 4.5, w: 11, h: 0.4, fontSize: 16, bold: true, color: ICE, fontFace: "Calibri", isTextBox: true,
  });
  const bullets = [
    { text: "112 of 200 SKUs (56%) are projected to stock out within their replenishment lead time — these are the reorder priorities.", options: { bullet: true, breakLine: true } },
    { text: "12 SKUs are sitting on far more stock than they'll sell — markdown candidates that free up ₹1.95 Cr in cash.", options: { bullet: true, breakLine: true } },
    { text: "The forecast model beats a naive \"same as last year\" plan by 18.8% (backtested on real held-out weeks), so the reorder and markdown lists below are worth acting on.", options: { bullet: true, breakLine: false } },
  ];
  slide.addText(bullets, { x: 1.0, y: 5.0, w: 11.3, h: 1.5, fontSize: 13.5, color: WHITE, fontFace: "Calibri", isTextBox: true, paraSpaceAfter: 8 });
  footer(slide, 2);
}

// ---------- Slide 3: The problem ----------
{
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  sectionHeader(slide, "The Brief", "Stocking on gut feel is costing NorthBay twice");

  slide.addShape(pres.ShapeType.roundRect, { x: 0.6, y: 1.85, w: 5.6, h: 4.7, rectRadius: 0.1, fill: { color: "FDEEEE" }, line: { type: "none" } });
  slide.addShape(pres.ShapeType.ellipse, { x: 0.95, y: 2.15, w: 0.6, h: 0.6, fill: { color: CORAL }, line: { type: "none" } });
  slide.addText("↓", { x: 0.95, y: 2.15, w: 0.6, h: 0.6, fontSize: 26, color: WHITE, align: "center", valign: "middle", isTextBox: true, margin: 0 });
  slide.addText("Stockouts", { x: 1.75, y: 2.18, w: 4, h: 0.5, fontSize: 20, bold: true, color: INK, fontFace: "Cambria", isTextBox: true });
  slide.addText(
    "Best-sellers run out. Every lost sale on a popular SKU is gone for good — and the customer may not come back next time.",
    { x: 0.95, y: 2.95, w: 4.9, h: 1.1, fontSize: 13.5, color: INK, fontFace: "Calibri", isTextBox: true }
  );
  slide.addText("112", { x: 0.95, y: 4.15, w: 2.5, h: 0.9, fontSize: 40, bold: true, color: CORAL, fontFace: "Cambria", isTextBox: true, margin: 0 });
  slide.addText("SKUs at stockout risk\nright now", { x: 0.95, y: 4.95, w: 3, h: 0.8, fontSize: 12, color: INK, fontFace: "Calibri", isTextBox: true, margin: 0 });

  slide.addShape(pres.ShapeType.roundRect, { x: 6.5, y: 1.85, w: 5.6, h: 4.7, rectRadius: 0.1, fill: { color: "EEF0FD" }, line: { type: "none" } });
  slide.addShape(pres.ShapeType.ellipse, { x: 6.85, y: 2.15, w: 0.6, h: 0.6, fill: { color: PURPLE }, line: { type: "none" } });
  slide.addText("↑", { x: 6.85, y: 2.15, w: 0.6, h: 0.6, fontSize: 26, color: WHITE, align: "center", valign: "middle", isTextBox: true, margin: 0 });
  slide.addText("Overstock", { x: 7.65, y: 2.18, w: 4, h: 0.5, fontSize: 20, bold: true, color: INK, fontFace: "Cambria", isTextBox: true });
  slide.addText(
    "Slow movers pile up. Cash sits in the warehouse instead of funding new stock, and it usually ends in a margin-eroding markdown anyway.",
    { x: 6.85, y: 2.95, w: 4.9, h: 1.1, fontSize: 13.5, color: INK, fontFace: "Calibri", isTextBox: true }
  );
  slide.addText("12", { x: 6.85, y: 4.15, w: 2.5, h: 0.9, fontSize: 40, bold: true, color: PURPLE, fontFace: "Cambria", isTextBox: true, margin: 0 });
  slide.addText("SKUs flagged for\nmarkdown / clearance", { x: 6.85, y: 4.95, w: 3, h: 0.8, fontSize: 12, color: INK, fontFace: "Calibri", isTextBox: true, margin: 0 });

  footer(slide, 3);
}

// ---------- Slide 4: What we built ----------
{
  const slide = pres.addSlide();
  slide.background = { color: LIGHT_BG };
  sectionHeader(slide, "The Solution", "From raw sales data to a stocking decision");

  const steps = [
    ["1", "Clean & unify", "One reproducible pipeline merges sales, inventory, SKU and calendar data into a single source of truth."],
    ["2", "Forecast demand", "A weekly, SKU-level model (LightGBM) predicts demand 6 weeks ahead, beating a naive baseline."],
    ["3", "Score risk", "Forecast + current stock position are combined into a transparent stockout / overstock score per SKU."],
    ["4", "Act", "A live dashboard and a scoring API turn the analysis into a reorder & markdown list the team can use daily."],
  ];
  let x = 0.6;
  steps.forEach(([num, title, desc], i) => {
    slide.addShape(pres.ShapeType.roundRect, { x, y: 2.0, w: 2.85, h: 4.3, rectRadius: 0.1, fill: { color: WHITE }, line: { color: "E3E6F0", width: 1 } });
    slide.addShape(pres.ShapeType.ellipse, { x: x + 0.25, y: 2.3, w: 0.55, h: 0.55, fill: { color: NAVY }, line: { type: "none" } });
    slide.addText(num, { x: x + 0.25, y: 2.3, w: 0.55, h: 0.55, fontSize: 18, bold: true, color: WHITE, align: "center", valign: "middle", isTextBox: true, margin: 0 });
    slide.addText(title, { x: x + 0.25, y: 3.05, w: 2.35, h: 0.7, fontSize: 15, bold: true, color: INK, fontFace: "Cambria", isTextBox: true, margin: 0 });
    slide.addText(desc, { x: x + 0.25, y: 3.7, w: 2.35, h: 2.4, fontSize: 11.5, color: "4B5170", fontFace: "Calibri", isTextBox: true, margin: 0 });
    if (i < 3) {
      slide.addText("→", { x: x + 2.85, y: 3.9, w: 0.3, h: 0.5, fontSize: 20, color: MUTED, align: "center", isTextBox: true, margin: 0 });
    }
    x += 3.15;
  });
  footer(slide, 4);
}

// ---------- Slide 5: Forecast accuracy (chart) ----------
{
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  sectionHeader(slide, "Forecast Accuracy", "The model beats naive planning — honestly tested");

  const chartData = [
    {
      name: "WAPE (lower is better)",
      labels: ["Fold 1", "Fold 2", "Fold 3", "Fold 4", "Fold 5"],
      values: [19.2, 22.6, 24.7, 22.0, 34.0],
    },
    {
      name: "Baseline WAPE",
      labels: ["Fold 1", "Fold 2", "Fold 3", "Fold 4", "Fold 5"],
      values: [25.8, 31.9, 25.8, 25.6, 41.7],
    },
  ];
  slide.addChart(pres.ChartType.bar, chartData, {
    x: 0.6, y: 1.9, w: 7.6, h: 4.6,
    barDir: "col",
    showTitle: true, title: "Model vs. seasonal-naive baseline, 5 backtest windows (WAPE %)",
    titleFontSize: 13,
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 9,
    chartColors: [PURPLE, "C7CCE0"],
    showLegend: true, legendPos: "b", legendFontSize: 10,
    catAxisLabelColor: "4B5170", valAxisLabelColor: "4B5170",
    valAxisTitle: "WAPE %", showValAxisTitle: true,
    valGridLine: { color: "EDEFF6", size: 1 },
    catGridLine: { style: "none" },
  });

  slide.addShape(pres.ShapeType.roundRect, { x: 8.5, y: 1.9, w: 4.2, h: 4.6, rectRadius: 0.1, fill: { color: LIGHT_BG }, line: { type: "none" } });
  slide.addText("18.8%", { x: 8.8, y: 2.15, w: 3.6, h: 0.9, fontSize: 40, bold: true, color: GREEN, fontFace: "Cambria", isTextBox: true, margin: 0 });
  slide.addText("average WAPE improvement over the naive baseline, across all 5 backtest windows.", { x: 8.8, y: 3.0, w: 3.6, h: 0.9, fontSize: 12.5, color: INK, fontFace: "Calibri", isTextBox: true, margin: 0 });
  slide.addShape(pres.ShapeType.rect, { x: 8.8, y: 4.05, w: 3.5, h: 0.02, fill: { color: "D8DBE8" }, line: { type: "none" } });
  slide.addText([
    { text: "How we tested it honestly:", options: { bold: true, breakLine: true } },
    { text: "Rolling-origin backtest — the model only ever sees the past. No future data touches a feature. The model won on all 5 folds, not a cherry-picked one.", options: { breakLine: false } },
  ], { x: 8.8, y: 4.25, w: 3.6, h: 2.1, fontSize: 12, color: "4B5170", fontFace: "Calibri", isTextBox: true, margin: 0, paraSpaceAfter: 6 });

  footer(slide, 5);
}

// ---------- Slide 6: Risk breakdown ----------
{
  const slide = pres.addSlide();
  slide.background = { color: LIGHT_BG };
  sectionHeader(slide, "Risk Breakdown", "Where every SKU stands today");

  slide.addChart(pres.ChartType.doughnut,
    [{ name: "SKUs", labels: ["Reorder Now", "Healthy", "Markdown / Clear"], values: [112, 76, 12] }],
    {
      x: 0.7, y: 2.0, w: 5.2, h: 4.4,
      showTitle: true, title: "200 SKUs, by risk quadrant", titleFontSize: 13,
      chartColors: [CORAL, GREEN, PURPLE],
      showLegend: true, legendPos: "b", legendFontSize: 11,
      showValue: true, dataLabelColor: WHITE, dataLabelFontSize: 11, showPercent: false,
      dataLabelFormatCode: "0",
    }
  );

  const rows = [
    [{ text: "SKU", options: { bold: true, fill: { color: NAVY }, color: WHITE } },
     { text: "Category", options: { bold: true, fill: { color: NAVY }, color: WHITE } },
     { text: "Weeks of cover", options: { bold: true, fill: { color: NAVY }, color: WHITE } },
     { text: "₹ at stake", options: { bold: true, fill: { color: NAVY }, color: WHITE } }],
    ["NB-0133", "Decor", "0.0", "9,52,358"],
    ["NB-0065", "Small Appliances", "0.0", "7,85,632"],
    ["NB-0156", "Small Appliances", "0.3", "6,66,431"],
    ["NB-0199", "Furniture", "0.0", "6,11,458"],
    ["NB-0023", "Decor", "0.0", "5,51,057"],
  ];
  slide.addText("Top 5 reorder priorities (by rupee value at stake)", { x: 6.3, y: 1.95, w: 6.4, h: 0.35, fontSize: 13, bold: true, color: INK, fontFace: "Calibri", isTextBox: true });
  slide.addTable(rows, {
    x: 6.3, y: 2.35, w: 6.4, h: 2.0,
    fontSize: 10.5, fontFace: "Calibri", color: INK,
    border: { type: "solid", color: "E3E6F0", pt: 0.5 },
    autoPage: false,
    colW: [1.5, 2.2, 1.3, 1.4],
  });

  const rows2 = [
    [{ text: "SKU", options: { bold: true, fill: { color: PURPLE }, color: WHITE } },
     { text: "Category", options: { bold: true, fill: { color: PURPLE }, color: WHITE } },
     { text: "Weeks of cover", options: { bold: true, fill: { color: PURPLE }, color: WHITE } },
     { text: "₹ locked", options: { bold: true, fill: { color: PURPLE }, color: WHITE } }],
    ["NB-0163", "Lighting", "56.3", "1,05,75,836"],
    ["NB-0190", "Lighting", "57.2", "30,26,137"],
    ["NB-0181", "Bed & Bath", "40.8", "17,12,755"],
  ];
  slide.addText("Top 3 markdown / clearance candidates", { x: 6.3, y: 4.55, w: 6.4, h: 0.35, fontSize: 13, bold: true, color: INK, fontFace: "Calibri", isTextBox: true });
  slide.addTable(rows2, {
    x: 6.3, y: 4.95, w: 6.4, h: 1.3,
    fontSize: 10.5, fontFace: "Calibri", color: INK,
    border: { type: "solid", color: "E3E6F0", pt: 0.5 },
    autoPage: false,
    colW: [1.5, 2.2, 1.3, 1.4],
  });

  footer(slide, 6);
}

// ---------- Slide 7: Honest limitations ----------
{
  const slide = pres.addSlide();
  slide.background = { color: NAVY };
  sectionHeader(slide, "Honest Limitations", "What this system does not do yet", { dark: true });

  const items = [
    ["New SKUs", "SKUs launched in the last few weeks fall back to category-level trends until they build their own sales history."],
    ["Simulated data", "This engagement used realistic synthetic data, not a live feed. Numbers are illustrative of the method, not NorthBay's live P&L."],
    ["No live integration", "The service reads from the latest pipeline run. Connecting it to NorthBay's live systems is a follow-on step, not part of this scope."],
    ["Rule-based risk, not optimization", "Risk scoring is transparent and explainable by design — it flags priorities, it doesn't calculate optimal order quantities."],
  ];
  let y = 1.95;
  items.forEach(([title, desc]) => {
    slide.addShape(pres.ShapeType.ellipse, { x: 0.7, y: y + 0.05, w: 0.12, h: 0.12, fill: { color: ICE }, line: { type: "none" } });
    slide.addText(title, { x: 1.0, y, w: 3.0, h: 0.9, fontSize: 14, bold: true, color: WHITE, fontFace: "Calibri", isTextBox: true, margin: 0 });
    slide.addText(desc, { x: 4.1, y, w: 8.2, h: 0.9, fontSize: 13, color: ICE, fontFace: "Calibri", isTextBox: true, margin: 0 });
    y += 1.15;
  });
  footer(slide, 7);
}

// ---------- Slide 8: Recommendations / next steps ----------
{
  const slide = pres.addSlide();
  slide.background = { color: WHITE };
  sectionHeader(slide, "Recommendations", "What we'd do with another sprint");

  const recs = [
    ["This week", "Action the 5 top reorder SKUs and 3 top markdown SKUs on this deck directly — they carry ₹28L+ of combined value at stake.", GREEN],
    ["This month", "Connect the dashboard to NorthBay's live sales export on a weekly cadence so the reorder list refreshes itself.", PURPLE],
    ["This quarter", "Add a simple monitoring check that flags when live WAPE drifts from the 18.8%-better backtest result, so the team knows if the model needs a refresh.", CORAL],
  ];
  let x = 0.6;
  recs.forEach(([when, desc, color]) => {
    slide.addShape(pres.ShapeType.roundRect, { x, y: 2.0, w: 3.95, h: 4.3, rectRadius: 0.1, fill: { color: LIGHT_BG }, line: { type: "none" } });
    slide.addShape(pres.ShapeType.rect, { x: x + 0.35, y: 2.35, w: 0.6, h: 0.08, fill: { color }, line: { type: "none" } });
    slide.addText(when, { x: x + 0.35, y: 2.55, w: 3.2, h: 0.5, fontSize: 16, bold: true, color: INK, fontFace: "Cambria", isTextBox: true, margin: 0 });
    slide.addText(desc, { x: x + 0.35, y: 3.15, w: 3.25, h: 2.9, fontSize: 12.5, color: "4B5170", fontFace: "Calibri", isTextBox: true, margin: 0 });
    x += 4.2;
  });
  footer(slide, 8);
}

// ---------- Slide 9: Thank you / contacts ----------
{
  const slide = pres.addSlide();
  slide.background = { color: NAVY };
  slide.addShape(pres.ShapeType.ellipse, { x: -1.5, y: -1.8, w: 5, h: 5, fill: { color: PURPLE, transparency: 85 }, line: { type: "none" } });
  slide.addText("Thank you", { x: 0.7, y: 2.6, w: 10, h: 1.1, fontSize: 44, bold: true, color: WHITE, fontFace: "Cambria", isTextBox: true });
  slide.addText("Live dashboard, scoring API, and full repository are linked in the submission form.", {
    x: 0.7, y: 3.65, w: 9.5, h: 0.6, fontSize: 15, color: ICE, fontFace: "Calibri", isTextBox: true,
  });
  slide.addShape(pres.ShapeType.rect, { x: 0.7, y: 4.5, w: 6, h: 0.015, fill: { color: PURPLE }, line: { type: "none" } });
  slide.addText("Questions: reach out via your Zidio mentor / program admin.", {
    x: 0.7, y: 4.75, w: 8, h: 0.5, fontSize: 12, color: MUTED, fontFace: "Calibri", isTextBox: true,
  });
}

pres.writeFile({ fileName: "/home/claude/foresight/reports/Executive_Readout.pptx" }).then(() => {
  console.log("Deck written.");
});
