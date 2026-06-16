/** Hierarchy view: area -> device -> entity list. */

import { NODE_CONFIG } from "./constants.js";

export const HierarchyView = (Base) =>
  class extends Base {
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

      container.querySelector("#mode-list")?.addEventListener("click", () => {
        this._hierarchyMode = "list";
        this._renderHierarchy();
      });

      container.querySelector("#mode-tree")?.addEventListener("click", () => {
        this._hierarchyMode = "tree";
        this._renderHierarchy();
      });

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
      content.innerHTML = `
        <div class="hierarchy-tree">
          ${h.areas.map(renderHierarchyAreaNode).join("")}
          ${h.unassigned_devices.length > 0 ? `
            <details class="tree-area" open>
              <summary class="tree-branch area-branch unassigned">
                <span class="tree-icon">📦</span>
                <span class="tree-title area-title">Unassigned devices</span>
                <span class="tree-count">${h.unassigned_devices.length} dev</span>
              </summary>
              <div class="tree-children">
                ${h.unassigned_devices.map(renderHierarchyDeviceNode).join("")}
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
                ${h.unassigned_entities.map(renderHierarchyEntityRow).join("")}
              </div>
            </details>
          ` : ""}
        </div>
      `;

      this._wireHierarchyListEvents(content);
    }

    _wireHierarchyListEvents(content) {
      const root = content.closest(".hierarchy-view");

      root.querySelector("#expand-all")?.addEventListener("click", () => {
        content.querySelectorAll("details").forEach(d => d.open = true);
      });

      root.querySelector("#collapse-all")?.addEventListener("click", () => {
        content.querySelectorAll("details").forEach(d => d.open = false);
      });

      content.querySelectorAll("[data-node]").forEach(el => {
        el.addEventListener("dblclick", (e) => {
          e.preventDefault();
          const nodeId = el.dataset.node;

          if (!nodeId) {
            return;
          }

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
  };

function renderHierarchyEntityRow(ent) {
  const cfg = NODE_CONFIG[ent.node_type] || NODE_CONFIG.entity;
  const badges = [];

  if (ent.disabled) {
    badges.push('<span class="tree-badge disabled">disabled</span>');
  }

  if (!ent.available) {
    badges.push('<span class="tree-badge unavailable">unavailable</span>');
  }

  return `
    <div class="tree-leaf" data-node="${ent.node_id}">
      <span class="tree-icon" style="color:${cfg.color}">${cfg.icon}</span>
      <span class="tree-title">${ent.title}</span>
      <code class="tree-id">${ent.node_id}</code>
      ${badges.join("")}
    </div>`;
}

function renderHierarchyDeviceNode(dev) {
  const cfg = NODE_CONFIG.device;
  const meta = dev.metadata?.manufacturer
    ? `<span class="tree-meta">${dev.metadata.manufacturer}${dev.metadata.model ? " · " + dev.metadata.model : ""}</span>`
    : "";
  const children = dev.entities.length > 0
    ? dev.entities.map(renderHierarchyEntityRow).join("")
    : '<div class="tree-empty">No entities</div>';

  return `
    <details class="tree-device">
      <summary class="tree-branch" data-node="${dev.node_id}">
        <span class="tree-icon" style="color:${cfg.color}">${cfg.icon}</span>
        <span class="tree-title">${dev.title}</span>
        <span class="tree-count">${dev.entities.length}</span>
        ${meta}
      </summary>
      <div class="tree-children">
        ${children}
      </div>
    </details>`;
}

function renderHierarchyAreaNode(area) {
  const totalChildren = area.devices.length + area.entities.length;
  const directEntities = area.entities.length > 0
    ? `
        <div class="tree-direct-entities">
          <div class="tree-section-label">Direct entities</div>
          ${area.entities.map(renderHierarchyEntityRow).join("")}
        </div>
      `
    : "";
  const emptyNote = totalChildren === 0 ? '<div class="tree-empty">Empty area</div>' : "";

  return `
    <details class="tree-area" open>
      <summary class="tree-branch area-branch" data-node="${area.node_id}">
        <span class="tree-icon" style="color:${NODE_CONFIG.area.color}">🏠</span>
        <span class="tree-title area-title">${area.title}</span>
        <span class="tree-count">${area.device_count} dev</span>
        <span class="tree-count">${area.entity_count} total</span>
      </summary>
      <div class="tree-children">
        ${area.devices.map(renderHierarchyDeviceNode).join("")}
        ${directEntities}
        ${emptyNote}
      </div>
    </details>`;
}
