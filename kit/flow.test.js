const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const flow = require("./flow.js");

const ICONS = [
  "chat", "route", "spark", "shield", "mask", "cloud", "check", "ledger",
  "search", "people", "pool", "clock", "forward", "window", "database",
  "hub", "wallet", "code", "terminal", "user", "gear", "lock", "doc",
  "bolt", "globe", "eye", "key", "upload", "download", "bell", "image",
  "music", "game",
];

const NO_START = /^[、。，．,.：:；;？?！!‥…・ー〜～%％）〕］｝〉》」』】〙〗｣»ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶ々ゝゞヽヾ]/u;

function titles(n, text) {
  return Array.from({ length: n }, (_, i) => text || ("Step " + (i + 1)));
}

function overlap(a, b) {
  const x = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const y = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return x > 0.5 && y > 0.5;
}

function assertLayout(spec, name, count) {
  const label = [
    "Draft the change",
    "Review the diff before anyone ships it",
    "核心檢查把結果寫進同一本紀錄",
    "送出。下一步才開始",
    "Shared pool",
    "Outside the gate",
  ];
  const note = [
    "A short note under the title.",
    "第二行說明，用來確認寬度預算。",
    "完成。括號（不要掛在行首）後面還有字",
    "Keep the whole word together when it fits.",
    "Note",
    "Note",
  ];
  const tone = ["neutral", "info", "accent", "warn", "neutral", "info"];
  const drawn = flow.plan(
    Object.assign({ tickCount: 3 }, spec),
    label.slice(0, count),
    note.slice(0, count),
    tone.slice(0, count),
  );
  const steps = drawn.boxes.filter((box) => box.kind !== "lane").map((box) => box.step);
  assert.deepEqual(steps.slice().sort((a, b) => a - b), Array.from({ length: count }, (_, i) => i), name + " indexes");
  for (const box of drawn.boxes) {
    assert.ok(Number.isFinite(box.x + box.y + box.w + box.h), name + " finite");
    assert.ok(box.x >= -0.1, name + " x");
    assert.ok(box.y >= -0.1, name + " y");
    assert.ok(box.x + box.w <= flow.VIEW + 0.1, name + " right " + box.id);
    assert.ok(box.y + box.h <= drawn.height + 0.1, name + " bottom " + box.id);
  }
  for (let i = 0; i < drawn.boxes.length; i += 1) {
    for (let j = i + 1; j < drawn.boxes.length; j += 1) {
      assert.ok(!overlap(drawn.boxes[i], drawn.boxes[j]), name + " overlap " + drawn.boxes[i].id + " " + drawn.boxes[j].id);
    }
  }
  for (const box of drawn.boxes) {
    for (const run of box.texts) {
      if (!run.value) continue;
      const alone = flow.tokenise(run.value).length === 1 && flow.advance(run.value, run.size) > run.fit;
      if (!alone) assert.ok(flow.advance(run.value, run.size) <= run.fit + 0.01, name + " fit " + run.value);
      if (run.cls.indexOf("fd-idx") === -1 && run.cls.indexOf("fd-lane") === -1) {
        assert.ok(!NO_START.test(run.value), name + " line start " + run.value);
      }
    }
  }
  return drawn;
}

test("icon set matches the kit contract", () => {
  assert.deepEqual(flow.iconNames.slice().sort(), ICONS.slice().sort());
});

test("layouts place every step once, inside the viewBox, without overlap", () => {
  assertLayout({ columns: [[0], [1], [2], [3]], core: 2 }, "chain", 4);
  assertLayout({
    columns: [[0], [1]], core: 1, lanes: ["Atlas", "Birch", "Cedar", "Drift"], selectedLane: 2,
  }, "lanes", 2);
  assertLayout({ columns: [[0], [1]], core: 1, sinks: [2, 3] }, "sinks", 4);
  assertLayout({ columns: [[0], [1], [2]], core: 1, boundaryAfter: 1 }, "boundary", 3);
  const meter = assertLayout({ columns: [[0], [1], [2], [3]], core: 1, meter: true }, "meter", 4);
  assert.ok(meter.boxes.some((box) => box.kind === "core" && box.meter), "meter bar");
  const loop = assertLayout({ columns: [[0], [1], [2]], core: 1, loop: true }, "loop", 3);
  assert.ok(loop.loopY > Math.max(...loop.boxes.map((box) => box.y + box.h)) - 0.1, "loop under boxes");
  assert.ok(loop.wires.length >= 3, "loop adds a return rail");
  assertLayout({ columns: [[0, 1, 2], [3]], core: 3 }, "fan-in", 4);
  assertLayout({
    columns: [[3], [0], [1, 2]], core: 0, sinks: [4], boundaryAfter: 1,
  }, "mixed", 5);
});

