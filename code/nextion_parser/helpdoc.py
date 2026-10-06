"""Usage help of the simulator (help.html), bilingual (Hungarian / English).

The file is generated next to the emulator and linked from it. Both language versions are embedded in the same
file; a language switch (and ``?lang=hu|en`` / the emulator's stored choice) selects which one is visible.
The project-specific part (pages, scenarios) is built from the generated data.
"""
from __future__ import annotations

import html as _html
from pathlib import Path

from . import __version__
from .i18n import loc

E = _html.escape

REPORT_LABELS = {
    "coverage": {"hu": "Lefedettségi riport", "en": "Coverage report"},
    "unused": {"hu": "Nem használt erőforrások", "en": "Unused resources"},
    "navigation": {"hu": "Navigációs ábra", "en": "Navigation diagram"},
    "summary": {"hu": "Összefoglaló", "en": "Summary"},
}

CSS = """
:root{--bg:#f4f5f7;--fg:#1c1f24;--card:#fff;--line:#d5d9e0;--mut:#667085;--acc:#1d4ed8;--warn:#b45309;--ok:#15803d}
@media (prefers-color-scheme:dark){:root{--bg:#14161a;--fg:#e6e8ec;--card:#1d2026;--line:#333842;--mut:#98a2b3;--acc:#7ea6ff;--warn:#fbbf24;--ok:#4ade80}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,sans-serif}
.wrap{display:grid;grid-template-columns:240px minmax(0,1fr);gap:28px;max-width:1180px;margin:0 auto;padding:20px}
@media (max-width:860px){.wrap{grid-template-columns:1fr}nav{position:static!important;max-height:none!important}}
nav{position:sticky;top:16px;align-self:start;max-height:calc(100vh - 32px);overflow:auto;font-size:13px;border-right:1px solid var(--line);padding-right:12px}
nav b{display:block;margin:0 0 8px;font-size:14px}nav a{display:block;color:var(--fg);text-decoration:none;padding:3px 8px;border-radius:6px}
nav a:hover{background:rgba(125,125,125,.18)}nav a.sub{padding-left:20px;color:var(--mut)}
nav select{width:100%;margin:0 0 10px;font:inherit;padding:4px 6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg)}
html[lang="hu"] .lang-en,html[lang="en"] .lang-hu{display:none}
h1{font-size:26px;margin:0 0 4px}h2{font-size:20px;margin:34px 0 8px;padding-top:6px;border-top:1px solid var(--line)}h3{font-size:15px;margin:20px 0 6px}
p,li{max-width:78ch}a{color:var(--acc)}code,kbd{font:12.5px ui-monospace,monospace;background:rgba(125,125,125,.16);padding:1px 5px;border-radius:4px}
kbd{border:1px solid var(--line);border-bottom-width:2px}
pre{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px;overflow:auto;font:12.5px/1.45 ui-monospace,monospace}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);margin:8px 0;font-size:14px}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}th{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.note{border-left:4px solid var(--acc);background:rgba(125,125,125,.10);padding:8px 12px;border-radius:4px;margin:10px 0}
.warn{border-left-color:var(--warn)}.mut{color:var(--mut)}
.btn{display:inline-block;border:1px solid var(--line);background:var(--card);border-radius:6px;padding:0 7px;font-size:13px;white-space:nowrap}
.badge{display:inline-block;border-radius:10px;padding:0 8px;font-size:11px;font-weight:700;background:var(--acc);color:#fff}.badge.g{background:var(--mut)}.badge.r{background:#b91c1c}
.tag{display:inline-block;font-size:11px;border:1px solid var(--line);border-radius:10px;padding:0 7px;color:var(--mut)}
"""


def _btn(t: str) -> str:
    return f'<span class="btn">{t}</span>'


TOC = {
    "hu": [("attekintes", "Áttekintés"), ("gyors", "Gyors kezdés"), ("modok", "Egyszerű és expert mód"), ("kijelzo", "A kijelző"),
           ("lejatszo", "Forgatókönyvek lejátszása"), ("felirat", "Felirat-ablak"), ("rogzito", "Rögzítő (makró)"),
           ("szerkesztes", "Makró szerkesztése", True), ("csv", "CSV import"), ("valtozok", "Változók, napló, MCU-parancs"),
           ("formatum", "Forgatókönyv-formátum (JSON)"), ("nyelv", "Nyelv (HU/EN)"), ("riportok", "Riportok menü"),
           ("url", "URL-paraméterek, fájlok"), ("hibak", "Hibaelhárítás, korlátok"), ("projekt", "Ez a projekt")],
    "en": [("overview", "Overview"), ("quick", "Quick start"), ("modes", "Simple and expert mode"), ("display", "The display"),
           ("player", "Playing scenarios"), ("caption", "Caption window"), ("recorder", "Recorder (macro)"),
           ("editing", "Editing a macro", True), ("csvimport", "CSV import"), ("variables", "Variables, log, MCU command"),
           ("format", "Scenario format (JSON)"), ("language", "Language (HU/EN)"), ("reports", "Reports menu"),
           ("urls", "URL parameters, files"), ("trouble", "Troubleshooting, limitations"), ("project", "This project")],
}


