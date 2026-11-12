// Generates the SNAP Mini Power Controller schematic for KiCad 10: wire pads for up to four solar
// panels (each OR-ed in through its own Schottky), battery, switch and load, a CN3163 linear solar
// charger with CHRG/DONE LEDs behind a solder jumper, the switch in series with battery + toward
// the load, plus two M2 mounting holes.
// Usage: node tools/gen-schematic.js [project dir, default: repo root]
const fs = require("fs");
const crypto = require("crypto");
const path = require("path");

const LIBDIR = "C:/Program Files/KiCad/10.0/share/kicad/symbols";
const PROJ = process.argv[2] || ".";
const NAME = "SNAP_Power_Mini";
const SCH = path.join(PROJ, NAME + ".kicad_sch");
// Deterministic UUIDs keyed by what an item is (symbol ref, wire endpoints, ...), so
// regenerating keeps symbol identities stable for the PCB links and keeps git diffs small.
// Seeded with the project's original name so the later renames kept them.
const UUID_SEED = "MiniPDB";
function uuid(key) {
  const h = crypto.createHash("sha1").update(`${UUID_SEED}/${key}`).digest("hex");
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
// Top-level property blocks of a symbol, by name.
function propBlocks(sym) {
  const out = {};
  for (let i = sym.indexOf('\n\t\t(property "'); i >= 0; i = sym.indexOf('\n\t\t(property "', i + 1)) {
    const b = block(sym, i + 3);
    out[b.match(/^\(property "([^"]+)"/)[1]] = b;
  }
  return out;
}
// Returns a library symbol renamed to lib:name. A derived symbol (extends) is flattened: the
// base symbol's graphics and pins with the derived symbol's own properties.
function libSymbol(lib, name) {
  const text = fs.readFileSync(`${LIBDIR}/${lib}.kicad_sym`, "utf8").replace(/\r\n/g, "\n");
  let s = findSym(text, name);
  const ext = s.match(/\(extends "([^"]+)"\)/);
  if (ext) {
    const base = findSym(text, ext[1]);
    if (/\(extends /.test(base)) throw new Error(`${lib}:${name}: base ${ext[1]} is derived too`);
    let flat = base.replace(`(symbol "${ext[1]}"`, `(symbol "${name}"`).split(`(symbol "${ext[1]}_`).join(`(symbol "${name}_`);
    const bp = propBlocks(base);
    for (const [k, v] of Object.entries(propBlocks(s))) {
      if (bp[k]) flat = flat.replace(bp[k], v);
      else flat = flat.replace(`\n\t\t(symbol "${name}_`, `\n\t\t${v}\n\t\t(symbol "${name}_`);
    }
    s = flat;
  }
  return s.replace(`(symbol "${name}"`, `(symbol "${lib}:${name}"`);
}
function pinsOf(symText) {
  const out = {};
  for (const m of symText.matchAll(/\(pin \w+ \w+\s*\(at ([-\d.]+) ([-\d.]+) (\d+)\)[\s\S]*?\(number "([^"]*)"/g))
    out[m[4]] = { x: +m[1], y: +m[2] };
  return out;
}

// ---------- CN3163 symbol (pinout from the Consonance datasheet, eSOP-8) ----------
const fx = () => `(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)`;
function libProp(name, value, x, y, hide, justify) {
  return `\t\t(property "${name}" "${value}"
			(at ${x} ${y} 0)
			${hide ? "(hide yes)\n\t\t\t" : ""}(effects
				(font
					(size 1.27 1.27)
				)${justify ? `\n\t\t\t\t(justify ${justify})` : ""}
			)
		)`;
}
function libPin(type, x, y, ang, name, num) {
  return `\t\t\t(pin ${type} line
				(at ${x} ${y} ${ang})
				(length 2.54)
				(name "${name}"
					${fx().replace(/\n\t/g, "\n\t\t\t")}
				)
				(number "${num}"
					${fx().replace(/\n\t/g, "\n\t\t\t")}
				)
			)`;
}
const CN3163 = `\t(symbol "CN3163"
		(pin_names
			(offset 1.016)
		)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
${libProp("Reference", "U", -7.62, 8.89, false, "left")}
${libProp("Value", "CN3163", 7.62, 8.89, false, "right")}
${libProp("Footprint", "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm", 0, -17.78, true)}
${libProp("Datasheet", "http://www.consonance-elec.com/pdf/datasheet/DSE-CN3163.pdf", 0, -20.32, true)}
${libProp("Description", "1A linear Li-ion charger for solar-powered systems, input-adaptive current, 4.2V, eSOP-8", 0, 0, true)}
${libProp("ki_keywords", "solar lithium Li-ion charger linear", 0, 0, true)}
${libProp("ki_fp_filters", "SOIC*1EP*3.9x4.9mm*P1.27mm*", 0, 0, true)}
		(symbol "CN3163_0_1"
			(rectangle
				(start -7.62 7.62)
				(end 7.62 -10.16)
				(stroke
					(width 0.254)
					(type default)
				)
				(fill
					(type background)
				)
			)
		)
		(symbol "CN3163_1_1"
${[
  libPin("power_in", -10.16, 5.08, 0, "VIN", "4"),
  libPin("passive", -10.16, 0, 0, "ISET", "2"),
  libPin("input", -10.16, -5.08, 0, "TEMP", "1"),
  libPin("power_out", 10.16, 5.08, 180, "BAT", "5"),
  libPin("input", 10.16, 2.54, 180, "FB", "8"),
  libPin("open_collector", 10.16, 0, 180, "~{CHRG}", "7"),
  libPin("open_collector", 10.16, -2.54, 180, "~{DONE}", "6"),
  libPin("power_in", -1.27, -12.7, 90, "GND", "3"),
  libPin("passive", 1.27, -12.7, 90, "EP", "9"),
].join("\n")}
		)
		(embedded_fonts no)
	)`;

const SYMS = {};
function useSym(libId) {
  if (SYMS[libId]) return SYMS[libId];
  const [lib, name] = libId.split(":");
  const text = lib === "SNAP_Power_Mini" ? CN3163.replace('(symbol "CN3163"', '(symbol "SNAP_Power_Mini:CN3163"') : libSymbol(lib, name);
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
// SMD wire pads from the project library SNAP_Power_Mini.pretty: pairs side by side, and a solar row
// of four panel + pads and a double-size shared return in the middle (pad order 1, 2, 5, 3, 4).
const PADS = "SNAP_Power_Mini:WirePad_1x02_SMD_1.4x1.5mm_P2.0mm";
const SOLAR_PADS = "SNAP_Power_Mini:WirePad_Solar4_SMD_1.4x1.5mm_GND2.8x1.5mm";
const FP = {
  sod323: "Diode_SMD:D_SOD-323",
  jumper: "SNAP_Power_Mini:SolderJumper-2_P0.9mm_Open_Pad0.6x0.8mm",
  hole: "SNAP_Power_Mini:MountingHole_2.1mm_M2",
  r0603: "Resistor_SMD:R_0603_1608Metric",
  c0603: "Capacitor_SMD:C_0603_1608Metric",
  // The status LEDs and their resistors are 0402 so they fit beside the IC on this small board.
  r0402: "Resistor_SMD:R_0402_1005Metric",
  led0402: "LED_SMD:LED_0402_1005Metric",
};

// ---------- circuit ----------
// SOLAR -> CN3163 -> BAT+ (cell side, so the cell charges with the switch open);
// BATTERY + -> SWITCH -> LOAD + ; all negatives share GND.
// Charger as in the SD05CRMA module (datasheet Figure 1), with its CHRG (red) and DONE (green)
// LEDs from VIN, so they light only while the panel is delivering power.
const CH = 40.64; // charger block top rail
// Up to four panels, one shared return. Each panel + reaches VIN through its own Schottky, so a
// shaded or disconnected panel can't sink current from the others.
const J4 = placeByPin("J4", "Connector_Generic:Conn_01x05", "1", P(25.4, CH + 12.7), { mirror: "y", value: "SOLAR", fp: SOLAR_PADS, noBom: true });
for (let n = 1; n <= 4; n++) {
  wire(J4.pin(String(n)), P(27.94, J4.pin(String(n)).y));
  LABELS.push({ name: `SOL${n}`, at: P(27.94, J4.pin(String(n)).y), ang: 0 });
}
gnd(wire(J4.pin("5"), P(27.94, J4.pin("5").y), P(27.94, J4.pin("5").y + 2.54)));
const busX = 33.02;
for (let n = 1; n <= 4; n++) {
  const y = CH - (4 - n) * 7.62;
  const D = placeByPin(`D${n + 2}`, "Device:D_Schottky", "1", P(busX, y), { rot: 180, value: "1N5819WS", fp: FP.sod323 });
  wire(P(20.32, y), D.pin("2"));
  LABELS.push({ name: `SOL${n}`, at: P(20.32, y), ang: 0 });
  if (n > 1) junction(P(busX, y));
}
wire(P(busX, CH - 22.86), P(busX, CH));
const U1 = place("U1", "SNAP_Power_Mini:CN3163", 73.66, CH + 5.08, { value: "CN3163" });
const C1 = placeByPin("C1", "Device:C", "1", P(45.72, CH), { value: "10uF/10V", fp: FP.c0603, labelLeft: true });
// VIN is driven only by the diodes' passive pins: flag it for ERC.
const vinFlag = P(40.64, CH);
wire(P(busX, CH), vinFlag, P(45.72, CH), U1.pin("4"));
flag(vinFlag);
junction(vinFlag);
junction(P(45.72, CH));
LABELS.push({ name: "VIN", at: P(50.8, CH), ang: 0 });
gnd(C1.pin("2"));
// TEMP grounded: battery temperature sensing disabled (no NTC in a bare cell).
gnd(wire(U1.pin("1"), P(60.96, U1.pin("1").y)));
// R_ISET: ICH = 1188V / 1.2k = 0.99A (datasheet "Setting Charge Current").
const R1 = placeByPin("R1", "Device:R", "1", P(60.96, U1.pin("2").y), { rot: 270, value: "1.2k 1%", fp: FP.r0603 });
wire(U1.pin("2"), R1.pin("1"));
gnd(wire(R1.pin("2"), P(50.8, R1.pin("2").y), P(50.8, R1.pin("2").y + 2.54)));
const gndJoin = P(U1.pin("3").x, U1.pin("3").y + 2.54);
wire(U1.pin("3"), gndJoin, P(U1.pin("9").x, gndJoin.y), U1.pin("9"));
gnd(gndJoin);
// BAT and FB tied (4.2V float, no Rx); C2 is the datasheet's required BAT capacitor.
// The BAT+ rail runs above the IC so the LED chains can leave CHRG/DONE to the right.
const fbX = 86.36, batY = CH - 10.16;
wire(U1.pin("8"), P(fbX, U1.pin("8").y), P(fbX, batY), P(91.44, batY), P(96.52, batY));
wire(U1.pin("5"), P(fbX, U1.pin("5").y));
junction(P(fbX, U1.pin("5").y));
junction(P(91.44, batY));
LABELS.push({ name: "BAT+", at: P(96.52, batY), ang: 0 });
const C2 = placeByPin("C2", "Device:C", "1", P(91.44, batY), { value: "10uF/10V", fp: FP.c0603 });
gnd(C2.pin("2"));
// Status LEDs (datasheet "Open-Drain Status Outputs"): ~CHRG sinks while charging (red),
// ~DONE once charging has terminated (green). ~1k gives 2-3 mA from a 5V panel.
const ledX = 116.84;
function statusLed(n, y, colour) {
  const D = placeByPin(`D${n}`, "Device:LED", "1", P(96.52, y), { value: colour, fp: FP.led0402 });
  const R = placeByPin(`R${n + 1}`, "Device:R", "1", P(106.68, y), { rot: 90, value: "1k", fp: FP.r0402 });
  wire(D.pin("2"), R.pin("1"));
  wire(R.pin("2"), P(ledX, y));
  return D;
}
const D1 = statusLed(1, U1.pin("7").y, "RED");
wire(U1.pin("7"), D1.pin("1"));
const D2 = statusLed(2, U1.pin("6").y + 7.62, "GREEN");
wire(U1.pin("6"), P(fbX, U1.pin("6").y), P(fbX, D2.pin("1").y), D2.pin("1"));
// JP1, normally open, feeds both LED resistors from VIN: bridge it with solder to enable the LEDs.
// Left open they draw nothing.
const ledTop = U1.pin("7").y;
wire(P(ledX, D2.pin("1").y), P(ledX, ledTop), P(ledX, CH));
junction(P(ledX, ledTop));
const JP1 = placeByPin("JP1", "Jumper:SolderJumper_2_Open", "1", P(ledX + 2.54, CH), { value: "LED_EN", fp: FP.jumper });
wire(P(ledX, CH), JP1.pin("1"));
LABELS.push({ name: "LED_PWR", at: P(ledX, CH), ang: 180 });
wire(JP1.pin("2"), P(JP1.pin("2").x + 2.54, CH));
LABELS.push({ name: "VIN", at: P(JP1.pin("2").x + 2.54, CH), ang: 0 });

// BATTERY + -> Q1 -> BAT+ -> SWITCH -> LOAD + ; BATTERY - and LOAD - share GND.
// Q1 AO3401A, gate to GND, is the reverse-battery guard: a cell the right way round turns it on
// through its body diode (then ~60 mOhm both ways, so the charger still charges through it); a
// reversed cell leaves it off and the body diode blocks.
const RAIL = 76.2;
const J1 = placeByPin("J1", "Connector_Generic:Conn_01x02", "1", P(55.88, RAIL), { mirror: "y", value: "BATTERY", fp: PADS, noBom: true });
// The switch pads face down so the battery and load sides read left to right.
const J2 = placeByPin("J2", "Connector_Generic:Conn_01x02", "1", P(81.28, RAIL - 5.08), { rot: 90, value: "SWITCH", fp: PADS, noBom: true });
const J3 = placeByPin("J3", "Connector_Generic:Conn_01x02", "1", P(96.52, RAIL), { value: "LOAD", fp: PADS, noBom: true });
const Q1 = placeByPin("Q1", "Transistor_FET:AO3401A", "3", P(66.04, RAIL), { rot: 90, value: "AO3401A", fieldsRight: true });
wire(J1.pin("1"), Q1.pin("3"));
LABELS.push({ name: "BAT_IN", at: P(57.15, RAIL), ang: 0 });
gnd(Q1.pin("1"));
// BAT+ is driven by the charger's BAT pin, so it needs no PWR_FLAG.
wire(Q1.pin("2"), P(J2.pin("1").x, RAIL), J2.pin("1"));
LABELS.push({ name: "BAT+", at: P(77.47, RAIL), ang: 0 });
wire(J2.pin("2"), P(J2.pin("2").x, RAIL), J3.pin("1"));
LABELS.push({ name: "VOUT", at: P(86.36, RAIL), ang: 0 });
gnd(wire(J1.pin("2"), P(60.96, J1.pin("2").y), P(60.96, RAIL + 7.62)));
gnd(wire(J3.pin("2"), P(91.44, J3.pin("2").y), P(91.44, RAIL + 7.62)));
// GND needs a driver for ERC; tie a flag to a stand-alone ground symbol.
wire(P(109.22, RAIL + 5.08), P(109.22, RAIL + 7.62));
flag(P(109.22, RAIL + 5.08));
gnd(P(109.22, RAIL + 7.62));
// M2 mounting holes (non-plated), one at each end of the board
for (let i = 0; i < 2; i++)
  place(`H${i + 1}`, "Mechanical:MountingHole", 121.92 + i * 12.7, RAIL, { value: "M2", fp: FP.hole });
TEXTS.push({
  at: P(50.8, 116.84),
  text: [
    "SNAP Mini Power Controller: solar charger + power distribution for a handheld LoRa mesh node, 20 x 15 mm, two M2 holes. No net carries more than 1 A.",
    "- J4 SOLAR: up to four 5V panels on S1-S4 (+) with one shared GND pad. Each + passes its own 1N5819WS (D3-D6) to VIN,",
    "  so panels can't feed current into each other. CN3163 input 4.4-6V after the ~0.3-0.4V diode drop, absolute max 6.5V:",
    "  panel Voc must stay below 6.5V.",
    "- U1 CN3163 linear charger, 4.2V float (FB = BAT), ICH = 1188V / R1 = 0.99A, cut back automatically when the panel",
    "  sags toward 4.4V and by thermal regulation (~130C die). TEMP grounded (no NTC).",
    "- D1 red = charging (~CHRG low), D2 green = charge done (~DONE low). Fed from VIN through JP1, a normally open",
    "  solder jumper: bridge it to enable the LEDs. Left open the LEDs are off and draw nothing.",
    "- J1 BATTERY: 1S Li-ion, 1 = BAT_IN (+), 2 = GND. Q1 AO3401A (gate to GND) passes it to BAT+ and blocks a reversed cell.",
    "  The charger feeds BAT+ directly, so the cell charges with the switch open.",
    "- J2 SWITCH: off-board SPST in series with battery + toward the load. 1 = BAT+, 2 = VOUT.",
    "- J3 LOAD: 1 = VOUT (switched battery +), 2 = GND.",
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
  // Device:R and Device:C are drawn vertical at rotation 0, the LED and the diode horizontal.
  const horiz = !!(p.rot % 180) !== (p.libId === "Device:LED" || p.libId === "Device:D_Schottky");
  if (o.power) {
    refAt = [x, y]; valAt = [x, y + 3.81];
    hideVal = p.libId === "power:PWR_FLAG";
  } else if (p.libId === "SNAP_Power_Mini:CN3163") {
    refAt = [x - 7.62, y - 8.89]; valAt = [x + 7.62, y - 8.89];
  } else if (p.libId.startsWith("Device") && horiz) {
    // Horizontal: reference above, value below (an LED's light arrows hang below its body).
    refAt = [x, y - 2.54]; valAt = [x, y + (p.libId === "Device:LED" ? 3.81 : 2.54)];
  } else if (p.libId.startsWith("Device")) {
    const dx = o.labelLeft ? -2.54 : 2.54;
    refAt = [x + dx, y - 1.27]; valAt = [x + dx, y + 1.27];
  } else if (o.fieldsRight) {
    refAt = [x + 3.81, y - 1.27]; valAt = [x + 3.81, y + 1.27];
  } else if (p.libId.startsWith("Connector") && p.rot === 90) {
    // Pins point down: fields to the right of the body.
    refAt = [x + 5.08, y - 1.27]; valAt = [x + 5.08, y + 1.27];
  } else if (p.libId.startsWith("Connector")) {
    // Value beside the body, on the side away from the pins.
    const dir = p.mirror === "y" ? -1 : 1;
    refAt = [x, y - 3.81]; valAt = [x + dir * (2.54 + w(o.value) / 2), y + 3.81];
  } else {
    refAt = [x, y - 3.81]; valAt = [x, y + 3.81];
  }
  const side = o.labelLeft ? "right" : "left";
  const just =
    p.libId === "SNAP_Power_Mini:CN3163" ? ["left", "right"]
    : p.libId.startsWith("Device") && !horiz ? [side, side]
    : (p.libId.startsWith("Connector") && p.rot === 90) || o.fieldsRight ? ["left", "left"]
    : [];
  // Field angles are relative to the symbol, so counter-rotate to keep text horizontal.
  const ang = p.rot % 180 ? (360 - p.rot) % 360 : 0;
  const props = [
    prop("Reference", p.ref, ...refAt, { hide: o.power, justify: just[0], ang }),
    prop("Value", o.value, ...valAt, { hide: hideVal, justify: just[1], ang }),
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
		(title "SNAP Mini Power Controller")
		(date "2026-10-30")
		(rev "0.2")
		(comment 1 "4 solar inputs -> CN3163 -> Q1 -> battery; switch -> load. 20 x 15 mm")
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

// Project symbol library + table so the CN3163 is reusable from the symbol chooser.
fs.writeFileSync(
  path.join(PROJ, "SNAP_Power_Mini.kicad_sym"),
  `(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "kicad_symbol_editor")\n\t(generator_version "10.0")\n${CN3163}\n)\n`
);
const tbl = path.join(PROJ, "sym-lib-table");
if (!fs.existsSync(tbl))
  fs.writeFileSync(
    tbl,
    `(sym_lib_table\n\t(version 7)\n\t(lib (name "SNAP_Power_Mini")(type "KiCad")(uri "\${KIPRJMOD}/SNAP_Power_Mini.kicad_sym")(options "")(descr "Project-specific symbols"))\n)\n`
  );

for (const p of PARTS.filter((p) => !p.o.power))
  console.log(p.ref.padEnd(4), p.libId.padEnd(34), String(p.o.value).padEnd(10), Object.entries(p.sym.pins).map(([n]) => `${n}@${JSON.stringify(p.pin(n))}`).join(" "));
console.log(`${PARTS.length} symbols, ${WIRES.length} wires, ${LABELS.length} labels, ${JUNCTIONS.length} junctions`);
