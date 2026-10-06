/* Nextion emulator core: state + interpreter of the Nextion language. DOM-free (runs in the browser and in Node).
 *
 * createCore(DATA, host)
 *   DATA = {pages:[{index,name,page,comps}], picmap, fonts, screen:{w,h}, start}
 *   host = {log(text, cls), render(), changed(), t(key, vars)}   (all optional; t() localizes the core messages)
 */
function createCore(DATA, host) {
  "use strict";
  host = host || {};
  const pages = DATA.pages;
  const byName = {}; pages.forEach((p, i) => byName[p.name] = i);
  const pageByIndex = n => pages.find(p => p.index === n);
  const stats = { cmds: {}, unknown: [], errors: [], fired: {}, refErrors: [], visited: {} };
  const options = { timerPageJumps: true };   // false: ignore `page` jumps started from a timer event (idle return)
  let S, G, EE, cur = null, queue = null, acc = {}, steps = 0, where = "";
  const log = (t, c) => host.log && host.log(t, c);
  // core messages: English defaults; the GUI can localize them through host.t("core.<key>", vars)
  const MSG = {
    unknownTarget: "? unknown target: {ref}", unknownStatement: "? unknown statement: {line}", unknownPage: "page: unknown page {page}",
    timerBlocked: "(timer jump blocked: {page})", error: "Error ({where}): {msg}", scenario: "Scenario: {msg}", scnWhere: "scenario",
    expr: "expression: {s}", emptyExpr: "empty expression: {s}", tooManySteps: "too many steps (infinite loop?)", repeatDepth: "repeat nested too deeply",
    unknownRef: "unknown reference: {ref}", noComponent: "no such component on the current page ({page}): {name}",
    unknownScnPage: "unknown page: {page}", unknownWave: "unknown waveform: {ref}",
  };
  const tr = (k, v) => host.t ? host.t("core." + k, v) : String(MSG[k]).replace(/\{(\w+)\}/g, (m, n) => (v && v[n] !== undefined ? v[n] : m));
  const clone = o => JSON.parse(JSON.stringify(o));
  const num = v => typeof v === "number" ? v : (parseInt(v) || 0);
  class Sig { constructor(t, v) { this.t = t; this.v = v; } }
  const stat = k => { stats.cmds[k] = (stats.cmds[k] || 0) + 1; };

  function init() {
    S = {}; G = { sys0: 0, sys1: 0, sys2: 0, dim: 100, baud: 9600, recmod: 0 }; EE = {};
    pages.forEach(p => { S[p.name] = { "@page": clone(p.page) }; p.comps.forEach(c => S[p.name][c.objname] = clone(c)); });
  }
  function stripc(s) { let q = false, o = ""; for (let i = 0; i < s.length; i++) { const ch = s[i]; if (ch == '"') q = !q; if (!q && ch == "/" && s[i + 1] == "/") break; o += ch; } return o.trim(); }

  // ---------- references and expressions ----------
  function parseRef(s) {
    s = s.trim(); let m;
    if ((m = /^p\[(.+?)\]\.b\[(.+?)\]\.(\w+)$/.exec(s))) return { k: "pb", p: m[1], b: m[2], a: m[3] };
    m = /^([A-Za-z_]\w*)(?:\.([A-Za-z_]\w*))?(?:\.([A-Za-z_]\w*))?$/.exec(s);
    if (!m) return null;
    return { k: "n", parts: [m[1], m[2], m[3]].filter(x => x !== undefined) };
  }
  function findObj(parts) {
    if (parts.length == 3 && S[parts[0]] && S[parts[0]][parts[1]]) return [S[parts[0]][parts[1]], parts[2]];
    if (parts.length == 2) {
      if (S[cur][parts[0]]) return [S[cur][parts[0]], parts[1]];
      if (parts[0] == cur) return [S[cur]["@page"], parts[1]];
      if (S[parts[0]] && parts[1] in S[parts[0]]["@page"]) return [S[parts[0]]["@page"], parts[1]];
      if (parts[0] in G && parts[1] == "val") return [G, parts[0]];
    }
    if (parts.length == 1 && parts[0] in G) return [G, parts[0]];
    return null;
  }
  function resolve(r) {
    if (r.k == "pb") {
      const pg = pageByIndex(num(ev(r.p))); if (!pg) return null;
      const c = pg.comps.find(c => c.id == num(ev(r.b))); if (!c) return null;
      return [S[pg.name][c.objname], r.a];
    }
    return findObj(r.parts);
  }
  function getRef(s) { const r = parseRef(s); if (!r) return undefined; const t = resolve(r); if (!t) return undefined; const v = t[0][t[1]]; return v === undefined && t[0] === G ? 0 : v; }
  function refError(s) { stats.refErrors.push({ where, ref: s }); log(tr("unknownTarget", { ref: s }), "e"); }
  function setRef(s, v) {
    const r = parseRef(s); if (!r) return false; const t = resolve(r);
    if (!t) { refError(s); return false; }
    const [o, a] = t;
    if (typeof o[a] == "string" && typeof v != "string") v = String(v);
    else if (typeof o[a] != "string" && typeof v == "string" && a != "txt") v = parseInt(v) || 0;
    o[a] = v; return true;
  }
  function tok(s) {
    const t = [];
    const re = /\s*(?:("(?:[^"\\]|\\.)*")|(\d+(?:\.\d+)?)|([A-Za-z_]\w*(?:\[[^\]]*\])?(?:\.[A-Za-z_]\w*(?:\[[^\]]*\])?)*)|(==|!=|<=|>=|&&|\|\||[+\-*\/%<>()&|!]))/y;
    let m;
    while (re.lastIndex < s.length && (m = re.exec(s))) {
      if (m[1] !== undefined) t.push({ t: "s", v: m[1].slice(1, -1).replace(/\\r/g, "\r").replace(/\\n/g, "\n").replace(/\\"/g, '"') });
      else if (m[2] !== undefined) t.push({ t: "n", v: parseFloat(m[2]) });
      else if (m[3] !== undefined) t.push({ t: "r", v: m[3] });
      else t.push({ t: "o", v: m[4] });
    }
    if (re.lastIndex < s.trimEnd().length) throw new Error(tr("expr", { s }));
    return t;
  }
  const PREC = { "||": 1, "&&": 2, "|": 3, "&": 4, "==": 5, "!=": 5, "<": 6, ">": 6, "<=": 6, ">=": 6, "+": 7, "-": 7, "*": 8, "/": 8, "%": 8 };
  function ev(s) {
    const t = tok(s); let i = 0;
    function prim() {
      const x = t[i++]; if (!x) throw new Error(tr("emptyExpr", { s }));
      if (x.t == "n" || x.t == "s") return x.v;
      if (x.t == "r") { const v = getRef(x.v); if (v === undefined) stats.refErrors.push({ where, ref: x.v }); return v === undefined ? 0 : v; }
      if (x.v == "(") { const v = bin(0); i++; return v; }
      if (x.v == "-") return -num(prim());
      if (x.v == "!") return num(prim()) ? 0 : 1;
      throw new Error("? " + x.v);
    }
    function bin(p) {
      let l = prim();
      while (i < t.length && t[i].t == "o" && PREC[t[i].v] > p) {
        const op = t[i++].v; const r = bin(PREC[op]);
        if (op == "+" && (typeof l == "string" || typeof r == "string")) l = String(l) + String(r);
        else if ((op == "==" || op == "!=") && (typeof l == "string" || typeof r == "string")) l = +((String(l) == String(r)) == (op == "=="));
        else {
          const a = num(l), b = num(r);
          l = op == "+" ? a + b : op == "-" ? a - b : op == "*" ? a * b : op == "/" ? (b ? (a / b | 0) : 0) : op == "%" ? (b ? a % b : 0)
            : op == "==" ? +(a == b) : op == "!=" ? +(a != b) : op == "<" ? +(a < b) : op == ">" ? +(a > b) : op == "<=" ? +(a <= b) : op == ">=" ? +(a >= b)
            : op == "&&" ? +!!(a && b) : op == "||" ? +!!(a || b) : op == "&" ? a & b : a | b;
        }
      }
      return l;
    }
    return bin(0);
  }

  // ---------- statement tree ----------
  function normalize(code) {
    const out = [];
    for (let l of code.map(stripc)) {
      if (!l) continue;
      while (l.startsWith("}") && l.length > 1) { out.push("}"); l = l.slice(1).trim(); }
      if (!l) continue;
      if (l.length > 1 && l.endsWith("{")) { out.push(l.slice(0, -1).trim()); out.push("{"); continue; }
      out.push(l);
    }
    return out;
  }
  function parseSeq(L, i, top) {
    const out = [];
    while (i < L.length) {
      if (L[i] === "}") { if (top) { i++; continue; } return [out, i + 1]; }
      const r = parseStmt(L, i); out.push(r[0]); i = r[1];
    }
    return [out, i];
  }
  function parseBody(L, i) { if (L[i] === "{") return parseSeq(L, i + 1, false); const r = parseStmt(L, i); return [[r[0]], r[1]]; }
  function parseStmt(L, i) {
    const l = L[i]; let m;
    if ((m = /^if\s*\((.*)\)\s*(.*)$/.exec(l))) {
      const node = { t: "if", c: m[1], a: [], b: [] };
      const r = m[2] ? [[{ t: "cmd", s: m[2] }], i + 1] : parseBody(L, i + 1);
      node.a = r[0]; i = r[1];
      if (L[i] && /^else\b/.test(L[i])) {
        const rest = L[i].replace(/^else\s*/, "");
        if (rest) { L[i] = rest; const q = parseStmt(L, i); node.b = [q[0]]; i = q[1]; }
        else { const q = parseBody(L, i + 1); node.b = q[0]; i = q[1]; }
      }
      return [node, i];
    }
    if ((m = /^while\s*\((.*)\)\s*$/.exec(l))) { const r = parseBody(L, i + 1); return [{ t: "while", c: m[1], a: r[0] }, r[1]]; }
    if ((m = /^for\s*\((.*?);(.*?);(.*)\)\s*$/.exec(l))) { const r = parseBody(L, i + 1); return [{ t: "for", i: m[1], c: m[2], s: m[3], a: r[0] }, r[1]]; }
    return [{ t: "cmd", s: l }, i + 1];
  }
  const cache = new Map();
  function compile(code) {
    const key = code.join("\n");
    if (cache.has(key)) return cache.get(key);
    const ast = parseSeq(normalize(code), 0, true)[0];
    cache.set(key, ast); return ast;
  }

  // ---------- execution ----------
  function run(ast) { for (const n of ast) exec(n); }
  function exec(n) {
    if (++steps > 200000) throw new Error(tr("tooManySteps"));
    if (n.t == "if") { stat("if"); if (num(ev(n.c))) run(n.a); else run(n.b); }
    else if (n.t == "while") { stat("while"); let g = 0; while (num(ev(n.c))) { run(n.a); if (++g > 5000) break; } }
    else if (n.t == "for") { stat("for"); cmd(n.i); let g = 0; while (num(ev(n.c))) { run(n.a); cmd(n.s); if (++g > 5000) break; } }
    else cmd(n.s);
  }
  function splitArgs(s) { const a = []; let d = 0, q = false, c = ""; for (const ch of s) { if (ch == '"') q = !q; if (!q) { if (ch == "(" || ch == "[") d++; if (ch == ")" || ch == "]") d--; if (ch == "," && d == 0) { a.push(c.trim()); c = ""; continue; } } c += ch; } if (c.trim() || a.length) a.push(c.trim()); return a; }
  function cmd(s) {
    s = s.trim(); if (!s || s == "{" || s == "}") return;
    let m;
    if ((m = /^page\s+(.+)$/.exec(s))) { stat("page"); const t = m[1].trim(); let name = byName[t] !== undefined ? t : (pageByIndex(num(ev(t))) || {}).name;
      if (!name) { log(tr("unknownPage", { page: t }), "e"); stats.errors.push({ where, msg: tr("unknownPage", { page: t }) }); return; } throw new Sig("page", name); }
    if ((m = /^int\s+(.+)$/.exec(s))) { stat("int"); m[1].split(",").forEach(x => { const q = x.split("="); G[q[0].trim()] = q[1] ? num(ev(q[1])) : 0; }); return; }
    if ((m = /^covx\s+(.+)$/.exec(s))) { stat("covx"); return covx(splitArgs(m[1])); }
    if ((m = /^cov\s+(.+)$/.exec(s))) { stat("cov"); const a = splitArgs(m[1]); a.push("0"); return covx(a); }
    if ((m = /^substr\s+(.+)$/.exec(s))) { stat("substr"); const a = splitArgs(m[1]); setRef(a[1], String(ev(a[0])).substr(num(ev(a[2])), num(ev(a[3])))); return; }
    if ((m = /^(btlen|strlen)\s+(.+)$/.exec(s))) { stat(m[1]); const a = splitArgs(m[2]); setRef(a[1], new TextEncoder().encode(String(ev(a[0]))).length); return; }
    if ((m = /^wepo\s+(.+)$/.exec(s))) { stat("wepo"); const a = splitArgs(m[1]); EE[num(ev(a[1]))] = ev(a[0]); return; }
    if ((m = /^repo\s+(.+)$/.exec(s))) { stat("repo"); const a = splitArgs(m[1]); const v = EE[num(ev(a[1]))]; setRef(a[0], v === undefined ? 0 : v); return; }
    if ((m = /^printh\s+(.+)$/.exec(s))) { stat("printh"); log("TX hex: " + m[1].trim(), "o"); return; }
    if ((m = /^prints\s+(.+)$/.exec(s))) { stat("prints"); const a = splitArgs(m[1]); let v = ev(a[0]); const n = num(ev(a[1] || "0")); if (typeof v == "string" && n > 0) v = v.slice(0, n); log("TX: " + v, "o"); return; }
    if ((m = /^print\s+(.+)$/.exec(s))) { stat("print"); log("TX: " + ev(m[1]), "o"); return; }
    if ((m = /^click\s+(.+)$/.exec(s))) { stat("click"); const a = splitArgs(m[1]); if (S[cur][a[0]]) { fireNoFlush(a[0], "down"); fireNoFlush(a[0], "up"); } return; }
    if ((m = /^vis\s+(.+)$/.exec(s))) { stat("vis"); const a = splitArgs(m[1]); const o = S[cur][a[0]]; if (o) o["@hidden"] = !num(ev(a[1])); return; }
    if ((m = /^add\s+(.+)$/.exec(s))) { stat("add"); const a = splitArgs(m[1]); const o = S[cur][a[0]]; if (o) { o["@wave"] = o["@wave"] || [[], [], [], []]; (o["@wave"][num(ev(a[1]))] || []).push(num(ev(a[2]))); } return; }
    if ((m = /^cle\s+(.+)$/.exec(s))) { stat("cle"); const a = splitArgs(m[1]); const o = S[cur][a[0]]; if (o && o["@wave"]) { const ch = num(ev(a[1] || "255")); if (ch === 255) o["@wave"] = [[], [], [], []]; else o["@wave"][ch] = []; } return; }
    if ((m = /^(delay|tsw|ref|get|rest|sleep|thsp|thup|bkcmd|doevents|addt)\b/.exec(s))) { stat("ignored:" + m[1]); return; }
    if ((m = /^(.+?)(\+\+|--)$/.exec(s))) { stat("incdec"); setRef(m[1], num(getRef(m[1]) || 0) + (m[2] == "++" ? 1 : -1)); return; }
    if ((m = /^([A-Za-z_][\w\[\]\.]*?)\s*(\+=|-=|\*=|\/=|=)\s*(.+)$/.exec(s))) {
      stat("assign");
      let v = ev(m[3]);
      if (m[2] != "=") { const o = getRef(m[1]); const a = typeof o == "string" ? o : num(o);
        v = m[2] == "+=" ? (typeof a == "string" || typeof v == "string" ? String(a) + String(v) : a + num(v)) : m[2] == "-=" ? num(a) - num(v) : m[2] == "*=" ? num(a) * num(v) : (num(v) ? num(a) / num(v) | 0 : 0); }
      if (/^[A-Za-z_]\w*$/.test(m[1]) && !resolve(parseRef(m[1]))) { G[m[1]] = v; return; }
      setRef(m[1], v); return;
    }
    stat("unknown"); stats.unknown.push({ where, line: s }); log(tr("unknownStatement", { line: s }), "e");
  }
  function covx(a) {
    const src = ev(a[0]); const len = num(ev(a[2] || "0")); const r = parseRef(a[1]); const t = r && resolve(r);
    if (t && t[1] == "txt") { let s = String(num(src)); if (len > 0) s = s.padStart(len, "0"); setRef(a[1], s); }
    else setRef(a[1], parseInt(src) || 0);
  }

  // ---------- events ----------
  function codeOf(name, evn) {
    const base = pages[byName[cur]];
    const src = name == "@page" ? base.page : base.comps.find(c => c.objname == name);
    return src && src.code && src.code[evn];
  }
  function fireNoFlush(name, evn) {
    const code = codeOf(name, evn); if (!code || !code.length) return;
    where = cur + "." + (name == "@page" ? "page" : name) + "." + evn;
    stats.fired[where] = (stats.fired[where] || 0) + 1;
    steps = 0;
    try { run(compile(code)); }
    catch (e) {
      if (e instanceof Sig) {
        if (evn === "timer" && !options.timerPageJumps) { stats.blockedTimerJumps = (stats.blockedTimerJumps || 0) + 1; log(tr("timerBlocked", { page: e.v }), "o"); }
        else queue = e.v;
      } else { stats.errors.push({ where, msg: e.message }); log(tr("error", { where, msg: e.message }), "e"); }
    }
  }
  function flush() { let g = 0; while (queue && g++ < 20) { const p = queue; queue = null; load(p); } host.render && host.render(); host.changed && host.changed(); }
  function fire(name, evn) { fireNoFlush(name, evn); flush(); }
  function load(name) {
    if (cur) fireNoFlush("@page", "unload");
    cur = name; stats.visited[name] = (stats.visited[name] || 0) + 1; const pg = pages[byName[name]];
    pg.comps.forEach(c => { if (c.vscope != 1) S[name][c.objname] = clone(c); });
    S[name]["@page"] = clone(pg.page);
    acc = {};
    fireNoFlush("@page", "load");
    if (queue) return;
    pg.comps.forEach(c => { if (c.code && c.code.load && c.code.load.length) fireNoFlush(c.objname, "load"); });
    fireNoFlush("@page", "loadend");
  }
  function tick(ms) {
    if (!cur) return;
    pages[byName[cur]].comps.forEach(c => {
      if (c.tim === undefined) return;
      const o = S[cur][c.objname]; if (!o || !o.en) return;
      acc[c.objname] = (acc[c.objname] || 0) + ms;
      if (acc[c.objname] >= Math.max(ms, o.tim)) { acc[c.objname] = 0; fireNoFlush(c.objname, "timer"); }
    });
  }
  function boot(start) { init(); cur = null; queue = null; load(start || DATA.start); flush(); }
  function goto_(name) { queue = name; flush(); }


  // ---------- scenarios (MCU simulation) ----------
  // steps: {set:{ref:value}} | {cmd:"nextion instruction"|[..]} | {click:"obj"} | {goto:"page"} | {wait:ms}
  //          | {say:"felirat"} | {ramp:{ref,from,to,step,every}} | {repeat:n, steps:[..]}
  stats.scenarioErrors = [];
  function scnErr(msg) { stats.scenarioErrors.push({ where, msg }); log(tr("scenario", { msg }), "e"); }
  function expandSteps(steps, depth) {
    depth = depth || 0; const out = [];
    for (const st of steps || []) {
      if (st.repeat !== undefined) { if (depth > 4) { scnErr(tr("repeatDepth")); continue; } for (let i = 0; i < Math.min(+st.repeat || 0, 1000); i++) out.push(...expandSteps(st.steps, depth + 1)); }
      else if (st.ramp) {
        const r = st.ramp, step = Math.abs(+r.step || 1) * (r.to >= r.from ? 1 : -1);
        let n = 0;
        if (st.say) out.push({ say: st.say });
        for (let v = +r.from; step > 0 ? v <= r.to : v >= r.to; v += step) { if (++n > 5000) break; out.push({ set: { [r.ref]: v } }); if (r.every) out.push({ wait: +r.every }); }
      }
      else out.push(st);
    }
    return out;
  }
  function genWave(w) {
    if (Array.isArray(w.data)) return w.data.map(Number);
    const n = Math.min(+w.n || 200, 5000), lo = w.min === undefined ? 0 : +w.min, hi = w.max === undefined ? 255 : +w.max, per = +w.periods || 1;
    const out = []; let seed = 1234567;
    const rnd = () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff;
    for (let i = 0; i < n; i++) {
      const x = i / Math.max(1, n - 1); let u;
      u = w.fn === "ramp" ? x : w.fn === "noise" ? rnd() : w.fn === "square" ? ((x * per * 2 | 0) % 2) : w.fn === "step" ? (x < 0.5 ? 0 : 1)
        : (Math.sin(2 * Math.PI * per * x) + 1) / 2;
      if (w.noise) u = Math.max(0, Math.min(1, u + (rnd() - 0.5) * +w.noise));
      out.push(Math.round(lo + (hi - lo) * u));
    }
    return out;
  }
  function setWave(w) {                       // ref: "page.obj" or "obj" (current page)
    const parts = String(w.ref || "").split(".");
    const obj = parts.length === 1 ? S[cur] && S[cur][parts[0]] : (S[parts[0]] && S[parts[0]][parts[1]]);
    if (!obj) { scnErr(tr("unknownWave", { ref: w.ref })); return; }
    obj["@wave"] = obj["@wave"] || [[], [], [], []];
    obj["@wave"][+w.ch || 0] = genWave(w);
  }
  function setValue(ref, v) {
    const r = parseRef(ref); const t = r && resolve(r);
    if (!t) { scnErr(tr("unknownRef", { ref })); return false; }
    const [o, a] = t;
    o[a] = typeof o[a] === "number" ? (typeof v === "number" ? v : (parseInt(v) || 0)) : (typeof o[a] === "string" ? String(v) : v);
    return true;
  }
  /* execute one elementary step; returns {wait, say} */
  function applyStep(st) {
    where = tr("scnWhere");
    const res = { wait: 0, say: null };
    if (st.say !== undefined) res.say = st.say;
    if (st.goto) { if (byName[st.goto] === undefined) scnErr(tr("unknownScnPage", { page: st.goto })); else { queue = st.goto; flush(); } }
    if (st.wave) { setWave(st.wave); flush(); }
    if (st.set) { for (const [k, v] of Object.entries(st.set)) setValue(k, v); flush(); }
    if (st.cmd) { where = tr("scnWhere") + ".cmd"; steps = 0; const lines = Array.isArray(st.cmd) ? st.cmd : [st.cmd];
      try { run(compile(lines)); } catch (e) { if (e instanceof Sig) queue = e.v; else scnErr(e.message); } flush(); }
    if (st.click) { if (!S[cur][st.click]) scnErr(tr("noComponent", { page: cur, name: st.click })); else { fire(st.click, "down"); fire(st.click, "up"); } }
    if (st.wait) res.wait = +st.wait;
    return res;
  }
  function startScenario(scn) {
    boot(scn.page || DATA.start);
    return expandSteps(scn.steps);
  }
  /* synchronous (headless) playback: timers keep ticking during waits */
  function runScenarioSync(scn) {
    const before = stats.scenarioErrors.length + stats.errors.length + stats.unknown.length;
    const flat = startScenario(scn); let t = 0;
    for (const st of flat) {
      const r = applyStep(st);
      for (let w = 0; w < Math.min(r.wait, 600000); w += 50) { tick(50); if (queue) flush(); t += 50; }
    }
    return { steps: flat.length, simulatedMs: t, problems: stats.scenarioErrors.length + stats.errors.length + stats.unknown.length - before };
  }

  return { options, expandSteps, applyStep, startScenario, runScenarioSync, setValue, getRef, pages, picmap: DATA.picmap, fonts: DATA.fonts || {}, stats, boot, fire, flush, tick, goto: goto_, load,
    S: () => S, G: () => G, cur: () => cur, hasQueue: () => !!queue, pageByIndex };
}
if (typeof module !== "undefined") module.exports = { createCore };