def _body_hu(c: dict) -> str:
    b = _btn
    return f"""
<h1>Szimulátor – használati súgó</h1>
<p class="mut">Projekt: <b>{c['project']}</b> · kijelző {c['w']}×{c['h']} px · induló oldal: <code>{c['start']}</code></p>

<h2 id="attekintes">Áttekintés</h2>
<p>Az emulátor egy <b>böngészőben futó, offline</b> másolata a Nextion kijelzőnek: a <code>.HMI</code> fájlból kinyert oldalakat, komponenseket, képeket és a
<b>valódi eseménykódot</b> (kattintás, oldalbetöltés, időzítők) futtatja. Nincs szükség szerverre vagy internetre: nyisd meg az <code>index.html</code>-t.</p>
<p>Két használati mód van: <b>Egyszerű</b> (bemutatáshoz: végiglépkedhető forgatókönyvek) és <b>Expert</b> (fejlesztéshez: változók kézi állítása, makró-rögzítés, CSV, riportok).
Az emulátor <b>nem a valódi kijelző</b>: a betűtípusok rendszerfontok, az időzítés közelítő, és a soros (MCU) oldalt a forgatókönyvek szimulálják.</p>
<p>A mappa fájljai: <code>index.html</code> (a felület), <code>data.js</code> (a projekt adatai), <code>nextion_core.js</code> (a Nextion-nyelv értelmezője),
<code>nextion_tools.js</code> (CSV/statisztika), <code>i18n.js</code> (a felület szövegei), <code>img/</code> (képek), <code>help.html</code> (ez a súgó).</p>

<h2 id="gyors">Gyors kezdés</h2>
<ol>
<li>Nyisd meg az <code>index.html</code>-t. Ha vannak beágyazott forgatókönyvek, <b>Egyszerű</b> módban indul.</li>
<li>Válassz egy forgatókönyvet a <b>Forgatókönyvek</b> listából.</li>
<li>Nyomd meg a {b("▶")} gombot (automatikus lejátszás) vagy a {b("▶|")} gombot (lépésenként). A felirat-ablak elmondja, mi történik.</li>
<li>Kézi kipróbáláshoz válts <b>Expert</b> módra, és kattints közvetlenül a kijelzőn.</li>
</ol>

<h2 id="modok">Egyszerű és expert mód</h2>
<p>A fejléc <b>Mód</b> listájával (vagy <code>?mode=simple|expert</code>) váltható.</p>
<table><tr><th></th><th>Egyszerű</th><th>Expert</th></tr>
<tr><td>Cél</td><td>Bemutató, oktatás</td><td>Fejlesztés, hibakeresés, forgatókönyv-készítés</td></tr>
<tr><td>Látszik</td><td>Kijelző, felirat-ablak, forgatókönyv-lejátszó, lépéslista</td><td>Minden: + rögzítő, változók, globális változók, napló, méretezés, riportok</td></tr>
<tr><td>Kijelző-kattintás</td><td>Igen (a kijelző kezelhető)</td><td>Igen, + hover-tooltip az elem nevével</td></tr>
<tr><td>Kattintás-jelzés</td><td>Magenta keret + hullám</td><td>Ugyanez + a gomb neve</td></tr>
<tr><td>Üresjárati visszaugrás</td><td>Mindig tiltva</td><td>Kapcsolható</td></tr></table>

<h2 id="kijelzo">A kijelző</h2>
<ul>
<li><b>Kezelés:</b> a gombokra kattintva a HMI <code>down</code>/<code>up</code> eseményei futnak, mint az eszközön. Oldalváltásnál az új oldal <code>load</code>/<code>loadend</code> kódja is lefut.</li>
<li><b>Tooltip (expert):</b> az elem fölé víve megjelenik a neve és típusa (pl. <code>bstart</code> · gomb). Átfedő elemeknél a legfelsőt mutatja, a „+N alatta” jelzéssel.</li>
<li><b>Oldal</b> lista (a fejlécben, expert): mindig az aktuális oldalt mutatja; másikat választva odaugrik. <b>Újraindítás</b>: a projekt indulóoldalára, tiszta állapotból.</li>
<li><b>Kijelző vezérlés</b> blokk (expert, alapból összecsukva) – minden kijelzőbeállítás egy helyen:
<ul><li><b>Képernyő W×H</b> és <b>Nagyítás</b>: az emulált vászon mérete és a nagyítás („illeszkedő” = a szabad helyhez igazodik, ablakátméretezéskor újraszámol). {b("↺ Alap méret")} visszaállítja a projekt felbontását és az illeszkedő nagyítást.</li>
<li><b>hitbox-ok</b>: minden komponens körvonalát megmutatja (a láthatatlan hotspotokét is).</li>
<li><b>Üresjárati visszaugrás</b>: a HMI időzítői tétlenség után (itt a <code>sleep_sec</code>, alap 30 mp) visszaugranak a főoldalra. Az emulátor ezt alapból <b>tiltja</b> (a naplóba írja: „időzítő-ugrás letiltva”); bejelölve az eredeti viselkedés tér vissza.</li></ul></li>
</ul>

<h2 id="lejatszo">Forgatókönyvek lejátszása</h2>
<p>A forgatókönyv lépések sora (gombnyomás, érték-beállítás, várakozás…), amit az emulátor az MCU nevében „végrehajt”. A <b>Forgatókönyvek</b> panelen:</p>
<table><tr><th>Vezérlő</th><th>Mit csinál</th></tr>
<tr><td>{b("↺ Elölről")}</td><td>Vissza az elejére (a forgatókönyv indulóállapotára), leállítja a lejátszást.</td></tr>
<tr><td>{b("◀ Előző")}</td><td>Előző lépés: az elejétől újrajátssza az állapotot, ezért mindig pontos.</td></tr>
<tr><td>{b("▶ Lejátszás / ⏸ Szünet")}</td><td>Egyetlen gomb: indítja az automatikus lejátszást, lejátszás közben szünetelteti, szünet után folytatja (ha közben kézzel nem módosítottál semmit). A lejátszás a forgatókönyv saját állapotából indul, nem az aktuális oldalról.</td></tr>
<tr><td>{b("Következő ▶")}</td><td>Következő lépés. A várakozás átugorható (az időzítők szimulált idővel ketyegnek). Ha még fut az előző lépés animációja, azonnal befejezi.</td></tr>
<tr><td>Tempó: 1× 2× 4×</td><td>Az automatikus lejátszás sebessége a forgatókönyv saját várakozásaival.</td></tr>
<tr><td>Tempó: Egyenletes szünet</td><td>Minden lépés után ugyanannyi másodpercet vár (megadható); a forgatókönyv saját várakozás-lépéseit figyelmen kívül hagyja. Bemutatóhoz kényelmes, egyenletes ritmus.</td></tr>
<tr><td>Kattintás a kijelzőre</td><td>Ha lejátszás közben beleklikkelsz a kijelzőbe, a lejátszás megáll, és átveheted az irányítást.</td></tr>
<tr><td>Lépéslista</td><td>A lépésekre kattintva az adott lépésig újrajátssza az állapotot.</td></tr></table>
<p><b>Kiinduló állapot:</b> a lejátszás (▶ Lejátszás) és az első léptetés (Következő ▶) <u>előbb ~1 másodpercig a forgatókönyv induló oldalát mutatja</u> („Kiinduló állapot – oldal” felirattal), és csak utána jön az első kiemelés és kattintás – így látszik, melyik oldalon történik az első gombnyomás.</p>
<p><b>Kattintás-jelzés:</b> gombnyomás-lépésnél a gombot előbb magenta keret és hullám jelzi a még látható oldalon, ~0,5 s múlva történik meg a kattintás, és a keret eltűnik.</p>
<div class="note">Ha kézzel módosítasz valamit (kattintás, érték, oldalugrás, újraindítás), a következő lejátszás vagy léptetés előtt az emulátor <b>újraszinkronizál</b>: az eddigi lépéseket újrajátssza, így a forgatókönyv sosem a rossz oldalon próbál kattintani.</div>

<h2 id="felirat">Felirat-ablak</h2>
<p>A kijelző alatt, nagy betűvel mutatja az aktuális lépés feliratát.</p>
<ul>
<li><span class="badge">FELIRAT</span> a forgatókönyv saját feliratát mutatja (a lépés <code>say</code> értéke), mellette „lépés n / N”.</li>
<li><span class="badge">LÉPÉS</span> felirat nélküli lépés automatikus leírása (pl. „Gombnyomás: bmenu”, „Várakozás 1.0 s”).</li>
<li><span class="badge g">ÁLLAPOT</span> rendszerüzenet (pl. forgatókönyv betöltve, „Vége.”).</li>
<li><b>Hibák</b> külön piros buborékban jelennek meg, <u>csak ha van hiba</u> (ismeretlen hivatkozás, hibás utasítás, betöltési hiba). A buborékra kattintva lenyílik a lista.</li>
<li><b>Előzmények:</b> a gombbal lenyílik az eddigi feliratok és hibák teljes listája (a jelenlegi kiemelve), így visszakövethető, mi történt.</li>
</ul>

<h2 id="rogzito">Rögzítő (makró) <span class="tag">expert</span></h2>
<p>A rögzítő a kijelzőn végzett műveleteidet forgatókönyvvé alakítja, mint egy makró-felvevő. Három fázis: <b>1. Rögzítés → 2. Szerkesztés → 3. Mentés</b>.</p>
<ol>
<li>Válaszd ki az <b>Indulóoldalt</b>, majd nyomd meg a {b("● Rögzítés indítása")} gombot. A rögzítés <u>tiszta állapotból</u> indul az adott oldalon.</li>
<li>Használd a kijelzőt: <b>kattintások</b>, a <b>változó-módosítások</b> (Aktuális oldal / Globális változók panel), az <b>Oldal</b> lista ugrásai és az <b>MCU-parancsok</b> (lásd lent) mind bekerülnek a listába.</li>
<li>Nyomd meg a {b("■ Rögzítés leállítása")} gombot (ugyanaz a gomb).</li>
<li>Szerkeszd a listát (lásd lent), írj nevet/leírást, majd <b>Mentés</b>: letölt egy <code>.json</code>-t, és a forgatókönyv azonnal megjelenik a listában.</li>
</ol>
<h3>Időzítés: nincs automatikus várakozás</h3>
<p>A lépések között alapból <b>nincs</b> várakozás. A tempót te adod meg a <b>+ Késleltetés</b> sorral: másodperc és <i>opcionális felirat</i>, a lista végére kerül (bárhová áthúzható ▲▼-vel). A „valós idő rögzítése késleltetésként” jelölőnégyzettel kérhető, hogy a tényleges szünetek is késleltetésként rögzüljenek (0,1 s-ra kerekítve, legfeljebb 30 s).</p>
<h3>Feliratok</h3>
<p>Minden lépéshez (és késleltetéshez) tartozhat <b>felirat</b>: a lista soraiban a „felirat (opcionális)” mezőbe írd. Önálló felirat-lépést a „Felirat lépés” gombbal szúrhatsz be. A felirat a <b>kiválasztott nyelven</b> kerül a lépésbe; kétnyelvű feliratot a ✎ (JSON) szerkesztővel adhatsz meg: <code>"say": {{"hu": "…", "en": "…"}}</code>.</p>
<h3>Mentés és fájl</h3>
<p>A letöltött <code>.json</code>-t tedd a <code>scenarios/</code> mappába, hogy a következő generálásba (és az offline csomagba) bekerüljön. A böngészőben a lista csak a lap újratöltéséig tárolja.</p>

<h2 id="szerkesztes">Makró szerkesztése <span class="tag">expert</span></h2>
<p>Bármely forgatókönyv (mentett makró, betöltött JSON, vagy a generálással érkezett) szerkeszthető:</p>
<ol>
<li>Válaszd ki a listában, majd {b("✎ Szerkesztés a rögzítőben")}. A lépések, a név, a leírás és az indulóoldal betöltődik. A panel jelzi, mit szerkesztesz.</li>
<li>Soronként: felirat átírása, késleltetés másodperce, {b("▲")} {b("▼")} sorrend, {b("✕")} törlés, {b("✎")} a lépés <b>JSON-ja</b> (ramp, wave, set stb. is; hibás JSON-t elutasít).</li>
<li>{b("➕ Folytatás a végétől")}: a meglévő lépéseket azonnal lejátssza, majd onnan folytatja a rögzítést; az új lépések a lista végére kerülnek.</li>
<li><b>Mentés</b>: ha a nevet nem változtattad, ugyanazzal az azonosítóval (fájlnévvel) <b>felülírja</b> a forgatókönyvet (a kétnyelvű név/leírás megmarad); új néven új forgatókönyv lesz.</li>
</ol>

<h2 id="csv">CSV import</h2>
<p>A <b>Forgatókönyvek</b> blokk <b>Forgatókönyv / CSV betöltése…</b> gombjával vagy a <code>.csv</code> fájl ablakra húzásával (egyszerű és expert módban is). Megnyílik az import-ablak; az elválasztó (<code>;</code> <code>,</code> tab), a BOM és a tizedesvessző felismerése automatikus. Két mód:</p>
<h3>Statisztika (értékekből)</h3>
<p>Egy <b>érték-oszlopból</b> (opcionálisan <b>csoport-oszlop</b> szerint) kiszámolja az egyedszámot, az átlagot, a <b>mintaszórást</b> (n−1) és a CV-t, beírja a cél-változókba, és a nyers értékeket <b>waveformként</b> is felrajzolja. A cél-változók és az oda vezető navigáció a <code>scenarios/csv_profiles.json</code> profilból jönnek, az ablakban átírhatók. Az <code>xfloat</code> komponens tizedesjegyeihez automatikusan skáláz; a kijelzőn látható pontosságot a komponens tizedesjegyei korlátozzák.</p>
<h3>Idősor (soronként értékek)</h3>
<p>A fejléc a változó: teljes hivatkozás (<code>oldal.komponens.attribútum</code>), <code>variables.json</code>-beli címke, vagy egyedi név. Minden sor egy lépés. Speciális oszlopok: <code>t_ms</code> (abszolút idő) vagy <code>wait_ms</code>, <code>say</code> (felirat), <code>goto</code> (oldal), <code>cmd</code> (Nextion-utasítás).</p>
<pre>t_ms,pageMainAuto.charge_level.val,Töltés alatt,say
0,100,0,Lemerülés
800,90,0,
1600,80,0,</pre>
<p>Az eredmény mint bármely forgatókönyv lépegethető/lejátszható; a <b>JSON letöltése</b> gombbal menthető. A generált név és feliratok kétnyelvűek.</p>

<h2 id="valtozok">Változók, napló, MCU-parancs <span class="tag">expert</span></h2>
<ul>
<li><b>Aktuális oldal változói:</b> az éppen látható oldal számai és szövegei; átírva azonnal érvénybe lépnek, és ha rögzítesz, bekerülnek a felvételbe. A helyi változók oldalbetöltéskor visszaállnak.</li>
<li><b>Globális változók:</b> a <code>Program.s</code>-ben deklarált (<code>int</code>) és rendszerváltozók (<code>sys0…</code>, <code>dim</code>, <code>baud</code>…); alapból összecsukva.</li>
<li><b>Soros kimenet / napló:</b> a kijelző <code>print</code>/<code>prints</code>/<code>printh</code> kimenete („TX: …”), az időzítő-ugrás tiltásának jelzése, hibák. Alatta az <b>MCU-parancs</b> mező: ide Nextion-utasítást írhatsz (<code>page pageStat1</code>, <code>pageMainAuto.charge_level.val=40</code>), <kbd>Enter</kbd> vagy <b>Küld</b> – ahogy az MCU küldené. Rögzítéskor <code>cmd</code> lépésként mentődik.</li>
<li>Minden blokk fejlécére kattintva ki-/becsukható; az állapotot a böngésző megjegyzi.</li>
</ul>

<h2 id="formatum">Forgatókönyv-formátum (JSON)</h2>
<pre>{{
  "name": {{"hu": "Alacsony akku", "en": "Low battery"}},
  "description": "Mit mutat a kijelző 12%-os töltöttségnél?",
  "page": "pageMainAuto",
  "steps": [
    {{"say": {{"hu": "Az MCU 12%-ot jelent", "en": "The MCU reports 12 %"}}, "set": {{"pageMainAuto.charge_level.val": 12}}}},
    {{"wait": 1500}},
    {{"say": "START", "click": "bstart"}},
    {{"cmd": "page pageMainAuto"}},
    {{"ramp": {{"ref": "pageMainAuto.charge_level.val", "from": 100, "to": 0, "step": 10, "every": 500}}}},
    {{"wave": {{"ref": "pageStat2.s0", "fn": "sine", "n": 300, "min": 40, "max": 200}}}}
  ]
}}</pre>
<p>A <code>name</code>, <code>description</code> és <code>say</code> mező lehet egyszerű szöveg vagy <code>{{"hu": "…", "en": "…"}}</code> – a felület a kiválasztott nyelven mutatja (hiányzó nyelvnél a másikat). A <code>variables.json</code> <code>label</code>/<code>unit</code>/<code>group</code>/<code>description</code> mezői is így adhatók meg.</p>
<table><tr><th>Lépés</th><th>Jelentés</th></tr>
<tr><td><code>say</code></td><td>Felirat. Bármely más lépéssel egy objektumban is szerepelhet.</td></tr>
<tr><td><code>set</code></td><td>Értékek beállítása: <code>{{"oldal.komponens.attribútum": érték}}</code> (a kijelző a változást a kódjával dolgozza fel).</td></tr>
<tr><td><code>click</code></td><td>Gombnyomás az <b>aktuális oldalon</b> (<code>down</code> + <code>up</code>); komponensnév.</td></tr>
<tr><td><code>goto</code></td><td>Oldalra ugrás (név).</td></tr>
<tr><td><code>cmd</code></td><td>Nyers Nextion-utasítás (string vagy lista), mintha az MCU küldené.</td></tr>
<tr><td><code>wait</code></td><td>Várakozás ezredmásodpercben (az időzítők közben ketyegnek).</td></tr>
<tr><td><code>ramp</code></td><td>Egy változó léptetése: <code>ref, from, to, step, every</code> (ms). Pl. akku-lemerülés.</td></tr>
<tr><td><code>wave</code></td><td>Waveform nyers adatsor: <code>ref</code> (<code>oldal.obj</code>), <code>ch</code>, és <code>data</code> (tömb) <i>vagy</i> <code>fn</code> (sine, ramp, square, noise, step) + <code>n, min, max, periods, noise</code>.</td></tr>
<tr><td><code>repeat</code></td><td><code>{{"repeat": 3, "steps": [...]}}</code> – ismétlés.</td></tr></table>
<div class="note warn"><b>Fontos:</b> a <code>set</code> a változót közvetlenül írja. Ha a HMI kódja az értéket máshonnan tölti vissza (pl. a nyelv a főoldal betöltésekor az EEPROM-ból), akkor a <i>valódi felhasználói utat</i> kell követni (gombnyomások), nem közvetlenül állítani.</div>
<p><b>Hivatkozások:</b> <code>oldal.komponens.attribútum</code> (pl. <code>pageStat1.xmean.val</code>); az aktuális oldal komponense <code>komponens.attribútum</code>-mal is elérhető. A helyi (nem globális) változók oldalbetöltéskor visszaállnak, ezért oldalváltás <u>után</u> állítsd őket.</p>
<p>Fájlok a <code>scenarios/</code> mappában: <code>*.json</code> (forgatókönyvek; egy fájl egy forgatókönyv vagy <code>{{"scenarios": [...]}}</code>), <code>variables.json</code> (címkék, egységek a feliratokhoz és a CSV-hez), <code>csv_profiles.json</code> (a CSV-statisztika célváltozói).</p>

<h2 id="nyelv">Nyelv (HU/EN)</h2>
<p>A felület és ez a súgó kétnyelvű. Az emulátor fejlécében lévő <b>Magyar / English</b> választóval bármikor átváltható; a választás megmarad (böngésző <code>localStorage</code>), és a súgó is követi. Az alapnyelvet a generálás <code>--lang hu|en</code> kapcsolója adja; az URL <code>?lang=en</code> paramétere felülbírálja. A riportok (lefedettség, nem használt erőforrások, összefoglaló, navigáció) és a parancssor angolul készülnek.</p>
<p>A HMI saját szövegei (pl. a gombfeliratok) nem a felület nyelvétől függnek: azokat a HMI <code>lang</code> változója választja (lásd a „nyelvváltás” mintaforgatókönyvet).</p>

<h2 id="riportok">Riportok menü <span class="tag">expert</span></h2>
<p>A jobb felső <b>Riportok ▾</b> menü új lapon nyitja meg a generált HTML riportokat. A menü csak azokat mutatja, amelyek az emulátor mellett, testvér-mappában léteznek. Itt: {c['reports']}.</p>
<table><tr><th>Riport</th><th>Mire jó</th></tr>
<tr><td>Lefedettségi riport</td><td>Mennyit ad vissza az emulátor a HMI-ből: szerkezet, komponens- és attribútum-támogatás, kódparancsok, erőforrások, futási füstteszt, forgatókönyvek. (A riportok angol nyelvűek.)</td></tr>
<tr><td>Nem használt erőforrások</td><td>Hivatkozatlan képek (előnézettel), betűtípusok, oldalak, felesleges komponensek, a fájl „holt” tartalma – a HMI „tömörítéséhez”.</td></tr>
<tr><td>Navigációs ábra</td><td>Oldalak közti ugrások folyamatábrája (internet kell a Mermaid-hez).</td></tr>
<tr><td>Összefoglaló</td><td>Kijelző, oldalak, indulási program, navigáció, figyelmeztetések.</td></tr></table>

<h2 id="url">URL-paraméterek, fájlok</h2>
<table><tr><th>Paraméter</th><th>Hatás</th></tr>
<tr><td><code>?mode=simple</code> / <code>expert</code></td><td>Mód kiválasztása.</td></tr>
<tr><td><code>?scn=azonosító</code></td><td>Forgatókönyv előválasztása (az azonosító a fájlnév kiterjesztés nélkül).</td></tr>
<tr><td><code>&amp;autoplay</code></td><td>A kiválasztott forgatókönyv automatikus indítása.</td></tr>
<tr><td><code>?lang=hu</code> / <code>en</code></td><td>A felület nyelve.</td></tr></table>
<p>Példa bemutatóhoz: <code>index.html?mode=simple&amp;lang=en&amp;scn=SCENARIO_ID&amp;autoplay</code></p>
<p><b>Húzd-és-ejtsd:</b> egy <code>.json</code> (forgatókönyv) vagy <code>.csv</code> fájl az ablakra húzva betöltődik, újragenerálás nélkül.</p>
<p><b>Generálás:</b> <code>./code/setup_and_run.sh emulator FÁJL.HMI --screen 800x480 --zoom fit --lang en</code> (a kapcsolók: <code>--start</code>, <code>--screen</code>, <code>--zoom</code>, <code>--scenarios</code>, <code>--lang</code>); minden riporttal együtt: <code>all</code>.</p>

<h2 id="hibak">Hibaelhárítás, korlátok</h2>
<table><tr><th>Jelenség</th><th>Ok / teendő</th></tr>
<tr><td>A kijelző nem változik egy beállítás után</td><td>A változó lehet helyi (oldalbetöltéskor visszaáll), vagy a HMI kódja máshonnan tölti vissza. Állítsd az oldal betöltése <u>után</u>, vagy kövesd a felhasználói utat.</td></tr>
<tr><td>Piros hibabuborék „ismeretlen hivatkozás”</td><td>A forgatókönyvben elírt <code>oldal.komponens.attribútum</code>, vagy a komponens nem az aktuális oldalon van. Nyisd meg az Előzményeket a részletekért.</td></tr>
<tr><td>„ismeretlen utasítás” a naplóban</td><td>A HMI olyan Nextion-parancsot használ, amit az értelmező nem ismer (pl. rajzoló parancsok). A lefedettségi riport listázza.</td></tr>
<tr><td>Az emulátor magától főoldalra ugrik</td><td>Az üresjárati időzítő; expert módban az „üresjárati visszaugrás” jelölőnégyzet vezérli (alapból tiltott).</td></tr>
<tr><td>Hiányzik egy riport a menüből</td><td>Az emulátort a riportok <u>után</u> kell generálni (az <code>all</code> így csinálja).</td></tr>
<tr><td>Eltérő betű/kinézet az eszközhöz képest</td><td>A <code>.zi</code> betűtípusok nem renderelhetők: rendszerfont jelenik meg, a betűmagasság a HMI-ből jön. A komponensek kezdeti láthatósága (<code>vis</code>) nincs a fájlban.</td></tr>
<tr><td>Elveszett beállítások/panel-állapot</td><td>A blokkok ki/be állapota és a nyelv a böngésző <code>localStorage</code>-ában van; törlése visszaállítja az alapot.</td></tr></table>
<p><b>Korlátok:</b> csúszka, jelölőnégyzet, rádiógomb csak vázlatosan jelenik meg; a waveform adatsora csak <code>wave</code>/<code>add</code> lépésből jön; a soros protokoll nem modellezett (a forgatókönyv írja le, mit küldene az MCU); a hosszú nyomás időtartama nem rögzül.</p>

<h2 id="projekt">Ez a projekt</h2>
<h3>Beágyazott forgatókönyvek</h3>
<table><tr><th>Azonosító</th><th>Név</th><th>Leírás</th><th>Lépés</th></tr>{c['scn_rows']}</table>
<h3>Oldalak</h3>
<table><tr><th>#</th><th>Név</th><th>Komponens</th></tr>{c['page_rows']}</table>
<p class="mut">Generálta: nextion_parser {c['version']} · {c['project']}.HMI</p>
"""


