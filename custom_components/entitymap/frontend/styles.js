/** EntityMap panel styles. */

import { SEVERITY_COLORS } from "./constants.js";

export const STYLES = `
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
        /* Theme-derived accents so glows and status colors track the active theme */
        --em-primary-glow: color-mix(in srgb, var(--em-primary) 28%, transparent);
        --em-primary-tint: color-mix(in srgb, var(--em-primary) 6%, transparent);
        --em-warning-bg: color-mix(in srgb, var(--warning-color, #ffa726) 16%, transparent);
        --em-warning-text: var(--warning-color, #e65100);
        --em-success-text: var(--success-color, #2e7d32);
        --em-error-text: var(--error-color, #d32f2f);
      }
      * { box-sizing: border-box; margin: 0; padding: 0; }

      /* Layout */
      .entitymap-container {
        display: flex; flex-direction: column; height: 100%;
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
        box-shadow: 0 1px 4px var(--em-primary-glow);
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
        box-shadow: 0 0 0 3px var(--em-primary-glow);
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
      .btn-primary:hover { opacity: 0.92; box-shadow: 0 2px 8px var(--em-primary-glow); }

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
      .main-content { flex: 1; display: flex; overflow: hidden; position: relative; }
      .graph-area {
        flex: 1; overflow: hidden; position: relative;
        background: var(--em-bg);
      }
      .graph-canvas { width: 100%; height: 100%; }
      .graph-canvas svg { width: 100%; height: 100%; }
      .graph-zoom-controls {
        position: absolute; bottom: 16px; right: 16px;
        display: flex; flex-direction: column; gap: 4px; z-index: 3;
      }
      .graph-zoom-controls[hidden] { display: none; }
      .zoom-btn {
        width: 34px; height: 34px; border-radius: 8px;
        border: 1px solid var(--em-border); background: var(--em-bg);
        color: var(--em-text); font-size: 16px; font-weight: 600;
        cursor: pointer; box-shadow: var(--em-shadow-sm);
        display: flex; align-items: center; justify-content: center;
        transition: all var(--em-transition);
      }
      .zoom-btn:hover { background: var(--em-surface); }
      .zoom-btn:focus-visible { outline: 2px solid var(--em-primary); outline-offset: 2px; }

      /* Detail panel */
      .detail-panel {
        position: absolute; top: 0; right: 0; bottom: 0;
        width: min(400px, 100%); overflow-y: auto;
        background: var(--em-bg); border-left: 1px solid var(--em-border);
        box-shadow: -2px 0 12px rgba(0,0,0,0.10);
        transform: translateX(100%); will-change: transform;
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 4;
      }
      .detail-panel.open { transform: translateX(0); }
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
        background: var(--em-warning-bg); color: var(--em-warning-text);
        margin-top: 10px; font-weight: 500;
      }
      .warning-badge.muted { background: var(--em-surface); color: var(--em-text-secondary); }

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
      .legend-dot.legend-rect { border-radius: 2px; }
      .legend-dot.legend-diamond { border-radius: 2px; transform: rotate(45deg); }
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
      .empty-state.success { color: var(--em-success-text); }
      .empty-illustration { font-size: 48px; opacity: 0.55; line-height: 1; }
      .empty-state .btn-primary { margin-top: 6px; }
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
        font-size: 14px; color: var(--em-error-text); padding: 40px;
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
      .tree-leaf:hover { background: var(--em-primary-tint); }

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

      /* Icon toggle buttons (density, colorblind) */
      .icon-btn { padding: 7px 10px; font-size: 14px; line-height: 1; }
      .icon-btn.active {
        background: var(--em-primary); color: #fff; border-color: var(--em-primary);
      }

      /* Legend as filter */
      .legend-toggle {
        display: inline-flex; align-items: center; gap: 5px;
        background: none; border: none; cursor: pointer; padding: 2px 5px;
        font-size: 11px; color: var(--em-text-secondary); border-radius: 6px;
        font-family: inherit; transition: all var(--em-transition);
      }
      .legend-toggle:hover { background: var(--em-surface); }
      .legend-toggle:focus-visible { outline: 2px solid var(--em-primary); outline-offset: 2px; }
      .legend-toggle.filtered-out { opacity: 0.4; text-decoration: line-through; }

      /* Severity chip + sticky detail header */
      .risk-row { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
      .severity-chip {
        padding: 2px 10px; border-radius: 12px; font-size: 10px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.04em; color: #fff;
      }
      .detail-header { position: sticky; top: 0; z-index: 1; }

      /* Minimap */
      .minimap {
        position: absolute; top: 12px; right: 12px;
        width: 160px; height: 110px; z-index: 3; overflow: hidden;
        background: color-mix(in srgb, var(--em-bg) 88%, transparent);
        border: 1px solid var(--em-border); border-radius: 8px;
        box-shadow: var(--em-shadow-sm);
      }
      .minimap[hidden] { display: none; }
      .minimap-viewport { fill: var(--em-primary-tint); stroke: var(--em-primary); stroke-width: 1; }

      /* Compact density */
      .entitymap-container.compact .filter-bar { padding: 6px 16px; }
      .entitymap-container.compact .legend { padding: 6px 16px; }
      .entitymap-container.compact .detail-section { padding: 12px 16px; }
      .entitymap-container.compact .detail-header { padding: 12px 16px; }
      .entitymap-container.compact .tree-branch { padding: 8px 14px; }
      .entitymap-container.compact .tree-leaf { padding: 4px 14px 4px 56px; }
      .entitymap-container.compact .finding-card { padding: 12px; }
      .entitymap-container.compact .findings-grid { gap: 8px; }

      /* Graph toolbar, banner, screen-reader live region */
      .toolbar-sep { width: 1px; align-self: stretch; background: var(--em-border); margin: 0 4px; }
      .scope-select {
        padding: 4px 10px; border-radius: 8px; border: 1px solid var(--em-border);
        background: var(--em-bg); color: var(--em-text); font-size: 12px; cursor: pointer;
        max-width: 200px;
      }
      .scope-select:focus-visible { outline: 2px solid var(--em-primary); outline-offset: 2px; }
      .graph-banner {
        position: absolute; top: 12px; left: 50%; transform: translateX(-50%);
        z-index: 4; max-width: 80%;
        display: flex; align-items: center; gap: 10px;
        padding: 6px 14px; border-radius: 20px;
        background: color-mix(in srgb, var(--em-bg) 92%, transparent);
        border: 1px solid var(--em-border); box-shadow: var(--em-shadow-md);
        font-size: 12px; color: var(--em-text);
      }
      .graph-banner[hidden] { display: none; }
      .graph-banner code { font-size: 11px; }
      .banner-clear {
        border: none; background: var(--em-surface); color: var(--em-text);
        border-radius: 8px; padding: 2px 8px; font-size: 11px; cursor: pointer;
      }
      .banner-clear:hover { background: var(--em-border); }
      .sr-only {
        position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
        overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0;
      }

      /* Responsive: narrow panel / mobile */
      @media (max-width: 700px) {
        .entitymap-header { padding: 12px 16px; }
        .header-actions { width: 100%; }
        .view-tabs { width: 100%; }
        .view-tabs .tab { flex: 1; }
        .search-box, .search-input { width: 100%; }
        .filter-bar { padding: 8px 16px; }
        .legend { padding: 8px 16px; }
        .detail-panel { width: 100%; }
        .findings-grid { grid-template-columns: 1fr; }
        .findings-view, .hierarchy-view { padding: 16px; }
      }
    `;
