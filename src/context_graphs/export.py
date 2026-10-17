"""Safe HTML/SVG export with no JavaScript or runtime dependencies."""

from html import escape
from pathlib import Path

from .model import Graph

COLORS = {
    "incident": "#fb7185", "job": "#38bdf8", "vehicle": "#a78bfa",
    "courier": "#fbbf24", "zone": "#34d399", "event": "#94a3b8",
    "decision": "#2dd4bf", "policy": "#f472b6",
}


def render_html(graph: Graph, path: Path) -> None:
    """Render a dependency-free, accessible operational map."""
    import json

    nodes = list(graph.nodes.values())
    count = max(len(nodes), 1)
    import math

    positions = {
        node.id: (500 + 315 * math.cos(2 * math.pi * i / count),
                  350 + 240 * math.sin(2 * math.pi * i / count))
        for i, node in enumerate(nodes)
    }
    edges_svg = []
    for edge in graph.edges:
        x1, y1 = positions[edge.source]
        x2, y2 = positions[edge.target]
        edges_svg.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            'stroke="#526178" stroke-width="2" marker-end="url(#arrow)"/>'
        )
    nodes_svg = []
    for node in nodes:
        x, y = positions[node.id]
        color = COLORS.get(node.kind, "#cbd5e1")
        title = escape(node.label)
        node_json = escape(json.dumps({"id": node.id, "type": node.kind, **node.attributes}))
        nodes_svg.append(
            f'<g class="node" tabindex="0" role="button" aria-label="{title}" '
            f'data-detail="{node_json}"><circle cx="{x:.1f}" cy="{y:.1f}" r="33" '
            f'fill="#162337" stroke="{color}" stroke-width="3"/>'
            f'<text x="{x:.1f}" y="{y+52:.1f}" text-anchor="middle">{title}</text></g>'
        )
    markup = "\n".join(edges_svg + nodes_svg)
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Context Graphs Playground | Operational trace</title>
<style>
:root{{color-scheme:dark;font-family:Inter,system-ui,sans-serif}}body{{margin:0;background:#0b1220;color:#dce8f5}}
header{{padding:28px max(24px,5vw);border-bottom:1px solid #29384c}}h1{{font-size:clamp(24px,3vw,36px);margin:0 0 8px}}
p{{color:#9eb0c3;line-height:1.6}}main{{display:grid;grid-template-columns:minmax(0,3fr) minmax(250px,1fr);gap:20px;padding:24px max(24px,5vw)}}
.panel{{border:1px solid #29384c;border-radius:16px;background:#101b2c;padding:18px;min-width:0}}
svg{{width:100%;height:auto;display:block}}svg text{{fill:#dce8f5;font-size:15px;font-weight:500;pointer-events:none}}
.node{{cursor:pointer;outline:none}}.node:focus circle,.node:hover circle{{stroke-width:6}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;color:#a5f3dc;line-height:1.7}}.chip{{color:#5eead4;font-size:12px;letter-spacing:.16em;font-weight:700}}
footer{{padding:0 5vw 25px;color:#94a3b8;font-size:13px}}
@media(max-width:800px){{main{{grid-template-columns:1fr}}}}
</style></head><body><header><div class="chip">CONTEXT / OPERATIONS / EXPLAINABILITY</div>
<h1>Operational Context Graph</h1><p>An incident is more than a status: trace the job, evidence, decision and policy behind it.</p></header>
<main><section class="panel"><svg viewBox="0 0 1000 700" role="img" aria-label="Directed operational context graph">
<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="25" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#526178"/></marker></defs>
{markup}</svg></section><aside class="panel"><div class="chip">NODE INSPECTOR</div><h2 id="selection">Choose a node</h2>
<p>Click a node to inspect its attributes and context. All data is synthetic.</p><pre id="detail">No node selected.</pre></aside></main>
<footer>Reference implementation · local, dependency-free visualization · no external services</footer>
<script>
for (const node of document.querySelectorAll('.node')) {{
  const show = () => {{
    const data = JSON.parse(node.dataset.detail);
    document.getElementById('selection').textContent = data.id;
    document.getElementById('detail').textContent = JSON.stringify(data,null,2);
  }};
  node.addEventListener('click', show);
  node.addEventListener('keydown', e => {{if(e.key === 'Enter' || e.key === ' '){{e.preventDefault();show()}}}});
}}
</script></body></html>'''
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