def _body_en(c: dict) -> str:
    b = _btn
    return f"""
<h1>Simulator – usage help</h1>
<p class="mut">Project: <b>{c['project']}</b> · display {c['w']}×{c['h']} px · start page: <code>{c['start']}</code></p>

<h2 id="overview">Overview</h2>
<p>The emulator is a <b>browser-based, offline</b> copy of the Nextion display: it runs the pages, components and images extracted from the <code>.HMI</code> file and the
<b>real event code</b> (clicks, page loads, timers). No server and no internet are needed: just open <code>index.html</code>.</p>
<p>There are two modes: <b>Simple</b> (for demos: scenarios you can step through) and <b>Expert</b> (for development: manual variable editing, macro recording, CSV, reports).
The emulator is <b>not the real display</b>: fonts are system fonts, timing is approximate, and the serial (MCU) side is simulated by scenarios.</p>
<p>Files in the folder: <code>index.html</code> (the GUI), <code>data.js</code> (project data), <code>nextion_core.js</code> (interpreter of the Nextion language),
<code>nextion_tools.js</code> (CSV/statistics), <code>i18n.js</code> (GUI texts), <code>img/</code> (images), <code>help.html</code> (this help).</p>

<h2 id="quick">Quick start</h2>
<ol>
<li>Open <code>index.html</code>. If there are embedded scenarios it starts in <b>Simple</b> mode.</li>
<li>Pick a scenario in the <b>Scenarios</b> list.</li>
<li>Press {b("▶")} (play automatically) or {b("▶|")} (step by step). The caption window tells you what is going on.</li>
<li>To try things by hand, switch to <b>Expert</b> mode and click directly on the display.</li>
</ol>

<h2 id="modes">Simple and expert mode</h2>
<p>Switch with the <b>Mode</b> list in the header (or <code>?mode=simple|expert</code>).</p>
<table><tr><th></th><th>Simple</th><th>Expert</th></tr>
<tr><td>Purpose</td><td>Demo, teaching</td><td>Development, debugging, authoring scenarios</td></tr>
<tr><td>Visible</td><td>Display, caption window, scenario player, step list</td><td>Everything: + recorder, variables, global variables, log, sizing, reports</td></tr>
<tr><td>Clicking the display</td><td>Yes (the display is operable)</td><td>Yes, + hover tooltip with the element name</td></tr>
<tr><td>Click marker</td><td>Magenta frame + ripple</td><td>Same + the button name</td></tr>
<tr><td>Idle return jump</td><td>Always disabled</td><td>Switchable</td></tr></table>

<h2 id="display">The display</h2>
<ul>
<li><b>Operation:</b> clicking buttons runs the HMI's <code>down</code>/<code>up</code> events, as on the device. On a page change the new page's <code>load</code>/<code>loadend</code> code runs too.</li>
<li><b>Tooltip (expert):</b> hovering over an element shows its name and type (e.g. <code>bstart</code> · button). For overlapping elements the topmost is shown, with a "+N below" hint.</li>
<li><b>Page</b> list (in the header, expert): always shows the current page; selecting another one jumps there. <b>Restart</b>: back to the project's start page from a clean state.</li>
<li><b>Display controls</b> block (expert, collapsed by default) – all display settings in one place:
<ul><li><b>Screen W×H</b> and <b>Zoom</b>: size of the emulated canvas and the magnification ("fit" adapts to the free space and recalculates on window resize). {b("↺ Default size")} resets the project resolution and the fit zoom.</li>
<li><b>hitboxes</b>: outlines every component (invisible hotspots too).</li>
<li><b>Idle return jump</b>: after inactivity (here <code>sleep_sec</code>, 30 s by default) the HMI timers jump back to the main page. The emulator <b>disables</b> this by default (it logs "timer jump blocked"); tick the box to get the original behaviour back.</li></ul></li>
</ul>

<h2 id="player">Playing scenarios</h2>
<p>A scenario is a list of steps (button press, set a value, wait…) that the emulator "executes" on behalf of the MCU. In the <b>Scenarios</b> panel:</p>
<table><tr><th>Control</th><th>What it does</th></tr>
<tr><td>{b("↺ From start")}</td><td>Back to the start (the scenario's initial state); stops the playback.</td></tr>
<tr><td>{b("◀ Previous")}</td><td>Previous step: replays the state from the start, so it is always exact.</td></tr>
<tr><td>{b("▶ Play / ⏸ Pause")}</td><td>One button: starts the automatic playback, pauses it while playing, and resumes after a pause (if you did not change anything by hand meanwhile). Playback starts from the scenario's own state, not from the current page.</td></tr>
<tr><td>{b("Next ▶")}</td><td>Next step. Waits are skipped (timers tick in simulated time). If the animation of the previous step is still running it is finished immediately.</td></tr>
<tr><td>Pace: 1× 2× 4×</td><td>Speed of the automatic playback, using the scenario's own waits.</td></tr>
<tr><td>Pace: Even pause</td><td>Waits the same number of seconds after every step (adjustable) and ignores the scenario's own wait steps. Handy for presentations with a steady rhythm.</td></tr>
<tr><td>Click on the display</td><td>If you click the display during playback, the playback stops and you take over.</td></tr>
<tr><td>Step list</td><td>Click a step to replay the state up to that step.</td></tr></table>
<p><b>Initial state:</b> playback (▶ Play) and the first step (Next ▶) <u>first show the scenario's start page for ~1 second</u> (captioned "Initial state – page") and only then come the first highlight and click – so you can see on which page the first press happens.</p>
<p><b>Click marker:</b> for a button-press step the button is first marked by a magenta frame and ripple on the still-visible page, the click happens ~0.5 s later, and the frame disappears.</p>
<div class="note">If you change something by hand (click, value, page jump, restart), the emulator <b>re-synchronizes</b> before the next playback or step: it replays the steps so far, so a scenario never tries to click on the wrong page.</div>

<h2 id="caption">Caption window</h2>
<p>Below the display, in large type, it shows the caption of the current step.</p>
<ul>
<li><span class="badge">CAPTION</span> shows the scenario's own caption (the step's <code>say</code> value), next to "step n / N".</li>
<li><span class="badge">STEP</span> an automatic description of a step without a caption (e.g. "Button press: bmenu", "Wait 1.0 s").</li>
<li><span class="badge g">STATUS</span> a system message (e.g. scenario loaded, "The end.").</li>
<li><b>Errors</b> appear in a separate red bubble, <u>only when there is an error</u> (unknown reference, bad instruction, load error). Click the bubble to open the list.</li>
<li><b>History:</b> the button opens the full list of captions and errors so far (the current one highlighted), so you can trace back what happened.</li>
</ul>

<h2 id="recorder">Recorder (macro) <span class="tag">expert</span></h2>
<p>The recorder turns your actions on the display into a scenario, like a macro recorder. Three phases: <b>1. Record → 2. Edit → 3. Save</b>.</p>
<ol>
<li>Pick the <b>Start page</b>, then press {b("● Start recording")}. Recording starts <u>from a clean state</u> on that page.</li>
<li>Use the display: <b>clicks</b>, <b>variable changes</b> (Current page / Global variables panel), jumps from the <b>Page</b> list and <b>MCU commands</b> (see below) are all added to the list.</li>
<li>Press {b("■ Stop recording")} (the same button).</li>
<li>Edit the list (see below), give it a name/description, then <b>Save</b>: a <code>.json</code> is downloaded and the scenario immediately shows up in the list.</li>
</ol>
<h3>Timing: no automatic waits</h3>
<p>By default there is <b>no</b> wait between steps. You set the pace with the <b>+ Delay</b> row: seconds and an <i>optional caption</i>; it is appended to the end of the list (move it anywhere with ▲▼). The "record real time as delays" checkbox makes the real pauses be recorded as delays too (rounded to 0.1 s, at most 30 s).</p>
<h3>Captions</h3>
<p>Every step (and delay) can have a <b>caption</b>: type it into the "caption (optional)" field in the list rows. A stand-alone caption step can be inserted with the "Caption step" button. The caption is stored <b>in the selected language</b>; for a bilingual caption use the ✎ (JSON) editor: <code>"say": {{"hu": "…", "en": "…"}}</code>.</p>
<h3>Saving and the file</h3>
<p>Put the downloaded <code>.json</code> into the <code>scenarios/</code> folder so that it is included in the next generation (and the offline package). In the browser the list is kept only until the page is reloaded.</p>

<h2 id="editing">Editing a macro <span class="tag">expert</span></h2>
<p>Any scenario (a saved macro, a loaded JSON, or one that came with the generation) can be edited:</p>
<ol>
<li>Select it in the list, then {b("✎ Edit in the recorder")}. The steps, name, description and start page are loaded. The panel shows what you are editing.</li>
<li>Per row: edit the caption, the delay seconds, {b("▲")} {b("▼")} order, {b("✕")} delete, {b("✎")} the step's <b>JSON</b> (ramp, wave, set… too; invalid JSON is rejected).</li>
<li>{b("➕ Continue from the end")}: immediately replays the existing steps, then continues recording from there; the new steps are appended to the list.</li>
<li><b>Save</b>: if you did not change the name it <b>overwrites</b> the scenario under the same id (file name), keeping a bilingual name/description; with a new name it becomes a new scenario.</li>
</ol>

<h2 id="csvimport">CSV import</h2>
<p>With the <b>Load scenario / CSV…</b> button of the <b>Scenarios</b> block, or by dropping a <code>.csv</code> file on the window (in simple and expert mode). The import dialog opens; the delimiter (<code>;</code> <code>,</code> tab), the BOM and the decimal comma are detected automatically. Two modes:</p>
<h3>Statistics (from values)</h3>
<p>From one <b>value column</b> (optionally split by a <b>group column</b>) it computes the count, mean, <b>sample SD</b> (n−1) and CV, writes them into the target variables, and also draws the raw values as a <b>waveform</b>. The target variables and the navigation that leads there come from the <code>scenarios/csv_profiles.json</code> profile and can be edited in the dialog. It scales automatically to the decimals of an <code>xfloat</code> component; the precision visible on the display is limited by the component's decimals.</p>
<h3>Time series (values per row)</h3>
<p>The header is the variable: a full reference (<code>page.component.attribute</code>), a label from <code>variables.json</code>, or a unique name. Each row is one step. Special columns: <code>t_ms</code> (absolute time) or <code>wait_ms</code>, <code>say</code> (caption), <code>goto</code> (page), <code>cmd</code> (Nextion instruction).</p>
<pre>t_ms,pageMainAuto.charge_level.val,Charging,say
0,100,0,Discharging
800,90,0,
1600,80,0,</pre>
<p>The result can be stepped through / played like any scenario; it can be saved with the <b>Download JSON</b> button. The generated name and captions are bilingual.</p>

<h2 id="variables">Variables, log, MCU command <span class="tag">expert</span></h2>
<ul>
<li><b>Current page variables:</b> the numbers and texts of the page currently shown; edited values take effect immediately and, while recording, are added to the recording. Local variables are reset on page load.</li>
<li><b>Global variables:</b> declared in <code>Program.s</code> (<code>int</code>) and system variables (<code>sys0…</code>, <code>dim</code>, <code>baud</code>…); collapsed by default.</li>
<li><b>Serial output / log:</b> the display's <code>print</code>/<code>prints</code>/<code>printh</code> output ("TX: …"), the note about blocked timer jumps, errors. Below it is the <b>MCU command</b> field: type a Nextion instruction here (<code>page pageStat1</code>, <code>pageMainAuto.charge_level.val=40</code>) and press <kbd>Enter</kbd> or <b>Send</b> – as the MCU would send it. While recording it is saved as a <code>cmd</code> step.</li>
<li>Click the header of any block to collapse / expand it; the browser remembers the state.</li>
</ul>

<h2 id="format">Scenario format (JSON)</h2>
<pre>{{
  "name": {{"hu": "Alacsony akku", "en": "Low battery"}},
  "description": "What does the display show at 12 % charge?",
  "page": "pageMainAuto",
  "steps": [
    {{"say": {{"hu": "Az MCU 12%-ot jelent", "en": "The MCU reports 12 %"}}, "set": {{"pageMainAuto.charge_level.val": 12}}}},
    {{"wait": 1500}},
    {{"say": "START", "click": "bstart"}},
    {{"cmd": "page pageMainAuto"}},
    {{"ramp": {{"ref": "pageMainAuto.charge_level.val", "from": 100, "to": 0, "step": 10, "every": 500}}}},
    {{"wave": {{"ref": "pageStat2.s0", "fn": "sine", "n": 300, "min": 40, "max": 200}}}}
  ]
}}</pre>
<p><code>name</code>, <code>description</code> and <code>say</code> can be plain text or <code>{{"hu": "…", "en": "…"}}</code> – the GUI shows the selected language (falling back to the other one). The <code>label</code>/<code>unit</code>/<code>group</code>/<code>description</code> fields of <code>variables.json</code> can be given the same way.</p>
<table><tr><th>Step</th><th>Meaning</th></tr>
<tr><td><code>say</code></td><td>Caption. May also appear in the same object as any other step.</td></tr>
<tr><td><code>set</code></td><td>Set values: <code>{{"page.component.attribute": value}}</code> (the display processes the change with its own code).</td></tr>
<tr><td><code>click</code></td><td>Button press on the <b>current page</b> (<code>down</code> + <code>up</code>); component name.</td></tr>
<tr><td><code>goto</code></td><td>Jump to a page (name).</td></tr>
<tr><td><code>cmd</code></td><td>Raw Nextion instruction (string or list), as if the MCU sent it.</td></tr>
<tr><td><code>wait</code></td><td>Wait in milliseconds (timers keep ticking).</td></tr>
<tr><td><code>ramp</code></td><td>Step a variable: <code>ref, from, to, step, every</code> (ms). E.g. battery discharge.</td></tr>
<tr><td><code>wave</code></td><td>Raw data series for a waveform: <code>ref</code> (<code>page.obj</code>), <code>ch</code>, and <code>data</code> (array) <i>or</i> <code>fn</code> (sine, ramp, square, noise, step) + <code>n, min, max, periods, noise</code>.</td></tr>
<tr><td><code>repeat</code></td><td><code>{{"repeat": 3, "steps": [...]}}</code> – repetition.</td></tr></table>
<div class="note warn"><b>Important:</b> <code>set</code> writes the variable directly. If the HMI code reloads the value from elsewhere (e.g. the language from EEPROM when the main page loads) you have to follow the <i>real user path</i> (button presses) instead of setting it directly.</div>
<p><b>References:</b> <code>page.component.attribute</code> (e.g. <code>pageStat1.xmean.val</code>); a component of the current page can also be addressed as <code>component.attribute</code>. Local (non-global) variables are reset on page load, so set them <u>after</u> the page change.</p>
<p>Files in the <code>scenarios/</code> folder: <code>*.json</code> (scenarios; one file is one scenario or <code>{{"scenarios": [...]}}</code>), <code>variables.json</code> (labels, units for captions and CSV), <code>csv_profiles.json</code> (target variables of the CSV statistics).</p>

<h2 id="language">Language (HU/EN)</h2>
<p>The GUI and this help are bilingual. Use the <b>Magyar / English</b> selector in the emulator header at any time; the choice is remembered (browser <code>localStorage</code>) and the help follows it. The default language comes from the generation switch <code>--lang hu|en</code>; the URL parameter <code>?lang=en</code> overrides it. The reports (coverage, unused resources, summary, navigation) and the command line are in English.</p>
<p>The HMI's own texts (e.g. button captions) do not depend on the GUI language: they are selected by the HMI's <code>lang</code> variable (see the "language change" sample scenario).</p>

<h2 id="reports">Reports menu <span class="tag">expert</span></h2>
<p>The <b>Reports ▾</b> menu at the top right opens the generated HTML reports in a new tab. It only lists those that exist in a sibling folder next to the emulator. Here: {c['reports']}.</p>
<table><tr><th>Report</th><th>What it is for</th></tr>
<tr><td>Coverage report</td><td>How much of the HMI the emulator reproduces: structure, component and attribute support, code commands, resources, runtime smoke test, scenarios.</td></tr>
<tr><td>Unused resources</td><td>Unreferenced images (with preview), fonts, pages, superfluous components, the file's "dead" content – for "compressing" the HMI.</td></tr>
<tr><td>Navigation diagram</td><td>Flowchart of the jumps between pages (needs internet for Mermaid).</td></tr>
<tr><td>Summary</td><td>Display, pages, start-up program, navigation, warnings.</td></tr></table>

<h2 id="urls">URL parameters, files</h2>
<table><tr><th>Parameter</th><th>Effect</th></tr>
<tr><td><code>?mode=simple</code> / <code>expert</code></td><td>Select the mode.</td></tr>
<tr><td><code>?scn=id</code></td><td>Pre-select a scenario (the id is the file name without extension).</td></tr>
<tr><td><code>&amp;autoplay</code></td><td>Start the selected scenario automatically.</td></tr>
<tr><td><code>?lang=hu</code> / <code>en</code></td><td>GUI language.</td></tr></table>
<p>Demo example: <code>index.html?mode=simple&amp;lang=en&amp;scn=SCENARIO_ID&amp;autoplay</code></p>
<p><b>Drag & drop:</b> a <code>.json</code> (scenario) or <code>.csv</code> file dropped on the window is loaded without regenerating.</p>
<p><b>Generation:</b> <code>./code/setup_and_run.sh emulator FILE.HMI --screen 800x480 --zoom fit --lang en</code> (switches: <code>--start</code>, <code>--screen</code>, <code>--zoom</code>, <code>--scenarios</code>, <code>--lang</code>); everything together with the reports: <code>all</code>.</p>

<h2 id="trouble">Troubleshooting, limitations</h2>
<table><tr><th>Symptom</th><th>Cause / what to do</th></tr>
<tr><td>The display does not change after setting a value</td><td>The variable may be local (reset on page load), or the HMI code reloads it from elsewhere. Set it <u>after</u> the page loads, or follow the user path.</td></tr>
<tr><td>Red error bubble "unknown reference"</td><td>A mistyped <code>page.component.attribute</code> in the scenario, or the component is not on the current page. Open History for details.</td></tr>
<tr><td>"unknown statement" in the log</td><td>The HMI uses a Nextion command the interpreter does not know (e.g. drawing commands). The coverage report lists them.</td></tr>
<tr><td>The emulator jumps to the main page by itself</td><td>The idle timer; in expert mode the "idle return jump" checkbox controls it (disabled by default).</td></tr>
<tr><td>A report is missing from the menu</td><td>The emulator must be generated <u>after</u> the reports (<code>all</code> does it this way).</td></tr>
<tr><td>Fonts/look differ from the device</td><td>The <code>.zi</code> fonts cannot be rendered: a system font is used, the glyph height comes from the HMI. The initial visibility of components (<code>vis</code>) is not in the file.</td></tr>
<tr><td>Lost settings / panel state</td><td>The collapsed state of blocks and the language are kept in the browser's <code>localStorage</code>; clearing it restores the defaults.</td></tr></table>
<p><b>Limitations:</b> slider, checkbox and radio button are drawn only roughly; waveform data only comes from <code>wave</code>/<code>add</code> steps; the serial protocol is not modelled (the scenario describes what the MCU would send); the duration of a long press is not recorded.</p>

<h2 id="project">This project</h2>
<h3>Embedded scenarios</h3>
<table><tr><th>Id</th><th>Name</th><th>Description</th><th>Steps</th></tr>{c['scn_rows']}</table>
<h3>Pages</h3>
<table><tr><th>#</th><th>Name</th><th>Components</th></tr>{c['page_rows']}</table>
<p class="mut">Generated by nextion_parser {c['version']} · {c['project']}.HMI</p>
"""


