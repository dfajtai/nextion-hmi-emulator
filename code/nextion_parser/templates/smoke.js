// Headless (Node) smoke test of the emulator core: runs every event of every page.
//   node smoke.js <data.js> <nextion_core.js>   ->  JSON a stdout-ra
"use strict";
const fs = require("fs");
const [dataPath, corePath] = process.argv.slice(2);
const DATA = new Function(fs.readFileSync(dataPath, "utf8") + "; return DATA;")();
const { createCore } = require(require("path").resolve(corePath));

const results = [], transitions = {};
const logs = [];
const host = { log: (t, c) => logs.push({ t, c }), render() {}, changed() {} };
const EVENTS = ["load", "loadend", "down", "up", "timer", "unload"];

function snapshot(core) { const s = core.stats; return { unk: s.unknown.length, err: s.errors.length, ref: s.refErrors.length }; }

for (const page of DATA.pages) {
  const targets = [["@page", page.page], ...page.comps.map(c => [c.objname, c])];
  for (const [name, comp] of targets) {
    for (const evn of EVENTS) {
      const code = comp.code && comp.code[evn];
      if (!code || !code.length) continue;
      logs.length = 0;
      const core = createCore(DATA, host);
      let status = "ok", detail = "", to = null;
      try {
        core.boot(page.name);
        if (core.cur() !== page.name) { status = "redirect"; detail = "jumps to another page on load: " + core.cur(); to = core.cur(); }
        const before = snapshot(core), cur0 = core.cur();
        if (name === "@page" && (evn === "load" || evn === "loadend")) { /* already executed during boot */ }
        else {
          if (evn === "timer") { const o = core.S()[page.name][name]; if (o) o.en = 1; }
          core.fire(name, evn);
        }
        const after = snapshot(core);
        const s = core.stats;
        if (after.err > before.err) { status = "error"; detail = s.errors.slice(before.err).map(e => e.msg).join("; "); }
        else if (after.unk > before.unk) { status = "unsupported"; detail = s.unknown.slice(before.unk).map(u => u.line).join("; "); }
        else if (after.ref > before.ref && status === "ok") { status = "unresolved-ref"; detail = [...new Set(s.refErrors.slice(before.ref).map(r => r.ref))].join(", "); }
        if (core.cur() !== cur0) to = core.cur();
        // errors during boot count as well (load/loadend)
        if (name === "@page" && (evn === "load" || evn === "loadend") && (s.errors.length || s.unknown.length)) {
          if (s.errors.length) { status = "error"; detail = s.errors.map(e => e.msg).join("; "); }
          else { status = "unsupported"; detail = s.unknown.map(u => u.line).join("; "); }
        }
      } catch (e) { status = "crash"; detail = String(e && e.message || e); }
      results.push({ page: page.name, comp: name === "@page" ? "(page)" : name, event: evn, lines: code.length, status, detail, to });
      if (to && to !== page.name && evn !== "load" && evn !== "loadend") (transitions[page.name] = transitions[page.name] || new Set()).add(to);
    }
  }
}
// reachability from the start page (via click transitions)
const reach = new Set([DATA.start]); const q = [DATA.start];
while (q.length) { const p = q.shift(); for (const t of (transitions[p] || [])) if (!reach.has(t)) { reach.add(t); q.push(t); } }
// headless playback of the scenarios
const scenarios = (DATA.scenarios || []).map(scn => {
  const core = createCore(DATA, host);
  let r, crash = null;
  try { r = core.runScenarioSync(scn); } catch (e) { crash = String(e && e.message || e); }
  const st = core.stats;
  return { id: scn.id, name: scn.name, steps: r ? r.steps : 0, simulatedMs: r ? r.simulatedMs : 0, crash,
    scenarioErrors: st.scenarioErrors.map(e => e.msg), errors: st.errors.map(e => e.where + ": " + e.msg),
    unknown: st.unknown.map(u => u.line), refErrors: [...new Set(st.refErrors.map(x => x.ref))],
    visited: Object.keys(st.visited) };
});
console.log(JSON.stringify({
  results,
  reachable: [...reach],
  unreachable: DATA.pages.map(p => p.name).filter(n => !reach.has(n)),
  transitions: Object.fromEntries(Object.entries(transitions).map(([k, v]) => [k, [...v]])),
  scenarios,
}));
