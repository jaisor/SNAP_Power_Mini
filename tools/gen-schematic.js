// Generates the MiniPDB schematic for KiCad 10: battery, switch and load wire pads,
// with the switch in series with battery +, plus two M2 mounting holes.
// Usage: node tools/gen-schematic.js [project dir, default: repo root]
const fs = require("fs");
const crypto = require("crypto");
const path = require("path");

const LIBDIR = "C:/Program Files/KiCad/10.0/share/kicad/symbols";
const PROJ = process.argv[2] || ".";
const NAME = "MiniPDB";
const SCH = path.join(PROJ, NAME + ".kicad_sch");
// Deterministic UUIDs keyed by what an item is (symbol ref, wire endpoints, ...), so
// regenerating keeps symbol identities stable for the PCB links and keeps git diffs small.
function uuid(key) {
  const h = crypto.createHash("sha1").update(`${NAME}/${key}`).digest("hex");
  const variant = (8 | (parseInt(h[16], 16) & 3)).toString(16);
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-4${h.slice(13, 16)}-${variant}${h.slice(17, 20)}-${h.slice(20, 32)}`;
}
const r = (v) => Math.round(v * 1e4) / 1e4;

// ---------- s-expression helpers ----------
function block(text, i) {
  let d = 0;
  for (let j = i; j < text.length; j++) {
    if (text[j] === "(") d++;
    else if (text[j] === ")" && --d === 0) return text.slice(i, j + 1);
  }
  throw new Error("unbalanced at " + i);
}
function findSym(text, name) {
  const k = text.indexOf(`\n\t(symbol "${name}"\n`);
  if (k < 0) throw new Error("symbol not found: " + name);
  return block(text, k + 2);
}
// Returns a library symbol renamed to lib:name (none of the symbols used here are derived).
function libSymbol(lib, name) {
  const text = fs.readFileSync(`${LIBDIR}/${lib}.kicad_sym`, "utf8").replace(/\r\n/g, "\n");
  const s = findSym(text, name);
  if (/\(extends /.test(s)) throw new Error(`${lib}:${name} is derived; flatten it first`);
  return s.replace(`(symbol "${name}"`, `(symbol "${lib}:${name}"`);
}
function pinsOf(symText) {
  const out = {};
  for (const m of symText.matchAll(/\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)[\s\S]*?\(number "([^"]*)"/g))
    out[m[4]] = { x: +m[1], y: +m[2] };
  return out;
}

const SYMS = {};
function useSym(libId) {
  if (SYMS[libId]) return SYMS[libId];
  const [lib, name] = libId.split(":");
  const text = libSymbol(lib, name);
  return (SYMS[libId] = { text, pins: pinsOf(text) });
}

// ---------- placement ----------
// Library coords are Y-up; schematic is Y-down. Angle rotates counter-clockwise on screen.
function xf(p, rot, mirror) {
  let x = p.x, y = -p.y;
  for (let i = 0; i < ((rot / 90) % 4); i++) [x, y] = [y, -x];
  if (mirror === "y") x = -x;
  return { x, y };
}
const PARTS = [];
let pwrN = 0, flgN = 0;
function place(ref, libId, x, y, o = {}) {
  const sym = useSym(libId);
  const part = { ref, libId, x: r(x), y: r(y), rot: o.rot || 0, mirror: o.mirror, o, sym };
  part.pin = (n) => {
    const p = xf(sym.pins[n], part.rot, part.mirror);
    if (!p) throw new Error(`${ref} has no pin ${n}`);
    return { x: r(part.x + p.x), y: r(part.y + p.y) };
  };
  PARTS.push(part);
  return part;
}
function placeByPin(ref, libId, pinNum, at, o = {}) {
  const sym = useSym(libId);
  const p = xf(sym.pins[pinNum], o.rot || 0, o.mirror);
  return place(ref, libId, at.x - p.x, at.y - p.y, o);
}
const WIRES = [], LABELS = [], JUNCTIONS = [], TEXTS = [];
const P = (x, y) => ({ x: r(x), y: r(y) });
function wire(...pts) {
  for (let i = 0; i < pts.length - 1; i++) WIRES.push([pts[i], pts[i + 1]]);
  return pts[pts.length - 1];
}
const junction = (p) => JUNCTIONS.push(p);
function gnd(at) {
  pwrN++;
  return place(`#PWR0${String(pwrN).padStart(2, "0")}`, "power:GND", at.x, at.y, { value: "GND", power: true });
}
function flag(at, rot) {
  flgN++;
  return place(`#FLG0${String(flgN).padStart(2, "0")}`, "power:PWR_FLAG", at.x, at.y, { value: "PWR_FLAG", power: true, rot });
}
// Two SMD wire pads per footprint (pad 1 on top), project library MiniPDB.pretty.
const PADS = "MiniPDB:WirePad_1x02_SMD_2.9x3.6mm_P5.0mm";

// ---------- circuit ----------
// BATTERY + -> SWITCH -> LOAD + ; BATTERY - and LOAD - share GND.
const RAIL = 76.2;
const J1 = placeByPin("J1", "Connector_Generic:Conn_01x02", "1", P(55.88, RAIL), { mirror: "y", value: "BATTERY", fp: PADS, noBom: true });
// The switch pads face down so the battery and load sides read left to right.
const J2 = placeByPin("J2", "Connector_Generic:Conn_01x02", "1", P(76.2, RAIL - 5.08), { rot: 90, value: "SWITCH", fp: PADS, noBom: true });
const J3 = placeByPin("J3", "Connector_Generic:Conn_01x02", "1", P(96.52, RAIL), { value: "LOAD", fp: PADS, noBom: true });
const batFlag = P(66.04, RAIL);
wire(J1.pin("1"), batFlag, P(J2.pin("1").x, RAIL), J2.pin("1"));
flag(batFlag);
junction(batFlag);
LABELS.push({ name: "BAT+", at: P(58.42, RAIL), ang: 0 });
wire(J2.pin("2"), P(J2.pin("2").x, RAIL), J3.pin("1"));
LABELS.push({ name: "VOUT", at: P(86.36, RAIL), ang: 0 });
gnd(wire(J1.pin("2"), P(60.96, J1.pin("2").y), P(60.96, RAIL + 7.62)));
gnd(wire(J3.pin("2"), P(91.44, J3.pin("2").y), P(91.44, RAIL + 7.62)));
// GND needs a driver for ERC; tie a flag to a stand-alone ground symbol.
wire(P(66.04, RAIL + 5.08), P(66.04, RAIL + 7.62));
flag(P(66.04, RAIL + 5.08));
gnd(P(66.04, RAIL + 7.62));
// M2 mounting holes (non-plated), one at each end of the board
for (let i = 0; i < 2; i++)
  place(`H${i + 1}`, "Mechanical:MountingHole", 121.92 + i * 12.7, RAIL, { value: "M2", fp: "MountingHole:MountingHole_2.2mm_M2" });
TEXTS.push({
  at: P(50.8, 101.6),
  text: [
    "Minimal power distribution board, 20 x 10 mm, two M2 holes.",
    "- J1 BATTERY: wire pads, 1 = BAT+, 2 = GND.",
    "- J2 SWITCH: an off-board SPST switch in series with battery +. 1 = BAT+, 2 = VOUT. Rate it for the full load current.",
    "- J3 LOAD: wire pads, 1 = VOUT (switched battery +), 2 = GND.",
    "- Pads 2.9 x 3.6 mm suit wires up to ~16 AWG. Copper path sized for ~5 A on 1 oz copper (see CLAUDE.md).",
  ].join("\\n"),
});

// ---------- emit ----------
const sheetUuid = uuid("sheet");
const indent = (s) => s.replace(/\n/g, "\n\t");
function prop(name, value, x, y, { hide, justify, ang = 0 } = {}) {
  return `\t\t(property "${name}" "${value}"
			(at ${r(x)} ${r(y)} ${ang})
			${hide ? "(hide yes)\n\t\t\t" : ""}(effects
				(font
					(size 1.27 1.27)
				)${justify ? `\n\t\t\t\t(justify ${justify})` : ""}
			)
		)`;
}
function emitPart(p) {
  const { x, y, o } = p;
  // Property values may contain escaped quotes (e.g. power:GND's description).
  const libVal = (name) => (p.sym.text.match(new RegExp(`\\(property "${name}" "((?:[^"\\\\]|\\\\.)*)"`)) || [])[1];
  const libFp = libVal("Footprint") || "";
  const libDs = libVal("Datasheet") || "~";
  const libDesc = libVal("Description") || "";
  const w = (s) => s.length * 1.1;
  let refAt, valAt, hideVal;
  if (o.power) {
    refAt = [x, y]; valAt = [x, y + 3.81];
    hideVal = p.libId === "power:PWR_FLAG";
  } else if (p.libId.startsWith("Connector") && p.rot === 90) {
    // Pins point down: fields above the body.
    refAt = [x + 1.27, y - 5.08]; valAt = [x + 1.27, y - 2.54];
  } else if (p.libId.startsWith("Connector")) {
    // Value beside the body, on the side away from the pins.
    const dir = p.mirror === "y" ? -1 : 1;
    refAt = [x, y - 3.81]; valAt = [x + dir * (2.54 + w(o.value) / 2), y + 3.81];
  } else {
    refAt = [x, y - 3.81]; valAt = [x, y + 3.81];
  }
  const props = [
    prop("Reference", p.ref, ...refAt, { hide: o.power }),
    prop("Value", o.value, ...valAt, { hide: hideVal }),
    prop("Footprint", o.fp || libFp, x, y, { hide: true }),
    prop("Datasheet", libDs, x, y, { hide: true }),
    prop("Description", libDesc, x, y, { hide: true }),
  ];
  const pins = Object.keys(p.sym.pins).map((n) => `\t\t(pin "${n}"\n\t\t\t(uuid "${uuid(`pin/${p.ref}/${n}`)}")\n\t\t)`);
  const inBom = !(o.power || o.noBom || /\n\t\t\(in_bom no\)/.test(p.sym.text));
  return `\t(symbol
		(lib_id "${p.libId}")
		(at ${x} ${y} ${p.rot})
${p.mirror ? `\t\t(mirror ${p.mirror})\n` : ""}		(unit 1)
		(exclude_from_sim no)
		(in_bom ${inBom ? "yes" : "no"})
		(on_board ${o.power ? "no" : "yes"})
		(dnp no)
		(uuid "${uuid(`sym/${p.ref}`)}")
${props.join("\n")}
${pins.join("\n")}
		(instances
			(project "${NAME}"
				(path "/${sheetUuid}"
					(reference "${p.ref}")
					(unit 1)
				)
			)
		)
	)`;
}
const JUST = { 0: "left bottom", 90: "left bottom", 180: "right bottom", 270: "right bottom" };
const out = [
  `(kicad_sch
	(version 20260306)
	(generator "eeschema")
	(generator_version "10.0")
	(uuid "${sheetUuid}")
	(paper "A4")
	(title_block
		(title "Mini PDB")
		(date "2026-10-30")
		(rev "0.1")
		(comment 1 "Battery -> switch -> load wire-pad distribution board, 20 x 10 mm, 2x M2")
	)
	(lib_symbols
${Object.values(SYMS).map((s) => "\t\t" + indent(s.text.replace(/^\t/, ""))).join("\n")}
	)`,
  ...JUNCTIONS.map((j) => `\t(junction\n\t\t(at ${j.x} ${j.y})\n\t\t(diameter 0)\n\t\t(color 0 0 0 0)\n\t\t(uuid "${uuid(`junction/${j.x},${j.y}`)}")\n\t)`),
  ...WIRES.map(([a, b]) => `\t(wire\n\t\t(pts\n\t\t\t(xy ${a.x} ${a.y}) (xy ${b.x} ${b.y})\n\t\t)\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type default)\n\t\t)\n\t\t(uuid "${uuid(`wire/${a.x},${a.y}/${b.x},${b.y}`)}")\n\t)`),
  ...TEXTS.map((t) => `\t(text "${t.text}"\n\t\t(exclude_from_sim no)\n\t\t(at ${t.at.x} ${t.at.y} 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "${uuid(`text/${t.at.x},${t.at.y}`)}")\n\t)`),
  ...LABELS.map((l) => `\t(label "${l.name}"\n\t\t(at ${l.at.x} ${l.at.y} ${l.ang})\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n\t\t\t)\n\t\t\t(justify ${JUST[l.ang]})\n\t\t)\n\t\t(uuid "${uuid(`label/${l.name}/${l.at.x},${l.at.y}`)}")\n\t)`),
  ...PARTS.map(emitPart),
  `\t(sheet_instances
		(path "/"
			(page "1")
		)
	)
	(embedded_fonts no)
)
`,
];
fs.writeFileSync(SCH, out.join("\n"));

for (const p of PARTS.filter((p) => !p.o.power))
  console.log(p.ref.padEnd(4), p.libId.padEnd(34), String(p.o.value).padEnd(10), Object.entries(p.sym.pins).map(([n]) => `${n}@${JSON.stringify(p.pin(n))}`).join(" "));
console.log(`${PARTS.length} symbols, ${WIRES.length} wires, ${LABELS.length} labels, ${JUNCTIONS.length} junctions`);