test("wrapping stays inside the budget and keeps closing marks off the line start", () => {
  const budget = 15 * 4;
  const samples = [
    "先完成這一步。再做下一步，然後收尾",
    "計算（結果）不要把句號放在行首。真的。",
    "hello world. Next sentence stays with its period",
    "共享容量會在這裡換行，標點跟著上一行",
  ];
  for (const sample of samples) {
    const lines = flow.wrap(sample, 15, budget);
    assert.ok(lines.length >= 1);
    for (const line of lines) {
      const tokens = flow.tokenise(line);
      const alone = tokens.length === 1 && flow.advance(line, 15) > budget;
      if (!alone) assert.ok(flow.advance(line, 15) <= budget + 0.01, line);
      assert.ok(!NO_START.test(line), "starts with closing mark: " + line);
    }
  }
});

test("a closing mark moves onto the previous line when it fits", () => {
  const lines = flow.wrap("甲乙丙丁。", 10, 25);
  assert.ok(lines.every((line) => !NO_START.test(line)), lines.join(" | "));
  assert.ok(lines.some((line) => line.indexOf("。") > 0), lines.join(" | "));
});

test("status lines are never both visible", () => {
  const span = flow.STATUS.fade + flow.STATUS.hold + flow.STATUS.out + flow.STATUS.gap;
  for (const count of [1, 2, 3, 4]) {
    for (let t = 0; t < span * count * 2; t += 5) {
      const visible = flow.statusVisible(t, count).filter((opacity) => opacity > 0);
      assert.ok(visible.length <= 1, "t=" + t + " count=" + count);
    }
  }
  const gapStart = flow.STATUS.fade + flow.STATUS.hold + flow.STATUS.out;
  for (let local = gapStart; local < span; local += 1) {
    const frame = flow.statusAt(local, 3);
    assert.equal(frame.index, 0);
    assert.equal(frame.opacity, 0);
  }
  const next = flow.statusAt(span, 3);
  assert.equal(next.index, 1);
  assert.equal(next.opacity, 0);
  const midFade = flow.statusAt(gapStart - 40, 3);
  assert.equal(midFade.index, 0);
  assert.ok(midFade.opacity > 0 && midFade.opacity < 1);
  assert.equal(flow.statusVisible(midFade.local, 3).filter((opacity) => opacity > 0).length, 1);
});

test("the stylesheet fades a status line out before the next iteration", () => {
  const css = fs.readFileSync(path.join(__dirname, "flow.css"), "utf8");
  const block = css.slice(css.indexOf("@keyframes fd-tick"), css.indexOf("@keyframes fd-dash-y"));
  const stops = [...block.matchAll(/([\d.]+)%\s*\{\s*opacity:\s*([\d.]+)/g)].map((match) => ({
    at: Number(match[1]),
    opacity: Number(match[2]),
  }));
  const span = flow.STATUS.fade + flow.STATUS.hold + flow.STATUS.out + flow.STATUS.gap;
  const expect = [0, flow.STATUS.fade, flow.STATUS.fade + flow.STATUS.hold, flow.STATUS.fade + flow.STATUS.hold + flow.STATUS.out, span];
  assert.equal(stops.length, expect.length);
  expect.forEach((ms, i) => {
    assert.ok(Math.abs(stops[i].at - (ms / span) * 100) < 0.02, stops[i].at + " vs " + ms);
  });
  assert.equal(stops[0].opacity, 0);
  assert.equal(stops[1].opacity, 1);
  assert.equal(stops[2].opacity, 1);
  assert.equal(stops[3].opacity, 0);
  assert.equal(stops[4].opacity, 0);
  assert.match(block, /2\.48s|2480ms/);
  assert.match(css, /animation:\s*fd-tick\s+2\.48s/);
});
