#!/usr/bin/env python3
"""Generate the Home Assistant floorplan (Grundriss) dashboard.

Geometry is traced from the Bemusterungsplan "Haus 77" (Funari / Hildmann,
21.02.2022, M 1:50). All coordinates are in centimetres, origin = inner
top-left corner of the house (entrance/street side on top, garden at the
bottom). Interior: 464 x 1150 cm. Lamp positions are the ceiling outlets
from the electrical plan.

Outputs:
  eg.svg, og.svg, dg.svg      floorplans (light + dark palette via media query)
  grundriss-<floor>.json      dashboard config per floor (images embedded as data URIs)
  ../grundriss-<floor>.yaml   same configs as YAML (repo export)
  preview/                    local previews (not used by HA)

Run:  python3 dashboard/floorplan/generate.py
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))

IN_W, IN_H = 464, 1150
WL, WR, WT, WB = 19, 36.5, 36.5, 36.5          # wall thickness left/right/top/bottom
# View boxes (plan coordinates: x0, y0, x extent, y extent).
# Floors, sized for an iPad 8 in landscape (plan area about 1080 x 628 pt
# below the header and above the navbar, aspect 1.72). The house fills the
# width and is centred vertically.
# EG: house + terrace (the terrace is the button to the garden view).
_HY0, _HY1 = -75, 1503                         # entrance side .. terrace edge
_HX = round((_HY1 - _HY0) / 1.72, 1)
HOUSE_VB = (round(240.75 - _HX / 2, 1), _HY0, _HX, _HY1 - _HY0)
# OG / DG: house only (outer walls y -36.5 .. 1186.5 plus room for the shutter
# chips on the walls), so the house is drawn about 1.26x larger.
_UY0, _UY1 = -60, 1210
_UX = round((_UY1 - _UY0) / 1.72, 1)
UPPER_VB = (round(240.75 - _UX / 2, 1), _UY0, _UX, _UY1 - _UY0)
# Garden: the whole property.
VIEWBOX = (-35, -150, 835, 2165)


# The plan is drawn in plan coordinates (entrance on top) and shown rotated
# 90 degrees clockwise: entrance on the right, garden on the left.
def scr(x, y):
    """Plan coordinates -> screen coordinates of the rotated plan."""
    return -y, x


def scr_box(x0, y0, x1, y1):
    return -y1, x0, -y0, x1


def scr_viewbox(vx, vy, vw, vh):
    return -(vy + vh), vx, vh, vw

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
LIGHT = {
    "ft": "fill:#eeece8", "fg": "fill:none;stroke:#dedad3;stroke-width:1.3",
    "fb": "fill:#e7ebee", "fbg": "fill:none;stroke:#d5dbe0;stroke-width:1",
    "fw": "fill:#e5c79d", "fw2": "fill:#e0c095", "fw3": "fill:#e9cca4", "fw4": "fill:#ddbc90",
    "fwl": "fill:none;stroke:#cba679;stroke-width:1", "fwg": "fill:none;stroke:#cfa97a;stroke-opacity:.4;stroke-width:1",
    "td": "fill:#50555c", "tdg": "fill:none;stroke:#686d74;stroke-width:1.2",
    "mz": "fill:#6c7178", "mz1": "fill:#464b52", "mz2": "fill:#4e535a",
    "gls": "fill:none;stroke:#bfe0f5;stroke-width:3;stroke-linecap:round",
    "fs": "fill:#dcd7ce", "fsl": "fill:none;stroke:#cbc4b8;stroke-width:1.4",
    "fl": "fill:#c3dcac", "fld": "fill:#b2d198",
    "hd": "fill:#7fa968;stroke:#6b9556;stroke-width:1",
    "hdb": "fill:#6a9554", "hdr": "fill:#c9372c",
    "hde": "fill:url(#hedge);stroke:#557f42;stroke-width:2",
    "gv": "fill:#70767d", "gvd": "fill:#8b9198",
    "gh": "fill:#50565e;stroke:#3a3f45;stroke-width:1.5", "ghl": "fill:none;stroke:#6b727b;stroke-width:1.2",
    "gt": "fill:#3a3f46",
    "bd": "fill:#8b6a4b;stroke:#b8864f;stroke-width:5",
    "tr": "fill:#d4eabf;fill-opacity:.9;stroke:#9cc47f;stroke-width:2", "trk": "fill:#8d6e47",
    "spt": "fill:#2f343a;stroke:#f5c04a;stroke-width:2.5",
    "lp": "fill:#ffffff;stroke:#a3abb5;stroke-width:2", "lpi": "fill:none;stroke:#c5cbd2;stroke-width:2",
    "lps": "fill:none;stroke:#a3abb5;stroke-width:9;stroke-linecap:round",
    "lpc": "fill:none;stroke:#ffffff;stroke-width:4;stroke-linecap:round",
    "st": "fill:#e2c99f", "stl": "fill:none;stroke:#b8956a;stroke-width:1.6",
    "wl": "fill:none;stroke:#8d6e47;stroke-width:1.6",
    "wla": "fill:#8d6e47",
    "we": "fill:#363b43", "wi": "fill:#4a505a", "wg": "fill:#a3a9b1",
    "vw": "fill:#d5d9de;stroke:#b8bec6;stroke-width:1",
    "fx": "fill:#ffffff;stroke:#9aa3ad;stroke-width:1.6",
    "fxi": "fill:#eef2f5;stroke:#a9b1ba;stroke-width:1.2",
    "ct": "fill:#f7f6f3;stroke:#b5b0a6;stroke-width:1.6",
    "cab": "fill:#e9e6e0;stroke:#b5b0a6;stroke-width:1.6",
    "ck": "fill:#2c3035", "ckr": "fill:none;stroke:#6b737c;stroke-width:1.6",
    "dk": "fill:#8d6b51;stroke:#6b4f3a;stroke-width:1.6", "dkl": "fill:none;stroke:#a07e63;stroke-width:1",
    "bm": "fill:#f6f3ee;stroke:#c9c3b8;stroke-width:1.2", "bl": "fill:#c9a24e", "bll": "fill:none;stroke:#b08a3c;stroke-width:1.2",
    "pl": "fill:#6d529c",
    "lt": "fill:#c9ced5;stroke:#9aa1aa;stroke-width:1.2",
    "sk": "fill:#d3d9de;stroke:#9aa3ad;stroke-width:1.4",
    "wf": "fill:#ffffff;stroke:#8a96a3;stroke-width:1.2",
    "gl": "fill:#a9d4f2", "wm": "fill:none;stroke:#8a96a3;stroke-width:1.4",
    "thr": "fill:#cfc9bf",
    "dl": "fill:none;stroke:#7c8792;stroke-width:2.2",
    "da": "fill:none;stroke:#9aa4af;stroke-width:1.4;stroke-dasharray:5 5",
    "rw": "fill:#a9d4f2;fill-opacity:.55;stroke:#6aa6d6;stroke-width:2;stroke-dasharray:7 5",
    "hl": "fill:none;stroke:#9aa4af;stroke-width:1.2",
    "hz": "fill:url(#hatch)", "hh": "fill:none;stroke:#8a7556;stroke-opacity:.5;stroke-width:1.6",
    "lh": "fill:none;stroke:#8e98a3;stroke-width:1.5;stroke-dasharray:10 8",
    "sp": "fill:none;stroke:#7c8792;stroke-width:2;stroke-dasharray:7 5",
    "rn": "fill:#3d4450;font-size:21px;font-weight:600", "rn2": "fill:#3d4450;font-size:17px;font-weight:600",
    "ra": "fill:#7d8692;font-size:15px",
    "rs": "fill:#7d8692;font-size:12px",
    "rsw": "fill:#eef0f2;font-size:12px",
    "rnw": "fill:#f3f4f6;font-size:21px;font-weight:600", "raw": "fill:#c3c8ce;font-size:15px",
    # garden view: larger type (the plan is shown at half scale)
    "gnw": "fill:#f3f4f6;fill-opacity:.9;font-size:34px;font-weight:600",
    "gn": "fill:#3d4450;font-size:34px;font-weight:600", "gn2": "fill:#3d4450;font-size:27px;font-weight:600",
    "gs": "fill:#5d6672;font-size:22px", "gsw": "fill:#eef0f2;font-size:21px",
}
DARK = {
    "ft": "fill:#34373c", "fg": "fill:none;stroke:#2b2e32;stroke-width:1.3",
    "fb": "fill:#30353a", "fbg": "fill:none;stroke:#272b30;stroke-width:1",
    "fw": "fill:#4d3d2b", "fw2": "fill:#473828", "fw3": "fill:#524130", "fw4": "fill:#443526",
    "fwl": "fill:none;stroke:#34291d;stroke-width:1", "fwg": "fill:none;stroke:#3b2f22;stroke-opacity:.6;stroke-width:1",
    "td": "fill:#2b2e33", "tdg": "fill:none;stroke:#3a3e44;stroke-width:1.2",
    "mz": "fill:#3a3e44", "mz1": "fill:#25282c", "mz2": "fill:#2c3035",
    "gls": "fill:none;stroke:#7fb3d6;stroke-width:3;stroke-linecap:round",
    "fs": "fill:#3a3833", "fsl": "fill:none;stroke:#2f2d29;stroke-width:1.4",
    "fl": "fill:#2c3d26", "fld": "fill:#26361f",
    "hd": "fill:#355a2b;stroke:#2b4a23;stroke-width:1",
    "hdb": "fill:#2a4423", "hdr": "fill:#9a2f26",
    "hde": "fill:url(#hedge);stroke:#24391e;stroke-width:2",
    "gv": "fill:#2b2f34", "gvd": "fill:#3c4147",
    "gh": "fill:#59606a;stroke:#7a828c;stroke-width:1.5", "ghl": "fill:none;stroke:#737b85;stroke-width:1.2",
    "gt": "fill:#9aa2ad",
    "bd": "fill:#4a3a2b;stroke:#8d6a43;stroke-width:5",
    "tr": "fill:#6f8f5c;fill-opacity:.9;stroke:#8fb07a;stroke-width:2", "trk": "fill:#c9a877",
    "spt": "fill:#15171a;stroke:#f5c04a;stroke-width:2.5",
    "lp": "fill:#5b626c;stroke:#80888f;stroke-width:2", "lpi": "fill:none;stroke:#454b53;stroke-width:2",
    "lps": "fill:none;stroke:#80888f;stroke-width:9;stroke-linecap:round",
    "lpc": "fill:none;stroke:#5b626c;stroke-width:4;stroke-linecap:round",
    "st": "fill:#5b4a34", "stl": "fill:none;stroke:#7a6446;stroke-width:1.6",
    "wl": "fill:none;stroke:#c9a877;stroke-width:1.6",
    "wla": "fill:#c9a877",
    "we": "fill:#858d98", "wi": "fill:#6c7480", "wg": "fill:#5b626b",
    "vw": "fill:#474d55;stroke:#5c636c;stroke-width:1",
    "fx": "fill:#4b5159;stroke:#6f7781;stroke-width:1.6",
    "fxi": "fill:#3b4047;stroke:#626a73;stroke-width:1.2",
    "ct": "fill:#41454b;stroke:#5f656d;stroke-width:1.6",
    "cab": "fill:#383c42;stroke:#5f656d;stroke-width:1.6",
    "ck": "fill:#15171a", "ckr": "fill:none;stroke:#4c535b;stroke-width:1.6",
    "dk": "fill:#5c4535;stroke:#7b5f48;stroke-width:1.6", "dkl": "fill:none;stroke:#6c523f;stroke-width:1",
    "bm": "fill:#565b62;stroke:#6c7179;stroke-width:1.2", "bl": "fill:#8c7034", "bll": "fill:none;stroke:#735c2a;stroke-width:1.2",
    "pl": "fill:#4d3a70",
    "lt": "fill:#7a8089;stroke:#959ca5;stroke-width:1.2",
    "sk": "fill:#5a6168;stroke:#7a828b;stroke-width:1.4",
    "wf": "fill:#5f6772;stroke:#8b939e;stroke-width:1.2",
    "gl": "fill:#4f86ad", "wm": "fill:none;stroke:#8b939e;stroke-width:1.4",
    "thr": "fill:#55524c",
    "dl": "fill:none;stroke:#a6aeb8;stroke-width:2.2",
    "da": "fill:none;stroke:#7f8791;stroke-width:1.4;stroke-dasharray:5 5",
    "rw": "fill:#4f86ad;fill-opacity:.3;stroke:#6ea3c9;stroke-width:2;stroke-dasharray:7 5",
    "hl": "fill:none;stroke:#5c646d;stroke-width:1.2",
    "hz": "fill:url(#hatch)", "hh": "fill:none;stroke:#d9c49c;stroke-opacity:.35;stroke-width:1.6",
    "lh": "fill:none;stroke:#6c757f;stroke-width:1.5;stroke-dasharray:10 8",
    "sp": "fill:none;stroke:#a6aeb8;stroke-width:2;stroke-dasharray:7 5",
    "rn": "fill:#dfe3e8;font-size:21px;font-weight:600", "rn2": "fill:#dfe3e8;font-size:17px;font-weight:600",
    "ra": "fill:#9aa3ad;font-size:15px",
    "rs": "fill:#9aa3ad;font-size:12px",
    "rsw": "fill:#f1f3f5;font-size:12px",
    "rnw": "fill:#f3f4f6;font-size:21px;font-weight:600", "raw": "fill:#c3c8ce;font-size:15px",
    "gnw": "fill:#f3f4f6;fill-opacity:.9;font-size:34px;font-weight:600",
    "gn": "fill:#f1ece4;font-size:34px;font-weight:600", "gn2": "fill:#dfe3e8;font-size:27px;font-weight:600",
    "gs": "fill:#aab2bc;font-size:22px", "gsw": "fill:#f1f3f5;font-size:21px",
}
FONT = "text{font-family:-apple-system,system-ui,Roboto,'Segoe UI',Helvetica,Arial,sans-serif;text-anchor:middle}"

GLOW = "#ffc65c"


def css(force_dark=False):
    light = "".join(".%s{%s}" % kv for kv in LIGHT.items())
    dark = "".join(".%s{%s}" % kv for kv in DARK.items())
    shadow_dark = "#sh feDropShadow,#fs feDropShadow{flood-opacity:.6}"
    if force_dark:
        return FONT + light + dark + shadow_dark
    return FONT + light + "@media (prefers-color-scheme:dark){" + dark + shadow_dark + "}"


DEFS = (
    '<pattern id="t60" width="60" height="60" patternUnits="userSpaceOnUse">'
    '<rect class="ft" width="60" height="60"/><path class="fg" d="M0 .6H60M.6 0V60"/></pattern>'
    '<pattern id="t30" width="30" height="30" patternUnits="userSpaceOnUse">'
    '<rect class="fb" width="30" height="30"/><path class="fbg" d="M0 .5H30M.5 0V30"/></pattern>'
    '<pattern id="wood" width="240" height="75" patternUnits="userSpaceOnUse" patternTransform="rotate(90)">'
    '<rect class="fw" x="0" y="0" width="150" height="15"/><rect class="fw2" x="150" y="0" width="90" height="15"/><rect class="fw3" x="0" y="15" width="60" height="15"/><rect class="fw" x="60" y="15" width="150" height="15"/><rect class="fw3" x="210" y="15" width="30" height="15"/><rect class="fw4" x="0" y="30" width="20" height="15"/><rect class="fw3" x="20" y="30" width="110" height="15"/><rect class="fw4" x="130" y="30" width="110" height="15"/><rect class="fw2" x="0" y="45" width="90" height="15"/><rect class="fw4" x="90" y="45" width="110" height="15"/><rect class="fw2" x="200" y="45" width="40" height="15"/><rect class="fw" x="0" y="60" width="40" height="15"/><rect class="fw2" x="40" y="60" width="130" height="15"/><rect class="fw" x="170" y="60" width="70" height="15"/>'
    '<path class="fwg" d="M25 5.5H95M185 10.5H240M85 20.5H155M5 25.5H60M45 35.5H115M165 40.5H220M115 50.5H185M235 55.5H240M65 65.5H135M205 70.5H240"/><path class="fwl" d="M0 0.5H240M0.5 0V15M150.5 0V15M0 15.5H240M60.5 15V30M210.5 15V30M0 30.5H240M20.5 30V45M130.5 30V45M0 45.5H240M90.5 45V60M200.5 45V60M0 60.5H240M40.5 60V75M170.5 60V75"/></pattern>'
    '<pattern id="t60d" width="60" height="60" patternUnits="userSpaceOnUse">'
    '<rect class="td" width="60" height="60"/><path class="tdg" d="M0 .6H60M.6 0V60"/></pattern>'
    '<pattern id="mosaic" width="10" height="10" patternUnits="userSpaceOnUse">'
    '<rect class="mz" width="10" height="10"/><rect class="mz1" x=".6" y=".6" width="3.9" height="3.9"/>'
    '<rect class="mz2" x="5.6" y=".6" width="3.9" height="3.9"/><rect class="mz2" x=".6" y="5.6" width="3.9" height="3.9"/>'
    '<rect class="mz1" x="5.6" y="5.6" width="3.9" height="3.9"/></pattern>'
    '<pattern id="stone" width="80" height="40" patternUnits="userSpaceOnUse">'
    '<rect class="fs" width="80" height="40"/><path class="fsl" d="M0 .7H80M0 20.7H80M.7 0V20M40.7 20V40"/></pattern>'
    '<pattern id="lawn" width="26" height="26" patternUnits="userSpaceOnUse">'
    '<rect class="fl" width="26" height="26"/><circle class="fld" cx="6" cy="7" r="2.2"/>'
    '<circle class="fld" cx="19" cy="17" r="2.2"/><circle class="fld" cx="14" cy="4" r="1.4"/></pattern>'
    '<pattern id="hedge" width="44" height="44" patternUnits="userSpaceOnUse">'
    '<rect class="hdb" width="44" height="44"/>'
    '<circle class="hd" cx="8" cy="9" r="9"/><circle class="hd" cx="29" cy="6" r="9"/>'
    '<circle class="hd" cx="20" cy="24" r="11"/><circle class="hd" cx="4" cy="33" r="8"/>'
    '<circle class="hd" cx="39" cy="29" r="10"/><circle class="hd" cx="16" cy="41" r="7"/>'
    '<circle class="hdr" cx="10" cy="6" r="3.2"/><circle class="hdr" cx="31" cy="26" r="3.6"/>'
    '<circle class="hdr" cx="21" cy="19" r="2.6"/><circle class="hdr" cx="41" cy="8" r="3"/>'
    '<circle class="hdr" cx="6" cy="30" r="2.8"/><circle class="hdr" cx="17" cy="38" r="2.4"/></pattern>'
    '<pattern id="gravel" width="16" height="16" patternUnits="userSpaceOnUse">'
    '<rect class="gv" width="16" height="16"/><ellipse class="gvd" cx="4" cy="4" rx="2.4" ry="1.6"/>'
    '<ellipse class="gvd" cx="11" cy="7" rx="2" ry="1.4"/><ellipse class="gvd" cx="6" cy="12" rx="1.8" ry="1.3"/>'
    '<ellipse class="gvd" cx="13" cy="14" rx="2.2" ry="1.5"/></pattern>'
    '<pattern id="hatch" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    '<path class="hh" d="M0 0V12"/></pattern>'
    '<filter id="sh" x="-5%" y="-5%" width="110%" height="110%">'
    '<feDropShadow dx="2" dy="0" stdDeviation="2.5" flood-color="#000" flood-opacity=".35"/></filter>'
    '<filter id="fs" x="-10%" y="-10%" width="120%" height="120%">'
    '<feDropShadow dx="1.5" dy="0" stdDeviation="1.6" flood-color="#000" flood-opacity=".22"/></filter>'
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def fmt(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def pts(poly):
    return " ".join("%s,%s" % (fmt(x), fmt(y)) for x, y in poly)


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def thick(p1, p2, t):
    """Wall polygon of thickness t along the segment p1-p2."""
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * t / 2, dx / L * t / 2
    return [(p1[0] + nx, p1[1] + ny), (p2[0] + nx, p2[1] + ny),
            (p2[0] - nx, p2[1] - ny), (p1[0] - nx, p1[1] - ny)]


def poly(cls, p, extra=""):
    return '<polygon class="%s" points="%s"%s/>' % (cls, pts(p), extra)


def r(cls, x0, y0, x1, y1, rx=0):
    s = '<rect class="%s" x="%s" y="%s" width="%s" height="%s"' % (
        cls, fmt(x0), fmt(y0), fmt(x1 - x0), fmt(y1 - y0))
    return s + (' rx="%s"/>' % fmt(rx) if rx else "/>")


def line(cls, x1, y1, x2, y2):
    return '<line class="%s" x1="%s" y1="%s" x2="%s" y2="%s"/>' % (cls, fmt(x1), fmt(y1), fmt(x2), fmt(y2))


def text(cls, x, y, s):
    return '<text class="%s" x="%s" y="%s">%s</text>' % (cls, fmt(x), fmt(y), s)


def bbox(polys):
    xs = [p[0] for pl in polys for p in pl]
    ys = [p[1] for pl in polys for p in pl]
    return min(xs), min(ys), max(xs), max(ys)


# --------------------------------------------------------------------------
# Building blocks
# --------------------------------------------------------------------------
def door(hx, hy, rad, a_closed, a_open):
    """Door leaf (open position) and dashed swing arc."""
    ac, ao = math.radians(a_closed), math.radians(a_open)
    cx, cy = hx + rad * math.cos(ac), hy + rad * math.sin(ac)
    ox, oy = hx + rad * math.cos(ao), hy + rad * math.sin(ao)
    sweep = 1 if (a_open - a_closed) % 360 < 180 else 0
    return ('<path class="da" d="M%s,%s A%s,%s 0 0 %d %s,%s"/>' % (
        fmt(cx), fmt(cy), fmt(rad), fmt(rad), sweep, fmt(ox), fmt(oy))
        + line("dl", hx, hy, ox, oy))


def window_h(a, b, y_mid, panels=None, kind="window"):
    """Window/door element in a horizontal wall (top/bottom)."""
    w = b - a
    panels = panels or max(1, round(w / 100))
    out = []
    if kind == "slide":
        m = a + w / 2
        out.append(r("wf", a, y_mid - 7, b, y_mid + 7))
        out.append(r("gl", a + 2, y_mid - 5, m + 6, y_mid - 0.5))
        out.append(r("gl", m - 6, y_mid + 0.5, b - 2, y_mid + 5))
        out.append(line("wm", a + 2, y_mid - 0.5, m + 6, y_mid - 0.5))
        out.append(line("wm", m - 6, y_mid + 0.5, b - 2, y_mid + 0.5))
        return out
    out.append(r("wf", a, y_mid - 6, b, y_mid + 6))
    out.append(r("gl", a + 2.5, y_mid - 2.5, b - 2.5, y_mid + 2.5))
    for i in range(1, panels):
        x = a + w * i / panels
        out.append(line("wm", x, y_mid - 6, x, y_mid + 6))
    return out


def window_v(a, b, x_mid, panels=None, kind="window"):
    w = b - a
    panels = panels or max(1, round(w / 100))
    out = []
    if kind == "slide":
        m = a + w / 2
        out.append(r("wf", x_mid - 7, a, x_mid + 7, b))
        out.append(r("gl", x_mid - 5, a + 2, x_mid - 0.5, m + 6))
        out.append(r("gl", x_mid + 0.5, m - 6, x_mid + 5, b - 2))
        return out
    out.append(r("wf", x_mid - 6, a, x_mid + 6, b))
    out.append(r("gl", x_mid - 2.5, a + 2.5, x_mid + 2.5, b - 2.5))
    for i in range(1, panels):
        y = a + w * i / panels
        out.append(line("wm", x_mid - 6, y, x_mid + 6, y))
    return out


def toilet(x, y, rot):
    return ('<g transform="translate(%s %s) rotate(%s)" filter="url(#fs)">'
            '<rect class="fx" x="-19" y="0" width="38" height="17" rx="4"/>'
            '<path class="fx" d="M-16,17 C-17,48 -9,62 0,62 C9,62 17,48 16,17 Z"/>'
            '<ellipse class="fxi" cx="0" cy="37" rx="9.5" ry="15"/></g>') % (fmt(x), fmt(y), fmt(rot))


def basin(x, y, rot, w=58, d=44):
    return ('<g transform="translate(%s %s) rotate(%s)" filter="url(#fs)">'
            '<rect class="fx" x="%s" y="0" width="%s" height="%s" rx="5"/>'
            '<ellipse class="fxi" cx="0" cy="%s" rx="%s" ry="%s"/>'
            '<circle class="sk" cx="0" cy="7" r="3"/></g>') % (
        fmt(x), fmt(y), fmt(rot), fmt(-w / 2), fmt(w), fmt(d), fmt(d / 2 + 3), fmt(w / 2 - 8), fmt(d / 2 - 9))


def shower(x0, y0, x1, y1):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return ('<g filter="url(#fs)">' + r("fx", x0, y0, x1, y1, 3) + "</g>"
            + '<path class="hl" d="M%s,%sL%s,%sM%s,%sL%s,%s"/>' % (
                fmt(x0 + 4), fmt(y0 + 4), fmt(x1 - 4), fmt(y1 - 4), fmt(x1 - 4), fmt(y0 + 4), fmt(x0 + 4), fmt(y1 - 4))
            + '<circle class="sk" cx="%s" cy="%s" r="5"/>' % (fmt(cx), fmt(cy)))


def walkin(x0, y0, x1, y1, glass_x, glass_y0, drain, head):
    """Walk-in shower: mosaic floor up to the walls, glass panel on the room side, drain and rain head."""
    dx, dy = drain
    hx, hy = head
    return (poly("", rect(x0, y0, x1, y1), ' fill="url(#mosaic)"')
            + '<rect class="sk" x="%s" y="%s" width="16" height="16" rx="2"/>' % (fmt(dx - 8), fmt(dy - 8))
            + line("hl", dx - 5, dy - 3, dx + 5, dy - 3) + line("hl", dx - 5, dy + 3, dx + 5, dy + 3)
            + '<g filter="url(#fs)"><circle class="fx" cx="%s" cy="%s" r="13"/></g>' % (fmt(hx), fmt(hy))
            + '<circle class="fxi" cx="%s" cy="%s" r="8"/>' % (fmt(hx), fmt(hy))
            + line("gls", glass_x, glass_y0, glass_x, y1))


def buero_moebel():
    """Philipps Buero, from the user's sketch (true to the sketch's arrangement, sizes from the real furniture).
    Window wall y=0, door wall y=377 (y=359.5 behind the bath), outer wall x=0, Flekke wall x=464."""
    s = ['<g filter="url(#fs)">',
         # corner desk: arm along the outer wall (monitors, gaming PC) and arm under the window
         '<path class="dk" d="M0,0H208V75H130A55,55 0 0 0 75,130V188H0Z"/>',
         r("fx", 0, 227, 58, 377),                  # Pax 2 x 75
         r("dk", 208, 307, 308, 359.5),             # coffee bar
         r("fx", 317, 320.5, 464, 359.5),           # Kallax 4 cells
         r("fx", 370, 0, 464, 207, 4),              # Flekke daybed
         r("dk", 326, 3, 366, 43, 3),               # side table
         r("fx", 450, 247, 464, 283, 3),            # robot dock
         r("fx", 282, 4, 314, 36, 7),               # air purifier (clear of the window button)
         '<circle class="ck" cx="432" cy="265" r="17"/>',  # robot vacuum in front of its dock
         "</g>",
         # desk: monitors, laptop on its dock, gaming PC, PC
         r("ck", 9, 58, 15, 100, 1.5), r("ck", 9, 103, 15, 145, 1.5),
         r("ck", 3, 33, 9, 47, 1.5), r("lt", 12, 25, 34, 55, 2.5), line("hl", 15, 27, 15, 53),
         r("fx", 5, 150, 50, 181, 2), line("hl", 12, 155, 12, 176),
         r("fx", 38, 4, 104, 25, 2), line("hl", 44, 10, 98, 10),
         # Pax: two frames, doors on the room side
         line("hl", 0, 302, 58, 302), line("hl", 52, 227, 52, 377),
         # Kallax cells
         line("hl", 353.75, 320.5, 353.75, 359.5), line("hl", 390.5, 320.5, 390.5, 359.5),
         line("hl", 427.25, 320.5, 427.25, 359.5),
         # coffee bar: machine + cup
         r("ck", 220, 318, 250, 350, 3), '<circle class="ckr" cx="235" cy="334" r="6"/>',
         '<circle class="fx" cx="270" cy="333" r="6"/>',
         # Flekke: mattress, ochre throw, purple cushions against the wall
         r("bm", 376, 6, 458, 201, 6), r("bl", 376, 64, 458, 201, 6), line("bll", 376, 72, 458, 72),
         r("pl", 436, 10, 456, 56, 7), r("pl", 436, 60, 456, 104, 7),
         # robot vacuum: lidar dome + bumper
         '<circle class="fx" cx="426" cy="265" r="6"/>', line("hl", 446, 255, 446, 275),
         # side table: drawer line
         line("dkl", 346, 6, 346, 40),
         # air purifier grille
         '<circle class="fxi" cx="298" cy="20" r="11"/><circle class="sk" cx="298" cy="20" r="4"/>',
         ]
    return s


BLUR = "<filter id='b' x='-50%' y='-50%' width='200%' height='200%'><feGaussianBlur stdDeviation='3'/></filter>"


def spin(x, y, dur):
    return ("<animateTransform attributeName='transform' type='rotate' from='0 %s %s' to='360 %s %s' "
            "dur='%ss' repeatCount='indefinite'/>" % (x, y, x, y, dur))


def ring_glow(x, y, rad, color, inner):
    """Soft glow around a device; transparent over the device itself so it keeps its theme colours."""
    return ("<radialGradient id='rg'><stop offset='0' stop-color='%s' stop-opacity='0'/>"
            "<stop offset='%s' stop-color='%s' stop-opacity='0'/><stop offset='%s' stop-color='%s' stop-opacity='.5'/>"
            "<stop offset='1' stop-color='%s' stop-opacity='0'/></radialGradient>"
            "<circle cx='%s' cy='%s' r='%s' fill='url(#rg)'/>" % (
                color, inner, color, inner + .1, color, color, x, y, rad))


def buero_geraete():
    """Office devices drawn by buero_moebel(): tap target over the furniture plus state overlays.
    PCs only open their details (never cut power to a running PC); 'running' means the plug measures > 10 W.
    Schreibtisch1 (PC) and Schreibtisch2 (monitors, laptop docks) are always switched together: both open the HA group switch.schreibtisch (Schreibtisch)."""
    purifier = (ring_glow(298, 20, 52, "#22d3ee", .42)
                + "<circle cx='298' cy='20' r='11' fill='#cffafe' stroke='#06b6d4' stroke-width='2'/>"
                + "<circle cx='298' cy='20' r='7' fill='none' stroke='#0891b2' stroke-width='3.5' "
                  "stroke-dasharray='4.4 2.93'>" + spin(298, 20, 2.4) + "</circle>"
                + "<circle cx='298' cy='20' r='2.5' fill='#0891b2'/>")
    pc = (BLUR + "<rect x='42' y='20' width='58' height='10' rx='4' fill='#3b82f6' opacity='.85' filter='url(#b)'/>"
          + "<line x1='44' y1='23' x2='98' y2='23' stroke='#93c5fd' stroke-width='2.5' stroke-linecap='round'/>"
          + "<circle cx='97' cy='15' r='2.5' fill='#60a5fa'/>")
    stops = "".join("<stop offset='%s' stop-color='%s'><animate attributeName='stop-color' values='%s' dur='6s' "
                    "repeatCount='indefinite'/></stop>" % (o, c[0], ";".join(c + c[:1]))
                    for o, c in (("0", ["#ec4899", "#8b5cf6", "#06b6d4"]), (".5", ["#8b5cf6", "#06b6d4", "#ec4899"]),
                                 ("1", ["#06b6d4", "#ec4899", "#8b5cf6"])))
    gaming = (BLUR + "<linearGradient id='rgb' gradientUnits='userSpaceOnUse' x1='0' y1='150' x2='0' y2='181'>"
              + stops + "</linearGradient>"
              + "<rect x='43' y='149' width='13' height='33' rx='5' fill='url(#rgb)' opacity='.8' filter='url(#b)'/>"
              + "<line x1='46' y1='154' x2='46' y2='177' stroke='url(#rgb)' stroke-width='3' stroke-linecap='round'/>")
    robo_on = ("<circle cx='432' cy='265' r='22' fill='none' stroke='#22c55e' stroke-width='3' "
               "stroke-dasharray='8.6 5.22'>" + spin(432, 265, 3) + "</circle>"
               + "<circle cx='426' cy='265' r='6' fill='#22c55e'/>")
    robo_err = ("<g><circle cx='432' cy='265' r='22' fill='none' stroke='#ef4444' stroke-width='3.5'/>"
                "<circle cx='426' cy='265' r='6' fill='#ef4444'/>"
                "<animate attributeName='opacity' values='1;.4;1' dur='1.6s' repeatCount='indefinite'/></g>")

    screens = (BLUR + "<rect x='13' y='57' width='17' height='89' rx='6' fill='#bfdbfe' opacity='.8' filter='url(#b)'/>"
               + "<line x1='14.5' y1='59.5' x2='14.5' y2='98.5' stroke='#e0f2fe' stroke-width='2'/>"
               + "<line x1='14.5' y1='104.5' x2='14.5' y2='143.5' stroke='#e0f2fe' stroke-width='2'/>"
               + "<circle cx='8' cy='40' r='1.8' fill='#22c55e'/>")

    def watt(sensor):
        return [{"condition": "numeric_state", "entity": sensor, "above": 10}]

    def state(entity, st):
        return [{"condition": "state", "entity": entity, "state": st}]

    return [
        dict(entity="switch.luftfilter", tap="toggle", hit=(282, 4, 314, 36),
             states=[(state("switch.luftfilter", "on"), purifier, (246, 0, 350, 72))]),
        dict(entity="switch.schreibtisch", tap="more-info", hit=(9, 22, 15, 138),      # monitors + laptop docks (Schreibtisch2)
             states=[(watt("sensor.schreibtisch2_leistung"), screens, (0, 30, 44, 152))]),
        dict(entity="switch.schreibtisch", tap="more-info", hit=(38, 4, 104, 25),      # PC (Schreibtisch1)
             states=[(watt("sensor.schreibtisch1_leistung"), pc, (30, 0, 112, 40))]),
        dict(entity="switch.philipps_buro_gaming_pc", tap="more-info", hit=(5, 150, 50, 181),
             states=[(watt("sensor.philipps_buro_gaming_pc_leistung"), gaming, (30, 136, 70, 196))]),
        dict(entity="vacuum.robo", tap="more-info", hit=(415, 248, 449, 282),
             states=[(state("vacuum.robo", ["cleaning", "returning"]), robo_on, (404, 237, 460, 293)),
                     (state("vacuum.robo", "error"), robo_err, (404, 237, 460, 293))]),
    ]


def bathtub(x0, y0, x1, y1):
    return ('<g filter="url(#fs)">' + r("fx", x0, y0, x1, y1, 8) + "</g>"
            + r("fxi", x0 + 7, y0 + 7, x1 - 7, y1 - 7, 22)
            + '<circle class="sk" cx="%s" cy="%s" r="4"/>' % (fmt(x1 - 22), fmt((y0 + y1) / 2)))


def washer(x0, y0, s=60):
    cx, cy = x0 + s / 2, y0 + s / 2 + 3
    return ('<g filter="url(#fs)">' + r("fx", x0, y0, x0 + s, y0 + s, 4) + "</g>"
            + '<circle class="fxi" cx="%s" cy="%s" r="20"/><circle class="sk" cx="%s" cy="%s" r="13"/>' % (
                fmt(cx), fmt(cy), fmt(cx), fmt(cy))
            + line("hl", x0 + 6, y0 + 9, x0 + s - 6, y0 + 9))


def stair(x0, y0, x1, y1, steps=14):
    """Winder stair (U-shaped walking line around the stringer at x1).
    Entry bottom-right, exit top-right, as in the plan."""
    rad = 46
    pb = (x1, y1 - 77)    # lower pivot
    pt = (x1, y0 + 77)    # upper pivot
    straight = pb[1] - pt[1]
    arc = math.pi / 2 * rad
    L = 2 * arc + straight
    out = [r("st", x0, y0, x1, y1)]

    def ray(p, ang):
        dx, dy = math.cos(ang), math.sin(ang)
        ts = []
        if dx < -1e-9:
            ts.append((x0 - p[0]) / dx)
        if dy > 1e-9:
            ts.append((y1 - p[1]) / dy)
        if dy < -1e-9:
            ts.append((y0 - p[1]) / dy)
        t = min(ts)
        return p[0] + dx * t, p[1] + dy * t

    walk = []
    for i in range(0, steps + 1):
        s = L * i / steps
        if s <= arc:
            a = math.pi / 2 + s / rad
            ex, ey = ray(pb, a)
            if 0 < i < steps:
                out.append(line("stl", pb[0], pb[1], ex, ey))
        elif s <= arc + straight:
            y = pb[1] - (s - arc)
            if 0 < i < steps:
                out.append(line("stl", x0, y, x1, y))
        else:
            a = math.pi + (s - arc - straight) / rad
            ex, ey = ray(pt, a)
            if 0 < i < steps:
                out.append(line("stl", pt[0], pt[1], ex, ey))
    # walking line
    n = 40
    for i in range(n + 1):
        s = L * i / n
        if s <= arc:
            a = math.pi / 2 + s / rad
            walk.append((pb[0] + rad * math.cos(a), pb[1] + rad * math.sin(a)))
        elif s <= arc + straight:
            walk.append((x1 - rad, pb[1] - (s - arc)))
        else:
            a = math.pi + (s - arc - straight) / rad
            walk.append((pt[0] + rad * math.cos(a), pt[1] + rad * math.sin(a)))
    walk[-1] = (walk[-1][0] - 8, walk[-1][1])
    out.append('<polyline class="wl" points="%s"/>' % pts(walk))
    sx, sy = walk[0]
    out.append('<circle class="wla" cx="%s" cy="%s" r="4"/>' % (fmt(sx), fmt(sy)))
    ex, ey = walk[-1]
    out.append(poly("wla", [(ex + 9, ey), (ex - 3, ey - 7), (ex - 3, ey + 7)]))
    return out


def outer_walls(openings, top_kind="we", bottom_kind="we"):
    x0, x1 = -WL, IN_W + WR
    y0, y1 = -WT, IN_H + WB

    def split(a, b, ops):
        segs, cur = [], a
        for f, t, *_ in sorted(ops):
            segs.append((cur, f))
            cur = t
        segs.append((cur, b))
        return [(s, e) for s, e in segs if e - s > 0.1]

    walls = []
    for s, e in split(x0, x1, openings.get("top", [])):
        walls.append(poly(top_kind, rect(s, y0, e, 0)))
    for s, e in split(x0, x1, openings.get("bottom", [])):
        walls.append(poly(bottom_kind, rect(s, IN_H, e, y1)))
    for s, e in split(0, IN_H, openings.get("right", [])):
        walls.append(poly("we", rect(IN_W, s, x1, e)))
    walls.append(poly("we", rect(x0, 0, 0, IN_H)))      # Haustrennwand

    elems = []
    for f, t, kind, *rest in openings.get("top", []):
        if kind == "door":
            elems.append(r("thr", f, y0, t, 0))
        else:
            elems += window_h(f, t, -WT / 2, kind=kind)
    for f, t, kind, *rest in openings.get("bottom", []):
        elems += window_h(f, t, IN_H + WB / 2, kind=kind)
    for f, t, kind, *rest in openings.get("right", []):
        elems += window_v(f, t, IN_W + WR / 2, kind=kind)
    return walls, elems


def opening_rect(side, a, b):
    """Rectangle of an exterior opening (whole wall thickness)."""
    if side == "top":
        return rect(a, -WT, b, 0)
    if side == "bottom":
        return rect(a, IN_H, b, IN_H + WB)
    return rect(IN_W, a, IN_W + WR, b)


# --------------------------------------------------------------------------
# Outdoor area: side garden along the Seitentuer wall and the main garden
# behind the terrace, both enclosed by a Photinia (Glanzmispel) hedge.
# Terrace size is from the plan; the rest is schematic (photos and a sketch).
# Back boundary, from the neighbour side to the side hedge: Gartenhaus, gate,
# a short piece of hedge, then Stromkasten with a pallet bed in front of it.
# --------------------------------------------------------------------------
TER_Y1 = 1493                      # terrace 5.20 x 3.05 m (15,84 m2)
SIDE_X0, SIDE_X1 = 545, 690        # side garden lawn (gravel strip 500.5..545)
HEDGE_X1 = 770                     # outer edge of the side hedge
BACK_Y1 = 1985                     # back boundary
SHED = (-12, 1747, 200, BACK_Y1)   # Gartenhaus in the corner at the neighbour side
BED = (-12, 200, 1623, 1747)       # D-shaped bed in front of the shed: x0, x1, tip y, shed y
GATE = (200, 327)                  # garden gate in the back boundary
BACK_HEDGE = (327, 1885, 498, BACK_Y1)
POWER = (498, 1936, SIDE_X1, BACK_Y1)   # Stromkasten
PALLET = (498, 1885, SIDE_X1, 1936)     # Palettenbeet in front of it
# 6 spots at the foot of the side hedge, along its whole length (front hedge
# to the pallet bed at the back)
HEDGE_SPOTS = [(682, y) for y in (255, 550, 850, 1145, 1440, 1735)]
FACADE_SPOTS = {"light.gartenspot": (520, 288.5), "light.gartenspot_2": (520, 1020)}
GARDEN = [(500.5, -36.5), (HEDGE_X1, -36.5), (HEDGE_X1, BACK_Y1), (-12, BACK_Y1),
          (-12, 1186.5), (500.5, 1186.5)]


HOUSE = rect(-WL, -WT, IN_W + WR, IN_H + WB)   # outer footprint
TERRACE = (-19, 1186.5, 500.5, TER_Y1)
GARDEN_PATH = "/dashboard-grundriss-garten/garten"
EG_PATH = "/dashboard-grundriss/eg"


def hedge(x0, y0, x1, y1):
    return r("hde", x0, y0, x1, y1, 16)


def surroundings():
    """Terrace and entrance path around the ground floor."""
    return [poly("", rect(*TERRACE), ' fill="url(#stone)"'),
            poly("", rect(100, -150, 240, -36.5), ' fill="url(#stone)"')]


def outdoor(detail=True):
    s = [
        poly("", GARDEN, ' fill="url(#lawn)"'),
        poly("", rect(500.5, -36.5, SIDE_X0, 1186.5), ' fill="url(#gravel)"'),
        poly("", rect(*TERRACE), ' fill="url(#stone)"'),
        poly("", rect(100, -150, 240, -36.5), ' fill="url(#stone)"'),
        r("gt", -19, 1186.5, -12, BACK_Y1),                     # privacy screens to the neighbour
        hedge(SIDE_X1, 30, HEDGE_X1, BACK_Y1),                  # side hedge
        hedge(548, 30, SIDE_X1 + 10, 110),                      # front hedge
        hedge(*BACK_HEDGE),
        r("gt", GATE[0], BACK_Y1 - 24, GATE[0] + 8, BACK_Y1),   # gate posts
        r("gt", GATE[1] - 8, BACK_Y1 - 24, GATE[1], BACK_Y1),
    ]
    s += door(GATE[0] + 8, BACK_Y1 - 12, GATE[1] - GATE[0] - 16, 0, 270)
    s += ['<g filter="url(#fs)">', r("gh", *SHED, 3), r("fx", *POWER, 3), "</g>",
          r("ghl", SHED[0] + 7, SHED[1] + 7, SHED[2] - 7, SHED[3] - 7, 2)]
    # pallet bed: soil in a wooden frame, boards along its length
    x0, y0, x1, y1 = PALLET
    s.append(r("bd", *PALLET, 3))
    s += [line("stl", x0 + 4, y, x1 - 4, y) for y in (y0 + 17, y0 + 34)]
    # D-shaped bed, flat side on the shed
    bx0, bx1, tip, flat = BED
    cx, ry = (bx0 + bx1) / 2, 82
    s.append('<path class="bd" d="M%s,%sL%s,%sA%s,%s 0 0 1 %s,%sA%s,%s 0 0 1 %s,%sL%s,%sZ"/>' % (
        fmt(bx0), fmt(flat), fmt(bx0), fmt(tip + ry), fmt(cx - bx0), ry, fmt(cx), fmt(tip),
        fmt(bx1 - cx), ry, fmt(bx1), fmt(tip + ry), fmt(bx1), fmt(flat)))
    for x, y, rad, col in ((30, 1720, 16, "#5d8f45"), (75, 1698, 13, "#e2508c"), (120, 1725, 15, "#6f9e52"),
                           (165, 1705, 12, "#b04ad9"), (60, 1665, 11, "#9a8be0"), (110, 1655, 14, "#5d8f45"),
                           (150, 1675, 10, "#f3f0e6"), (15, 1690, 9, "#5b8def"), (95, 1735, 8, "#f5c04a")):
        s.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (x, y, rad, col))
    if detail:
        for x, y in HEDGE_SPOTS + list(FACADE_SPOTS.values()):
            s.append('<circle class="spt" cx="%s" cy="%s" r="%s"/>' % (fmt(x), fmt(y), SPOT_R))
    return s


# --------------------------------------------------------------------------
# Lamps (drawn into the plan; lit version lives in the glow overlay)
# --------------------------------------------------------------------------
SPOT_R = 11
LAMP_ON, LAMP_ON_EDGE, LAMP_CORE = "#ffd54f", "#f0a800", "#fff7d6"
HEART = "M0 13C-20 0 -17 -15 -8.5 -15C-3.5 -15 0 -11 0 -8C0 -11 3.5 -15 8.5 -15C17 -15 20 0 0 13Z"


def lamp_kind(l):
    """Light tuple: (entity, x, y, glow x, glow y, glow radius, rooms[, kind]); kind defaults to a ceiling lamp."""
    return l[7] if len(l) > 7 else ("round", 17)


def lamp_box(l):
    x, y = l[1], l[2]
    k = lamp_kind(l)
    if k[0] == "strip":
        return min(k[1], k[3]), min(k[2], k[4]), max(k[1], k[3]), max(k[2], k[4])
    if k[0] == "spots":
        return bbox([k[1]])
    return x, y, x, y


def halo(x, y, rad):
    return ("<radialGradient id='lh'><stop offset='.35' stop-color='#ffe9a8' stop-opacity='.95'/>"
            "<stop offset='1' stop-color='#ffe9a8' stop-opacity='0'/></radialGradient>"
            "<circle cx='%s' cy='%s' r='%s' fill='url(#lh)'/>" % (fmt(x), fmt(y), fmt(rad)))


def lit_spot(x, y):
    return (halo(x, y, SPOT_R * 2.6)
            + "<circle cx='%s' cy='%s' r='%s' fill='%s' stroke='%s' stroke-width='2.5'/>" % (
                fmt(x), fmt(y), SPOT_R, LAMP_ON, LAMP_ON_EDGE)
            + "<circle cx='%s' cy='%s' r='%s' fill='%s'/>" % (fmt(x), fmt(y), fmt(SPOT_R * .45), LAMP_CORE))


def lamp_svg(l, lit=False):
    """Lamp symbol at its place in the plan: grey when off, yellow and glowing when lit."""
    x, y = l[1], l[2]
    k = lamp_kind(l)
    if k[0] in ("spot", "spots"):                # garden spots are drawn by outdoor(), lit ones by the glow
        return ""
    if k[0] == "strip":
        x1, y1, x2, y2 = (fmt(v) for v in k[1:5])
        if not lit:
            seg = 'x1="%s" y1="%s" x2="%s" y2="%s"/>' % (x1, y1, x2, y2)
            return '<line class="lps" ' + seg + '<line class="lpc" ' + seg
        seg = "<line x1='%s' y1='%s' x2='%s' y2='%s' stroke-linecap='round' " % (x1, y1, x2, y2)
        return (seg + "stroke='#ffe082' stroke-opacity='.55' stroke-width='22'/>"
                + seg + "stroke='%s' stroke-width='9'/>" % LAMP_ON_EDGE
                + seg + "stroke='%s' stroke-width='6'/>" % LAMP_ON
                + seg + "stroke='%s' stroke-width='2.5'/>" % LAMP_CORE)
    if k[0] == "heart":
        g = '<g transform="translate(%s %s) rotate(-90)">' % (fmt(x), fmt(y))
        if not lit:
            return g + '<path class="lp" d="%s" filter="url(#fs)"/></g>' % HEART
        return (halo(x, y, 34) + g.replace('"', "'")
                + "<path d='%s' fill='%s' stroke='%s' stroke-width='2'/></g>" % (HEART, LAMP_ON, LAMP_ON_EDGE))
    rad = k[1]
    c = (fmt(x), fmt(y))
    if not lit:
        return ('<circle class="lp" cx="%s" cy="%s" r="%s" filter="url(#fs)"/>' % (*c, rad)
                + '<circle class="lpi" cx="%s" cy="%s" r="%s"/>' % (*c, fmt(rad * .55)))
    return (halo(x, y, rad * 2.3)
            + "<circle cx='%s' cy='%s' r='%s' fill='%s' stroke='%s' stroke-width='2'/>" % (*c, rad, LAMP_ON, LAMP_ON_EDGE)
            + "<circle cx='%s' cy='%s' r='%s' fill='%s'/>" % (*c, fmt(rad * .55), LAMP_CORE))


# --------------------------------------------------------------------------
# Floor definitions
# --------------------------------------------------------------------------
def eg():
    rooms = {
        "diele": [(0, 0), (231, 0), (231, 190), (214, 211), (144, 285), (26, 167), (0, 167)],
        "wc": [(0, 175), (26, 175), (140, 289), (140, 380), (0, 380)],
        "kueche": [(239, 0), (464, 0), (464, 420), (148, 420), (148, 289), (214, 211), (239, 190)],
        "treppe": rect(0, 392.5, 92, 717.5),
        "ess": [(100, 388), (148, 388), (148, 420), (464, 420), (464, 732.5), (100, 732.5)],
        "wohn": rect(0, 732.5, 464, 1150),
        "terrasse": rect(*TERRACE),
    }
    openings = {
        "top": [(112.5, 226.5, "door"), (301.5, 401.5, "window")],
        "bottom": [(85, 375.5, "slide")],
        "right": [(613.5, 853.5, "window")],
    }
    walls_in = [
        rect(231, 0, 239, 190),
        thick((235, 188), (213, 210), 8),
        rect(0, 167, 30, 175),
        thick((26, 171), (76, 221), 8),
        thick((133, 278), (144, 289), 8),
        rect(140, 285, 148, 388),
        rect(100, 380, 148, 388),
        rect(0, 377.5, 100, 392.5),
        rect(92, 478, 100, 628),
        rect(0, 717.5, 100, 732.5),
    ]
    under = surroundings() + [poly("", rect(0, 0, IN_W, IN_H), ' fill="url(#t60)"')]
    fixtures = [
        '<g filter="url(#fs)">',
        r("cab", 239, 0, 299, 190),
        r("ct", 404, 0, 464, 309),
        r("ct", 239, 309, 464, 415),
        "</g>",
        line("ckr", 239, 63, 299, 63), line("ckr", 239, 126, 299, 126),
        line("ckr", 404, 60, 464, 60),
        r("sk", 411, 136, 457, 184, 6), r("sk", 411, 190, 457, 224, 6),
        '<circle class="sk" cx="452" cy="187" r="3"/>',
        r("ck", 301, 318, 362, 368, 4),
        '<circle class="ckr" cx="316" cy="332" r="9"/><circle class="ckr" cx="346" cy="331" r="11"/>'
        '<circle class="ckr" cx="317" cy="355" r="10"/><circle class="ckr" cx="347" cy="356" r="8"/>',
        toilet(0, 338, -90),
    ]
    doors = [
        door(226.5, 0, 100, 180, 90),             # Haustür
        door(133, 278, 80, 225, 315),             # WC
    ]
    labels = [
        ("Diele", "5,26 m²", 35, 95),
        ("WC", "2,17 m²", 45, 270),
        ("Küche", "8,50 m²", 318, 235),
        ("Essen", None, 215, 556),
        ("Wohnzimmer", "Wohnen/Essen 35,17 m²", 175, 840),
        ("Terrasse", "15,84 m²", 195, 1340),
    ]
    # little room on the entrance side: written vertically along the edge
    texts = [("ra", 170, -51, "Eingang", "middle", 90)]
    entities = {
        "lights": [
            # entity, chip x/y, glow x/y, radius, clip rooms
            ("light.deckenlampe_light", 138, 100, 115, 92, 220, ["diele"]),
            ("light.schalter_gaste_wc_schalter_gaste_wc", 104, 330, 70, 300, 170, ["wc"]),
            ("light.kuche_deckenlampe", 325, 116, 349, 161, 270, ["kueche"]),
            ("light.arbeitsplatte_light", 459, 156, 434, 160, 190, ["kueche"], ("strip", 459, 14, 459, 298)),
            ("light.barlampe", 349, 393, 349, 393, 210, ["kueche", "ess"]),
            ("light.esszimmer_oben_light", 305, 556, 349, 556, 260, ["ess"]),
            ("light.esszimmer_unten_light", 385, 556, 349, 556, 230, ["ess"]),
            ("light.treppenhaus_eg_treppenhaus_eg", 60, 506, 81, 514, 190, ["treppe"]),
            ("light.wandlampe_light", 44, 655, 44, 655, 120, ["treppe"], ("round", 12)),
            ("light.deckenlampe_wohnzimmer_light", 300, 941, 238, 941, 320, ["wohn"]),
            ("light.stehlampe", 52, 1098, 52, 1098, 210, ["wohn"], ("round", 13)),
        ],
        # the whole terrace is an invisible button to the garden view
        "buttons": [(TERRACE, GARDEN_PATH)],
        "covers": [
            ("cover.rollladen_kuche", "top", 301.5, 401.5),
            ("cover.rollladen_seitentur", "right", 613.5, 853.5),
            ("cover.rollladen_terrassentur", "bottom", 85, 375.5),
        ],
        "contacts": [
            ("binary_sensor.fenstersensor_kuche_opening", "top", 301.5, 401.5),
            ("binary_sensor.tursensor_seitentur_opening", "right", 613.5, 853.5),
            ("binary_sensor.tursensor_terassentur_opening", "bottom", 85, 375.5),
        ],
        "motion": [
            ("binary_sensor.bewegungsmelder_diele", ["diele"]),
            ("binary_sensor.bewegungsmelder_gaste_wc_belegung", ["wc"]),
            ("binary_sensor.bewegungsmelder_esszimmer_belegung", ["ess"]),
            ("binary_sensor.bewegungsmelder_treppenhaus_eg_belegung", ["treppe"]),
            ("binary_sensor.bewegungsmelder_technikraum", ["treppe"]),
        ],
        "climate": [
            ("sensor.tado_smart_thermostat_ru4163584512_current_temperature",
             "sensor.tado_smart_thermostat_ru4163584512_current_humidity", 78, 95),
            ("sensor.tado_smart_thermostat_ru2167095808_current_temperature",
             "sensor.tado_smart_thermostat_ru2167095808_current_humidity", 360, 235),
            ("sensor.tado_smart_thermostat_ru1244545536_current_temperature",
             "sensor.tado_smart_thermostat_ru1244545536_current_humidity", 222, 840),
            ("sensor.eve_weather_20ebs9901_temperatur", None, 250, 1340),
        ],
        "lock": ("lock.haustur", "top", 112.5, 226.5),
    }
    return dict(key="eg", title="Erdgeschoss", viewbox=HOUSE_VB, rooms=rooms,
                openings=openings, walls_in=walls_in, under=under, fixtures=fixtures,
                stair=(0, 392.5, 92, 717.5), doors=doors, labels=labels, texts=texts, extras=[],
                entities=entities)


def og():
    rooms = {
        "buero": [(0, 0), (464, 0), (464, 359.5), (208, 359.5), (208, 377), (0, 377)],
        "flur": rect(100, 385, 208, 724),
        "treppe": rect(0, 392.5, 92, 717.5),
        "bad": rect(216, 367.5, 464, 671),
        "hwr": rect(216, 679, 464, 823.5),
        "schlaf": [(0, 732.5), (208, 732.5), (208, 831.5), (464, 831.5), (464, 1150), (0, 1150)],
    }
    openings = {
        "top": [(110, 400.5, "window")],
        "bottom": [(85, 375.5, "window")],
        "right": [(387.5, 467.5, "window")],
    }
    walls_in = [
        rect(208, 359.5, 464, 367.5),
        rect(0, 377, 100, 392.5), rect(100, 377, 110, 385), rect(199, 377, 208, 385),
        rect(208, 359.5, 216, 527), rect(208, 603, 216, 831.5),
        rect(216, 671, 232, 679), rect(308, 671, 464, 679),
        rect(216, 823.5, 464, 831.5),
        rect(0, 717.5, 100, 732.5), rect(100, 724, 110, 732.5), rect(198, 724, 208, 732.5),
        rect(92, 483, 100, 627),
    ]
    under = [                                     # upper floor: no ground around the house
        poly("", rooms["buero"], ' fill="url(#wood)"'),
        poly("", rect(92, 377, 208, 732.5), ' fill="url(#wood)"'),
        poly("", rooms["schlaf"], ' fill="url(#wood)"'),
        poly("", rect(216, 359.5, 464, 831.5), ' fill="url(#t60d)"'),   # bath + HWR: anthracite 60x60
        walkin(340, 527, 436, 671, 340, 571, (388, 612), (418, 648)),
    ]
    fixtures = [
        r("vw", 216, 367.5, 464, 387),
        toilet(268, 387, 0),
        basin(367, 387, 0, 62, 46),
        '<rect x="436" y="513" width="28" height="94" fill="url(#hatch)"/>' + r("hl", 436, 513, 464, 607),
        washer(398, 690),
        washer(398, 755),
    ] + buero_moebel()
    doors = [
        door(199, 381, 89, 180, 270),     # Büro
        door(216, 527, 76, 90, 0),        # Bad
        door(232, 675, 76, 0, 90),        # HWR (vom Bad)
        door(198, 728, 88, 180, 90),      # Schlafzimmer
    ]
    labels = [
        ("Philipps Büro", "17,08 m²", 125, 189),
        ("Flur", "3,63 m²", 155, 450),
        ("Bad", "6,25 m²", 262, 488, "rnw"),
        ("HWR", "3,70 m²", 290, 784, "rnw"),
        ("Schlafzimmer", "16,87 m²", 115, 890),
    ]
    entities = {
        "lights": [
            ("light.deckenlampe_philipps_buro", 232, 189, 231, 189, 320, ["buero"]),
            ("light.liane_light", 46, 555, 46, 555, 230, ["treppe", "flur"]),
            ("light.spiegel_spiegel", 367, 373, 367, 400, 210, ["bad"], ("strip", 340, 373, 394, 373)),
            ("light.hwr_deckenlampe", 340, 749, 340, 749, 200, ["hwr"]),
            ("light.schlafzimmer_deckenlampe", 232, 991, 232, 991, 320, ["schlaf"]),
            ("light.nachttischlampe_laura", 78, 1000, 78, 1000, 150, ["schlaf"], ("round", 12)),
            ("light.nachttischlampe_philipp", 386, 1000, 386, 1000, 150, ["schlaf"], ("round", 12)),
            ("light.herzlampe", 232, 1082, 232, 1082, 150, ["schlaf"], ("heart",)),
        ],
        "covers": [
            ("cover.rollladen_philipps_buro", "top", 110, 400.5),
            ("cover.rollladen_bad_1_og", "right", 387.5, 467.5),
            ("cover.rollladen_schlafzimmer", "bottom", 85, 375.5),
        ],
        "contacts": [
            ("binary_sensor.fenstersensor_philipps_buro_opening", "top", 110, 400.5),
            ("binary_sensor.fenstersensor_bad_1_og_opening", "right", 387.5, 467.5),
            ("binary_sensor.fenstersensor_schlafzimmer_opening", "bottom", 85, 375.5),
        ],
        "motion": [
            ("binary_sensor.bewegungsmelder_hwr_belegung", ["hwr"]),
        ],
        "devices": buero_geraete(),
        "climate": [
            ("sensor.tado_smart_thermostat_ru3678551808_current_temperature",
             "sensor.tado_smart_thermostat_ru3678551808_current_humidity", 170, 189),
            ("sensor.tado_smart_thermostat_ru2720481792_current_temperature",
             "sensor.tado_smart_thermostat_ru2720481792_current_humidity", 312, 490),
            ("sensor.tado_smart_thermostat_ru3532674816_current_temperature",
             "sensor.tado_smart_thermostat_ru3532674816_current_humidity", 162, 890),
        ],
    }
    return dict(key="og", title="1. Obergeschoss", viewbox=UPPER_VB, rooms=rooms,
                openings=openings, walls_in=walls_in, under=under, fixtures=fixtures,
                stair=(0, 392.5, 92, 717.5), doors=doors, labels=labels, texts=[], extras=[],
                entities=entities)


def dg():
    rooms = {
        "laura": rect(0, 0, 464, 384.5),
        "flur": rect(100, 392.5, 208, 717.5),
        "treppe": rect(0, 392.5, 92, 717.5),
        "abst": rect(216, 392.5, 464, 505.5),
        "bad": rect(216, 513.5, 464, 717.5),
        "sport": rect(0, 725.5, 464, 1150),
        "luke": rect(125, 547, 191, 664),
    }
    openings = {
        "top": [(242, 356, "window")],
        "bottom": [(242, 356, "window")],
        "right": [(637.5, 717.5, "window")],
    }
    walls_in = [
        rect(0, 384.5, 111, 392.5), rect(199, 384.5, 464, 392.5),
        rect(0, 717.5, 111, 725.5), rect(199, 717.5, 464, 725.5),
        rect(208, 392.5, 216, 409), rect(208, 489, 216, 526), rect(208, 606, 216, 717.5),
        rect(216, 505.5, 464, 513.5),
    ]
    under = [                                     # upper floor: no ground around the house
        poly("", rooms["laura"], ' fill="url(#wood)"'),
        poly("", rooms["sport"], ' fill="url(#wood)"'),
        poly("", rect(92, 384.5, 216, 725.5), ' fill="url(#wood)"'),
        poly("", rooms["abst"], ' fill="url(#wood)"'),
        poly("", rect(216, 505.5, 464, 717.5), ' fill="url(#t60d)"'),   # anthracite 60x60
    ]
    extras = [
        # Dachschräge (lichte Höhe < 1 m) und Linie lichte Höhe 2,00 m
        poly("hz", rect(0, 0, 242, 58)), poly("hz", rect(356, 0, 464, 58)),
        poly("hz", rect(0, 1092, 242, 1150)), poly("hz", rect(356, 1092, 464, 1150)),
        line("lh", 0, 206, 464, 206), line("lh", 0, 941, 464, 941),
        # Dachflächenfenster (Projektion)
        r("rw", 125, 92, 199, 206, 3), r("rw", 125, 941, 199, 1055, 3),
        # Spitzboden-Luke
        r("sp", 125, 547, 191, 664, 2),
        line("hl", 133, 565, 183, 565), line("hl", 133, 585, 183, 585), line("hl", 133, 605, 183, 605),
        line("hl", 133, 625, 183, 625), line("hl", 133, 645, 183, 645),
    ]
    fixtures = [
        toilet(254, 717.5, 180),
        bathtub(296, 643, 462, 712),
        basin(464, 572, 90, 60, 44),
        r("wi", 92, 392.5, 100, 717.5),        # Geländer (GK ummauert)
    ]
    doors = [
        door(111, 388, 88, 0, 270),       # Lauras Büro
        door(216, 489, 78, 270, 0),       # Abstellraum
        door(216, 606, 78, 270, 0),       # Bad
        door(111, 721, 88, 0, 90),        # Sportzimmer
    ]
    labels = [
        ("Lauras Büro", "11,79 m²", 318, 290),
        ("Flur", "3,67 m²", 150, 440),
        ("Abstellraum", "2,50 m²", 352, 449, "rn2"),
        ("Bad", "4,64 m²", 325, 560, "rnw"),
        ("Sportzimmer", "13,65 m²", 300, 830),
    ]
    texts = [
        # lichte Höhe 2,00 m, written on the low-ceiling side of the line
        ("rs", 24, 200, "LH 2,00 m", "start"),
        ("rs", 24, 947, "LH 2,00 m", "end"),
        ("rs", 204, 605, "Spitzboden", "middle"),
    ]
    entities = {
        "lights": [
            ("light.lauras_buro_deckenlampe", 232, 253, 232, 253, 320, ["laura"]),
            ("light.schreibtisch", 420, 345, 420, 330, 170, ["laura"], ("round", 12)),
            ("light.deckenlampe_treppenhaus", 150, 505, 150, 520, 230, ["flur", "treppe"]),
            ("light.dachboden_deckenlampe_dachboden", 158, 606, 158, 606, 70, ["luke"], ("round", 11)),
            ("light.deckenlampe_sportzimmer_light_2", 232, 897, 232, 897, 320, ["sport"]),
        ],
        "covers": [
            ("cover.lauras_buro_gross_2", "top", 242, 356),
            ("cover.lauras_buro_klein_2", "roof", 125, 92, 199, 206),
            ("cover.sportzimmer_gross_2", "bottom", 242, 356),
            ("cover.sportzimmer_klein_2", "roof", 125, 941, 199, 1055),
        ],
        "contacts": [
            ("binary_sensor.fenster_lauras_buro", "top", 242, 356),
            ("binary_sensor.fenster_sportzimmer", "bottom", 242, 356),
            ("binary_sensor.fenstersensor_bad_dg_opening", "right", 637.5, 717.5),
            ("binary_sensor.dachboden_dachbodentur_tur", "area", 125, 547, 191, 664),
        ],
        "motion": [
            ("binary_sensor.treppenhaus_bewegungsmelder_treppenhaus_dg_belegung", ["flur", "treppe"]),
        ],
        "climate": [
            ("sensor.tado_smart_thermostat_ru0690373120_current_temperature",
             "sensor.tado_smart_thermostat_ru0690373120_current_humidity", 362, 290),
            ("sensor.tado_smart_thermostat_ru0673595904_current_temperature",
             "sensor.tado_smart_thermostat_ru0673595904_current_humidity", 372, 580),
            ("sensor.tado_smart_thermostat_ru0630216448_current_temperature",
             "sensor.tado_smart_thermostat_ru0630216448_current_humidity", 345, 830),
        ],
    }
    return dict(key="dg", title="Dachgeschoss", viewbox=UPPER_VB, rooms=rooms,
                openings=openings, walls_in=walls_in, under=under, fixtures=fixtures,
                stair=(0, 392.5, 92, 717.5), doors=doors, labels=labels, texts=texts, extras=extras,
                entities=entities)


# Roof, from the aerial photos: gable roof with the ridge across the row
# (parallel to the street, eaves at the front and the garden side), black
# in-roof solar tiles, two roof windows per slope (Lauras Büro / Sportzimmer:
# small one higher up as in the DG plan, large one near the eave) and two
# vents just below the ridge on the street side, towards the free gable.
RIDGE_Y = (HOUSE[0][1] + HOUSE[2][1]) / 2
ROOF_WINDOWS = [(125, 92, 199, 206), (242, -10, 356, 95), (125, 941, 199, 1055), (242, 1055, 356, 1160)]
ROOF_VENTS = [(352, 490, 378, 512), (352, 525, 378, 547)]


def rf(fill, x0, y0, x1, y1, rx=0, extra=""):
    """Rectangle with an inline fill (the roof looks the same in light and dark mode)."""
    return '<rect x="%s" y="%s" width="%s" height="%s"%s fill="%s"%s/>' % (
        fmt(x0), fmt(y0), fmt(x1 - x0), fmt(y1 - y0), ' rx="%s"' % fmt(rx) if rx else "", fill, extra)


def roof():
    x0, y0, x1, y1 = bbox([HOUSE])
    pw = (x1 - x0) / 9                        # 9 columns of solar tiles across the roof
    s = ['<defs><pattern id="pv" x="%s" y="%s" width="%s" height="66" patternUnits="userSpaceOnUse">'
         '<rect width="%s" height="66" fill="#1e232b"/>'
         '<path d="M0 1H%sM1 0V66" stroke="#39404b" stroke-width="2" fill="none"/>'
         '<path d="M4 5H%s" stroke="#2a3039" stroke-width="2" fill="none"/></pattern>'
         '<linearGradient id="sky" x2="1" y2="1"><stop offset="0" stop-color="#dcebf7"/>'
         '<stop offset="1" stop-color="#7ea5cb"/></linearGradient></defs>' % (
             fmt(x0), fmt(y0), fmt(pw), fmt(pw), fmt(pw), fmt(pw - 4)),
         '<g filter="url(#sh)">', poly("", HOUSE, ' fill="url(#pv)"'), "</g>",
         rf("#000", x0, y0, x1, RIDGE_Y, extra=' fill-opacity=".2"'),          # street side in shade
         rf("#fff", x0, RIDGE_Y, x1, y1, extra=' fill-opacity=".05"'),
         rf("#8b939d", x0, y0, x1, y0 + 8), rf("#8b939d", x0, y1 - 8, x1, y1),  # gutters
         rf("#2c323b", x1 - 8, y0, x1, y1), rf("#4b5461", x0, y0, x0 + 4, y1),  # verge / party wall
         rf("#2c323b", x0, RIDGE_Y - 7, x1, RIDGE_Y + 7),                       # ridge cap
         line("", x0, RIDGE_Y, x1, RIDGE_Y).replace("/>", ' stroke="#4f5865" stroke-width="1.5"/>')]
    for a, b, c, d in ROOF_WINDOWS:
        s += ['<g filter="url(#fs)">', rf("#9aa2ac", a, b, c, d, 3), "</g>",
              rf("url(#sky)", a + 6, b + 6, c - 6, d - 6, 2),
              '<path d="M%s %sL%s %s" stroke="#fff" stroke-opacity=".55" stroke-width="5" stroke-linecap="round"/>' % (
                  fmt(a + 16), fmt(d - 22), fmt(a + (c - a) * .55), fmt(b + 16))]
    for a, b, c, d in ROOF_VENTS:
        s += ['<g filter="url(#fs)">', rf("#121519", a, b, c, d, 3), "</g>", rf("#2f353e", a + 3, b + 3, c - 3, b + 9, 2)]
    return s


def garten():
    """The whole property. The house is shown from above (roof) and leads back
    to the EG; only the garden devices are interactive."""
    under = outdoor() + roof()
    cx = (HOUSE[0][0] + HOUSE[2][0]) / 2
    labels = [
        ("Haus", None, cx + 12, 380, "gnw"),
        ("Terrasse", None, 205, 1340, "gn2"),
        ("Seitengarten", None, 622, 530, "gn2"),
        ("Garten", None, 430, 1690, "gn"),
    ]
    texts = [("gs", 170, -88, "Eingang", "middle"),
             ("gsw", (SHED[0] + SHED[2]) / 2 + 7, (SHED[1] + SHED[3]) / 2, "Gartenhaus", "middle"),
             ("gs", 300, 1815, "Gartentür", "middle"),
             # narrow strips along the back boundary: written vertically, as in the sketch
             ("gs", (POWER[0] + POWER[2]) / 2, (POWER[1] + POWER[3]) / 2 + 7.5, "Stromkasten", "middle", 90),
             ("gsw", (PALLET[0] + PALLET[2]) / 2, (PALLET[1] + PALLET[3]) / 2 + 7.5, "Palettenbeet", "middle", 90)]
    entities = {
        "lights": [
            # lamps only, the glows are custom (see "glows")
            ("light.gartenspot", *FACADE_SPOTS["light.gartenspot"], None, None, None, None, ("spot",)),
            ("light.gartenspot_2", *FACADE_SPOTS["light.gartenspot_2"], None, None, None, None, ("spot",)),
            ("light.garten_garten_controller", 682, 995, None, None, None, None, ("spots", HEDGE_SPOTS)),
        ],
        "glows": [(e, facade_glow_svg(*xy), facade_glow_box(*xy)) for e, xy in FACADE_SPOTS.items()]
        + [("light.garten_garten_controller", spots_glow_svg(HEDGE_SPOTS, 100), spots_glow_box(HEDGE_SPOTS, 100))],
        "motion": [("binary_sensor.outdoor_kamera_person", ["garten"])],
        "climate": [("sensor.eve_weather_20ebs9901_temperatur", None, 290, 1340)],
        "buttons": [(bbox([HOUSE]), EG_PATH)],
    }
    tiles = [
        ("light.garten_garten_controller", "Heckenspots", "mdi:spotlight-beam"),
        ("light.gartenspot", "Fassade vorne", "mdi:light-flood-up"),
        ("light.gartenspot_2", "Fassade hinten", "mdi:light-flood-up"),
    ]
    cards = [{"type": "grid", "columns": 4, "square": False, "cards": [
        {"type": "tile", "entity": e, "name": n, "icon": i, "features": [{"type": "light-brightness"}]}
        for e, n, i in tiles] + [
        {"type": "tile", "entity": "sensor.eve_weather_20ebs9901_temperatur", "name": "Außentemperatur"}]}]
    return dict(key="garten", title="Garten", viewbox=VIEWBOX, rooms={"garten": GARDEN},
                openings=None, walls_in=[], under=under, fixtures=[], stair=None, doors=[],
                labels=labels, texts=texts, extras=[], entities=entities, cards=cards)




# --------------------------------------------------------------------------
# SVG assembly
# --------------------------------------------------------------------------
def build_svg(fl, force_dark=False):
    vb = " ".join(fmt(v) for v in scr_viewbox(*fl["viewbox"]))
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s">' % vb,
           "<defs><style>%s</style>%s</defs>" % (css(force_dark), DEFS),
           '<g transform="rotate(90)">']
    out += fl["under"]
    if fl["stair"]:
        out += stair(*fl["stair"])
    out += fl["extras"]
    out += fl["fixtures"]
    if fl["openings"] is not None:                # garden view: no walls, the house is one block
        walls, win = outer_walls(fl["openings"])
        out.append('<g filter="url(#sh)">')
        out += walls
        out += [poly("wi", p) for p in fl["walls_in"]]
        out.append("</g>")
        out += win
    out += fl["doors"]
    out += [lamp_svg(l) for l in fl["entities"]["lights"]]
    out.append("</g>")
    # texts stay upright: placed at the rotated position, not rotated themselves
    for name, area, x, y, *cls in fl["labels"]:
        sx, sy = scr(x, y)
        out.append(text(cls[0] if cls else "rn", sx, sy, name))
        if area:
            out.append(text("raw" if cls and cls[0] == "rnw" else "ra", sx, sy + 20, area))
    for cls, x, y, s, anchor, *rot in fl["texts"]:
        sx, sy = scr(x, y)
        extra = "" if anchor == "middle" else ' style="text-anchor:%s"' % anchor
        if rot:
            extra += ' transform="rotate(%s %s %s)"' % (rot[0], fmt(sx), fmt(sy))
        out.append('<text class="%s" x="%s" y="%s"%s>%s</text>' % (cls, fmt(sx), fmt(sy), extra, s))
    out.append("</svg>")
    return "".join(out)


def data_uri(svg):
    # Modern browsers only need '%' and '#' escaped inside an SVG data URI.
    svg = svg.replace('"', "'").replace("%", "%25").replace("#", "%23")
    return "data:image/svg+xml;charset=utf-8," + svg


# --------------------------------------------------------------------------
# Overlays (state dependent images)
# --------------------------------------------------------------------------
def overlay_box(polys, pad=0):
    x0, y0, x1, y1 = bbox(polys)
    return x0 - pad, y0 - pad, x1 + pad, y1 + pad


def svg_head(box):
    """Overlay header: view box of the rotated plan box, content in plan coordinates."""
    x0, y0, x1, y1 = scr_box(*box)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s %s %s %s"><g transform="rotate(90)">' % (
        fmt(x0), fmt(y0), fmt(x1 - x0), fmt(y1 - y0)))


SVG_TAIL = "</g></svg>"


def glow_svg(clips, gx, gy, rad, lamp=""):
    """Warm light cone around the lamp, limited to the room polygon(s), plus the lit lamp itself."""
    box = overlay_box(clips)
    stops = "".join("<stop offset='%s' stop-color='%s' stop-opacity='%s'/>" % (o, GLOW, a)
                    for o, a in (("0", ".72"), (".45", ".34"), ("1", "0")))
    return (svg_head(box)
            + "<radialGradient id='g' cx='%s' cy='%s' r='%s' gradientUnits='userSpaceOnUse'>%s</radialGradient>" % (
                fmt(gx), fmt(gy), fmt(rad), stops)
            + "".join("<polygon points='%s' fill='url(#g)'/>" % pts(p) for p in clips) + lamp + SVG_TAIL)


def _stops():
    return "".join("<stop offset='%s' stop-color='%s' stop-opacity='%s'/>" % (o, GLOW, a)
                   for o, a in (("0", ".72"), (".45", ".34"), ("1", "0")))


def facade_glow_box(x, y):
    return 490, y - 230, 500.5 + 110, y + 230


def facade_glow_svg(x, y):
    """Up-light on the facade: bright stripe on the wall face plus a soft glow on the ground."""
    return (svg_head(facade_glow_box(x, y))
            + "<radialGradient id='g'>%s</radialGradient>" % _stops()
            + "<linearGradient id='w' x2='0' y2='1'><stop offset='0' stop-color='#ffd27a' stop-opacity='0'/>"
              "<stop offset='.5' stop-color='#ffd27a'/><stop offset='1' stop-color='#ffd27a' stop-opacity='0'/>"
              "</linearGradient>"
            + "<ellipse cx='500.5' cy='%s' rx='105' ry='200' fill='url(#g)'/>" % fmt(y)
            + "<rect x='490' y='%s' width='10.5' height='400' fill='url(#w)'/>" % fmt(y - 200)
            + lit_spot(x, y) + SVG_TAIL)


def spots_glow_box(spots, rad):
    return overlay_box([[(x - rad, y - rad), (x + rad, y + rad)] for x, y in spots])


def spots_glow_svg(spots, rad):
    return (svg_head(spots_glow_box(spots, rad)) + "<radialGradient id='g'>%s</radialGradient>" % _stops()
            + "".join("<circle cx='%s' cy='%s' r='%s' fill='url(#g)'/>" % (fmt(x), fmt(y), rad) for x, y in spots)
            + "".join(lit_spot(x, y) for x, y in spots) + SVG_TAIL)


def motion_svg(clips):
    box = overlay_box(clips)
    body = "".join('<polygon points="%s"/>' % pts(p) for p in clips)
    return (svg_head(box) + '<g fill="#3b82f6" opacity=".1">%s'
            '<animate attributeName="opacity" values=".06;.24;.06" dur="2.4s" repeatCount="indefinite"/>'
            '</g>' % body + SVG_TAIL)


def contact_svg(p):
    box = overlay_box([p], 14)
    x0, y0, x1, y1 = bbox([p])
    return (svg_head(box)
            + '<defs><filter id="b" x="-50%%" y="-50%%" width="200%%" height="200%%">'
              '<feGaussianBlur stdDeviation="5"/></filter></defs>'
              '<g><rect x="%s" y="%s" width="%s" height="%s" rx="4" fill="#ef4444" filter="url(#b)" opacity=".9"/>'
              '<rect x="%s" y="%s" width="%s" height="%s" rx="3" fill="#ef4444"/>'
              '<animate attributeName="opacity" values="1;.55;1" dur="1.6s" repeatCount="indefinite"/></g>' % (
                fmt(x0), fmt(y0), fmt(x1 - x0), fmt(y1 - y0), fmt(x0 + 2), fmt(y0 + 2), fmt(x1 - x0 - 4), fmt(y1 - y0 - 4))
            + SVG_TAIL)


def shutter_svg(p, vertical):
    box = overlay_box([p])
    x0, y0, x1, y1 = box
    if vertical:
        lines = "".join('<path d="M%s %sV%s" stroke="#1f2937" stroke-opacity=".5" stroke-width="1.6"/>' % (
            fmt(x), fmt(y0), fmt(y1)) for x in frange(x0 + 4, x1, 5))
    else:
        lines = "".join('<path d="M%s %sH%s" stroke="#1f2937" stroke-opacity=".5" stroke-width="1.6"/>' % (
            fmt(x0), fmt(y), fmt(x1)) for y in frange(y0 + 4, y1, 5))
    return (svg_head(box) + '<rect x="%s" y="%s" width="%s" height="%s" rx="2" fill="#6b7280" fill-opacity=".92"/>%s' % (
        fmt(x0), fmt(y0), fmt(x1 - x0), fmt(y1 - y0), lines) + SVG_TAIL)


def frange(a, b, step):
    v = a
    while v < b - 0.5:
        yield v
        v += step


def lock_svg(p):
    return contact_svg(p)


FLOORS = [eg(), og(), dg(), garten()]


# --------------------------------------------------------------------------
# Dashboard elements
# --------------------------------------------------------------------------
def pct(fl, x, y):
    """Plan coordinates -> left/top in % of the (rotated) floorplan image."""
    vx, vy, vw, vh = scr_viewbox(*fl["viewbox"])
    sx, sy = scr(x, y)
    return "%s%%" % fmt((sx - vx) / vw * 100), "%s%%" % fmt((sy - vy) / vh * 100)


def place(fl, box):
    """Style for an overlay image covering box (x0,y0,x1,y1) in plan cm."""
    x0, y0, x1, y1 = box
    left, top = pct(fl, (x0 + x1) / 2, (y0 + y1) / 2)
    vw = scr_viewbox(*fl["viewbox"])[2]
    return {"left": left, "top": top, "width": "%s%%" % fmt((y1 - y0) / vw * 100), "pointer-events": "none"}


# Chips (40 px on the iPad) for covers and the lock.
CHIP = {
    "transform": "translate(-50%,-50%)",
    "--mdc-icon-size": "22px",
    "background-color": "var(--card-background-color)",
    "border-radius": "50%",
    "box-shadow": "0 1px 4px rgba(0,0,0,.3)",
}
PILL = {
    "background-color": "var(--card-background-color)",
    "border-radius": "9px",
    "padding": "1px 7px",
    "font-size": "11px",
    "font-weight": "600",
    "line-height": "16px",
    "white-space": "nowrap",
    "box-shadow": "0 1px 3px rgba(0,0,0,.25)",
}


def cond(entity, state=None, state_not=None):
    c = {"condition": "state", "entity": entity}
    if state is not None:
        c["state"] = state
    if state_not is not None:
        c["state_not"] = state_not
    return [c]


def overlay(conditions, svg, box):
    return {"type": "conditional", "conditions": conditions,
            "elements": [{"type": "image", "image": data_uri(svg), "style": {}}],
            "_box": box}


def opening_box(side, a, b, *rest):
    if side == "roof":
        return rect(a, b, rest[0], rest[1])
    if side == "area":
        return rect(a, b, rest[0], rest[1])
    return opening_rect(side, a, b)


def elements(fl):
    ents = fl["entities"]
    rooms = fl["rooms"]
    ov = []
    # 1) light glows
    for l in ents["lights"]:
        entity, cx, cy, gx, gy, rad, clips = l[:7]
        if not clips:
            continue
        polys = [rooms[c] for c in clips]
        ov.append(overlay(cond(entity, "on"), glow_svg(polys, gx, gy, rad, lamp_svg(l, True)), overlay_box(polys)))
    for entity, svg, box in ents.get("glows", []):
        ov.append(overlay(cond(entity, "on"), svg, box))
    for d in ents.get("devices", []):
        for conds, body, box in d["states"]:
            ov.append(overlay(conds, svg_head(box) + body + SVG_TAIL, box))
    # 2) motion
    for entity, clips in ents.get("motion", []):
        polys = [rooms[c] for c in clips]
        ov.append(overlay(cond(entity, "on"), motion_svg(polys), overlay_box(polys)))
    # 3) closed shutters
    for c in ents.get("covers", []):
        entity, side = c[0], c[1]
        p = opening_box(side, *c[2:])
        vertical = side == "right"
        if side == "roof":
            vertical = False
        ov.append(overlay(cond(entity, "closed"), shutter_svg(p, vertical), overlay_box([p])))
    # 4) open windows / doors
    for c in ents.get("contacts", []):
        entity, side = c[0], c[1]
        p = opening_box(side, *c[2:])
        ov.append(overlay(cond(entity, "on"), contact_svg(p), overlay_box([p], 14)))
    # 5) unlocked front door
    if ents.get("lock"):
        entity, side, a, b = ents["lock"]
        p = opening_box(side, a, b)
        ov.append(overlay(cond(entity, state_not="locked"), lock_svg(p), overlay_box([p], 14)))

    # invisible buttons (bottom layer, so chips on top stay tappable)
    els = []
    for box, path in ents.get("buttons", []):
        style = place(fl, box)
        del style["pointer-events"]
        els.append({"type": "image", "image": data_uri(svg_head(box) + SVG_TAIL),
                    "tap_action": {"action": "navigate", "navigation_path": path},
                    "hold_action": {"action": "none"}, "style": style})
    for o in ov:
        box = o.pop("_box")
        o["elements"][0]["style"] = place(fl, box)
        els.append(o)

    # lamps: the drawn lamp is the button (invisible, finger sized hit area on top of it)
    T = 44 * fl["viewbox"][3] / 1080             # 44 pt on the iPad, in plan cm

    def target(entity, box, tap):
        x0, y0, x1, y1 = box
        px, py = max(0, (T - (x1 - x0)) / 2), max(0, (T - (y1 - y0)) / 2)
        box = (x0 - px, y0 - py, x1 + px, y1 + py)
        style = place(fl, box)
        del style["pointer-events"]
        return {"type": "image", "entity": entity, "image": data_uri(svg_head(box) + SVG_TAIL),
                "tap_action": {"action": tap}, "hold_action": {"action": "more-info"}, "style": style}

    for l in ents["lights"]:
        els.append(target(l[0], lamp_box(l), "toggle"))
    # devices: the drawn furniture is the button, like the lamps
    for d in ents.get("devices", []):
        els.append(target(d["entity"], d["hit"], d["tap"]))
    # chips: covers (placed on the window)
    for c in ents.get("covers", []):
        entity, side = c[0], c[1]
        p = opening_box(side, *c[2:])
        x0, y0, x1, y1 = bbox([p])
        left, top = pct(fl, (x0 + x1) / 2, (y0 + y1) / 2)
        els.append({"type": "state-icon", "entity": entity, "tap_action": {"action": "more-info"},
                    "style": {"left": left, "top": top, **CHIP}})
    # chip: lock
    if ents.get("lock"):
        entity, side, a, b = ents["lock"]
        x0, y0, x1, y1 = bbox([opening_box(side, a, b)])
        left, top = pct(fl, (x0 + x1) / 2 - 30, (y0 + y1) / 2)
        els.append({"type": "state-icon", "entity": entity, "tap_action": {"action": "more-info"},
                    "style": {"left": left, "top": top, **CHIP}})
    # pills: temperature + humidity
    for temp, hum, x, y in ents.get("climate", []):
        left, top = pct(fl, x, y)
        if hum:
            els.append({"type": "state-label", "entity": temp, "tap_action": {"action": "more-info"},
                        "style": {"left": left, "top": top, "transform": "translate(calc(-100% - 2px),-50%)",
                                  "color": "var(--primary-text-color)", **PILL}})
            els.append({"type": "state-label", "entity": hum, "tap_action": {"action": "more-info"},
                        "style": {"left": left, "top": top, "transform": "translate(2px,-50%)",
                                  "color": "var(--secondary-text-color)", **PILL}})
        else:
            els.append({"type": "state-label", "entity": temp, "tap_action": {"action": "more-info"},
                        "style": {"left": left, "top": top, "transform": "translate(-50%,-50%)",
                                  "color": "var(--primary-text-color)", **PILL}})
    return els


# One dashboard per floor; a navbar-card (same style as the other dashboards)
# switches between the floors.
DASHBOARDS = {
    "eg": {"url_path": "dashboard-grundriss", "title": "Grundriss", "icon": "mdi:floor-plan",
           "show_in_sidebar": True, "view_icon": "mdi:home-floor-0"},
    "og": {"url_path": "dashboard-grundriss-og", "title": "Grundriss OG", "icon": "mdi:floor-plan",
           "show_in_sidebar": False, "view_icon": "mdi:home-floor-1"},
    "dg": {"url_path": "dashboard-grundriss-dg", "title": "Grundriss DG", "icon": "mdi:floor-plan",
           "show_in_sidebar": False, "view_icon": "mdi:home-floor-2"},
    "garten": {"url_path": "dashboard-grundriss-garten", "title": "Grundriss Garten", "icon": "mdi:flower",
               "show_in_sidebar": False, "view_icon": "mdi:flower"},
}

NAVBAR = {
    "type": "custom:navbar-card",
    "desktop": {"show_labels": True, "position": "bottom"},
    "mobile": {"show_labels": True},
    "routes": [
        {"url": EG_PATH, "icon": "mdi:home-floor-0", "label": "EG"},
        {"url": "/dashboard-grundriss-og/og", "icon": "mdi:home-floor-1", "label": "1. OG"},
        {"url": "/dashboard-grundriss-dg/dg", "icon": "mdi:home-floor-2", "label": "DG"},
        {"url": GARDEN_PATH, "icon": "mdi:flower", "label": "Garten"},
    ],
    "styles": ".navbar { --navbar-primary-color: #FFB300; }",
}


def dashboard(fl):
    """Panel view (full width, no heading): plan, optional cards, navbar."""
    meta = DASHBOARDS[fl["key"]]
    plan = {"type": "picture-elements", "image": data_uri(build_svg(fl)), "elements": elements(fl)}
    return {
        "title": meta["title"],
        "views": [{
            "title": fl["title"],
            "path": fl["key"],
            "icon": meta["view_icon"],
            "type": "panel",
            "cards": [{"type": "vertical-stack", "cards": [plan] + fl.get("cards", []) + [NAVBAR]}],
        }],
    }


def plan_card(cfg):
    return cfg["views"][0]["cards"][0]["cards"][0]


# --------------------------------------------------------------------------
# Minimal YAML emitter (stdlib only)
# --------------------------------------------------------------------------
def yaml_scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    plain_ok = (s and s[0] not in "-?:,[]{}#&*!|>'\"%@`" and ": " not in s and " #" not in s
                and s.strip() == s and s.lower() not in ("on", "off", "yes", "no", "true", "false", "null", "none")
                and not s.replace(".", "", 1).isdigit())
    return s if plain_ok else json.dumps(s, ensure_ascii=False)


def to_yaml(obj, indent=0):
    pad = "  " * indent
    lines = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = yaml_scalar(k)
            if isinstance(v, (dict, list)) and v:
                lines.append("%s%s:" % (pad, key))
                lines.append(to_yaml(v, indent + 1 if isinstance(v, dict) else indent))
            elif isinstance(v, (dict, list)):
                lines.append("%s%s: %s" % (pad, key, "{}" if isinstance(v, dict) else "[]"))
            else:
                lines.append("%s%s: %s" % (pad, key, yaml_scalar(v)))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                sub = to_yaml(item, indent + 1).split("\n")
                lines.append("%s- %s" % (pad, sub[0][len(pad) + 2:]))
                lines.extend(sub[1:])
            else:
                lines.append("%s- %s" % (pad, yaml_scalar(item)))
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Local preview (approximates the picture-elements card)
# --------------------------------------------------------------------------
def preview_html(cfgs, dark=False, all_on=True):
    import html as h
    bg, card, fg = ("#111315", "#1c1c1e", "#e5e7eb") if dark else ("#f3f4f6", "#ffffff", "#111827")
    out = ['<html><head><meta charset="utf-8"></head><body style="margin:0;background:%s;'
           'font-family:-apple-system,sans-serif;display:flex;flex-direction:column;gap:16px;padding:16px;'
           'align-items:flex-start">' % bg]
    for fl in FLOORS:
        if fl["key"] not in cfgs:
            continue
        pe = plan_card(cfgs[fl["key"]])
        img = data_uri(build_svg(fl, force_dark=dark))
        out.append('<div style="width:900px;background:%s;border-radius:14px;padding:10px;'
                   'box-shadow:0 1px 3px rgba(0,0,0,.2)"><div style="color:%s;font-weight:600;margin:4px 6px 8px">%s</div>'
                   '<div style="position:relative">' % (card, fg, fl["title"]))
        out.append('<img src="%s" style="width:100%%;display:block">' % h.escape(img))
        for e in pe["elements"]:
            if e["type"] == "conditional":
                if all_on:
                    s = e["elements"][0]
                    st = s["style"]
                    out.append('<img src="%s" style="position:absolute;left:%s;top:%s;width:%s;'
                               'transform:translate(-50%%,-50%%)">' % (h.escape(s["image"]), st["left"], st["top"], st["width"]))
                continue
            if e["type"] == "image":          # invisible button
                continue
            st = e["style"]
            dom = e["entity"].split(".")[0]
            if e["type"] == "state-label":
                txt = "21,4 °C" if "temp" in e["entity"] else "45 %"
                col = fg if "temp" in e["entity"] else "#8b95a1"
                out.append('<div style="position:absolute;left:%s;top:%s;transform:%s;background:%s;border-radius:9px;'
                           'padding:1px 7px;font-size:11px;font-weight:600;line-height:16px;color:%s;'
                           'box-shadow:0 1px 3px rgba(0,0,0,.25);white-space:nowrap">%s</div>' % (
                               st["left"], st["top"], st["transform"], card, col, txt))
            else:
                glyph = {"light": "💡", "cover": "▤", "lock": "🔒"}.get(dom, "•")
                col = "#f5b300" if (dom == "light" and all_on) else ("#9aa3ad" if dom == "light" else "#5b8def")
                sc = float(st["transform"].split("scale(")[1].rstrip(")")) if "scale(" in st["transform"] else 1
                px = round(40 * sc)
                out.append('<div style="position:absolute;left:%s;top:%s;transform:translate(-50%%,-50%%);width:%dpx;'
                           'height:%dpx;border-radius:50%%;background:%s;box-shadow:0 1px 4px rgba(0,0,0,.3);display:flex;'
                           'align-items:center;justify-content:center;font-size:%dpx;color:%s">%s</div>' % (
                               st["left"], st["top"], px, px, card, round(px * .5), col, glyph))
        out.append("</div></div>")
    out.append("</body></html>")
    return "".join(out)


def main():
    cfgs = {}
    for fl in FLOORS:
        key = fl["key"]
        with open(os.path.join(HERE, key + ".svg"), "w", encoding="utf-8") as f:
            f.write(build_svg(fl))
        cfgs[key] = cfg = dashboard(fl)
        with open(os.path.join(HERE, "grundriss-%s.json" % key), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, separators=(",", ":"))
        with open(os.path.join(HERE, "..", "grundriss-%s.yaml" % key), "w", encoding="utf-8") as f:
            f.write("# %s -> /%s/%s (generated by floorplan/generate.py)\n" % (
                DASHBOARDS[key]["title"], DASHBOARDS[key]["url_path"], key))
            f.write(to_yaml(cfg) + "\n")
        pe = plan_card(cfg)
        print(" ", key, "config bytes:", len(json.dumps(cfg, ensure_ascii=False, separators=(",", ":"))),
              "image:", len(pe["image"]), "elements:", len(pe["elements"]))
    prev = os.environ.get("FLOORPLAN_PREVIEW_DIR")
    if prev:
        os.makedirs(prev, exist_ok=True)
        for name, dark, on in (("light_on", False, True), ("light_off", False, False),
                               ("dark_on", True, True), ("dark_off", True, False)):
            with open(os.path.join(prev, name + ".html"), "w", encoding="utf-8") as f:
                f.write(preview_html(cfgs, dark, on))


if __name__ == "__main__":
    main()
