/** Detail drawer: impact, fragility and migration for a node. */

import { NODE_CONFIG, SEVERITY_COLORS } from "./constants.js";

export const DetailView = (Base) =>
  class extends Base {
    _renderDetailPanel() {
      const panel = this.shadowRoot.getElementById("detail-panel");
      if (!panel || !this._selectedNode) return;
      panel.classList.add("open");

      const node = this._graph?.nodes?.find(n => n.node_id === this._selectedNode);
      const impact = this._selectedImpact;
      const migration = this._selectedMigration;
      const cfg = NODE_CONFIG[node?.node_type] || NODE_CONFIG.unknown;

      panel.innerHTML = `
        <div class="detail-header">
          <button class="close-btn" id="close-detail">✕</button>
          <div class="detail-title">
            <span class="node-badge" style="background:${this._typeColor(node?.node_type)}">${cfg.icon} ${cfg.label}</span>
            <h2>${node?.title || this._selectedNode}</h2>
            <code class="node-id">${this._selectedNode}</code>
          </div>
          ${node && !node.available ? '<div class="warning-badge">⚠️ Missing / Unavailable</div>' : ''}
          ${node?.disabled ? '<div class="warning-badge muted">🚫 Disabled</div>' : ''}
        </div>

        ${impact ? `
        <section class="detail-section">
          <h3>📊 Impact Analysis</h3>
          <div class="impact-summary">
            <div class="risk-meter">
              <div class="risk-bar" style="width:${impact.risk_score}%;background:${SEVERITY_COLORS[impact.severity]}"></div>
            </div>
            <div class="risk-row">
              <span class="severity-chip" style="background:${SEVERITY_COLORS[impact.severity]}">${impact.severity}</span>
              <span class="risk-label">Risk ${impact.risk_score.toFixed(0)}%</span>
            </div>
          </div>
          <p class="impact-text">${impact.summary}</p>
          ${Object.keys(impact.affected_by_type).length > 0 ? `
          <div class="affected-chips">
            ${Object.entries(impact.affected_by_type).map(([type, count]) => {
              const tcfg = NODE_CONFIG[type] || NODE_CONFIG.unknown;
              const tcolor = this._typeColor(type);
              return `<span class="chip" style="background:${tcolor}20;border-color:${tcolor}">
                ${tcfg.icon} ${count} ${type}${count > 1 ? 's' : ''}
              </span>`;
            }).join("")}
          </div>
          ` : ''}
        </section>
        ` : ''}

        ${impact?.fragility_findings?.length > 0 ? `
        <section class="detail-section">
          <h3>⚠️ Fragility Issues</h3>
          <ul class="findings-list">
            ${impact.fragility_findings.map(f => `
              <li class="finding-item severity-${f.severity}">
                <span class="severity-dot" style="background:${SEVERITY_COLORS[f.severity]}"></span>
                <div>
                  <strong>${f.fragility_type.replace(/_/g, " ")}</strong>
                  <p>${f.rationale}</p>
                  <p class="remediation">💡 ${f.remediation}</p>
                </div>
              </li>
            `).join("")}
          </ul>
        </section>
        ` : ''}

        ${migration?.suggestions?.length > 0 ? `
        <section class="detail-section">
          <h3>🔄 Migration Guidance</h3>
          <ul class="migration-list">
            ${migration.suggestions.map(s => `
              <li class="migration-item">
                <p>${s.description}</p>
                ${s.recommendation ? `<p class="recommendation">📋 ${s.recommendation}</p>` : ''}
                ${s.affected_items?.length > 0 ? `
                  <details>
                    <summary>${s.affected_items.length} affected item(s)</summary>
                    <ul class="affected-list">
                      ${s.affected_items.map(i => `<li><code>${i}</code></li>`).join("")}
                    </ul>
                  </details>
                ` : ''}
              </li>
            `).join("")}
          </ul>
        </section>
        ` : ''}
      `;

      panel.querySelector("#close-detail")?.addEventListener("click", () => this._closeDetail());
    }

    _closeDetail() {
      this._selectedNode = null;
      const panel = this.shadowRoot.getElementById("detail-panel");
      if (panel) {
        panel.classList.remove("open");
        panel.innerHTML = '<div class="empty-state">Select a node to view details</div>';
      }
      this._resetHighlight();
    }
  };
