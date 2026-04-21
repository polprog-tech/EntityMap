/**
 * EntityMap Panel - Interactive dependency graph visualization for Home Assistant.
 *
 * Uses LitElement for the component framework and D3.js for the force-directed
 * graph layout. Renders as SVG for crisp scaling and accessibility.
 */

const D3_CDN = "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js";

// ── Node type visual configuration ─────────────────────────────────
const NODE_CONFIG = {
  device:     { icon: "🔌", color: "#42A5F5", shape: "rect",    label: "Device" },
  entity:     { icon: "📡", color: "#66BB6A", shape: "circle",  label: "Entity" },
  automation: { icon: "⚙️", color: "#FFA726", shape: "diamond", label: "Automation" },
  script:     { icon: "📜", color: "#AB47BC", shape: "diamond", label: "Script" },
  scene:      { icon: "🎬", color: "#EC407A", shape: "rect",    label: "Scene" },
  helper:     { icon: "🔧", color: "#8D6E63", shape: "circle",  label: "Helper" },
  group:      { icon: "📁", color: "#78909C", shape: "rect",    label: "Group" },
  area:       { icon: "🏠", color: "#FFEE58", shape: "rect",    label: "Area" },
  unknown:    { icon: "❓", color: "#BDBDBD", shape: "circle",  label: "Unknown" },
};

const EDGE_COLORS = {
  high:   "var(--entitymap-edge-high, #78909c)",
  medium: "var(--entitymap-edge-medium, #b0bec5)",
  low:    "var(--entitymap-edge-low, #e0e0e0)",
};

const SEVERITY_COLORS = {
  critical: "#d32f2f",
  high:     "#f57c00",
  medium:   "#fbc02d",
  low:      "#66bb6a",
  info:     "#42a5f5",
};

class EntityMapPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._graph = null;
    this._findings = null;
    this._selectedNode = null;
    this._simulation = null;
    this._d3Loaded = false;
    this._filterTypes = new Set();
    this._searchQuery = "";
    this._viewMode = "graph"; // "graph" | "findings" | "hierarchy"
    this._hierarchy = null;
  }

  set hass(value) {
    this._hass = value;
    if (!this._graph) {
      this._loadData();
    }
  }

  set narrow(value) { this._narrow = value; }
  set route(value) { this._route = value; }
  set panel(value) { this._panel = value; }

  connectedCallback() {
    this._render();
    this._loadD3().then(() => this._loadData());
  }

  async _loadD3() {
    if (this._d3Loaded || window.d3) {
      this._d3Loaded = true;
      return;
    }
    return new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = D3_CDN;
      script.onload = () => { this._d3Loaded = true; resolve(); };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  async _loadData() {
    if (!this._hass) return;
    try {
      const [graphResult, findingsResult, hierarchyResult] = await Promise.all([
        this._hass.callWS({ type: "entitymap/graph" }),
        this._hass.callWS({ type: "entitymap/findings" }),
        this._hass.callWS({ type: "entitymap/hierarchy" }),
      ]);
      this._graph = graphResult;
      this._findings = findingsResult;
      this._hierarchy = hierarchyResult;
      this._render();
      if (this._viewMode === "graph" && this._d3Loaded) {
        this._renderGraph();
      }
    } catch (e) {
      console.error("EntityMap: Failed to load data", e);
      this._renderError("Failed to load dependency data. Is a scan complete?");
    }
  }

  async _triggerScan() {
    if (!this._hass) return;
    this._renderLoading("Scanning dependencies...");
    try {
      await this._hass.callWS({ type: "entitymap/scan" });
      await this._loadData();
    } catch (e) {
      console.error("EntityMap: Scan failed", e);
      this._renderError("Scan failed. Check logs for details.");
    }
  }

  async _selectNode(nodeId) {
    this._selectedNode = nodeId;
    if (!this._hass) return;
    try {
      const [impact, neighborhood, migration] = await Promise.all([
        this._hass.callWS({ type: "entitymap/impact", node_id: nodeId }),
        this._hass.callWS({ type: "entitymap/neighborhood", node_id: nodeId, depth: 2 }),
        this._hass.callWS({ type: "entitymap/migration", node_id: nodeId }),
      ]);
      this._selectedImpact = impact;
      this._selectedNeighborhood = neighborhood;
      this._selectedMigration = migration;
      this._renderDetailPanel();
      this._highlightNeighborhood(nodeId, neighborhood);
    } catch (e) {
      console.error("EntityMap: Failed to load node details", e);
    }
  }

  _render() {
    const root = this.shadowRoot;
    root.innerHTML = `
      <style>${this._getStyles()}</style>
      <div class="entitymap-container">
        <header class="entitymap-header">
          <div class="header-left">
            <h1>🗺️ EntityMap</h1>
            <span class="subtitle">${this._graph
              ? `${this._graph.node_count} nodes · ${this._graph.edge_count} dependencies`
              : "Loading..."
            }${this._findings ? ` · ${this._findings.count} issues` : ""}</span>
          </div>
          <div class="header-actions">
            <div class="view-tabs">
              <button class="tab ${this._viewMode === 'graph' ? 'active' : ''}"
                      data-mode="graph">Graph</button>
              <button class="tab ${this._viewMode === 'findings' ? 'active' : ''}"
                      data-mode="findings">Issues</button>
              <button class="tab ${this._viewMode === 'hierarchy' ? 'active' : ''}"
                      data-mode="hierarchy">Hierarchy</button>
            </div>
            <div class="search-box">
              <input type="text" placeholder="Search nodes..." class="search-input"
                     value="${this._searchQuery}" />
            </div>
            <button class="btn btn-primary scan-btn">↻ Rescan</button>
          </div>
        </header>
        <div class="entitymap-body">
          <div class="filter-bar">
            ${this._renderFilterChips()}
          </div>
          <div class="main-content">
            <div class="graph-area" id="graph-container">
              ${!this._graph ? '<div class="empty-state">Loading dependency graph...</div>' : ''}
            </div>
            <aside class="detail-panel ${this._selectedNode ? 'open' : ''}" id="detail-panel">
              ${this._selectedNode ? '' : '<div class="empty-state">Select a node to view details</div>'}
            </aside>
          </div>
        </div>
        <div class="legend">
          ${Object.entries(NODE_CONFIG).map(([type, cfg]) =>
            `<span class="legend-item">
              <span class="legend-dot" style="background:${cfg.color}"></span>
              ${cfg.label}
            </span>`
          ).join("")}
          <span class="legend-sep">|</span>
          <span class="legend-item">
            <span class="legend-line solid"></span> Direct
          </span>
          <span class="legend-item">
            <span class="legend-line dashed"></span> Inferred
          </span>
        </div>
        <footer class="entitymap-footer">
          <span>EntityMap v1.0.0</span>
          <span class="footer-sep">·</span>
          <span>by <a href="https://polprog.pl/" target="_blank" rel="noopener">POLPROG</a></span>
          <span class="footer-sep">·</span>
          <a href="https://github.com/polprog-tech/EntityMap" target="_blank" rel="noopener">📖 Docs</a>
          <span class="footer-sep">·</span>
          <a href="https://github.com/polprog-tech/EntityMap/issues" target="_blank" rel="noopener">🐛 Report Issue</a>
        </footer>
      </div>
    `;

    // Event listeners
    root.querySelector(".scan-btn")?.addEventListener("click", () => this._triggerScan());
    root.querySelectorAll(".tab").forEach(tab => {
      tab.addEventListener("click", (e) => {
        this._viewMode = e.target.dataset.mode;
        this._render();
        if (this._viewMode === "graph" && this._d3Loaded && this._graph) {
          requestAnimationFrame(() => this._renderGraph());
        } else if (this._viewMode === "findings") {
          this._renderFindingsList();
        } else if (this._viewMode === "hierarchy") {
          this._renderHierarchy();
        }
      });
    });
    root.querySelector(".search-input")?.addEventListener("input", (e) => {
      this._searchQuery = e.target.value.toLowerCase();
      this._applySearch();
    });
    root.querySelectorAll(".filter-chip").forEach(chip => {
      chip.addEventListener("click", (e) => {
        const type = e.target.closest(".filter-chip").dataset.type;
        if (this._filterTypes.has(type)) {
          this._filterTypes.delete(type);
        } else {
          this._filterTypes.add(type);
        }
        this._render();
        if (this._viewMode === "graph" && this._d3Loaded && this._graph) {
          requestAnimationFrame(() => this._renderGraph());
        }
      });
    });
  }

  _renderFilterChips() {
    return Object.entries(NODE_CONFIG).map(([type, cfg]) =>
      `<button class="filter-chip ${this._filterTypes.has(type) ? '' : 'active'}"
              data-type="${type}">
        ${cfg.icon} ${cfg.label}
      </button>`
    ).join("");
  }

  _renderGraph() {
    if (!this._graph || !window.d3) return;
    const container = this.shadowRoot.getElementById("graph-container");
    if (!container) return;
    container.innerHTML = "";

    const d3 = window.d3;
    const rect = container.getBoundingClientRect();
    const width = rect.width || 900;
    const height = rect.height || 600;

    // Filter nodes
    let nodes = this._graph.nodes.filter(n =>
      this._filterTypes.size === 0 || !this._filterTypes.has(n.node_type)
    );
    const nodeIds = new Set(nodes.map(n => n.node_id));
    let links = this._graph.edges.filter(e =>
      nodeIds.has(e.source) && nodeIds.has(e.target)
    );

    // Apply search filter
    if (this._searchQuery) {
      const q = this._searchQuery;
      const matchIds = new Set();
      nodes.forEach(n => {
        if (n.node_id.toLowerCase().includes(q) || n.title.toLowerCase().includes(q)) {
          matchIds.add(n.node_id);
        }
      });
      // Include neighbors of matched nodes
      links.forEach(l => {
        const src = typeof l.source === "object" ? l.source.node_id : l.source;
        const tgt = typeof l.target === "object" ? l.target.node_id : l.target;
        if (matchIds.has(src)) matchIds.add(tgt);
        if (matchIds.has(tgt)) matchIds.add(src);
      });
      nodes = nodes.filter(n => matchIds.has(n.node_id));
      const filteredIds = new Set(nodes.map(n => n.node_id));
      links = links.filter(e => {
        const src = typeof e.source === "object" ? e.source.node_id : e.source;
        const tgt = typeof e.target === "object" ? e.target.node_id : e.target;
        return filteredIds.has(src) && filteredIds.has(tgt);
      });
    }

    // Limit nodes for performance
    const MAX_NODES = 500;
    if (nodes.length > MAX_NODES) {
      nodes = nodes.slice(0, MAX_NODES);
      const limitedIds = new Set(nodes.map(n => n.node_id));
      links = links.filter(e => {
        const src = typeof e.source === "object" ? e.source.node_id : e.source;
        const tgt = typeof e.target === "object" ? e.target.node_id : e.target;
        return limitedIds.has(src) && limitedIds.has(tgt);
      });
    }

    // D3 force layout data (need id field for d3)
    const simNodes = nodes.map(n => ({ ...n, id: n.node_id }));
    const simLinks = links.map(l => ({
      ...l,
      source: l.source,
      target: l.target,
    }));

    const svg = d3.select(container)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height]);

    // Zoom container
    const g = svg.append("g");
    const zoom = d3.zoom()
      .scaleExtent([0.1, 5])
      .on("zoom", (event) => g.attr("transform", event.transform));
    svg.call(zoom);

    // Arrow marker
    svg.append("defs").selectAll("marker")
      .data(["arrow-high", "arrow-medium", "arrow-low"])
      .join("marker")
      .attr("id", d => d)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", d => EDGE_COLORS[d.split("-")[1]]);

    // Simulation
    const simulation = d3.forceSimulation(simNodes)
      .force("link", d3.forceLink(simLinks).id(d => d.id).distance(80))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(25));

    this._simulation = simulation;

    // Links
    const link = g.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(simLinks)
      .join("line")
      .attr("stroke", d => EDGE_COLORS[d.confidence] || EDGE_COLORS.high)
      .attr("stroke-width", d => d.confidence === "high" ? 2 : 1)
      .attr("stroke-dasharray", d => d.confidence === "low" ? "4,4" : d.confidence === "medium" ? "2,2" : "none")
      .attr("marker-end", d => `url(#arrow-${d.confidence || "high"})`)
      .attr("opacity", 0.6);

    // Node groups
    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(simNodes)
      .join("g")
      .attr("class", "node-group")
      .attr("cursor", "pointer")
      .call(d3.drag()
        .on("start", (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on("end", (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      );

    // Node shapes
    node.each(function(d) {
      const el = d3.select(this);
      const cfg = NODE_CONFIG[d.node_type] || NODE_CONFIG.unknown;
      const isMissing = !d.available;
      const fillColor = isMissing ? "#ff5252" : cfg.color;
      const strokeColor = isMissing ? "#d32f2f" : d3.color(cfg.color).darker(0.5);

      if (cfg.shape === "rect") {
        el.append("rect")
          .attr("width", 24).attr("height", 24)
          .attr("x", -12).attr("y", -12)
          .attr("rx", 4)
          .attr("fill", fillColor)
          .attr("stroke", strokeColor)
          .attr("stroke-width", 1.5);
      } else if (cfg.shape === "diamond") {
        el.append("polygon")
          .attr("points", "0,-14 14,0 0,14 -14,0")
          .attr("fill", fillColor)
          .attr("stroke", strokeColor)
          .attr("stroke-width", 1.5);
      } else {
        el.append("circle")
          .attr("r", 12)
          .attr("fill", fillColor)
          .attr("stroke", strokeColor)
          .attr("stroke-width", 1.5);
      }

      // Label
      el.append("text")
        .attr("dy", 26)
        .attr("text-anchor", "middle")
        .attr("font-size", "10px")
        .attr("fill", "var(--primary-text-color, #333)")
        .attr("font-family", "var(--paper-font-body1_-_font-family, sans-serif)")
        .attr("font-weight", "500")
        .text(d.title.length > 22 ? d.title.substring(0, 20) + "…" : d.title);

      // Missing badge
      if (isMissing) {
        el.append("circle")
          .attr("cx", 10).attr("cy", -10).attr("r", 5)
          .attr("fill", "#d32f2f");
        el.append("text")
          .attr("x", 10).attr("y", -7)
          .attr("text-anchor", "middle")
          .attr("font-size", "7px")
          .attr("fill", "white")
          .text("!");
      }
    });

    // Click handler
    node.on("click", (event, d) => {
      event.stopPropagation();
      this._selectNode(d.node_id);
    });

    // Deselect on background click
    svg.on("click", () => {
      this._selectedNode = null;
      this._resetHighlight();
      const panel = this.shadowRoot.getElementById("detail-panel");
      if (panel) {
        panel.classList.remove("open");
        panel.innerHTML = '<div class="empty-state">Select a node to view details</div>';
      }
    });

    // Tick
    simulation.on("tick", () => {
      link
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);
      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Fit to view after settling
    simulation.on("end", () => {
      const bounds = g.node().getBBox();
      const fullWidth = bounds.width || width;
      const fullHeight = bounds.height || height;
      const scale = Math.min(width / (fullWidth + 40), height / (fullHeight + 40), 1.5);
      const tx = width / 2 - (bounds.x + fullWidth / 2) * scale;
      const ty = height / 2 - (bounds.y + fullHeight / 2) * scale;
      svg.transition().duration(500).call(
        zoom.transform,
        d3.zoomIdentity.translate(tx, ty).scale(scale)
      );
    });
  }

  _highlightNeighborhood(nodeId, neighborhood) {
    if (!window.d3) return;
    const d3 = window.d3;
    const container = this.shadowRoot.getElementById("graph-container");
    if (!container) return;
    const svg = d3.select(container).select("svg");

    const neighborIds = new Set(neighborhood.nodes.map(n => n.node_id));
    neighborIds.add(nodeId);

    svg.selectAll(".node-group").attr("opacity", d =>
      neighborIds.has(d.node_id) ? 1 : 0.15
    );
    svg.selectAll(".links line").attr("opacity", d => {
      const src = typeof d.source === "object" ? d.source.node_id || d.source.id : d.source;
      const tgt = typeof d.target === "object" ? d.target.node_id || d.target.id : d.target;
      return neighborIds.has(src) && neighborIds.has(tgt) ? 0.8 : 0.05;
    });

    // Highlight selected node
    svg.selectAll(".node-group").each(function(d) {
      if (d.node_id === nodeId) {
        d3.select(this).select("rect, circle, polygon")
          .attr("stroke", "#fff")
          .attr("stroke-width", 3);
      }
    });
  }

  _resetHighlight() {
    if (!window.d3) return;
    const d3 = window.d3;
    const container = this.shadowRoot.getElementById("graph-container");
    if (!container) return;
    const svg = d3.select(container).select("svg");
    svg.selectAll(".node-group").attr("opacity", 1);
    svg.selectAll(".links line").attr("opacity", 0.6);
    svg.selectAll(".node-group").each(function(d) {
      const cfg = NODE_CONFIG[d.node_type] || NODE_CONFIG.unknown;
      d3.select(this).select("rect, circle, polygon")
        .attr("stroke-width", 1.5);
    });
  }

  _applySearch() {
    if (!window.d3 || !this._graph) return;
    // Re-render with search applied
    this._renderGraph();
  }

  _renderDetailPanel() {
    const panel = this.shadowRoot.getElementById("detail-panel");
    if (!panel || !this._selectedNode) return;
    panel.classList.add("open");

    const node = this._graph?.nodes?.find(n => n.node_id === this._selectedNode);
    const impact = this._selectedImpact;
    const migration = this._selectedMigration;
    const cfg = NODE_CONFIG[node?.node_type] || NODE_CONFIG.unknown;

    panel.innerHTML = `
      <div class="detail-header">
        <button class="close-btn" id="close-detail">✕</button>
        <div class="detail-title">
          <span class="node-badge" style="background:${cfg.color}">${cfg.icon} ${cfg.label}</span>
          <h2>${node?.title || this._selectedNode}</h2>
          <code class="node-id">${this._selectedNode}</code>
        </div>
        ${node && !node.available ? '<div class="warning-badge">⚠️ Missing / Unavailable</div>' : ''}
        ${node?.disabled ? '<div class="warning-badge muted">🚫 Disabled</div>' : ''}
      </div>

      ${impact ? `
      <section class="detail-section">
        <h3>📊 Impact Analysis</h3>
        <div class="impact-summary">
          <div class="risk-meter">
            <div class="risk-bar" style="width:${impact.risk_score}%;background:${SEVERITY_COLORS[impact.severity]}"></div>
          </div>
          <span class="risk-label">Risk: ${impact.risk_score.toFixed(0)}% - ${impact.severity}</span>
        </div>
        <p class="impact-text">${impact.summary}</p>
        ${Object.keys(impact.affected_by_type).length > 0 ? `
        <div class="affected-chips">
          ${Object.entries(impact.affected_by_type).map(([type, count]) => {
            const tcfg = NODE_CONFIG[type] || NODE_CONFIG.unknown;
            return `<span class="chip" style="background:${tcfg.color}20;border-color:${tcfg.color}">
              ${tcfg.icon} ${count} ${type}${count > 1 ? 's' : ''}
            </span>`;
          }).join("")}
        </div>
        ` : ''}
      </section>
      ` : ''}

      ${impact?.fragility_findings?.length > 0 ? `
      <section class="detail-section">
        <h3>⚠️ Fragility Issues</h3>
        <ul class="findings-list">
          ${impact.fragility_findings.map(f => `
            <li class="finding-item severity-${f.severity}">
              <span class="severity-dot" style="background:${SEVERITY_COLORS[f.severity]}"></span>
              <div>
                <strong>${f.fragility_type.replace(/_/g, " ")}</strong>
                <p>${f.rationale}</p>
                <p class="remediation">💡 ${f.remediation}</p>
              </div>
            </li>
          `).join("")}
        </ul>
      </section>
      ` : ''}

      ${migration?.suggestions?.length > 0 ? `
      <section class="detail-section">
        <h3>🔄 Migration Guidance</h3>
        <ul class="migration-list">
          ${migration.suggestions.map(s => `
            <li class="migration-item">
              <p>${s.description}</p>
              ${s.recommendation ? `<p class="recommendation">📋 ${s.recommendation}</p>` : ''}
              ${s.affected_items?.length > 0 ? `
                <details>
                  <summary>${s.affected_items.length} affected item(s)</summary>
                  <ul class="affected-list">
                    ${s.affected_items.map(i => `<li><code>${i}</code></li>`).join("")}
                  </ul>
                </details>
              ` : ''}
            </li>
          `).join("")}
        </ul>
      </section>
      ` : ''}
    `;

    panel.querySelector("#close-detail")?.addEventListener("click", () => {
      this._selectedNode = null;
      panel.classList.remove("open");
      panel.innerHTML = '<div class="empty-state">Select a node to view details</div>';
      this._resetHighlight();
    });
  }

  _renderFindingsList() {
    const container = this.shadowRoot.getElementById("graph-container");
    if (!container || !this._findings) return;

    const findings = this._findings.findings || [];
    container.innerHTML = `
      <div class="findings-view">
        <div class="findings-header">
          <h2>⚠️ Fragility Report</h2>
          <span class="count-badge">${findings.length} issue${findings.length !== 1 ? 's' : ''}</span>
        </div>
        ${findings.length === 0 ? '<div class="empty-state success">✅ No fragility issues detected!</div>' : ''}
        <div class="findings-grid">
          ${findings.map(f => `
            <div class="finding-card severity-${f.severity}" data-node="${f.node_id}">
              <div class="finding-card-header">
                <span class="severity-badge" style="background:${SEVERITY_COLORS[f.severity]}">${f.severity}</span>
                <span class="finding-type">${f.fragility_type.replace(/_/g, " ")}</span>
              </div>
              <p class="finding-rationale">${f.rationale}</p>
              <p class="finding-remediation">💡 ${f.remediation}</p>
              <div class="finding-meta">
                <code>${f.node_id}</code>
                ${f.related_node_ids?.map(r => `→ <code>${r}</code>`).join(" ") || ""}
              </div>
            </div>
          `).join("")}
        </div>
      </div>
    `;

    container.querySelectorAll(".finding-card").forEach(card => {
      card.addEventListener("click", () => {
        const nodeId = card.dataset.node;
        this._viewMode = "graph";
        this._searchQuery = "";
        this._render();
        requestAnimationFrame(() => {
          this._renderGraph();
          setTimeout(() => this._selectNode(nodeId), 200);
        });
      });
    });
  }

  _renderHierarchy() {
    const container = this.shadowRoot.getElementById("graph-container");
    if (!container || !this._hierarchy) return;

    if (!this._hierarchyMode) this._hierarchyMode = "list"; // "list" | "tree"
    if (!this._treeOrientation) this._treeOrientation = "horizontal"; // "horizontal" | "vertical"

    const h = this._hierarchy;
    const totalAreas = h.areas.length;
    const totalDevices = h.areas.reduce((s, a) => s + a.devices.length, 0) + h.unassigned_devices.length;

    container.innerHTML = `
      <div class="hierarchy-view">
        <div class="hierarchy-header">
          <h2>🏗️ Hierarchy</h2>
          <span class="count-badge">${totalAreas} areas · ${totalDevices} devices</span>
          <div class="hierarchy-actions">
            <div class="view-toggle">
              <button class="btn btn-sm ${this._hierarchyMode === 'list' ? 'toggle-active' : ''}" id="mode-list">☰ List</button>
              <button class="btn btn-sm ${this._hierarchyMode === 'tree' ? 'toggle-active' : ''}" id="mode-tree">🌳 Tree</button>
            </div>
            ${this._hierarchyMode === 'tree' ? `
              <div class="view-toggle">
                <button class="btn btn-sm ${this._treeOrientation === 'horizontal' ? 'toggle-active' : ''}" id="orient-h">↔ Horizontal</button>
                <button class="btn btn-sm ${this._treeOrientation === 'vertical' ? 'toggle-active' : ''}" id="orient-v">↕ Vertical</button>
              </div>
            ` : `
              <button class="btn btn-sm" id="expand-all">Expand all</button>
              <button class="btn btn-sm" id="collapse-all">Collapse all</button>
            `}
          </div>
        </div>
        <div class="hierarchy-content" id="hierarchy-content"></div>
      </div>
    `;

    // Mode toggle
    container.querySelector("#mode-list")?.addEventListener("click", () => {
      this._hierarchyMode = "list";
      this._renderHierarchy();
    });
    container.querySelector("#mode-tree")?.addEventListener("click", () => {
      this._hierarchyMode = "tree";
      this._renderHierarchy();
    });
    // Orientation toggle
    container.querySelector("#orient-h")?.addEventListener("click", () => {
      this._treeOrientation = "horizontal";
      this._renderHierarchy();
    });
    container.querySelector("#orient-v")?.addEventListener("click", () => {
      this._treeOrientation = "vertical";
      this._renderHierarchy();
    });

    const content = container.querySelector("#hierarchy-content");
    if (this._hierarchyMode === "list") {
      this._renderHierarchyList(content, h);
    } else {
      this._renderHierarchyTree(content, h);
    }
  }

  _renderHierarchyList(content, h) {
    const renderEntity = (ent) => {
      const cfg = NODE_CONFIG[ent.node_type] || NODE_CONFIG.entity;
      const badges = [];
      if (ent.disabled) badges.push('<span class="tree-badge disabled">disabled</span>');
      if (!ent.available) badges.push('<span class="tree-badge unavailable">unavailable</span>');
      return `
        <div class="tree-leaf" data-node="${ent.node_id}">
          <span class="tree-icon" style="color:${cfg.color}">${cfg.icon}</span>
          <span class="tree-title">${ent.title}</span>
          <code class="tree-id">${ent.node_id}</code>
          ${badges.join("")}
        </div>`;
    };

    const renderDevice = (dev) => {
      const entCount = dev.entities.length;
      const cfg = NODE_CONFIG.device;
      return `
        <details class="tree-device">
          <summary class="tree-branch" data-node="${dev.node_id}">
            <span class="tree-icon" style="color:${cfg.color}">${cfg.icon}</span>
            <span class="tree-title">${dev.title}</span>
            <span class="tree-count">${entCount}</span>
            ${dev.metadata?.manufacturer ? `<span class="tree-meta">${dev.metadata.manufacturer}${dev.metadata.model ? " · " + dev.metadata.model : ""}</span>` : ""}
          </summary>
          <div class="tree-children">
            ${dev.entities.length > 0
              ? dev.entities.map(renderEntity).join("")
              : '<div class="tree-empty">No entities</div>'}
          </div>
        </details>`;
    };

    const renderArea = (area) => {
      const devCount = area.devices.length;
      const directEntCount = area.entities.length;
      const totalChildren = devCount + directEntCount;
      return `
        <details class="tree-area" open>
          <summary class="tree-branch area-branch" data-node="${area.node_id}">
            <span class="tree-icon" style="color:${NODE_CONFIG.area.color}">🏠</span>
            <span class="tree-title area-title">${area.title}</span>
            <span class="tree-count">${area.device_count} dev</span>
            <span class="tree-count">${area.entity_count} total</span>
          </summary>
          <div class="tree-children">
            ${area.devices.map(renderDevice).join("")}
            ${area.entities.length > 0 ? `
              <div class="tree-direct-entities">
                <div class="tree-section-label">Direct entities</div>
                ${area.entities.map(renderEntity).join("")}
              </div>
            ` : ""}
            ${totalChildren === 0 ? '<div class="tree-empty">Empty area</div>' : ""}
          </div>
        </details>`;
    };

    content.innerHTML = `
      <div class="hierarchy-tree">
        ${h.areas.map(renderArea).join("")}
        ${h.unassigned_devices.length > 0 ? `
          <details class="tree-area" open>
            <summary class="tree-branch area-branch unassigned">
              <span class="tree-icon">📦</span>
              <span class="tree-title area-title">Unassigned devices</span>
              <span class="tree-count">${h.unassigned_devices.length} dev</span>
            </summary>
            <div class="tree-children">
              ${h.unassigned_devices.map(renderDevice).join("")}
            </div>
          </details>
        ` : ""}
        ${h.unassigned_entities.length > 0 ? `
          <details class="tree-area">
            <summary class="tree-branch area-branch unassigned">
              <span class="tree-icon">📦</span>
              <span class="tree-title area-title">Unassigned entities</span>
              <span class="tree-count">${h.unassigned_entities.length}</span>
            </summary>
            <div class="tree-children">
              ${h.unassigned_entities.map(renderEntity).join("")}
            </div>
          </details>
        ` : ""}
      </div>
    `;

    // Expand / collapse all
    const root = content.closest(".hierarchy-view");
    root.querySelector("#expand-all")?.addEventListener("click", () => {
      content.querySelectorAll("details").forEach(d => d.open = true);
    });
    root.querySelector("#collapse-all")?.addEventListener("click", () => {
      content.querySelectorAll("details").forEach(d => d.open = false);
    });

    // Double-click → go to graph
    content.querySelectorAll("[data-node]").forEach(el => {
      el.addEventListener("dblclick", (e) => {
        e.preventDefault();
        const nodeId = el.dataset.node;
        if (!nodeId) return;
        this._viewMode = "graph";
        this._searchQuery = "";
        this._render();
        requestAnimationFrame(() => {
          this._renderGraph();
          setTimeout(() => this._selectNode(nodeId), 200);
        });
      });
    });
  }

  _renderHierarchyTree(content, h) {
    if (!window.d3) {
      content.innerHTML = '<div class="empty-state">Loading D3 for tree visualization...</div>';
      this._loadD3().then(() => this._renderHierarchyTree(content, h));
      return;
    }
    const d3 = window.d3;
    const isVertical = this._treeOrientation === "vertical";

    // Build tree data structure for d3.hierarchy
    const treeData = {
      name: "Home",
      _icon: "🏠",
      _color: "#78909C",
      _type: "root",
      children: []
    };

    // Areas
    for (const area of h.areas) {
      const areaNode = {
        name: area.title,
        _icon: "🏠",
        _color: NODE_CONFIG.area.color,
        _type: "area",
        _nodeId: area.node_id,
        children: []
      };
      for (const dev of area.devices) {
        const devNode = {
          name: dev.title,
          _icon: "🔌",
          _color: NODE_CONFIG.device.color,
          _type: "device",
          _nodeId: dev.node_id,
          children: dev.entities.map(ent => ({
            name: ent.title,
            _icon: (NODE_CONFIG[ent.node_type] || NODE_CONFIG.entity).icon,
            _color: (NODE_CONFIG[ent.node_type] || NODE_CONFIG.entity).color,
            _type: ent.node_type,
            _nodeId: ent.node_id,
          }))
        };
        areaNode.children.push(devNode);
      }
      for (const ent of area.entities) {
        areaNode.children.push({
          name: ent.title,
          _icon: (NODE_CONFIG[ent.node_type] || NODE_CONFIG.entity).icon,
          _color: (NODE_CONFIG[ent.node_type] || NODE_CONFIG.entity).color,
          _type: ent.node_type,
          _nodeId: ent.node_id,
        });
      }
      if (areaNode.children.length > 0) treeData.children.push(areaNode);
    }

    // Unassigned
    if (h.unassigned_devices.length > 0 || h.unassigned_entities.length > 0) {
      const unassigned = {
        name: "Unassigned",
        _icon: "📦",
        _color: "#9E9E9E",
        _type: "unassigned",
        children: []
      };
      for (const dev of h.unassigned_devices) {
        unassigned.children.push({
          name: dev.title,
          _icon: "🔌",
          _color: NODE_CONFIG.device.color,
          _type: "device",
          _nodeId: dev.node_id,
          children: dev.entities.map(ent => ({
            name: ent.title,
            _icon: (NODE_CONFIG[ent.node_type] || NODE_CONFIG.entity).icon,
            _color: (NODE_CONFIG[ent.node_type] || NODE_CONFIG.entity).color,
            _type: ent.node_type,
            _nodeId: ent.node_id,
          }))
        });
      }
      for (const ent of h.unassigned_entities) {
        unassigned.children.push({
          name: ent.title,
          _icon: (NODE_CONFIG[ent.node_type] || NODE_CONFIG.entity).icon,
          _color: (NODE_CONFIG[ent.node_type] || NODE_CONFIG.entity).color,
          _type: ent.node_type,
          _nodeId: ent.node_id,
        });
      }
      treeData.children.push(unassigned);
    }

    if (treeData.children.length === 0) {
      content.innerHTML = '<div class="empty-state">No hierarchy data. Run a scan first.</div>';
      return;
    }

    // Calculate dimensions
    const root = d3.hierarchy(treeData);
    const totalLeaves = root.leaves().length;
    const nodeSpacing = 28;
    const containerRect = content.parentElement.getBoundingClientRect();
    const baseWidth = containerRect.width || 900;

    let width, height, marginLeft, marginTop;
    if (isVertical) {
      width = Math.max(600, totalLeaves * nodeSpacing + 120);
      height = Math.max(400, (root.height + 1) * 120 + 80);
      marginLeft = 40;
      marginTop = 40;
    } else {
      height = Math.max(400, totalLeaves * nodeSpacing + 80);
      width = baseWidth;
      marginLeft = 40;
      marginTop = 40;
    }
    const marginRight = 200;

    // D3 tree layout
    const treeLayout = isVertical
      ? d3.tree().size([width - marginLeft - marginRight, height - marginTop - 60])
      : d3.tree().size([height - 80, width - marginLeft - marginRight]);
    treeLayout(root);

    content.innerHTML = "";

    const svg = d3.select(content)
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .attr("class", "hierarchy-svg");

    const g = svg.append("g")
      .attr("transform", `translate(${marginLeft}, ${marginTop})`);

    // Zoom
    const zoom = d3.zoom()
      .scaleExtent([0.3, 3])
      .on("zoom", (event) => g.attr("transform", event.transform));
    svg.call(zoom);
    svg.call(zoom.transform, d3.zoomIdentity.translate(marginLeft, marginTop));

    // Links (curved paths)
    const linkGen = isVertical
      ? d3.linkVertical().x(d => d.x).y(d => d.y)
      : d3.linkHorizontal().x(d => d.y).y(d => d.x);
    g.selectAll(".tree-link")
      .data(root.links())
      .join("path")
      .attr("class", "tree-link")
      .attr("fill", "none")
      .attr("stroke", "var(--em-border, #e0e0e0)")
      .attr("stroke-width", 1.5)
      .attr("d", linkGen);

    // Nodes
    const node = g.selectAll(".tree-node")
      .data(root.descendants())
      .join("g")
      .attr("class", "tree-node")
      .attr("transform", d => isVertical ? `translate(${d.x},${d.y})` : `translate(${d.y},${d.x})`)
      .attr("cursor", d => d.data._nodeId ? "pointer" : "default");

    // Node circles
    node.append("circle")
      .attr("r", d => d.children ? 6 : 5)
      .attr("fill", d => d.data._color || "#78909C")
      .attr("stroke", d => d3.color(d.data._color || "#78909C").darker(0.5))
      .attr("stroke-width", 1.5);

    // Node icon
    node.append("text")
      .attr("x", isVertical ? 0 : -18)
      .attr("dy", isVertical ? -16 : "0.35em")
      .attr("text-anchor", "middle")
      .attr("font-size", "12px")
      .text(d => d.data._icon || "");

    // Node label
    node.append("text")
      .attr("x", d => isVertical
        ? 0
        : (d.children ? -24 : 12))
      .attr("dy", d => isVertical
        ? (d.children ? -28 : 18)
        : (d.children ? -12 : "0.35em"))
      .attr("text-anchor", d => isVertical
        ? "middle"
        : (d.children ? "end" : "start"))
      .attr("font-size", "12px")
      .attr("font-weight", d => d.children ? "600" : "400")
      .attr("fill", "var(--em-text, #333)")
      .attr("font-family", "var(--paper-font-body1_-_font-family, sans-serif)")
      .text(d => {
        const maxLen = d.children ? 30 : 35;
        return d.data.name.length > maxLen ? d.data.name.substring(0, maxLen - 1) + "…" : d.data.name;
      });

    // Click → navigate to graph
    node.filter(d => d.data._nodeId)
      .on("click", (event, d) => {
        event.stopPropagation();
        this._viewMode = "graph";
        this._searchQuery = "";
        this._render();
        requestAnimationFrame(() => {
          this._renderGraph();
          setTimeout(() => this._selectNode(d.data._nodeId), 200);
        });
      })
      .on("mouseover", function(event, d) {
        d3.select(this).select("circle")
          .attr("stroke-width", 3)
          .attr("stroke", "#fff");
      })
      .on("mouseout", function(event, d) {
        d3.select(this).select("circle")
          .attr("stroke-width", 1.5)
          .attr("stroke", d3.color(d.data._color || "#78909C").darker(0.5));
      });

    // Fit to view
    const bounds = g.node().getBBox();
    const scale = Math.min(
      (width - 20) / (bounds.width + 60),
      (height - 20) / (bounds.height + 60),
      1.2
    );
    const tx = 20 - bounds.x * scale;
    const ty = (height / 2) - (bounds.y + bounds.height / 2) * scale;
    svg.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
  }

  _renderLoading(message) {
    const container = this.shadowRoot.getElementById("graph-container");
    if (container) {
      container.innerHTML = `<div class="loading-state"><div class="spinner"></div><p>${message}</p></div>`;
    }
  }

  _renderError(message) {
    const container = this.shadowRoot.getElementById("graph-container");
    if (container) {
      container.innerHTML = `<div class="error-state">❌ ${message}</div>`;
    }
  }

  _getStyles() {
    return `
      :host {
        display: block;
        height: 100%;
        --em-bg: var(--card-background-color, #fff);
        --em-surface: var(--secondary-background-color, #f5f5f5);
        --em-text: var(--primary-text-color, #212121);
        --em-text-secondary: var(--secondary-text-color, #757575);
        --em-border: var(--divider-color, #e0e0e0);
        --em-primary: var(--primary-color, #1A73E8);
        --em-radius: 12px;
        --em-shadow-sm: 0 1px 3px rgba(0,0,0,0.06);
        --em-shadow-md: 0 2px 8px rgba(0,0,0,0.10);
        --em-transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      }
      * { box-sizing: border-box; margin: 0; padding: 0; }

      /* Layout */
      .entitymap-container {
        display: flex; flex-direction: column; height: 100vh;
        background: var(--em-surface); color: var(--em-text);
        font-family: var(--paper-font-body1_-_font-family, "Roboto", sans-serif);
      }

      /* Header */
      .entitymap-header {
        display: flex; align-items: center; justify-content: space-between;
        padding: 14px 24px; background: var(--em-bg);
        border-bottom: 1px solid var(--em-border);
        flex-wrap: wrap; gap: 10px;
        box-shadow: var(--em-shadow-sm);
        z-index: 2;
      }
      .header-left h1 { font-size: 20px; font-weight: 600; letter-spacing: -0.01em; }
      .subtitle { font-size: 13px; color: var(--em-text-secondary); margin-top: 2px; }
      .header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

      /* Tabs */
      .view-tabs {
        display: flex; gap: 2px; background: var(--em-surface);
        border-radius: 10px; padding: 3px;
      }
      .tab {
        padding: 7px 16px; border: none; border-radius: 8px; cursor: pointer;
        background: transparent; color: var(--em-text-secondary); font-size: 13px;
        font-weight: 500; transition: all var(--em-transition);
      }
      .tab.active {
        background: var(--em-primary); color: #fff;
        box-shadow: 0 1px 4px rgba(26,115,232,0.3);
      }
      .tab:hover:not(.active) { background: var(--em-border); }
      .tab:focus-visible {
        outline: 2px solid var(--em-primary); outline-offset: 2px;
      }

      /* Search */
      .search-box { position: relative; }
      .search-input {
        padding: 7px 14px; border-radius: 10px; border: 1px solid var(--em-border);
        background: var(--em-surface); color: var(--em-text); font-size: 13px;
        width: 220px; outline: none; transition: all var(--em-transition);
      }
      .search-input:focus {
        border-color: var(--em-primary);
        box-shadow: 0 0 0 3px rgba(26,115,232,0.12);
      }
      .search-input::placeholder { color: var(--em-text-secondary); opacity: 0.7; }

      /* Buttons */
      .btn {
        padding: 7px 16px; border: 1px solid var(--em-border); border-radius: 10px;
        cursor: pointer; font-size: 13px; font-weight: 500;
        transition: all var(--em-transition);
        background: var(--em-bg); color: var(--em-text);
      }
      .btn:hover { box-shadow: var(--em-shadow-sm); }
      .btn:focus-visible { outline: 2px solid var(--em-primary); outline-offset: 2px; }
      .btn-primary {
        background: var(--em-primary); color: #fff; border-color: var(--em-primary);
      }
      .btn-primary:hover { opacity: 0.92; box-shadow: 0 2px 8px rgba(26,115,232,0.3); }

      /* Filter bar */
      .filter-bar {
        display: flex; gap: 6px; padding: 10px 24px; flex-wrap: wrap;
        border-bottom: 1px solid var(--em-border); background: var(--em-bg);
      }
      .filter-chip {
        padding: 5px 12px; border-radius: 20px; border: 1px solid var(--em-border);
        cursor: pointer; font-size: 12px; font-weight: 500;
        transition: all var(--em-transition);
        background: var(--em-surface); color: var(--em-text-secondary);
        user-select: none;
      }
      .filter-chip.active {
        background: var(--em-primary); color: #fff;
        border-color: var(--em-primary); opacity: 0.9;
      }
      .filter-chip:hover { transform: translateY(-1px); box-shadow: var(--em-shadow-sm); }
      .filter-chip:focus-visible { outline: 2px solid var(--em-primary); outline-offset: 2px; }

      /* Body */
      .entitymap-body { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
      .main-content { flex: 1; display: flex; overflow: hidden; }
      .graph-area {
        flex: 1; overflow: hidden; position: relative;
        background: var(--em-bg);
      }
      .graph-area svg { width: 100%; height: 100%; }

      /* Detail panel */
      .detail-panel {
        width: 0; overflow: hidden; background: var(--em-bg);
        border-left: 1px solid var(--em-border);
        transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: -2px 0 12px rgba(0,0,0,0.04);
      }
      .detail-panel.open { width: 400px; overflow-y: auto; }
      .detail-header {
        padding: 20px; border-bottom: 1px solid var(--em-border);
        position: relative; background: var(--em-bg);
      }
      .close-btn {
        position: absolute; top: 14px; right: 14px; background: var(--em-surface);
        border: 1px solid var(--em-border); border-radius: 8px;
        cursor: pointer; font-size: 16px; color: var(--em-text-secondary);
        width: 32px; height: 32px; display: flex; align-items: center;
        justify-content: center; transition: all var(--em-transition);
      }
      .close-btn:hover { background: var(--em-border); }
      .close-btn:focus-visible { outline: 2px solid var(--em-primary); outline-offset: 2px; }
      .detail-title h2 { font-size: 16px; margin: 10px 0 4px; font-weight: 600; }
      .node-id { font-size: 11px; color: var(--em-text-secondary); word-break: break-all; }
      .node-badge {
        display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px;
        font-weight: 600; color: #000;
      }
      .warning-badge {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 6px 12px; border-radius: 8px; font-size: 12px;
        background: #fff3e0; color: #e65100; margin-top: 10px; font-weight: 500;
      }
      .warning-badge.muted { background: var(--em-surface); color: #9e9e9e; }

      /* Detail sections */
      .detail-section { padding: 20px; border-bottom: 1px solid var(--em-border); }
      .detail-section h3 {
        font-size: 14px; font-weight: 600; margin-bottom: 12px;
        letter-spacing: -0.01em;
      }
      .impact-summary { margin-bottom: 12px; }
      .risk-meter {
        height: 8px; background: var(--em-surface); border-radius: 4px;
        overflow: hidden; margin-bottom: 6px;
      }
      .risk-bar {
        height: 100%; border-radius: 4px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
      }
      .risk-label {
        font-size: 12px; color: var(--em-text-secondary);
        text-transform: uppercase; font-weight: 500; letter-spacing: 0.04em;
      }
      .impact-text { font-size: 13px; line-height: 1.6; margin: 10px 0; }
      .affected-chips { display: flex; flex-wrap: wrap; gap: 8px; }
      .chip {
        padding: 4px 10px; border-radius: 16px; font-size: 11px;
        border: 1px solid; white-space: nowrap; font-weight: 500;
      }

      /* Findings & migration lists */
      .findings-list, .migration-list { list-style: none; }
      .finding-item, .migration-item {
        padding: 12px 0; border-bottom: 1px solid var(--em-surface);
        display: flex; gap: 10px; font-size: 13px; line-height: 1.6;
      }
      .finding-item:last-child, .migration-item:last-child { border-bottom: none; }
      .severity-dot {
        width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
        margin-top: 5px;
      }
      .remediation, .recommendation {
        font-size: 12px; color: var(--em-text-secondary); margin-top: 6px;
        line-height: 1.5;
      }
      details { margin-top: 8px; font-size: 12px; }
      summary { cursor: pointer; color: var(--em-primary); font-weight: 500; }
      .affected-list { padding-left: 18px; margin-top: 6px; }
      .affected-list li { margin: 3px 0; }
      code {
        font-size: 11px; background: var(--em-surface); padding: 2px 6px;
        border-radius: 4px; word-break: break-all;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
      }

      /* Legend */
      .legend {
        display: flex; align-items: center; gap: 14px; padding: 10px 24px;
        border-top: 1px solid var(--em-border); background: var(--em-bg);
        font-size: 11px; color: var(--em-text-secondary); flex-wrap: wrap;
      }
      .legend-item { display: flex; align-items: center; gap: 5px; }
      .legend-dot { width: 10px; height: 10px; border-radius: 50%; }
      .legend-line { width: 20px; height: 2px; background: #78909c; }
      .legend-line.dashed {
        background: repeating-linear-gradient(90deg, #78909c 0, #78909c 4px, transparent 4px, transparent 8px);
      }
      .legend-sep { color: var(--em-border); }

      /* Footer */
      .entitymap-footer {
        display: flex; align-items: center; justify-content: center; gap: 8px;
        padding: 6px 24px; font-size: 11px; color: var(--em-text-secondary);
        border-top: 1px solid var(--em-border); background: var(--em-bg);
        flex-shrink: 0;
      }
      .entitymap-footer a {
        color: var(--em-primary); text-decoration: none;
      }
      .entitymap-footer a:hover { text-decoration: underline; }
      .footer-sep { color: var(--em-border); }

      /* Empty / loading / error states */
      .empty-state {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; height: 100%;
        font-size: 15px; color: var(--em-text-secondary); padding: 40px;
        text-align: center; gap: 8px;
      }
      .empty-state.success { color: #2e7d32; }
      .loading-state {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; height: 100%; gap: 16px;
      }
      .spinner {
        width: 36px; height: 36px; border: 3px solid var(--em-border);
        border-top-color: var(--em-primary); border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }
      .loading-state p {
        font-size: 14px; color: var(--em-text-secondary); font-weight: 500;
      }
      @keyframes spin { to { transform: rotate(360deg); } }
      .error-state {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; height: 100%;
        font-size: 14px; color: #d32f2f; padding: 40px;
        text-align: center; gap: 8px;
      }

      /* Findings view */
      .findings-view { padding: 24px; overflow-y: auto; height: 100%; }
      .findings-header {
        display: flex; align-items: center; gap: 12px; margin-bottom: 20px;
      }
      .findings-header h2 { font-size: 18px; font-weight: 600; }
      .count-badge {
        padding: 3px 12px; border-radius: 16px; font-size: 12px; font-weight: 600;
        background: var(--em-primary); color: #fff;
      }
      .findings-grid {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 14px;
      }
      .finding-card {
        background: var(--em-bg); border: 1px solid var(--em-border);
        border-radius: var(--em-radius); padding: 16px; cursor: pointer;
        transition: all var(--em-transition); border-left: 4px solid transparent;
      }
      .finding-card:hover {
        box-shadow: var(--em-shadow-md); transform: translateY(-1px);
      }
      .finding-card:focus-visible {
        outline: 2px solid var(--em-primary); outline-offset: 2px;
      }
      .finding-card.severity-critical { border-left-color: ${SEVERITY_COLORS.critical}; }
      .finding-card.severity-high { border-left-color: ${SEVERITY_COLORS.high}; }
      .finding-card.severity-medium { border-left-color: ${SEVERITY_COLORS.medium}; }
      .finding-card.severity-low { border-left-color: ${SEVERITY_COLORS.low}; }
      .finding-card.severity-info { border-left-color: ${SEVERITY_COLORS.info}; }
      .finding-card-header {
        display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
      }
      .severity-badge {
        padding: 3px 10px; border-radius: 8px; font-size: 10px;
        text-transform: uppercase; color: #fff; font-weight: 700;
        letter-spacing: 0.04em;
      }
      .finding-type { font-size: 13px; font-weight: 600; text-transform: capitalize; }
      .finding-rationale { font-size: 13px; line-height: 1.6; margin-bottom: 8px; }
      .finding-remediation {
        font-size: 12px; color: var(--em-text-secondary); margin-bottom: 10px;
        line-height: 1.5;
      }
      .finding-meta { font-size: 11px; color: var(--em-text-secondary); }

      /* Keyboard focus ring for graph nodes (SVG) */
      .node-group:focus { outline: none; }
      .node-group:focus-visible rect,
      .node-group:focus-visible circle,
      .node-group:focus-visible polygon {
        stroke: var(--em-primary, #1A73E8); stroke-width: 3;
      }

      /* Hierarchy view */
      .hierarchy-view { padding: 24px; overflow: hidden; height: 100%; display: flex; flex-direction: column; }
      .hierarchy-header {
        display: flex; align-items: center; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;
        flex-shrink: 0;
      }
      .hierarchy-header h2 { font-size: 18px; font-weight: 600; }
      .hierarchy-actions { display: flex; gap: 6px; margin-left: auto; align-items: center; }
      .hierarchy-content { flex: 1; overflow-y: auto; }
      .view-toggle {
        display: flex; gap: 2px; background: var(--em-surface);
        border-radius: 8px; padding: 2px;
      }
      .toggle-active {
        background: var(--em-primary) !important; color: #fff !important;
        border-color: var(--em-primary) !important;
      }
      .btn-sm {
        padding: 4px 12px; font-size: 11px; border-radius: 8px;
        border: 1px solid var(--em-border); background: var(--em-bg);
        color: var(--em-text-secondary); cursor: pointer;
        transition: all var(--em-transition);
      }
      .btn-sm:hover { background: var(--em-surface); box-shadow: var(--em-shadow-sm); }

      /* SVG tree */
      .hierarchy-svg { width: 100%; height: 100%; }

      .hierarchy-tree { display: flex; flex-direction: column; gap: 8px; }

      /* Area level */
      .tree-area {
        background: var(--em-bg); border: 1px solid var(--em-border);
        border-radius: var(--em-radius); overflow: hidden;
      }
      .tree-area > summary { list-style: none; }
      .tree-area > summary::-webkit-details-marker { display: none; }

      .tree-branch {
        display: flex; align-items: center; gap: 8px; padding: 12px 16px;
        cursor: pointer; user-select: none;
        transition: background var(--em-transition);
      }
      .tree-branch:hover { background: var(--em-surface); }
      .area-branch {
        font-weight: 600; font-size: 14px;
        border-bottom: 1px solid var(--em-border);
      }
      .area-branch.unassigned { color: var(--em-text-secondary); }
      .area-title { flex: 1; }

      .tree-icon { font-size: 16px; flex-shrink: 0; width: 22px; text-align: center; }
      .tree-title { font-size: 13px; }
      .tree-count {
        padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 600;
        background: var(--em-surface); color: var(--em-text-secondary);
        white-space: nowrap;
      }
      .tree-meta {
        font-size: 10px; color: var(--em-text-secondary); margin-left: auto;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 200px;
      }
      .tree-id {
        font-size: 10px; color: var(--em-text-secondary); margin-left: auto;
        flex-shrink: 0;
      }

      /* Device level */
      .tree-device {
        border-top: 1px solid var(--em-surface);
      }
      .tree-device > summary { list-style: none; padding-left: 32px; }
      .tree-device > summary::-webkit-details-marker { display: none; }
      .tree-device > .tree-children { padding-left: 32px; }

      /* Entity leaf */
      .tree-leaf {
        display: flex; align-items: center; gap: 8px;
        padding: 6px 16px 6px 64px; font-size: 13px;
        cursor: default;
        transition: background var(--em-transition);
        border-top: 1px solid var(--em-surface);
      }
      .tree-leaf:hover { background: rgba(26,115,232,0.04); }

      .tree-badge {
        padding: 1px 6px; border-radius: 6px; font-size: 9px; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.03em;
      }
      .tree-badge.disabled { background: #eeeeee; color: #9e9e9e; }
      .tree-badge.unavailable { background: #ffebee; color: #d32f2f; }

      .tree-empty {
        padding: 10px 16px 10px 64px; font-size: 12px;
        color: var(--em-text-secondary); font-style: italic;
      }
      .tree-section-label {
        padding: 8px 16px 4px 48px; font-size: 11px; font-weight: 600;
        color: var(--em-text-secondary); text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .tree-children { padding-bottom: 4px; }
    `;
  }
}

customElements.define("entitymap-panel", EntityMapPanel);
