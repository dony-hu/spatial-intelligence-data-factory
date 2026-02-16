from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from services.governance_api.app.models.manual_review_models import (
    ManualReviewDecisionRequest,
    ManualReviewDecisionResponse,
    ManualReviewQueueResponse,
)
from services.governance_api.app.repositories.governance_repository import REPOSITORY

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/manual-review/queue", response_model=ManualReviewQueueResponse)
def manual_review_queue(pending_only: bool = True, limit: int = 200) -> ManualReviewQueueResponse:
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be in [1, 1000]")
    items = REPOSITORY.list_manual_review_items(pending_only=pending_only, limit=limit)
    pending = sum(1 for item in items if not str(item.get("review_status") or ""))
    return ManualReviewQueueResponse(
        as_of=_now_iso(),
        total=len(items),
        pending=pending,
        items=items,
    )


@router.post("/manual-review/decision", response_model=ManualReviewDecisionResponse)
def submit_manual_review_decision(payload: ManualReviewDecisionRequest) -> ManualReviewDecisionResponse:
    try:
        outcome = REPOSITORY.submit_manual_review_decision(
            task_id=payload.task_id,
            raw_id=payload.raw_id,
            review_status=payload.review_status,
            reviewer=payload.reviewer,
            next_route=payload.next_route,
            comment=payload.comment,
            final_canon_text=payload.final_canon_text,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ManualReviewDecisionResponse(
        accepted=bool(outcome.get("accepted")),
        task_id=str(outcome.get("task_id") or payload.task_id),
        raw_id=str(outcome.get("raw_id") or payload.raw_id),
        review_status=str(outcome.get("review_status") or payload.review_status),
        next_route=str(outcome.get("next_route") or payload.next_route),
        audit_event_id=str(outcome.get("audit_event_id") or ""),
        updated_count=int(outcome.get("updated_count", 0) or 0),
    )


@router.get("/manual-review/view", response_class=HTMLResponse)
def manual_review_view() -> HTMLResponse:
    html = f"""
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>数据治理人工复核决策台</title>
    <style>
      :root {{
        --ink: #1b1f24;
        --line: #d7ddd0;
        --brand: #0d6e5c;
        --good: #1b7f5f;
        --warn: #b77714;
        --bad: #a73838;
      }}
      body {{
        margin: 0;
        padding: 16px;
        font-family: "IBM Plex Sans", "PingFang SC", "Microsoft YaHei", sans-serif;
        background: #ecf2ee;
        color: var(--ink);
      }}
      .hero {{
        background: linear-gradient(120deg, #0a4f43, var(--brand));
        color: #f6fffc;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 12px;
      }}
      .hero h1 {{ margin: 0 0 6px; font-size: 24px; }}
      .hero p {{ margin: 0; font-size: 13px; opacity: 0.92; }}
      .ops {{ margin-top: 10px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
      button, input, select {{
        border: 1px solid #9db7ae;
        border-radius: 8px;
        padding: 6px 8px;
        background: #fff;
      }}
      .panel {{
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 12px;
      }}
      .kpi {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 8px;
        margin-bottom: 10px;
      }}
      .kpi-item {{
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 8px;
        background: #f8fbf9;
      }}
      .kpi-item .v {{ font-size: 22px; font-weight: 700; }}
      .table-wrap {{ overflow: auto; }}
      table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
      th, td {{
        border-bottom: 1px solid var(--line);
        text-align: left;
        vertical-align: top;
        white-space: nowrap;
        padding: 8px 9px;
      }}
      th {{ background: #edf3ef; }}
      .risk {{
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
      }}
      .risk-high {{ color: var(--bad); background: #fde9e9; }}
      .risk-medium {{ color: var(--warn); background: #fff4dd; }}
      .risk-low {{ color: var(--good); background: #e5f5ee; }}
      .status-good {{ color: var(--good); }}
      .status-bad {{ color: var(--bad); }}
      @media (max-width: 960px) {{
        .kpi {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      }}
    </style>
  </head>
  <body>
    <header class="hero">
      <h1>数据治理人工复核决策台</h1>
      <p id="meta">连接 PG 实时数据 | 更新时间：{escape(_now_iso())}</p>
      <div class="ops">
        <label><input id="pendingOnly" type="checkbox" checked /> 仅显示未决策</label>
        <input id="reviewer" type="text" value="huda" placeholder="reviewer" />
        <button id="refreshBtn" type="button">刷新</button>
      </div>
    </header>

    <section class="panel">
      <div class="kpi" id="kpi"></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>task/raw</th>
              <th>阶段</th>
              <th>raw_text</th>
              <th>候选规范地址</th>
              <th>置信度</th>
              <th>风险</th>
              <th>当前策略</th>
              <th>证据</th>
              <th>人工决策</th>
            </tr>
          </thead>
          <tbody id="queueBody"></tbody>
        </table>
      </div>
    </section>

    <script>
      const apiBase = '/v1/governance/manual-review';
      const queueBody = document.getElementById('queueBody');
      const kpi = document.getElementById('kpi');
      const pendingOnly = document.getElementById('pendingOnly');
      const reviewer = document.getElementById('reviewer');
      const refreshBtn = document.getElementById('refreshBtn');
      const meta = document.getElementById('meta');
      let current = [];

      const esc = (s) => String(s || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

      function riskBadge(level) {{
        const v = String(level || 'low');
        const cls = v === 'high' ? 'risk risk-high' : (v === 'medium' ? 'risk risk-medium' : 'risk risk-low');
        const label = v === 'high' ? '高' : (v === 'medium' ? '中' : '低');
        return `<span class="${{cls}}">${{label}}</span>`;
      }}

      function renderKpi(items) {{
        const pending = items.filter((x) => !x.review_status).length;
        const decided = items.length - pending;
        const highRisk = items.filter((x) => x.risk_level === 'high').length;
        const reviewed = items.filter((x) => String(x.task_status).toUpperCase() === 'REVIEWED').length;
        kpi.innerHTML = [
          ['待人工确认', pending],
          ['已决策', decided],
          ['高风险', highRisk],
          ['任务已REVIEWED', reviewed],
        ].map(([k, v]) => `<article class="kpi-item"><div>${{k}}</div><div class="v">${{v}}</div></article>`).join('');
      }}

      function rowAction(item) {{
        if (item.review_status) {{
          return `<span class="${{item.review_status === 'rejected' ? 'status-bad' : 'status-good'}}">已决策: ${{esc(item.review_status)}}</span><br/><small>${{esc(item.reviewer || '-')}} ${{esc(item.reviewed_at || '')}}</small>`;
        }}
        return `
          <select data-role="review_status">
            <option value="approved">approved</option>
            <option value="rejected">rejected</option>
            <option value="edited">edited</option>
          </select>
          <select data-role="next_route">
            <option value="downstream">downstream</option>
            <option value="rule_fix">rule_fix</option>
            <option value="manual_replay">manual_replay</option>
            <option value="on_hold">on_hold</option>
          </select>
          <input data-role="comment" placeholder="备注（可选）" />
          <input data-role="final_canon_text" placeholder="edited时可填规范地址" />
          <button data-action="submit" data-task-id="${{esc(item.task_id)}}" data-raw-id="${{esc(item.raw_id)}}">提交</button>
        `;
      }}

      function renderRows(items) {{
        if (!items.length) {{
          queueBody.innerHTML = '<tr><td colspan="9">暂无数据</td></tr>';
          return;
        }}
        queueBody.innerHTML = items.map((item) => `
          <tr>
            <td><strong>${{esc(item.task_id)}}</strong><br><small>${{esc(item.raw_id)}}</small></td>
            <td>${{esc(item.stage)}}</td>
            <td>${{esc(item.raw_text)}}</td>
            <td>${{esc(item.canon_text)}}</td>
            <td>${{Number(item.confidence || 0).toFixed(4)}}</td>
            <td>${{riskBadge(item.risk_level)}}</td>
            <td>${{esc(item.strategy)}}</td>
            <td><a href="${{esc(item.evidence_ref)}}" target="_blank" rel="noopener noreferrer">结果</a></td>
            <td>${{rowAction(item)}}</td>
          </tr>
        `).join('');
      }}

      async function refresh() {{
        const resp = await fetch(`${{apiBase}}/queue?pending_only=${{pendingOnly.checked ? 'true' : 'false'}}&limit=300`, {{ cache: 'no-store' }});
        if (!resp.ok) {{
          const txt = await resp.text();
          throw new Error(txt || 'queue load failed');
        }}
        const data = await resp.json();
        current = Array.isArray(data.items) ? data.items : [];
        renderKpi(current);
        renderRows(current);
        meta.textContent = `连接 PG 实时数据 | 更新时间：${{new Date(data.as_of).toLocaleString()}} | items=${{data.total}} pending=${{data.pending}}`;
      }}

      async function submitDecision(btn) {{
        const row = btn.closest('td');
        const reviewStatus = row.querySelector('[data-role="review_status"]').value;
        const nextRoute = row.querySelector('[data-role="next_route"]').value;
        const comment = row.querySelector('[data-role="comment"]').value;
        const finalCanonText = row.querySelector('[data-role="final_canon_text"]').value;
        const payload = {{
          task_id: btn.getAttribute('data-task-id'),
          raw_id: btn.getAttribute('data-raw-id'),
          review_status: reviewStatus,
          reviewer: reviewer.value || 'anonymous',
          next_route: nextRoute,
          comment: comment || '',
          final_canon_text: finalCanonText || null,
        }};
        const resp = await fetch(`${{apiBase}}/decision`, {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload),
        }});
        if (!resp.ok) {{
          const txt = await resp.text();
          throw new Error(txt || 'submit failed');
        }}
      }}

      queueBody.addEventListener('click', async (event) => {{
        const btn = event.target.closest('button[data-action="submit"]');
        if (!btn) return;
        try {{
          await submitDecision(btn);
          await refresh();
        }} catch (error) {{
          alert(error.message);
        }}
      }});

      refreshBtn.addEventListener('click', refresh);
      pendingOnly.addEventListener('change', refresh);
      refresh().catch((error) => {{
        meta.textContent = `加载失败: ${{error.message}}`;
      }});
    </script>
  </body>
</html>
"""
    return HTMLResponse(html)
