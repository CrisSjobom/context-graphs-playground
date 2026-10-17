/* ContextOps: dependency-free SVG graph explorer. Consumes /api/investigate's graph. */
(() => {
  'use strict';
  const NS = 'http://www.w3.org/2000/svg';
  const palette = { task: '#5eead4', event: '#93c5fd', finding: '#fbbf24' };
  const nodeRadius = { task: 29, event: 23, finding: 27 };
  const svg = document.getElementById('context-graph');
  const details = document.getElementById('node-details');
  const summary = document.getElementById('graph-summary');
  let model = { nodes: [], edges: [] };

  function element(tag, attributes = {}) {
    const item = document.createElementNS(NS, tag);
    for (const [name, value] of Object.entries(attributes)) item.setAttribute(name, String(value));
    return item;
  }

  function describe(node) {
    const related = model.edges.filter(edge => edge.source === node.id || edge.target === node.id);
    details.replaceChildren();
    const title = document.createElement('strong');
    title.textContent = node.label || node.id;
    const type = document.createElement('p');
    type.textContent = `Type: ${node.type} · ID: ${node.id}`;
    const time = document.createElement('p');
    if (node.time) time.textContent = `Occurred: ${node.time}`;
    const heading = document.createElement('p');
    heading.textContent = `${related.length} relationship(s)`;
    const list = document.createElement('ul');
    for (const edge of related) {
      const li = document.createElement('li');
      li.textContent = `${edge.source} — ${edge.label} → ${edge.target}`;
      list.append(li);
    }
    details.append(title, type);
    if (node.time) details.append(time);
    details.append(heading, list);
    svg.querySelectorAll('[data-node-id]').forEach(item => {
      item.classList.toggle('selected-node', item.getAttribute('data-node-id') === node.id);
    });
  }

  function layout(nodes, width, height) {
    const types = ['task', 'event', 'finding'];
    const columns = { task: width * 0.16, event: width * 0.49, finding: width * 0.84 };
    const result = new Map();
    for (const type of types) {
      const group = nodes.filter(node => node.type === type);
      group.forEach((node, index) => {
        result.set(node.id, {
          x: columns[type],
          y: (height * (index + 1)) / (group.length + 1),
        });
      });
    }
    return result;
  }

  function render(graph) {
    model = graph && Array.isArray(graph.nodes) && Array.isArray(graph.edges)
      ? graph : { nodes: [], edges: [] };
    svg.replaceChildren();
    details.textContent = 'Select a node to inspect relationships and evidence.';
    summary.textContent = `${model.nodes.length} nodes · ${model.edges.length} relationships`;
    if (!model.nodes.length) {
      const message = element('text', { x: 440, y: 210, 'text-anchor': 'middle', fill: '#a2b6cb' });
      message.textContent = 'No graph data for this task yet.';
      svg.append(message);
      return;
    }
    const width = 880;
    const height = Math.max(420, model.nodes.filter(n => n.type === 'event').length * 94);
    svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    const positions = layout(model.nodes, width, height);
    for (const edge of model.edges) {
      const a = positions.get(edge.source);
      const b = positions.get(edge.target);
      if (!a || !b) continue;
      const line = element('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y,
        stroke: '#51627b', 'stroke-width': 1.6, 'stroke-opacity': 0.9 });
      svg.append(line);
    }
    for (const node of model.nodes) {
      const position = positions.get(node.id);
      if (!position) continue;
      const group = element('g', { transform: `translate(${position.x} ${position.y})`,
        'data-node-id': node.id, tabindex: 0, role: 'button',
        'aria-label': `Inspect ${node.type}: ${node.label || node.id}` });
      const circle = element('circle', { r: nodeRadius[node.type] || 22, fill: palette[node.type] || '#cbd5e1',
        stroke: '#0b1120', 'stroke-width': 3 });
      const label = element('text', { x: 0, y: 47, 'text-anchor': 'middle', fill: '#e3eaf2',
        'font-size': 13 });
      const text = String(node.label || node.id);
      label.textContent = text.length > 24 ? `${text.slice(0, 22)}…` : text;
      const tooltip = element('title');
      tooltip.textContent = `${node.type}: ${node.label || node.id}`;
      group.append(circle, label, tooltip);
      const activate = () => describe(node);
      group.addEventListener('click', activate);
      group.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(); }
      });
      svg.append(group);
    }
    describe(model.nodes[0]);
  }

  window.ContextGraphExplorer = Object.freeze({ render });
})();
