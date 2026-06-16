/** Graph rendering primitives: markers, simulation, links, nodes, minimap, zoom. */

import { NODE_CONFIG, EDGE_COLORS, GRAPH } from "./constants.js";

export const GraphRenderView = (Base) =>
  class extends Base {
    _appendArrowMarkers(svg) {
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
    }

    _createSimulation(simNodes, simLinks, width, height) {
      const d3 = window.d3;
      const force = this._density === "compact" ? GRAPH.force.compact : GRAPH.force.comfortable;

      return d3.forceSimulation(simNodes)
        .force("link", d3.forceLink(simLinks).id(d => d.id).distance(force.distance))
        .force("charge", d3.forceManyBody().strength(force.charge))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(force.collide));
    }

    _drawLinks(g, simLinks) {
      const link = g.append("g")
        .attr("class", "links")
        .selectAll("path")
        .data(simLinks)
        .join("path")
        .attr("fill", "none")
        .attr("stroke", d => EDGE_COLORS[d.confidence] || EDGE_COLORS.high)
        .attr("stroke-width", d => d.confidence === "high" ? 2 : 1)
        .attr("stroke-dasharray", d => d.confidence === "low" ? "4,4" : d.confidence === "medium" ? "2,2" : "none")
        .attr("marker-end", d => `url(#arrow-${d.confidence || "high"})`)
        .attr("opacity", GRAPH.opacity.edge);

      link.append("title").text(d => {
        const kind = (d.dependency_kind || "").replace(/_/g, " ");
        const confidence = d.confidence ? ` (${d.confidence})` : "";
        return d.notes ? `${kind}${confidence} - ${d.notes}` : `${kind}${confidence}`;
      });

      return link;
    }

    _nodeRadius(degree) {
      const { base, max, growth } = GRAPH.nodeSize;

      return Math.min(max, base + Math.sqrt(degree) * growth);
    }

    _drawNodes(g, simNodes, simulation, degrees, perf) {
      const d3 = window.d3;
      const self = this;
      const radiusFor = (d) => this._nodeRadius(degrees.get(d.node_id) || 0);

      const node = g.append("g")
        .attr("class", "nodes")
        .selectAll("g")
        .data(simNodes)
        .join("g")
        .attr("class", "node-group")
        .attr("cursor", "pointer")
        .attr("tabindex", 0)
        .attr("role", "button")
        .attr("aria-label", d => `${(NODE_CONFIG[d.node_type] || NODE_CONFIG.unknown).label}: ${d.title}`)
        .call(d3.drag()
          .on("start", (event, d) => {
            this._userMovedGraph = true;

            if (!event.active) {
              simulation.alphaTarget(0.3).restart();
            }

            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => { d.fx = event.x; d.fy = event.y; })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
        );

      node.each(function(d) {
        const el = d3.select(this);
        const r = radiusFor(d);
        const style = self._nodeStyle(d);

        self._drawNodeShape(el, r, style);

        if (!perf) {
          self._drawNodeLabel(el, d, r);
        }

        if (style.isMissing) {
          self._drawMissingBadge(el, r);
        }
      });

      node.on("click", (event, d) => {
        event.stopPropagation();

        if (this._pathMode) {
          this._pickPathNode(d.node_id);
          return;
        }

        this._selectNode(d.node_id);
      });

      node.on("dblclick", (event, d) => {
        event.stopPropagation();
        this._enterFocus(d.node_id);
      });

      node.on("keydown", (event, d) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          this._selectNode(d.node_id);
        }
      });

      return node;
    }

    _nodeStyle(d) {
      const d3 = window.d3;
      const cfg = NODE_CONFIG[d.node_type] || NODE_CONFIG.unknown;
      const isMissing = !d.available;
      const baseColor = this._typeColor(d.node_type);
      const query = this._searchQuery;
      const matches =
        query && (d.node_id.toLowerCase().includes(query) || d.title.toLowerCase().includes(query));

      return {
        cfg,
        isMissing,
        fillColor: isMissing ? "#ff5252" : baseColor,
        strokeColor: matches
          ? GRAPH.searchHighlight
          : (isMissing ? "#d32f2f" : d3.color(baseColor).darker(0.5)),
        strokeWidth: matches ? 3 : 1.5,
      };
    }

    _drawNodeShape(el, r, style) {
      if (style.cfg.shape === "rect") {
        el.append("rect")
          .attr("width", r * 2).attr("height", r * 2)
          .attr("x", -r).attr("y", -r)
          .attr("rx", 4)
          .attr("fill", style.fillColor)
          .attr("stroke", style.strokeColor)
          .attr("stroke-width", style.strokeWidth);
        return;
      }

      if (style.cfg.shape === "diamond") {
        const p = r + 2;
        el.append("polygon")
          .attr("points", `0,${-p} ${p},0 0,${p} ${-p},0`)
          .attr("fill", style.fillColor)
          .attr("stroke", style.strokeColor)
          .attr("stroke-width", style.strokeWidth);
        return;
      }

      el.append("circle")
        .attr("r", r)
        .attr("fill", style.fillColor)
        .attr("stroke", style.strokeColor)
        .attr("stroke-width", style.strokeWidth);
    }

    _drawNodeLabel(el, d, r) {
      el.append("text")
        .attr("dy", r + 14)
        .attr("text-anchor", "middle")
        .attr("font-size", "10px")
        .attr("fill", "var(--primary-text-color, #333)")
        .attr("stroke", "var(--card-background-color, #fff)")
        .attr("stroke-width", 3)
        .attr("paint-order", "stroke")
        .attr("stroke-linejoin", "round")
        .attr("font-family", "var(--paper-font-body1_-_font-family, sans-serif)")
        .attr("font-weight", "500")
        .text(
          d.title.length > GRAPH.labelMaxChars
            ? d.title.substring(0, GRAPH.labelTruncateTo) + "…"
            : d.title
        );
    }

    _drawMissingBadge(el, r) {
      el.append("circle")
        .attr("cx", r - 2).attr("cy", -(r - 2)).attr("r", 5)
        .attr("fill", "#d32f2f");
      el.append("text")
        .attr("x", r - 2).attr("y", -(r - 5))
        .attr("text-anchor", "middle")
        .attr("font-size", "7px")
        .attr("fill", "white")
        .text("!");
    }

    _linkPath(d) {
      const x1 = d.source.x, y1 = d.source.y, x2 = d.target.x, y2 = d.target.y;

      if (!d._curve) {
        return `M${x1},${y1}L${x2},${y2}`;
      }

      const dx = x2 - x1, dy = y2 - y1;
      const dist = Math.hypot(dx, dy) || 1;
      const off = d._curve * GRAPH.parallelEdgeOffset;
      const cx = (x1 + x2) / 2 - (dy / dist) * off;
      const cy = (y1 + y2) / 2 + (dx / dist) * off;

      return `M${x1},${y1}Q${cx},${cy} ${x2},${y2}`;
    }

    _fitGraphToView(svg, g, zoom, width, height, duration = GRAPH.animMs.settle) {
      const d3 = window.d3;
      const bounds = g.node().getBBox();
      const fullWidth = bounds.width || width;
      const fullHeight = bounds.height || height;
      const scale = Math.min(
        width / (fullWidth + GRAPH.fitPadding),
        height / (fullHeight + GRAPH.fitPadding),
        GRAPH.fitMaxScale,
      );
      const tx = width / 2 - (bounds.x + fullWidth / 2) * scale;
      const ty = height / 2 - (bounds.y + fullHeight / 2) * scale;

      svg.transition().duration(duration).call(
        zoom.transform,
        d3.zoomIdentity.translate(tx, ty).scale(scale)
      );
    }

    _wireZoomControls(svg, zoom, fitToView) {
      const d3 = window.d3;
      const controls = this.shadowRoot.getElementById("graph-zoom-controls");

      if (!controls) {
        return;
      }

      controls.hidden = false;
      const bind = (action, fn) => {
        const btn = controls.querySelector(`[data-zoom="${action}"]`);
        if (btn) btn.onclick = fn;
      };
      bind("in", () => svg.transition().duration(GRAPH.animMs.zoom).call(zoom.scaleBy, GRAPH.zoomStep));
      bind("out", () => svg.transition().duration(GRAPH.animMs.zoom).call(zoom.scaleBy, 1 / GRAPH.zoomStep));
      bind("fit", () => fitToView(GRAPH.animMs.fit));
      bind("reset", () => svg.transition().duration(GRAPH.animMs.fit).call(zoom.transform, d3.zoomIdentity));
    }

    _setupMinimap(svg, simNodes, width, height) {
      const d3 = window.d3;
      const typeColor = (t) => this._typeColor(t);
      const MM_W = 160, MM_H = 110, MM_PAD = 6;
      const mmEl = this.shadowRoot.getElementById("graph-minimap");
      let mmDots = null, mmRect = null, mmScale = 1, mmMinX = 0, mmMinY = 0;

      if (mmEl) {
        mmEl.hidden = false;
        const mmSvg = d3.select(mmEl).attr("viewBox", `0 0 ${MM_W} ${MM_H}`);
        mmSvg.selectAll("*").remove();
        mmDots = mmSvg.append("g");
        mmRect = mmSvg.append("rect").attr("class", "minimap-viewport");
      }

      const updateMinimapViewport = (t) => {
        if (!mmRect) return;

        const k = t.k || 1;
        mmRect
          .attr("x", MM_PAD + ((0 - t.x) / k - mmMinX) * mmScale)
          .attr("y", MM_PAD + ((0 - t.y) / k - mmMinY) * mmScale)
          .attr("width", Math.max(0, (width / k) * mmScale))
          .attr("height", Math.max(0, (height / k) * mmScale));
      };
      this._mmViewport = updateMinimapViewport;

      const updateMinimap = () => {
        if (!mmDots) return;

        const xs = simNodes.map(n => n.x), ys = simNodes.map(n => n.y);
        const minX = Math.min(...xs), maxX = Math.max(...xs);
        const minY = Math.min(...ys), maxY = Math.max(...ys);
        mmScale = Math.min((MM_W - 2 * MM_PAD) / ((maxX - minX) || 1), (MM_H - 2 * MM_PAD) / ((maxY - minY) || 1));
        mmMinX = minX;
        mmMinY = minY;
        mmDots.selectAll("circle")
          .data(simNodes)
          .join("circle")
          .attr("r", 1.6)
          .attr("cx", d => MM_PAD + (d.x - minX) * mmScale)
          .attr("cy", d => MM_PAD + (d.y - minY) * mmScale)
          .attr("fill", d => typeColor(d.node_type));
        updateMinimapViewport(d3.zoomTransform(svg.node()));
      };

      return updateMinimap;
    }
  };
