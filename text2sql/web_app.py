"""Local browser interface for the existing policy-guarded Text-to-SQL service."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from datetime import date, datetime
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Sequence
from urllib.parse import urlsplit

from text2sql.charting import suggest_chart
from text2sql.catalog import load_config
from text2sql.evaluation.run_baselines import DEFAULT_GOLDEN_SET_PATH, _load_evaluation_set
from text2sql.executor import DuckDBExecutor
from text2sql.nl_service import NaturalLanguageQueryService, TextToSQLResponse
from text2sql.validator import validate_sql


_MAX_REQUEST_BYTES = 8_192
_SERVICE_LOCK = threading.Lock()


_PAGE = """<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>E-Commerce Analytics | Data Assistant</title>
  <style>
    :root { color-scheme: light; --ink:#172b4d; --muted:#62718a; --line:#dce3ed; --blue:#2559c7; --bg:#f4f7fb; --green:#087443; --red:#b42318; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 "Segoe UI",Arial,sans-serif; }
    main { width:min(1120px, calc(100% - 32px)); margin:36px auto 64px; }
    header { margin-bottom:24px; }
    h1 { margin:0 0 5px; font-size:30px; letter-spacing:-.5px; }
    h2 { margin:0; font-size:19px; }
    .subtitle,.muted { color:var(--muted); }
    .panel { background:#fff; border:1px solid var(--line); border-radius:14px; padding:22px; box-shadow:0 4px 18px #2538580a; margin:16px 0; }
    label { font-weight:600; display:block; margin-bottom:8px; }
    textarea { width:100%; min-height:106px; resize:vertical; border:1px solid #b9c5d5; border-radius:9px; padding:12px 14px; color:var(--ink); font:inherit; }
    textarea:focus,select:focus,button:focus-visible { outline:3px solid #9bb9ff; outline-offset:2px; }
    .actions { display:flex; align-items:center; gap:14px; margin-top:12px; }
    button { border:0; border-radius:8px; background:var(--blue); color:white; font:600 15px "Segoe UI",Arial,sans-serif; padding:10px 18px; cursor:pointer; }
    button.secondary { background:#eaf0fb; color:var(--blue); border:1px solid #c9d7f2; }
    button:disabled { opacity:.6; cursor:wait; }
    .hint { font-size:13px; color:var(--muted); }
    .status { display:inline-block; border-radius:100px; padding:3px 10px; background:#edf2fa; font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.04em; }
    .status.answered { color:var(--green); background:#e7f6ee; }
    .status.refused,.status.rejected,.status.failed,.status.unavailable { color:var(--red); background:#fff0ed; }
    .message { margin:12px 0 0; white-space:pre-wrap; }
    .meta { color:var(--muted); font-size:13px; margin-top:8px; }
    .result-head { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:14px; }
    .table-wrap { overflow:auto; max-height:520px; border:1px solid var(--line); border-radius:9px; }
    table { border-collapse:collapse; width:100%; min-width:600px; font-size:14px; }
    th,td { border-bottom:1px solid #e8edf4; padding:9px 12px; text-align:left; white-space:nowrap; }
    th { position:sticky; top:0; background:#f7f9fc; z-index:1; }
    tbody tr:hover { background:#f8faff; }
    .chart-controls { display:flex; flex-wrap:wrap; gap:14px; align-items:end; margin:12px 0 4px; }
    .chart-controls label { min-width:180px; margin:0; font-size:13px; }
    select { display:block; width:100%; margin-top:4px; border:1px solid #b9c5d5; border-radius:7px; padding:8px; background:#fff; color:var(--ink); font:inherit; }
    canvas { width:100%; height:330px; display:block; }
    .chart-empty { color:var(--muted); padding:18px 0; }
    .kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:10px 0 16px; }
    .kpi { border:1px solid var(--line); border-radius:9px; padding:12px; background:#fbfcfe; }
    .kpi-name { color:var(--muted); font-size:12px; overflow-wrap:anywhere; }
    .kpi-value { font-size:20px; font-weight:700; margin-top:3px; overflow-wrap:anywhere; }
    details { margin-top:14px; }
    summary { cursor:pointer; color:var(--blue); font-weight:600; }
    pre { padding:13px; overflow:auto; background:#f6f8fb; border-radius:8px; border:1px solid var(--line); }
    .disclaimer { font-size:12px; margin-top:18px; color:var(--muted); }
    [hidden] { display:none !important; }
    @media(max-width:640px) { main { width:calc(100% - 20px); margin-top:20px; } .panel { padding:15px; } h1 { font-size:24px; } .actions { align-items:flex-start; flex-direction:column; } canvas { height:270px; } }
  </style>
</head>
<body>
<main>
  <header>
    <h1>E-Commerce Analytics · Data Assistant</h1>
    <div class="subtitle">Đặt câu hỏi bằng tiếng Việt hoặc tiếng Anh trên các Gold marts được phê duyệt.</div>
  </header>
  <section class="panel">
    <form id="question-form">
      <label for="question">Câu hỏi phân tích</label>
      <textarea id="question" maxlength="2000" required placeholder="Ví dụ: So sánh total_sales và total_profit theo từng segment"></textarea>
      <div class="actions">
        <button id="ask-button" type="submit">Hỏi dữ liệu</button>
        <button id="demo-button" class="secondary" type="button">Biểu đồ mẫu Q02 · offline</button>
        <span class="hint">Yêu cầu phù hợp sẽ được gửi tới Gemini; safeguard cục bộ có thể từ chối hoặc hỏi làm rõ trước. SQL chỉ chạy sau khi qua policy và validator.</span>
      </div>
    </form>
  </section>
  <section id="answer-panel" class="panel" hidden aria-live="polite">
    <div><span id="answer-status" class="status"></span></div>
    <p id="answer-message" class="message"></p>
    <div id="answer-meta" class="meta"></div>
    <details id="sql-details" hidden><summary>Xem SQL đã được validator chấp nhận</summary><pre id="validated-sql"></pre></details>
  </section>
  <section id="result-panel" class="panel" hidden>
    <div class="result-head"><h2>Kết quả</h2><span id="row-count" class="muted"></span></div>
    <div id="kpis" class="kpis" hidden></div>
    <div id="chart-area" hidden>
      <h2>Biểu đồ kết quả</h2>
      <p class="hint">Biểu đồ dùng trực tiếp các hàng đã trả về; thay đổi trục để khám phá kết quả.</p>
      <div class="chart-controls">
        <label>Nhóm theo<select id="dimension-select"></select></label>
        <label>Chỉ số<select id="measure-select"></select></label>
      </div>
      <canvas id="chart" aria-label="Biểu đồ kết quả truy vấn"></canvas>
    </div>
    <p id="no-chart" class="chart-empty" hidden></p>
    <div class="table-wrap"><table id="result-table"></table></div>
    <details id="template-details" hidden><summary>Thông tin truy vấn tổng hợp</summary><p id="template-id" class="muted"></p></details>
  </section>
  <p class="disclaimer">Chạy cục bộ trên máy này. Kết quả kế thừa giới hạn truy cập, hard row cap và read-only của Text-to-SQL service. Biểu đồ chỉ trực quan hóa các hàng trả về, không suy diễn thêm dữ liệu.</p>
</main>
<script>
const form = document.getElementById('question-form');
const questionInput = document.getElementById('question');
const askButton = document.getElementById('ask-button');
const answerPanel = document.getElementById('answer-panel');
const resultPanel = document.getElementById('result-panel');
let currentResult = null;

function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function showStatus(data) {
  answerPanel.hidden = false;
  const status = document.getElementById('answer-status');
  status.className = 'status ' + String(data.status || 'failed');
  status.textContent = String(data.status || 'failed');
  document.getElementById('answer-message').textContent = data.message || 'Không có nội dung trả lời.';
  const meta = document.getElementById('answer-meta');
  meta.textContent = data.duration_ms === undefined ? '' : 'Thời gian truy vấn: ' + data.duration_ms + ' ms';
  const sqlDetails = document.getElementById('sql-details');
  sqlDetails.hidden = !data.sql;
  document.getElementById('validated-sql').textContent = data.sql || '';
}
function renderKpis(data) {
  const box = document.getElementById('kpis');
  box.replaceChildren();
  const rows = data.rows || [];
  const numeric = data.columns.filter((_, index) => rows[0] && !Number.isNaN(Number(rows[0][index])) && rows[0][index] !== null && rows[0][index] !== '');
  if (rows.length !== 1 || numeric.length < 2 || numeric.length > 6) { box.hidden = true; return; }
  numeric.forEach(name => {
    const index = data.columns.indexOf(name);
    const card = node('div', undefined, 'kpi');
    card.append(node('div', name, 'kpi-name'));
    card.append(node('div', String(rows[0][index]), 'kpi-value'));
    box.append(card);
  });
  box.hidden = false;
}
function renderTable(data) {
  const table = document.getElementById('result-table');
  table.replaceChildren();
  const thead = table.createTHead();
  const header = thead.insertRow();
  data.columns.forEach(column => header.append(node('th', column)));
  const tbody = table.createTBody();
  (data.rows || []).forEach(values => {
    const row = tbody.insertRow();
    values.forEach(value => row.insertCell().textContent = value === null ? 'NULL' : String(value));
  });
}
function drawChart() {
  if (!currentResult || !currentResult.chart) return;
  const dimension = document.getElementById('dimension-select').value;
  const measure = document.getElementById('measure-select').value;
  const xIndex = currentResult.columns.indexOf(dimension);
  const yIndex = currentResult.columns.indexOf(measure);
  const labels = currentResult.rows.map(row => String(row[xIndex]));
  const values = currentResult.rows.map(row => Number(row[yIndex]));
  const canvas = document.getElementById('chart');
  const width = Math.max(320, canvas.clientWidth);
  const height = canvas.clientHeight || 330;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  const ctx = canvas.getContext('2d');
  ctx.scale(ratio, ratio);
  ctx.clearRect(0, 0, width, height);
  const left = 66, right = 18, top = 18, bottom = 72;
  const plotW = width - left - right, plotH = height - top - bottom;
  const maxValue = Math.max(0, ...values);
  const minValue = Math.min(0, ...values);
  const span = (maxValue - minValue) || 1;
  ctx.font = '12px Segoe UI, Arial';
  ctx.strokeStyle = '#dce3ed'; ctx.fillStyle = '#62718a'; ctx.lineWidth = 1;
  for (let tick = 0; tick <= 4; tick++) {
    const y = top + plotH * tick / 4;
    const value = maxValue - span * tick / 4;
    ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(width - right, y); ctx.stroke();
    ctx.textAlign = 'right'; ctx.fillText(new Intl.NumberFormat('vi-VN', {maximumFractionDigits:1}).format(value), left - 8, y + 4);
  }
  ctx.strokeStyle = '#2559c7'; ctx.fillStyle = '#2559c7';
  const lineMode = /^\d{4}-\d{2}-\d{2}/.test(labels[0]);
  if (lineMode) {
    const points = values.map((value, index) => ({x:left + (labels.length === 1 ? .5 : index / (labels.length - 1)) * plotW, y:top + (maxValue - value) / span * plotH}));
    ctx.beginPath(); points.forEach((point,index) => index ? ctx.lineTo(point.x,point.y) : ctx.moveTo(point.x,point.y)); ctx.stroke();
    points.forEach((point,index) => { ctx.beginPath(); ctx.arc(point.x,point.y,3,0,Math.PI*2); ctx.fill(); if (index % Math.ceil(labels.length / 12) === 0 || index === labels.length - 1) { ctx.fillStyle='#62718a'; ctx.textAlign='center'; ctx.fillText(labels[index].slice(0,10),point.x,height-bottom+20); ctx.fillStyle='#2559c7'; } });
  } else {
    const slot = plotW / labels.length;
    values.forEach((value,index) => {
      const barW = Math.max(2, slot * .68);
      const x = left + index * slot + (slot-barW)/2;
      const zeroY = top + maxValue / span * plotH;
      const y = top + (maxValue-value) / span * plotH;
      ctx.fillRect(x, Math.min(y,zeroY), barW, Math.max(1,Math.abs(zeroY-y)));
      if (labels.length <= 16 || index % Math.ceil(labels.length / 16) === 0) {
        ctx.fillStyle='#62718a'; ctx.textAlign='center';
        const label = labels[index].length > 16 ? labels[index].slice(0,15)+'…' : labels[index];
        ctx.fillText(label, x+barW/2, height-bottom+20); ctx.fillStyle='#2559c7';
      }
    });
  }
  ctx.fillStyle='#172b4d'; ctx.textAlign='center'; ctx.fillText(measure, left + plotW/2, height-8);
}
function fillSelect(select, options, selected) {
  select.replaceChildren();
  options.forEach(value => { const option=node('option',value); option.value=value; option.selected=value===selected; select.append(option); });
}
function renderResult(data) {
  resultPanel.hidden = false;
  document.getElementById('row-count').textContent = data.row_count + ' dòng' + (data.truncated ? ' · đã giới hạn theo policy' : '');
  renderKpis(data);
  renderTable(data);
  const chartArea = document.getElementById('chart-area');
  const noChart = document.getElementById('no-chart');
  currentResult = data;
  if (data.chart && data.rows.length > 1) {
    chartArea.hidden = false; noChart.hidden = true;
    fillSelect(document.getElementById('dimension-select'), data.chart.dimensions, data.chart.default_dimension);
    fillSelect(document.getElementById('measure-select'), data.chart.measures, data.chart.default_measure);
    drawChart();
  } else {
    chartArea.hidden = true; noChart.hidden = false;
    noChart.textContent = data.rows.length === 0 ? 'Không có dòng dữ liệu phù hợp để vẽ biểu đồ.' : 'Kết quả dạng tổng hợp một dòng hoặc không có cặp trục phù hợp; xem KPI và bảng bên dưới.';
  }
  const templateDetails = document.getElementById('template-details');
  templateDetails.hidden = !data.template_id;
  document.getElementById('template-id').textContent = data.template_id || '';
}
form.addEventListener('submit', async event => {
  event.preventDefault();
  const question = questionInput.value.trim();
  if (!question) return;
  askButton.disabled = true; askButton.textContent = 'Đang xử lý…';
  answerPanel.hidden = true; resultPanel.hidden = true;
  try {
    const response = await fetch('/api/ask', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Không thể xử lý câu hỏi.');
    showStatus(data);
    if (data.result) renderResult(data.result);
  } catch (error) {
    showStatus({status:'failed', message:error.message || 'Không thể kết nối ứng dụng.'});
  } finally { askButton.disabled = false; askButton.textContent = 'Hỏi dữ liệu'; }
});
document.getElementById('demo-button').addEventListener('click', async () => {
  const demoButton = document.getElementById('demo-button');
  askButton.disabled = true; demoButton.disabled = true; demoButton.textContent = 'Đang chạy baseline…';
  answerPanel.hidden = true; resultPanel.hidden = true;
  try {
    const response = await fetch('/api/demo', {method:'POST'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.message || 'Không thể chạy ví dụ offline.');
    showStatus(data);
    if (data.result) renderResult(data.result);
  } catch (error) {
    showStatus({status:'failed', message:error.message || 'Không thể kết nối ứng dụng.'});
  } finally { askButton.disabled = false; demoButton.disabled = false; demoButton.textContent = 'Biểu đồ mẫu Q02 · offline'; }
});
document.getElementById('dimension-select').addEventListener('change', drawChart);
document.getElementById('measure-select').addEventListener('change', drawChart);
window.addEventListener('resize', () => { if (currentResult && currentResult.chart) drawChart(); });
</script>
</body>
</html>"""


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (Decimal, date, datetime)):
        return str(value) if isinstance(value, Decimal) else value.isoformat()
    return str(value)


def _response_payload(response: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"status": response.status, "message": response.message}
    if response.sql:
        payload["sql"] = response.sql
    if response.template_id:
        payload["template_id"] = response.template_id
    if response.result is not None:
        result = response.result
        rows = [[_json_value(value) for value in row] for row in result.rows]
        suggestion = suggest_chart(result.columns, result.rows)
        payload["result"] = {
            "columns": list(result.columns),
            "rows": rows,
            "row_count": result.row_count,
            "row_limit": result.row_limit,
            "truncated": result.truncated,
            "duration_ms": result.duration_ms,
            "chart": suggestion.__dict__ if suggestion else None,
        }
    if response.result is not None:
        payload["duration_ms"] = response.result.duration_ms
    return payload


class _RequestHandler(BaseHTTPRequestHandler):
    server_version = "EcommerceAnalytics/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        # Never log user questions or query results to the terminal.
        return

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/":
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        self._send(200, _PAGE.encode("utf-8"), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        route = urlsplit(self.path).path
        if route == "/api/demo":
            try:
                with _SERVICE_LOCK:
                    payload = _demo_payload()
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
            except Exception:
                body = json.dumps(
                    {"status": "failed", "message": "Không thể chạy baseline mẫu; kiểm tra DuckDB warehouse và dbt build."},
                    ensure_ascii=False,
                ).encode("utf-8")
                self._send(500, body, "application/json; charset=utf-8")
            return
        if route != "/api/ask":
            self._send(404, b'{"message":"Not found"}', "application/json; charset=utf-8")
            return
        if self.headers.get_content_type() != "application/json":
            self._send(415, b'{"message":"Expected application/json."}', "application/json; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > _MAX_REQUEST_BYTES:
            self._send(413, b'{"message":"Question request is empty or too large."}', "application/json; charset=utf-8")
            return
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(400, b'{"message":"Invalid JSON request."}', "application/json; charset=utf-8")
            return
        question = request.get("question") if isinstance(request, dict) else None
        if not isinstance(question, str) or not question.strip():
            self._send(400, b'{"message":"Enter a non-empty question."}', "application/json; charset=utf-8")
            return
        try:
            # Keep one local request active at a time. No question/result history is persisted.
            with _SERVICE_LOCK:
                service = NaturalLanguageQueryService()
                try:
                    response = service.ask(question)
                finally:
                    service.close()
            body = json.dumps(_response_payload(response), ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
        except Exception:
            body = json.dumps(
                {"status": "failed", "message": "Ứng dụng không thể xử lý yêu cầu; kiểm tra cấu hình cục bộ rồi thử lại."},
                ensure_ascii=False,
            ).encode("utf-8")
            self._send(500, body, "application/json; charset=utf-8")


def _demo_payload() -> dict[str, Any]:
    """Run the trusted q02 baseline through the normal validator/executor, without Gemini."""
    evaluation_set = _load_evaluation_set(DEFAULT_GOLDEN_SET_PATH)
    case = next(case for case in evaluation_set["cases"] if case["case_id"] == "q02")
    config = load_config()
    validated = validate_sql(str(case["baseline"]["sql"]), config, role=config.policy.default_role)
    result = DuckDBExecutor(config=config).execute(validated)
    response = TextToSQLResponse(
        status="answered",
        message=(
            "Ví dụ offline Q02: baseline doanh thu theo segment đã qua SQL validator và được chạy read-only. "
            "Đây không phải câu trả lời do Gemini sinh ra."
        ),
        result=result,
        sql=validated.sql,
    )
    return _response_payload(response)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local e-commerce Text-to-SQL browser UI.")
    parser.add_argument("--port", type=int, default=8765, help="Local HTTP port (default: 8765).")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically.")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535.")
    address = f"http://127.0.0.1:{args.port}/"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), _RequestHandler)
    except OSError as exc:
        print(f"Could not start the local UI ({type(exc).__name__}).", file=sys.stderr)
        return 2
    print(f"E-commerce Text-to-SQL is available at {address}", flush=True)
    print("Press Ctrl+C to stop. This server listens on localhost only.", flush=True)
    if not args.no_browser:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local Text-to-SQL UI.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
