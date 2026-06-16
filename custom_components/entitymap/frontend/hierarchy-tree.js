/** Hierarchy view: D3 tree layout. */

import { NODE_CONFIG } from "./constants.js";

const TREE = {
  nodeSpacing: 28,
  minWidth: 600,
  minHeight: 400,
  margin: { left: 40, top: 40, right: 200 },
  zoomExtent: [0.3, 3],
  fitMaxScale: 1.2,
};

export const HierarchyTreeView = (Base) =>
  class extends Base {
    _renderHierarchyTree(content, h) {
      if (!window.d3) {
        content.innerHTML = '<div class="empty-state">Loading D3 for tree visualization...</div>';
        this._loadD3().then(() => this._renderHierarchyTree(content, h));
        return;
      }

      const treeData = buildTreeData(h);

      if (treeData.children.length === 0) {
        content.innerHTML = '<div class="empty-state">No hierarchy data. Run a scan first.</div>';
        return;
      }

      const isVertical = this._treeOrientation === "vertical";
      const root = window.d3.hierarchy(treeData);
      const dims = this._treeDimensions(root, isVertical, content);

      this._layoutTree(root, isVertical, dims);

      const { svg, g, zoom } = this._createTreeSvg(content, dims);
      this._drawTreeLinks(g, root, isVertical);
      this._drawTreeNodes(g, root, isVertical);
      this._fitTree(svg, g, zoom, dims);
    }

    _treeDimensions(root, isVertical, content) {
      const baseWidth = content.parentElement.getBoundingClientRect().width || 900;
      const leaves = root.leaves().length;
      const margin = TREE.margin;

      if (isVertical) {
        return {
          width: Math.max(TREE.minWidth, leaves * TREE.nodeSpacing + 120),
          height: Math.max(TREE.minHeight, (root.height + 1) * 120 + 80),
          margin,
        };
      }

      return {
        width: baseWidth,
        height: Math.max(TREE.minHeight, leaves * TREE.nodeSpacing + 80),
        margin,
      };
    }

    _layoutTree(root, isVertical, dims) {
      const d3 = window.d3;
      const innerWidth = dims.width - dims.margin.left - dims.margin.right;
      const layout = isVertical
        ? d3.tree().size([innerWidth, dims.height - dims.margin.top - 60])
        : d3.tree().size([dims.height - 80, innerWidth]);

      layout(root);
    }

    _createTreeSvg(content, dims) {
      const d3 = window.d3;
      content.innerHTML = "";

      const svg = d3.select(content)
        .append("svg")
        .attr("width", dims.width)
        .attr("height", dims.height)
        .attr("class", "hierarchy-svg");
      const g = svg.append("g").attr("transform", `translate(${dims.margin.left}, ${dims.margin.top})`);

      const zoom = d3.zoom()
        .scaleExtent(TREE.zoomExtent)
        .on("zoom", (event) => g.attr("transform", event.transform));
      svg.call(zoom);
      svg.call(zoom.transform, d3.zoomIdentity.translate(dims.margin.left, dims.margin.top));

      return { svg, g, zoom };
    }

    _drawTreeLinks(g, root, isVertical) {
      const d3 = window.d3;
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
    }

    _drawTreeNodes(g, root, isVertical) {
      const node = g.selectAll(".tree-node")
        .data(root.descendants())
        .join("g")
        .attr("class", "tree-node")
        .attr("transform", d => isVertical ? `translate(${d.x},${d.y})` : `translate(${d.y},${d.x})`)
        .attr("cursor", d => d.data._nodeId ? "pointer" : "default");

      this._drawTreeNodeCircles(node);
      this._drawTreeNodeIcons(node, isVertical);
      this._drawTreeNodeLabels(node, isVertical);
      this._wireTreeNodeEvents(node);
    }

    _drawTreeNodeCircles(node) {
      const d3 = window.d3;

      node.append("circle")
        .attr("r", d => d.children ? 6 : 5)
        .attr("fill", d => d.data._color || "#78909C")
        .attr("stroke", d => d3.color(d.data._color || "#78909C").darker(0.5))
        .attr("stroke-width", 1.5);
    }

    _drawTreeNodeIcons(node, isVertical) {
      node.append("text")
        .attr("x", isVertical ? 0 : -18)
        .attr("dy", isVertical ? -16 : "0.35em")
        .attr("text-anchor", "middle")
        .attr("font-size", "12px")
        .text(d => d.data._icon || "");
    }

    _drawTreeNodeLabels(node, isVertical) {
      node.append("text")
        .attr("x", d => isVertical ? 0 : (d.children ? -24 : 12))
        .attr("dy", d => isVertical ? (d.children ? -28 : 18) : (d.children ? -12 : "0.35em"))
        .attr("text-anchor", d => isVertical ? "middle" : (d.children ? "end" : "start"))
        .attr("font-size", "12px")
        .attr("font-weight", d => d.children ? "600" : "400")
        .attr("fill", "var(--em-text, #333)")
        .attr("font-family", "var(--paper-font-body1_-_font-family, sans-serif)")
        .text(d => {
          const maxLen = d.children ? 30 : 35;
          return d.data.name.length > maxLen ? d.data.name.substring(0, maxLen - 1) + "…" : d.data.name;
        });
    }

    _wireTreeNodeEvents(node) {
      const d3 = window.d3;

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
        .on("mouseover", function() {
          d3.select(this).select("circle").attr("stroke-width", 3).attr("stroke", "#fff");
        })
        .on("mouseout", function(event, d) {
          d3.select(this).select("circle")
            .attr("stroke-width", 1.5)
            .attr("stroke", d3.color(d.data._color || "#78909C").darker(0.5));
        });
    }

    _fitTree(svg, g, zoom, dims) {
      const d3 = window.d3;
      const bounds = g.node().getBBox();
      const scale = Math.min(
        (dims.width - 20) / (bounds.width + 60),
        (dims.height - 20) / (bounds.height + 60),
        TREE.fitMaxScale
      );
      const tx = 20 - bounds.x * scale;
      const ty = dims.height / 2 - (bounds.y + bounds.height / 2) * scale;

      svg.call(zoom.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
    }
  };

export function buildTreeData(h) {
  const root = { name: "Home", _icon: "🏠", _color: "#78909C", _type: "root", children: [] };

  for (const area of h.areas) {
    const areaNode = _areaNode(area);

    if (areaNode.children.length > 0) {
      root.children.push(areaNode);
    }
  }

  if (h.unassigned_devices.length > 0 || h.unassigned_entities.length > 0) {
    root.children.push(_unassignedNode(h));
  }

  return root;
}

function _leafNode(item) {
  const cfg = NODE_CONFIG[item.node_type] || NODE_CONFIG.entity;

  return {
    name: item.title,
    _icon: cfg.icon,
    _color: cfg.color,
    _type: item.node_type,
    _nodeId: item.node_id,
  };
}

function _deviceNode(dev) {
  return {
    name: dev.title,
    _icon: "🔌",
    _color: NODE_CONFIG.device.color,
    _type: "device",
    _nodeId: dev.node_id,
    children: dev.entities.map(_leafNode),
  };
}

function _areaNode(area) {
  return {
    name: area.title,
    _icon: "🏠",
    _color: NODE_CONFIG.area.color,
    _type: "area",
    _nodeId: area.node_id,
    children: [...area.devices.map(_deviceNode), ...area.entities.map(_leafNode)],
  };
}

function _unassignedNode(h) {
  return {
    name: "Unassigned",
    _icon: "📦",
    _color: "#9E9E9E",
    _type: "unassigned",
    children: [...h.unassigned_devices.map(_deviceNode), ...h.unassigned_entities.map(_leafNode)],
  };
}