def _ctx(project, data: dict, lang: str) -> dict:
    scns = data.get("scenarios", [])
    pages = data.get("pages", [])
    w, h = data.get("screen", {}).get("native", [project.width, project.height])
    none = "(none – run the `all` command)" if lang == "en" else "(nincs – futtasd az `all` parancsot)"
    empty = ('No embedded scenario in this generation (see "Scenario format (JSON)").' if lang == "en"
             else "Ebben a generálásban nincs beágyazott forgatókönyv (lásd a „Forgatókönyv-formátum” fejezetet).")
    scn_rows = "".join(
        f"<tr><td><code>{E(s['id'])}</code></td><td>{E(loc(s['name'], lang))}</td><td>{E(loc(s.get('description', ''), lang))}</td><td>{len(s['steps'])}</td></tr>"
        for s in scns) or f'<tr><td colspan="4" class="mut">{E(empty)}</td></tr>'
    page_rows = "".join(f"<tr><td>{p['index']}</td><td><code>{E(p['name'])}</code></td><td>{len(p['comps'])}</td></tr>" for p in pages)
    reports = ", ".join(E(REPORT_LABELS[r["key"]][lang]) for r in data.get("reports", []) if r["key"] in REPORT_LABELS) or none
    return {"project": E(project.name), "w": w, "h": h, "start": E(data.get("start", "")), "version": E(__version__),
            "scn_rows": scn_rows, "page_rows": page_rows, "reports": reports}


