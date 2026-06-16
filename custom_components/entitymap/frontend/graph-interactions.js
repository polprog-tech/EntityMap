/** Graph interactions: scope/focus filtering, path highlight, image export, banner. */

import { GRAPH } from "./constants.js";
import { findPath, nodeDomain } from "./graph-data.js";

export const GraphInteractionsView = (Base) =>
  class extends Base {
    _nodePassesFilters(node) {
      if (this._filterTypes.has(node.node_type)) {
        return false;
      }

      if (!this._scopeFilter) {
        return true;
      }

      if (this._scopeFilter.kind === "area") {
        return node.area_id === this._scopeFilter.value;
      }

      return nodeDomain(node.node_id) === this._scopeFilter.value;
    }

    _applyFocus(nodes, links) {
      const keep = new Set([this._focusNode]);
      let frontier = new Set([this._focusNode]);

      for (let depth = 0; depth < GRAPH.focusDepth; depth++) {
        frontier = this._expandFocusFrontier(frontier, keep, links);
      }

      const focusedNodes = nodes.filter(n => keep.has(n.node_id));
      const focusedLinks = links.filter(
        e => keep.has(this._endId(e.source)) && keep.has(this._endId(e.target))
      );

      return { nodes: focusedNodes, links: focusedLinks };
    }

    _expandFocusFrontier(frontier, keep, links) {
      const next = new Set();

      for (const link of links) {
        const source = this._endId(link.source);
        const target = this._endId(link.target);

        if (frontier.has(source) && !keep.has(target)) {
          keep.add(target);
          next.add(target);
        }

        if (frontier.has(target) && !keep.has(source)) {
          keep.add(source);
          next.add(source);
        }
      }

      return next;
    }

    _enterFocus(nodeId) {
      this._focusNode = nodeId;
      this._pathMode = false;
      this._pathNodes = null;
      this._render();
      this._renderCurrentView();
    }

    _pickPathNode(nodeId) {
      this._pathEndpoints.push(nodeId);

      if (this._pathEndpoints.length < 2) {
        this._announce(`Path start set: ${nodeId}. Click the destination node.`);
        this._updateGraphBanner();
        return;
      }

      const [from, to] = this._pathEndpoints;
      this._pathNodes = findPath(this._graph.edges, from, to);
      this._pathMode = false;
      this._pathEndpoints = [];
      this._announce(
        this._pathNodes.length ? `Path found: ${this._pathNodes.length} nodes.` : "No path found."
      );
      this._render();
      this._renderCurrentView();
    }

    _highlightPath() {
      if (!this._pathNodes || !window.d3) {
        return;
      }

      const d3 = window.d3;
      const svg = d3.select(this.shadowRoot.getElementById("graph-container")).select("svg");
      const order = new Map(this._pathNodes.map((id, i) => [id, i]));
      const onPath = (a, b) => order.has(a) && order.has(b) && Math.abs(order.get(a) - order.get(b)) === 1;

      svg.selectAll(".node-group").attr("opacity", d =>
        order.has(d.node_id) ? 1 : GRAPH.opacity.nodeDimmed
      );
      svg.selectAll(".links path").attr("opacity", d =>
        onPath(this._endId(d.source), this._endId(d.target)) ? 1 : GRAPH.opacity.edgeDimmed
      );
      svg.selectAll(".links path")
        .filter(d => onPath(this._endId(d.source), this._endId(d.target)))
        .attr("stroke", GRAPH.pathHighlight)
        .attr("stroke-width", 3);
    }

    _exportGraphImage() {
      const svgEl = this.shadowRoot.querySelector("#graph-container svg");

      if (!svgEl) {
        return;
      }

      const rect = svgEl.getBoundingClientRect();
      const width = rect.width || 900;
      const height = rect.height || 600;
      const clone = svgEl.cloneNode(true);
      clone.setAttribute("width", width);
      clone.setAttribute("height", height);

      const url = URL.createObjectURL(
        new Blob([new XMLSerializer().serializeToString(clone)], { type: "image/svg+xml" })
      );
      const img = new Image();

      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = getComputedStyle(this).getPropertyValue("--card-background-color") || "#ffffff";
        ctx.fillRect(0, 0, width, height);
        ctx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
        canvas.toBlob((png) => this._downloadBlob(png, "entitymap-graph.png"));
      };
      img.src = url;
    }

    _downloadBlob(blob, filename) {
      if (!blob) {
        return;
      }

      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(href);
    }

    _updateGraphBanner() {
      const banner = this.shadowRoot.getElementById("graph-banner");

      if (!banner) {
        return;
      }

      const stats = this._graphStats || {};
      let html = "";

      if (this._pathMode) {
        html = `🔗 Path mode: click two nodes (${this._pathEndpoints.length}/2) <button class="banner-clear" id="clear-modes">✕ Cancel</button>`;
      } else if (this._focusNode) {
        html = `🎯 Focused on <code>${this._focusNode}</code> <button class="banner-clear" id="clear-modes">✕ Clear</button>`;
      } else if (this._pathNodes) {
        html = this._pathNodes.length
          ? `🔗 Path: ${this._pathNodes.length} nodes <button class="banner-clear" id="clear-modes">✕ Clear</button>`
          : `🔗 No path between the chosen nodes <button class="banner-clear" id="clear-modes">✕ Clear</button>`;
      } else if (stats.capped) {
        html = `Showing ${stats.shown} of ${stats.total} nodes — refine filters to see the rest.`;
      }

      banner.innerHTML = html;
      banner.hidden = !html;
      banner.querySelector("#clear-modes")?.addEventListener("click", () => this._clearGraphModes());
    }
  };
