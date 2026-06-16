/** EntityMap panel: a Shadow-DOM custom element composing the view mixins. */

import { NODE_CONFIG, COLORBLIND_COLORS, D3_CDN } from "./constants.js";
import { LayoutView } from "./layout.js";
import { GraphView } from "./graph-view.js";
import { GraphRenderView } from "./graph-render.js";
import { GraphInteractionsView } from "./graph-interactions.js";
import { HierarchyView } from "./hierarchy-view.js";
import { HierarchyTreeView } from "./hierarchy-tree.js";
import { FindingsView } from "./findings-view.js";
import { DetailView } from "./detail-view.js";

class EntityMapPanel extends LayoutView(
  DetailView(
    FindingsView(
      HierarchyTreeView(
        HierarchyView(
          GraphInteractionsView(GraphRenderView(GraphView(HTMLElement))),
        ),
      ),
    ),
  ),
) {
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
    this._mmViewport = null;
    try {
      this._density = localStorage.getItem("entitymap-density") === "compact" ? "compact" : "comfortable";
      this._colorblind = localStorage.getItem("entitymap-colorblind") === "1";
    } catch (e) {
      this._density = "comfortable";
      this._colorblind = false;
    }

    this._focusNode = null;
    this._pathMode = false;
    this._pathEndpoints = [];
    this._pathNodes = null;
    this._scopeFilter = null;

    this._onKeyDown = this._onKeyDown.bind(this);
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
    this.shadowRoot.addEventListener("keydown", this._onKeyDown);
  }

  disconnectedCallback() {
    this.shadowRoot.removeEventListener("keydown", this._onKeyDown);
  }

  _onKeyDown(e) {
    if (e.key !== "Escape") {
      return;
    }

    if (this._focusNode || this._pathMode || this._pathNodes) {
      e.stopPropagation();
      this._clearGraphModes();
      return;
    }

    if (this._selectedNode) {
      e.stopPropagation();
      this._closeDetail();
    }
  }

  _clearGraphModes() {
    this._focusNode = null;
    this._pathMode = false;
    this._pathEndpoints = [];
    this._pathNodes = null;
    this._render();
    this._renderCurrentView();
  }

  _announce(message) {
    const live = this.shadowRoot.getElementById("em-live");

    if (live) {
      live.textContent = message;
    }
  }

  _typeColor(type) {
    if (this._colorblind) return COLORBLIND_COLORS[type] || COLORBLIND_COLORS.unknown;
    return (NODE_CONFIG[type] || NODE_CONFIG.unknown).color;
  }

  _renderCurrentView() {
    if (this._viewMode === "graph" && this._d3Loaded && this._graph) {
      requestAnimationFrame(() => this._renderGraph());
    } else if (this._viewMode === "findings") {
      this._renderFindingsList();
    } else if (this._viewMode === "hierarchy") {
      this._renderHierarchy();
    }
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
    this._userMovedGraph = true;

    if (!this._hass) {
      return;
    }

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

      const node = this._graph?.nodes?.find(n => n.node_id === nodeId);
      this._announce(`Selected ${node?.title || nodeId}`);
    } catch (e) {
      console.error("EntityMap: Failed to load node details", e);
    }
  }

  _render() {
    const root = this.shadowRoot;
    root.innerHTML = this._shellMarkup();

    root.querySelector(".scan-btn")?.addEventListener("click", () => this._triggerScan());

    root.querySelectorAll(".tab").forEach(tab => {
      tab.addEventListener("click", (e) => {
        this._viewMode = e.target.dataset.mode;
        this._render();
        this._renderCurrentView();
      });
    });

    root.querySelector(".search-input")?.addEventListener("input", (e) => {
      this._searchQuery = e.target.value.toLowerCase();
      this._applySearch();
    });

    const toggleType = (type) => {
      if (!type) return;
      if (this._filterTypes.has(type)) this._filterTypes.delete(type);
      else this._filterTypes.add(type);
      this._render();
      this._renderCurrentView();
    };

    root.querySelectorAll(".filter-chip").forEach(chip =>
      chip.addEventListener("click", () => toggleType(chip.dataset.type))
    );

    root.querySelectorAll(".legend-toggle").forEach(item =>
      item.addEventListener("click", () => toggleType(item.dataset.type))
    );

    root.getElementById("density-toggle")?.addEventListener("click", () => {
      this._density = this._density === "compact" ? "comfortable" : "compact";
      try { localStorage.setItem("entitymap-density", this._density); } catch (e) {}
      this._render();
      this._renderCurrentView();
    });

    root.getElementById("cb-toggle")?.addEventListener("click", () => {
      this._colorblind = !this._colorblind;
      try { localStorage.setItem("entitymap-colorblind", this._colorblind ? "1" : "0"); } catch (e) {}
      this._render();
      this._renderCurrentView();
    });

    root.getElementById("scope-filter")?.addEventListener("change", (e) => {
      const [kind, value] = e.target.value.split(":");
      this._scopeFilter = value ? { kind, value } : null;
      this._render();
      this._renderCurrentView();
    });
    root.getElementById("path-toggle")?.addEventListener("click", () => {
      this._pathMode = !this._pathMode;
      this._pathEndpoints = [];
      this._pathNodes = null;
      this._render();
      this._renderCurrentView();
    });

    root.getElementById("export-btn")?.addEventListener("click", () => this._exportGraphImage());

    if (this._selectedNode && this._viewMode === "graph") {
      this._renderDetailPanel();
    }
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
}

customElements.define("entitymap-panel", EntityMapPanel);
