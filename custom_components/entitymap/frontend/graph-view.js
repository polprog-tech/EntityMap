/** Graph view: orchestrates the force-directed dependency graph and its filters. */

import { GRAPH } from "./constants.js";
import { computeDegrees } from "./graph-data.js";

export const GraphView = (Base) =>
  class extends Base {
    _renderGraph() {
      if (!this._graph || !window.d3) {
        return;
      }

      const container = this.shadowRoot.getElementById("graph-container");
      if (!container) {
        return;
      }

      container.innerHTML = "";

      const { nodes, links, total, capped } = this._buildGraphData();
      if (nodes.length === 0) {
        this._renderEmptyGraph(container);
        return;
      }

      const d3 = window.d3;
      const rect = container.getBoundingClientRect();
      const width = rect.width || 900;
      const height = rect.height || 600;

      const simNodes = nodes.map(n => ({ ...n, id: n.node_id }));
      const simLinks = links.map(l => ({ ...l, source: l.source, target: l.target }));
      this._assignEdgeCurvature(simLinks);

      const degrees = computeDegrees(simLinks);
      const perf = simNodes.length > GRAPH.perfThreshold;

      const svg = d3.select(container)
        .append("svg")
        .attr("width", width)
        .attr("height", height)
        .attr("viewBox", [0, 0, width, height]);
      const g = svg.append("g");

      this._mmViewport = null;
      this._userMovedGraph = false;
      this._fitDone = false;

      const zoom = d3.zoom()
        .scaleExtent(GRAPH.zoomExtent)
        .on("zoom", (event) => {
          g.attr("transform", event.transform);

          if (event.sourceEvent) {
            this._userMovedGraph = true;
          }

          if (this._mmViewport) {
            this._mmViewport(event.transform);
          }
        });
      svg.call(zoom);

      this._appendArrowMarkers(svg);

      const simulation = this._createSimulation(simNodes, simLinks, width, height);
      this._simulation = simulation;

      const link = this._drawLinks(g, simLinks);
      const node = this._drawNodes(g, simNodes, simulation, degrees, perf);
      svg.on("click", () => this._closeDetail());

      const updateMinimap = this._setupMinimap(svg, simNodes, width, height);
      const fitToView = (duration) => this._fitGraphToView(svg, g, zoom, width, height, duration);

      this._runSimulation(simulation, link, node, updateMinimap, fitToView);
      this._wireZoomControls(svg, zoom, fitToView);

      this._graphStats = { shown: simNodes.length, total, capped };
      this._updateGraphBanner();

      if (this._pathNodes) {
        this._highlightPath();
      }
    }

    _runSimulation(simulation, link, node, updateMinimap, fitToView) {
      let tickCount = 0;
      simulation.on("tick", () => {
        link.attr("d", d => this._linkPath(d));
        node.attr("transform", d => `translate(${d.x},${d.y})`);

        if (++tickCount % GRAPH.minimapRefreshEvery === 0) {
          updateMinimap();
        }
      });

      simulation.on("end", () => {
        updateMinimap();

        if (this._userMovedGraph || this._fitDone) {
          return;
        }

        this._fitDone = true;
        fitToView(GRAPH.animMs.settle);
      });
    }

    _buildGraphData() {
      let nodes = this._graph.nodes.filter(n => this._nodePassesFilters(n));
      const nodeIds = new Set(nodes.map(n => n.node_id));
      let links = this._graph.edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));

      if (this._focusNode) {
        ({ nodes, links } = this._applyFocus(nodes, links));
      }

      if (this._searchQuery) {
        ({ nodes, links } = this._applySearchFilter(nodes, links));
      }

      const total = nodes.length;
      let capped = false;

      if (nodes.length > GRAPH.maxNodes) {
        capped = true;
        nodes = nodes.slice(0, GRAPH.maxNodes);
        const limitedIds = new Set(nodes.map(n => n.node_id));
        links = links.filter(
          e => limitedIds.has(this._endId(e.source)) && limitedIds.has(this._endId(e.target))
        );
      }

      return { nodes, links, total, capped };
    }

    _applySearchFilter(nodes, links) {
      const q = this._searchQuery;
      const matchIds = new Set();
      nodes.forEach(n => {
        if (n.node_id.toLowerCase().includes(q) || n.title.toLowerCase().includes(q)) {
          matchIds.add(n.node_id);
        }
      });

      links.forEach(l => {
        const src = this._endId(l.source);
        const tgt = this._endId(l.target);
        if (matchIds.has(src)) matchIds.add(tgt);
        if (matchIds.has(tgt)) matchIds.add(src);
      });

      const matchedNodes = nodes.filter(n => matchIds.has(n.node_id));
      const keptIds = new Set(matchedNodes.map(n => n.node_id));
      const matchedLinks = links.filter(e =>
        keptIds.has(this._endId(e.source)) && keptIds.has(this._endId(e.target))
      );

      return { nodes: matchedNodes, links: matchedLinks };
    }

    _endId(end) {
      return typeof end === "object" ? end.node_id : end;
    }

    _renderEmptyGraph(container) {
      const scanned = this._graph.nodes.length;
      container.innerHTML = scanned === 0
        ? `<div class="empty-state">
             <div class="empty-illustration">🗺️</div>
             <p>No dependencies scanned yet.</p>
             <button class="btn btn-primary empty-scan-btn">↻ Scan now</button>
           </div>`
        : `<div class="empty-state">
             <div class="empty-illustration">🔍</div>
             <p>No nodes match the current search or filters.</p>
           </div>`;
      container.querySelector(".empty-scan-btn")
        ?.addEventListener("click", () => this._triggerScan());

      const controls = this.shadowRoot.getElementById("graph-zoom-controls");
      if (controls) controls.hidden = true;

      const minimap = this.shadowRoot.getElementById("graph-minimap");
      if (minimap) minimap.hidden = true;
    }

    _highlightNeighborhood(nodeId, neighborhood) {
      if (!window.d3) {
        return;
      }

      const d3 = window.d3;
      const container = this.shadowRoot.getElementById("graph-container");
      if (!container) {
        return;
      }

      const svg = d3.select(container).select("svg");
      const neighborIds = new Set(neighborhood.nodes.map(n => n.node_id));
      neighborIds.add(nodeId);

      svg.selectAll(".node-group").attr("opacity", d =>
        neighborIds.has(d.node_id) ? 1 : GRAPH.opacity.nodeDimmed
      );
      svg.selectAll(".links path").attr("opacity", d => {
        const src = typeof d.source === "object" ? d.source.node_id || d.source.id : d.source;
        const tgt = typeof d.target === "object" ? d.target.node_id || d.target.id : d.target;
        return neighborIds.has(src) && neighborIds.has(tgt)
          ? GRAPH.opacity.edgeHighlighted
          : GRAPH.opacity.edgeDimmed;
      });

      svg.selectAll(".node-group").each(function(d) {
        if (d.node_id === nodeId) {
          d3.select(this).select("rect, circle, polygon")
            .attr("stroke", "#fff")
            .attr("stroke-width", 3);
        }
      });
    }

    _resetHighlight() {
      if (!window.d3) {
        return;
      }

      const d3 = window.d3;
      const container = this.shadowRoot.getElementById("graph-container");
      if (!container) {
        return;
      }

      const svg = d3.select(container).select("svg");
      svg.selectAll(".node-group").attr("opacity", 1);
      svg.selectAll(".links path").attr("opacity", GRAPH.opacity.edge);
      svg.selectAll(".node-group").select("rect, circle, polygon").attr("stroke-width", 1.5);
    }

    _applySearch() {
      if (!window.d3 || !this._graph) {
        return;
      }

      this._renderGraph();
    }

    _assignEdgeCurvature(links) {
      const groups = this._groupParallelEdges(links);

      for (const group of groups.values()) {
        this._spreadEdgeGroup(group);
      }
    }

    _groupParallelEdges(links) {
      const groups = new Map();

      for (const link of links) {
        const key = link.source < link.target
          ? `${link.source}|${link.target}`
          : `${link.target}|${link.source}`;
        const existing = groups.get(key);

        if (existing) {
          existing.push(link);
        } else {
          groups.set(key, [link]);
        }
      }

      return groups;
    }

    _spreadEdgeGroup(group) {
      const last = group.length - 1;

      group.forEach((link, index) => {
        link._curve = last === 0 ? 0 : index - last / 2;
      });
    }
  };
