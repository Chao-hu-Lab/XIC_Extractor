"""CSS for the targeted evidence review report."""

from __future__ import annotations


def report_css() -> str:
    return """
:root {
  color-scheme: light;
  font-family: "Aptos", "Segoe UI", sans-serif;
  --ink: #17202a;
  --muted: #64748b;
  --paper: #fbfcf9;
  --panel: #ffffff;
  --line: #d8ddd7;
  --pass: #2f855a;
  --review-positive: #dc2626;
  --review: #d97706;
  --audit: #64748b;
  --neutral: #8a948f;
  color: var(--ink);
  background: #f4f5f2;
}
body { margin: 0; }
main {
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 24px 48px;
}
h1 { margin: 0 0 16px; font-size: 30px; }
h2 { margin: 0 0 14px; font-size: 20px; }
h3 { margin: 18px 0 8px; font-size: 15px; }
section {
  background: #fff;
  border: 1px solid #d8ddd7;
  border-radius: 8px;
  margin-top: 18px;
  padding: 18px;
}
.triage-board {
  min-height: 420px;
  background: #15201b;
  border: 0;
  color: #f8fafc;
  padding: 24px;
}
.triage-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}
.triage-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
  gap: 18px;
  margin-top: 24px;
}
.eyebrow {
  display: block;
  color: #a7b4ad;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.verdict {
  display: inline-block;
  border-radius: 6px;
  font-weight: 800;
  margin-top: 7px;
  padding: 8px 12px;
  font-size: 36px;
  line-height: 1;
}
.verdict-pass { background: #dcfce7; color: #14532d; }
.verdict-warn { background: #fef3c7; color: #78350f; }
.verdict-fail { background: #fee2e2; color: #7f1d1d; }
.verdict-message {
  color: #d2dbd5;
  margin: 12px 0 0;
}
.run-badge {
  min-width: 120px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 8px;
  padding: 10px 12px;
  text-align: right;
}
.run-badge span {
  display: block;
  color: #a7b4ad;
  font-size: 12px;
}
.run-badge strong { display: block; margin-top: 4px; font-size: 20px; }
.muted { color: var(--muted); }
.action-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(150px, 1fr));
  gap: 12px;
}
.action-card {
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-left-width: 7px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.07);
  min-height: 132px;
  padding: 14px;
}
.action-card span {
  display: block;
  color: #dbe4de;
  font-size: 13px;
  font-weight: 700;
}
.action-card strong {
  display: block;
  margin: 10px 0 4px;
  font-size: 46px;
  line-height: 1;
}
.action-card em {
  color: #aebbb4;
  font-size: 12px;
  font-style: normal;
}
.health-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(130px, 1fr));
  gap: 10px;
}
.health-item {
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-left-width: 5px;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.06);
  padding: 10px;
}
.health-item span {
  display: block;
  color: #aebbb4;
  font-size: 12px;
}
.health-item strong {
  display: block;
  margin-top: 4px;
  color: #f8fafc;
  overflow-wrap: anywhere;
}
.status-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.status-card {
  border-left: 6px solid #87929a;
  border-radius: 7px;
  background: #fbfcf9;
  padding: 10px 12px;
}
.status-card span { display: block; color: #59636f; font-size: 12px; }
.status-card strong { display: block; margin-top: 4px; font-size: 24px; }
.first-charts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 14px;
  margin-top: 16px;
}
.visual-panel {
  border: 1px solid #d9ded8;
  border-radius: 8px;
  background: #fbfcf9;
  padding: 14px;
}
.target-row, .queue-card {
  border: 1px solid #e1e6df;
  border-radius: 8px;
  padding: 12px;
  margin-top: 10px;
}
.queue-card {
  border-left-width: 7px;
  background: #fff;
}
.queue-card header {
  align-items: flex-start;
}
.target-row header, .queue-card header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}
.queue-card header p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
}
.mz {
  color: #475569;
  font-size: 12px;
  white-space: nowrap;
}
.risk, .source {
  color: var(--muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.issue-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.issue-pill, .state-pill {
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 700;
}
.state-pill {
  background: #eef2f7;
  color: #475569;
}
.row-source {
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}
.row-source summary {
  cursor: pointer;
  font-weight: 700;
}
.row-source p { margin: 4px 0; overflow-wrap: anywhere; }
.stacked-bar {
  display: flex;
  height: 22px;
  overflow: hidden;
  border-radius: 999px;
  background: #e7e9e4;
  border: 1px solid #d5d9d1;
  margin-top: 8px;
}
.stack-segment { min-width: 2px; }
.legend, .chips, .mini-fields {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  margin-top: 8px;
  color: #4b5563;
  font-size: 12px;
}
.legend span, .chip { display: inline-flex; align-items: center; gap: 6px; }
.chip {
  background: #f1f5f9;
  border-radius: 999px;
  padding: 4px 8px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  display: inline-block;
}
.bar-list { display: grid; gap: 8px; margin-top: 8px; }
.bar-row {
  display: grid;
  grid-template-columns: minmax(150px, 260px) 1fr;
  gap: 10px;
  align-items: center;
}
.bar-label { overflow-wrap: anywhere; font-size: 12px; color: #334155; }
.bar-track {
  display: block;
  height: 14px;
  border-radius: 999px;
  background: #e8ece7;
  overflow: hidden;
}
.bar-fill { display: block; height: 100%; border-radius: 999px; }
.queue-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
  margin: 12px 0;
}
.metrics div {
  border: 1px solid #e5e8e2;
  border-radius: 6px;
  padding: 10px;
}
dt { color: #64748b; font-size: 12px; margin-bottom: 5px; }
dd { margin: 0; font-weight: 700; overflow-wrap: anywhere; }
.tone-pass { border-color: var(--pass); }
.tone-pass.stack-segment, .tone-pass.bar-fill, .tone-pass.legend-dot {
  background: var(--pass);
}
.tone-review-positive { border-color: var(--review-positive); }
.tone-review-positive.stack-segment,
.tone-review-positive.bar-fill,
.tone-review-positive.legend-dot {
  background: var(--review-positive);
}
.tone-review { border-color: var(--review); }
.tone-review.stack-segment, .tone-review.bar-fill, .tone-review.legend-dot {
  background: var(--review);
}
.tone-warn { border-color: var(--review); }
.tone-warn.stack-segment, .tone-warn.bar-fill, .tone-warn.legend-dot {
  background: var(--review);
}
.tone-fail { border-color: var(--review-positive); }
.tone-fail.stack-segment, .tone-fail.bar-fill, .tone-fail.legend-dot {
  background: var(--review-positive);
}
.tone-audit { border-color: var(--audit); }
.tone-audit.stack-segment, .tone-audit.bar-fill, .tone-audit.legend-dot {
  background: var(--audit);
}
.tone-neutral { border-color: var(--neutral); }
.tone-neutral.stack-segment, .tone-neutral.bar-fill, .tone-neutral.legend-dot {
  background: var(--neutral);
}
.issue-pill.tone-fail { background: #fee2e2; color: #7f1d1d; }
.issue-pill.tone-warn { background: #fef3c7; color: #78350f; }
.issue-pill.tone-audit { background: #e2e8f0; color: #334155; }
.issue-pill.tone-neutral { background: #eef2f7; color: #475569; }
.queue-fail { border-left-color: var(--review-positive); }
.queue-warn { border-left-color: var(--review); }
.queue-audit { border-left-color: var(--audit); }
.queue-neutral { border-left-color: var(--neutral); }
.map-details {
  margin-top: 18px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px 18px;
}
.map-details summary {
  cursor: pointer;
  font-weight: 800;
}
details.sources {
  margin-top: 18px;
  color: #334155;
}
details.sources summary { cursor: pointer; font-weight: 700; }
@media (max-width: 820px) {
  .triage-layout { grid-template-columns: 1fr; }
  .action-grid { grid-template-columns: 1fr; }
  .triage-header { display: block; }
  .run-badge { margin-top: 14px; text-align: left; }
}
""".strip()