def render(project, data: dict) -> str:
    default = data.get("lang", "hu") if data.get("lang") in ("hu", "en") else "hu"
    navs = {lg: "".join('<a href="#%s"%s>%s</a>' % (t[0], ' class="sub"' if len(t) > 2 else "", E(t[1])) for t in TOC[lg])
            for lg in ("hu", "en")}
    title = {"hu": "szimulátor súgó", "en": "simulator help"}
    return f"""<!doctype html><html lang="{default}"><meta charset="utf-8"><title>{E(project.name)} – {title[default]}</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style><body><div class="wrap">
<nav><select id="hlang" title="language / nyelv"><option value="hu">Magyar</option><option value="en">English</option></select>
<div class="lang-hu"><b>Tartalom</b>{navs['hu']}</div><div class="lang-en"><b>Contents</b>{navs['en']}</div>
<p class="mut" style="font-size:12px;margin-top:14px">nextion_parser {E(__version__)}</p></nav>
<main><section class="lang-hu">{_body_hu(_ctx(project, data, "hu"))}</section>
<section class="lang-en">{_body_en(_ctx(project, data, "en"))}</section></main></div>
<script>
(function(){{
  var def="{default}",ls=null;
  try{{ls=localStorage.getItem('nx_lang');}}catch(e){{}}
  var q=new URLSearchParams(location.search).get('lang');
  var lang=(q==='hu'||q==='en')?q:((ls==='hu'||ls==='en')?ls:def);
  function set(l){{document.documentElement.lang=l;document.getElementById('hlang').value=l;
    document.title=document.title.replace(/ – .*$/,' – '+(l==='en'?'simulator help':'szimulátor súgó'));
    try{{localStorage.setItem('nx_lang',l);}}catch(e){{}}}}
  set(lang);
  document.getElementById('hlang').onchange=function(e){{set(e.target.value);}};
}})();
</script></body></html>"""


def write(out_dir: str | Path, project, data: dict) -> Path:
    p = Path(out_dir) / "help.html"
    p.write_text(render(project, data), encoding="utf-8")
    return p
