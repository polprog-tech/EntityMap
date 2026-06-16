/** Shared constants for the EntityMap panel. */

export const D3_CDN = "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js";

export const NODE_CONFIG = {
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

export const EDGE_COLORS = {
  high:   "var(--entitymap-edge-high, #78909c)",
  medium: "var(--entitymap-edge-medium, #b0bec5)",
  low:    "var(--entitymap-edge-low, #e0e0e0)",
};

export const SEVERITY_COLORS = {
  critical: "#d32f2f",
  high:     "#f57c00",
  medium:   "#fbc02d",
  low:      "#66bb6a",
  info:     "#42a5f5",
};

export const COLORBLIND_COLORS = {
  device:     "#0072B2",
  entity:     "#009E73",
  automation: "#E69F00",
  script:     "#CC79A7",
  scene:      "#D55E00",
  helper:     "#56B4E9",
  group:      "#999999",
  area:       "#F0E442",
  unknown:    "#BBBBBB",
};

// Tunable graph layout/rendering behaviour (SVG drawing geometry stays inline).
export const GRAPH = {
  maxNodes: 500,              // cap rendered nodes for performance
  minimapRefreshEvery: 8,    // refresh the minimap every N simulation ticks
  zoomExtent: [0.1, 5],
  zoomStep: 1.3,             // zoom in/out button factor
  fitPadding: 40,            // px of slack when fitting the graph to view
  fitMaxScale: 1.5,          // never zoom past this when auto-fitting
  parallelEdgeOffset: 22,    // px a curved parallel edge bows out per rank
  labelMaxChars: 22,         // truncate node labels longer than this...
  labelTruncateTo: 20,       // ...down to this many characters
  force: {
    comfortable: { distance: 80, charge: -200, collide: 25 },
    compact: { distance: 45, charge: -120, collide: 18 },
  },
  opacity: { edge: 0.6, edgeHighlighted: 0.8, edgeDimmed: 0.05, nodeDimmed: 0.15 },
  animMs: { zoom: 200, fit: 300, settle: 500 },
  nodeSize: { base: 11, max: 22, growth: 2.4 },  // radius grows with degree (importance)
  focusDepth: 1,                                  // hops shown around a focused node
  perfThreshold: 250,                             // above N nodes, simplify rendering
  searchHighlight: "#FFD600",                     // ring on search matches
  pathHighlight: "#FF4081",                       // path-between-nodes color
};
