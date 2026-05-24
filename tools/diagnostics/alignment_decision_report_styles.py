"""CSS for the alignment decision report."""

from __future__ import annotations


def report_css() -> str:
    return """
:root {
  color-scheme: light;
  font-family: "Aptos", "Segoe UI", sans-serif;
  color: #17202a;
  background: #f3f4f1;
}
body {
  margin: 0;
}
main {
  max-width: 1240px;
  margin: 0 auto;
  padding: 30px 28px 52px;
}
h1 {
  margin: 0 0 16px;
  font-size: 30px;
}
h2 {
  margin: 0 0 16px;
  font-size: 20px;
}
h3 {
  margin: 20px 0 10px;
  font-size: 15px;
}
section {
  background: #fff;
  border: 1px solid #d8ddd7;
  border-radius: 8px;
  margin-top: 18px;
  padding: 18px;
  box-shadow: 0 12px 24px rgba(24, 35, 43, 0.05);
}
.verdict {
  display: inline-block;
  border-radius: 6px;
  font-weight: 700;
  letter-spacing: 0;
  padding: 8px 12px;
}
.verdict-pass { background: #dcfce7; color: #14532d; }
.verdict-warn { background: #fef3c7; color: #78350f; }
.verdict-fail { background: #fee2e2; color: #7f1d1d; }
.visual-panel {
  border: 1px solid #d9ded8;
  border-radius: 8px;
  background: #fbfcf9;
  padding: 14px;
  margin-bottom: 14px;
}
.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(138px, 1fr));
  gap: 10px;
}
.status-card {
  border-left: 6px solid #87929a;
  border-radius: 7px;
  background: #fff;
  padding: 10px 12px;
}
.status-card span {
  display: block;
  color: #59636f;
  font-size: 12px;
}
.status-card strong {
  display: block;
  margin-top: 4px;
  font-size: 24px;
}
.stacked-bar {
  display: flex;
  height: 24px;
  overflow: hidden;
  border-radius: 999px;
  background: #e7e9e4;
  border: 1px solid #d5d9d1;
}
.stack-segment {
  min-width: 2px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 16px;
  margin-top: 9px;
  color: #4b5563;
  font-size: 12px;
}
.legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
}
.bar-list {
  display: grid;
  gap: 8px;
}
.bar-row {
  display: grid;
  grid-template-columns: minmax(130px, 230px) 1fr minmax(54px, auto);
  gap: 10px;
  align-items: center;
}
.bar-label {
  overflow-wrap: anywhere;
  font-size: 12px;
  color: #334155;
}
.bar-track {
  display: block;
  height: 14px;
  border-radius: 999px;
  background: #e8ece7;
  overflow: hidden;
}
.bar-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
}
.bar-row strong {
  text-align: right;
  font-size: 12px;
}
.istd-board {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.istd-tile {
  border: 1px solid #dce1db;
  border-top: 5px solid #87929a;
  border-radius: 8px;
  background: #fff;
  padding: 12px;
}
.istd-tile header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}
.known-chip {
  background: #fef3c7;
  border-radius: 999px;
  color: #78350f;
  font-size: 11px;
  font-weight: 800;
  padding: 2px 7px;
}
.tile-meta, .tile-foot {
  color: #64748b;
  font-size: 12px;
  margin-top: 6px;
  overflow-wrap: anywhere;
}
.mini-meter {
  display: grid;
  grid-template-columns: 80px 1fr 44px;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
}
.mini-track {
  display: block;
  height: 7px;
  border-radius: 999px;
  background: #e9ece7;
  overflow: hidden;
}
.mini-track span {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: #2f855a;
}
.tone-pass,
.tone-production { border-color: #2f855a; }
.tone-pass.stack-segment,
.tone-production.stack-segment,
.tone-pass.bar-fill,
.tone-production.bar-fill,
.tone-pass.legend-dot,
.tone-production.legend-dot {
  background: #2f855a;
}
.tone-warn { border-color: #d97706; }
.tone-warn.stack-segment,
.tone-warn.bar-fill,
.tone-warn.legend-dot {
  background: #d97706;
}
.tone-fail { border-color: #dc2626; }
.tone-fail.stack-segment,
.tone-fail.bar-fill,
.tone-fail.legend-dot {
  background: #dc2626;
}
.tone-provisional { border-color: #2563eb; }
.tone-provisional.stack-segment,
.tone-provisional.bar-fill,
.tone-provisional.legend-dot {
  background: #2563eb;
}
.tone-audit { border-color: #6b7280; }
.tone-audit.stack-segment,
.tone-audit.bar-fill,
.tone-audit.legend-dot {
  background: #6b7280;
}
.tone-rescue { border-color: #7c3aed; }
.tone-rescue.stack-segment,
.tone-rescue.bar-fill,
.tone-rescue.legend-dot {
  background: #7c3aed;
}
.tone-neutral { border-color: #64748b; }
.tone-neutral.stack-segment,
.tone-neutral.bar-fill,
.tone-neutral.legend-dot {
  background: #64748b;
}
.tone-runtime { border-color: #0f766e; }
.tone-runtime.stack-segment,
.tone-runtime.bar-fill,
.tone-runtime.legend-dot {
  background: #0f766e;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin: 14px 0 0;
}
.metrics div {
  border: 1px solid #e5e8e2;
  border-radius: 6px;
  padding: 10px;
  min-width: 0;
}
dt {
  color: #64748b;
  font-size: 12px;
  margin-bottom: 5px;
}
dd {
  margin: 0;
  overflow-wrap: anywhere;
  font-weight: 650;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-top: 10px;
}
th, td {
  border-bottom: 1px solid #e5e8e2;
  padding: 7px 8px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #f1f5f9;
  color: #334155;
  font-weight: 700;
}
.muted, .not-provided {
  color: #64748b;
}
details.data-table {
  margin-top: 14px;
}
details.data-table summary {
  cursor: pointer;
  color: #334155;
  font-weight: 700;
}
""".strip()
