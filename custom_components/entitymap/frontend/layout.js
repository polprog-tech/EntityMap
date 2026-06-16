/** Panel chrome: shell markup, type filter chips and the legend. */

import { NODE_CONFIG } from "./constants.js";
import { nodeDomain } from "./graph-data.js";
import { STYLES } from "./styles.js";

export const LayoutView = (Base) =>
  class extends Base {
    _shellMarkup() {
      return `
      <style>${STYLES}</style>
      <div class="entitymap-container ${this._density === 'compact' ? 'compact' : ''}">
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
            <button class="btn icon-btn ${this._density === 'compact' ? 'active' : ''}" id="density-toggle"
                    title="Toggle compact density" aria-label="Toggle compact density">⇕</button>
            <button class="btn icon-btn ${this._colorblind ? 'active' : ''}" id="cb-toggle"
                    title="Colorblind-safe palette" aria-label="Toggle colorblind-safe palette">◑</button>
            <button class="btn btn-primary scan-btn">↻ Rescan</button>
          </div>
        </header>
        <div class="entitymap-body">
          ${this._viewMode !== 'hierarchy'
            ? `<div class="filter-bar">${this._renderFilterChips()}${this._viewMode === 'graph' ? this._graphToolbar() : ''}</div>`
            : ''}
          <div class="main-content">
            <div class="graph-area">
              <div class="graph-canvas" id="graph-container">
                ${!this._graph ? '<div class="empty-state">Loading dependency graph...</div>' : ''}
              </div>
              <div class="graph-banner" id="graph-banner" hidden></div>
              <div class="graph-zoom-controls" id="graph-zoom-controls" ${this._viewMode === 'graph' ? '' : 'hidden'}>
                <button class="zoom-btn" data-zoom="in" title="Zoom in" aria-label="Zoom in">+</button>
                <button class="zoom-btn" data-zoom="out" title="Zoom out" aria-label="Zoom out">−</button>
                <button class="zoom-btn" data-zoom="fit" title="Fit to view" aria-label="Fit graph to view">⤢</button>
                <button class="zoom-btn" data-zoom="reset" title="Reset zoom" aria-label="Reset zoom">⟲</button>
              </div>
              <svg class="minimap" id="graph-minimap" ${this._viewMode === 'graph' ? '' : 'hidden'} aria-hidden="true"></svg>
            </div>
            <aside class="detail-panel ${this._selectedNode && this._viewMode === 'graph' ? 'open' : ''}" id="detail-panel">
              <div class="empty-state">Select a node to view details</div>
            </aside>
          </div>
        </div>
        <div class="legend">
          ${this._legendMarkup()}
          <span class="legend-sep">|</span>
          <span class="legend-item">
            <span class="legend-line solid"></span> Direct
          </span>
          <span class="legend-item">
            <span class="legend-line dashed"></span> Inferred
          </span>
        </div>
        <footer class="entitymap-footer">
          <span>EntityMap</span>
          <span class="footer-sep">·</span>
          <span>by <a href="https://polprog.pl/" target="_blank" rel="noopener">POLPROG</a></span>
          <span class="footer-sep">·</span>
          <a href="https://github.com/polprog-tech/EntityMap" target="_blank" rel="noopener">📖 Docs</a>
          <span class="footer-sep">·</span>
          <a href="https://github.com/polprog-tech/EntityMap/issues" target="_blank" rel="noopener">🐛 Report Issue</a>
        </footer>
        <div id="em-live" class="sr-only" aria-live="polite"></div>
      </div>
    `;
    }

    _graphToolbar() {
      return `
        <span class="toolbar-sep"></span>
        <select id="scope-filter" class="scope-select" aria-label="Filter by area or domain">
          ${this._scopeOptions()}
        </select>
        <button class="btn btn-sm ${this._pathMode ? 'toggle-active' : ''}" id="path-toggle"
                title="Highlight the path between two nodes">🔗 Path</button>
        <button class="btn btn-sm" id="export-btn" title="Download the graph as a PNG">⬇ PNG</button>`;
    }

    _scopeOptions() {
      if (!this._graph) {
        return "";
      }

      const areas = new Set();
      const domains = new Set();

      for (const node of this._graph.nodes) {
        if (node.area_id) areas.add(node.area_id);
        domains.add(nodeDomain(node.node_id));
      }

      const selected = this._scopeFilter ? `${this._scopeFilter.kind}:${this._scopeFilter.value}` : "";
      const option = (value, label) =>
        `<option value="${value}"${selected === value ? " selected" : ""}>${label}</option>`;
      const areaOpts = [...areas].sort().map(a => option(`area:${a}`, `Area: ${a}`)).join("");
      const domainOpts = [...domains].sort().map(d => option(`domain:${d}`, `Domain: ${d}`)).join("");

      return `${option("", "All scopes")}${areaOpts ? `<optgroup label="Areas">${areaOpts}</optgroup>` : ""}<optgroup label="Domains">${domainOpts}</optgroup>`;
    }

    _renderFilterChips() {
      return Object.entries(NODE_CONFIG).map(([type, cfg]) =>
        `<button class="filter-chip ${this._filterTypes.has(type) ? '' : 'active'}"
                data-type="${type}">
          ${cfg.icon} ${cfg.label}
        </button>`
      ).join("");
    }

    _legendMarkup() {
      return Object.entries(NODE_CONFIG).map(([type, cfg]) => {
        const dot = `<span class="legend-dot legend-${cfg.shape}" style="background:${this._typeColor(type)}"></span>`;

        if (this._viewMode === "hierarchy") {
          return `<span class="legend-item">${dot} ${cfg.label}</span>`;
        }

        return `<button class="legend-item legend-toggle ${this._filterTypes.has(type) ? 'filtered-out' : ''}"
                 data-type="${type}" title="Toggle ${cfg.label}" aria-pressed="${!this._filterTypes.has(type)}">${dot} ${cfg.label}</button>`;
      }).join("");
    }
  };
