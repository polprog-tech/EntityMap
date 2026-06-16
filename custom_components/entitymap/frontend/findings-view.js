/** Findings view: fragility report cards. */

import { SEVERITY_COLORS } from "./constants.js";

export const FindingsView = (Base) =>
  class extends Base {
    _renderFindingsList() {
      const container = this.shadowRoot.getElementById("graph-container");
      if (!container || !this._findings) return;

      const findings = (this._findings.findings || []).filter(f => {
        const node = this._graph?.nodes?.find(n => n.node_id === f.node_id);

        return !node || !this._filterTypes.has(node.node_type);
      });
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
  };
