/* CSV -> scenario tools (run in the browser and in Node, DOM-free).
 *
 *  NXTools.parseCSV(text, lang?)               -> {delimiter, header:[], rows:[[..]], warnings:[]}
 *  NXTools.numeric(table, colIndex)            -> {values:[..], skipped:n}
 *  NXTools.stats(values)                       -> {n, mean, sd, cv, min, max}
 *  NXTools.buildStatsScenario(table, opts, env)
 *  NXTools.buildSeriesScenario(table, opts, env)
 *
 *  env = {variables:[{ref,label,...}], scale(ref) -> 10^vvs1 (decimal place value of an xfloat), pages:[names], lang?:'hu'|'en'}
 *  The generated scenario name / description / captions are localized objects {hu, en}; error messages use env.lang (default en).
 */
(function (root) {
  "use strict";

  // ---- messages: {hu, en} ----
  const M = {
    emptyFile: { hu: "üres fájl", en: "empty file" },
    rowCols: { hu: (n, c, e) => `${n}. sor: ${c} oszlop (várt: ${e})`, en: (n, c, e) => `row ${n}: ${c} columns (expected ${e})` },
    unknownColumn: { hu: c => "ismeretlen oszlop: " + c, en: c => "unknown column: " + c },
    noNumbers: { hu: c => `nincs számként értelmezhető érték a(z) '${c}' oszlopban`, en: c => `no numeric value in column '${c}'` },
    all: { hu: "Összes", en: "All" }, none: { hu: "(nincs)", en: "(none)" },
    statsSay: { hu: (c, g, s, f) => `${c} – ${g}: n=${s.n}, átlag=${f(s.mean)}, szórás=${f(s.sd)}, CV=${f(s.cv)}%`,
                en: (c, g, s, f) => `${c} – ${g}: n=${s.n}, mean=${f(s.mean)}, SD=${f(s.sd)}, CV=${f(s.cv)}%` },
    rawSeries: { hu: "Nyers adatsor", en: "Raw data series" },
    statsName: { hu: c => "CSV statisztika: " + c, en: c => "CSV statistics: " + c },
    statsDesc: { hu: (r, n, g) => `${r} sor, ${n} csoport (${g})`, en: (r, n, g) => `${r} rows, ${n} groups (${g})` },
    seriesName: { hu: "CSV idősor", en: "CSV time series" },
    seriesDesc: { hu: (r, cols, unk) => `${r} sor; oszlopok: ${cols}` + (unk ? `; ismeretlen (kihagyva): ${unk}` : ""),
                  en: (r, cols, unk) => `${r} rows; columns: ${cols}` + (unk ? `; unknown (skipped): ${unk}` : "") },
  };
  const m1 = (key, lang, ...a) => { const e = M[key][lang === "hu" ? "hu" : "en"]; return typeof e === "function" ? e(...a) : e; };
  const mm = (key, ...a) => ({ hu: m1(key, "hu", ...a), en: m1(key, "en", ...a) });   // localized object

  function detectDelimiter(line) {
    const c = { ";": 0, ",": 0, "\t": 0 };
    let q = false;
    for (const ch of line) { if (ch === '"') q = !q; else if (!q && ch in c) c[ch]++; }
    return Object.entries(c).sort((a, b) => b[1] - a[1])[0][1] ? Object.entries(c).sort((a, b) => b[1] - a[1])[0][0] : ",";
  }

  function parseCSV(text, lang) {
    text = String(text).replace(/^\uFEFF/, "");
    const lines = text.split(/\r\n|\n|\r/).filter(l => l.trim() !== "");
    const warnings = [];
    if (!lines.length) return { delimiter: ",", header: [], rows: [], warnings: [m1("emptyFile", lang)] };
    const delimiter = detectDelimiter(lines[0]);
    const split = l => {
      const out = []; let cur = "", q = false;
      for (let i = 0; i < l.length; i++) {
        const ch = l[i];
        if (q) { if (ch === '"' && l[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') q = false; else cur += ch; }
        else if (ch === '"') q = true;
        else if (ch === delimiter) { out.push(cur); cur = ""; }
        else cur += ch;
      }
      out.push(cur);
      return out.map(s => s.trim());
    };
    const header = split(lines[0]);
    const rows = lines.slice(1).map(split);
    rows.forEach((r, i) => { if (r.length !== header.length) warnings.push(m1("rowCols", lang, i + 2, r.length, header.length)); });
    return { delimiter, header, rows, warnings: warnings.slice(0, 10) };
  }

  function toNumber(s, delimiter) {
    if (s === undefined || s === null) return NaN;
    let t = String(s).trim().replace(/\s/g, "");
    if (t === "") return NaN;
    if (delimiter !== ",") t = t.replace(",", ".");          // decimal comma
    return /^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$/.test(t) ? parseFloat(t) : NaN;
  }

  function numeric(table, col) {
    const values = []; let skipped = 0;
    for (const r of table.rows) { const v = toNumber(r[col], table.delimiter); if (Number.isFinite(v)) values.push(v); else skipped++; }
    return { values, skipped };
  }

  function stats(values) {
    const n = values.length;
    if (!n) return { n: 0, mean: 0, sd: 0, cv: 0, min: 0, max: 0 };
    const mean = values.reduce((a, b) => a + b, 0) / n;
    const sd = n > 1 ? Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / (n - 1)) : 0;   // sample standard deviation (n-1)
    return { n, mean, sd, cv: mean ? 100 * sd / mean : 0, min: Math.min(...values), max: Math.max(...values) };
  }

  const scaleOf = (env, ref) => (env && env.scale ? env.scale(ref) : 1) || 1;
  const quant = (x, env, ref) => Math.round(x * scaleOf(env, ref));

  function downsample(values, maxPoints) {
    if (values.length <= maxPoints) return values.slice();
    const out = [];
    for (let i = 0; i < maxPoints; i++) out.push(values[Math.floor(i * values.length / maxPoints)]);
    return out;
  }

  function rescale(values, lo, hi) {                         // raw values -> 0..255 (the waveform range)
    const mn = Math.min(...values), mx = Math.max(...values), span = (mx - mn) || 1;
    return values.map(v => Math.round(lo + (hi - lo) * (v - mn) / span));
  }

  /* STATISTICS mode: from the values of one column (per group) n / mean / SD / CV + the raw data series.
   * opts = {column, groupColumn?, profile:{page, path?, quantity, mean, sd, cv, group?, wave?:{ref, click?}}, waitMs?, name?} */
  function buildStatsScenario(table, opts, env) {
    const p = opts.profile || {};
    const col = typeof opts.column === "number" ? opts.column : table.header.indexOf(opts.column);
    const lang = (env && env.lang) || "en";
    if (col < 0) throw new Error(m1("unknownColumn", lang, opts.column));
    const gcol = opts.groupColumn === undefined || opts.groupColumn === "" || opts.groupColumn === null ? -1
      : (typeof opts.groupColumn === "number" ? opts.groupColumn : table.header.indexOf(opts.groupColumn));
    const groups = new Map();
    for (const r of table.rows) {
      const v = toNumber(r[col], table.delimiter); if (!Number.isFinite(v)) continue;
      const g = gcol >= 0 ? (r[gcol] || m1("none", lang)) : m1("all", lang);
      if (!groups.has(g)) groups.set(g, []);
      groups.get(g).push(v);
    }
    if (!groups.size) throw new Error(m1("noNumbers", lang, table.header[col]));
    const wait = opts.waitMs || 4000;
    const steps = [];
    let first = true;
    for (const [g, vals] of groups) {
      const s = stats(vals);
      if (p.path && p.path.length && first) p.path.forEach(c => { steps.push({ click: c }); steps.push({ wait: 900 }); });
      else if (p.page) steps.push({ goto: p.page });                       // page load: the local variables are reset
      first = false;
      const set = {};
      if (p.quantity) set[p.quantity] = s.n;
      if (p.mean) set[p.mean] = quant(s.mean, env, p.mean);
      if (p.sd) set[p.sd] = quant(s.sd, env, p.sd);
      if (p.cv) set[p.cv] = quant(s.cv, env, p.cv);
      if (p.group) set[p.group] = String(g);
      const fmt = x => (Math.round(x * 100) / 100).toString();
      steps.push({ say: { hu: m1("statsSay", "hu", table.header[col], g, s, fmt), en: m1("statsSay", "en", table.header[col], g, s, fmt) }, set });
      steps.push({ wait: 1200 });
      if (p.wave && p.wave.ref) {
        if (p.wave.click) { steps.push({ say: mm("rawSeries"), click: p.wave.click }); }
        steps.push({ wave: { ref: p.wave.ref, ch: 0, data: rescale(downsample(vals, p.wave.points || 400), 20, 235) } });
      }
      steps.push({ wait });
    }
    return {
      name: opts.name || mm("statsName", table.header[col]),
      description: mm("statsDesc", table.rows.length, groups.size, [...groups.keys()].join(", ")),
      page: opts.startPage || null, steps,
    };
  }

  /* TIME-SERIES mode: header = variable (full reference, label, obj.attr or unique obj); one step per row.
   * Special columns: t_ms (absolute time), wait_ms (wait after the row), say, goto, cmd.
   * opts = {name?, defaultWaitMs?, startPage?} */
  function resolveHeader(h, env) {
    const raw = h.trim(); const low = raw.toLowerCase();
    if (["t_ms", "t", "time_ms", "idő_ms", "ido_ms"].includes(low)) return { kind: "t" };
    if (["wait_ms", "várakozás_ms", "varakozas_ms", "delay_ms"].includes(low)) return { kind: "wait" };
    if (["say", "felirat", "caption"].includes(low)) return { kind: "say" };
    if (["goto", "oldal", "page"].includes(low)) return { kind: "goto" };
    if (["cmd", "parancs"].includes(low)) return { kind: "cmd" };
    const vars = (env && env.variables) || [];
    if (raw.split(".").length === 3) return { kind: "set", ref: raw };
    const labels = v => (typeof v.label === "string" ? [v.label] : Object.values(v.label || {})).map(x => String(x).toLowerCase());   // a label may be a {hu, en} object
    let m = vars.find(v => v.ref === raw) || vars.find(v => labels(v).includes(low));
    if (!m && raw.split(".").length === 2) m = vars.find(v => v.ref.endsWith("." + raw));
    if (!m) { const c = vars.filter(v => v.obj === raw && v.attr === "val"); if (c.length === 1) m = c[0]; }
    return m ? { kind: "set", ref: m.ref } : { kind: "unknown" };
  }

  function buildSeriesScenario(table, opts, env) {
    opts = opts || {};
    const cols = table.header.map(h => resolveHeader(h, env));
    const unknown = table.header.filter((h, i) => cols[i].kind === "unknown");
    const tcol = cols.findIndex(c => c.kind === "t"), wcol = cols.findIndex(c => c.kind === "wait");
    const defWait = opts.defaultWaitMs === undefined ? 1000 : opts.defaultWaitMs;
    const steps = [];
    const rows = table.rows;
    rows.forEach((r, i) => {
      const set = {}; let say = null, go = null, cmd = null;
      cols.forEach((c, j) => {
        const cell = r[j]; if (cell === undefined || cell === "") return;
        if (c.kind === "set") {
          const v = toNumber(cell, table.delimiter);
          set[c.ref] = Number.isFinite(v) ? v : cell;
        } else if (c.kind === "say") say = cell; else if (c.kind === "goto") go = cell; else if (c.kind === "cmd") cmd = cell;
      });
      if (go) steps.push({ goto: go });
      const st = {};
      if (say) st.say = say;
      if (Object.keys(set).length) st.set = set;
      if (cmd) st.cmd = cmd;
      if (Object.keys(st).length) steps.push(st);
      let wait = defWait;
      if (wcol >= 0) { const w = toNumber(r[wcol], table.delimiter); if (Number.isFinite(w)) wait = w; }
      else if (tcol >= 0) {
        const t0 = toNumber(r[tcol], table.delimiter), t1 = i + 1 < rows.length ? toNumber(rows[i + 1][tcol], table.delimiter) : NaN;
        if (Number.isFinite(t0) && Number.isFinite(t1)) wait = Math.max(0, t1 - t0);
      }
      if (wait > 0 && i < rows.length - 1) steps.push({ wait });
    });
    return {
      name: opts.name || mm("seriesName"),
      description: mm("seriesDesc", rows.length, table.header.filter((h, i) => cols[i].kind === "set").join(", "), unknown.join(", ")),
      page: opts.startPage || null, steps, unknownColumns: unknown,
    };
  }

  const api = { parseCSV, toNumber, numeric, stats, buildStatsScenario, buildSeriesScenario, resolveHeader, rescale, downsample };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.NXTools = api;
})(typeof window !== "undefined" ? window : globalThis);
