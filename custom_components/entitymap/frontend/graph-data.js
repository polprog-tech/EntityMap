/** Pure graph helpers (no DOM/D3): degree, domain, shortest path. */

export function endId(end) {
  return end && typeof end === "object" ? (end.node_id ?? end.id) : end;
}

export function nodeDomain(nodeId) {
  const dot = nodeId.indexOf(".");

  return dot === -1 ? nodeId : nodeId.slice(0, dot);
}

export function computeDegrees(links) {
  const degrees = new Map();
  const bump = (id) => degrees.set(id, (degrees.get(id) || 0) + 1);

  for (const link of links) {
    bump(endId(link.source));
    bump(endId(link.target));
  }

  return degrees;
}

export function findPath(links, fromId, toId) {
  if (fromId === toId) {
    return [fromId];
  }

  const adjacency = new Map();
  const connect = (a, b) => {
    if (!adjacency.has(a)) adjacency.set(a, []);
    adjacency.get(a).push(b);
  };

  for (const link of links) {
    const source = endId(link.source);
    const target = endId(link.target);
    connect(source, target);
    connect(target, source);
  }

  const prev = new Map([[fromId, null]]);
  const queue = [fromId];

  while (queue.length) {
    const current = queue.shift();

    if (current === toId) {
      return _reconstruct(prev, toId);
    }

    for (const next of adjacency.get(current) || []) {
      if (prev.has(next)) {
        continue;
      }

      prev.set(next, current);
      queue.push(next);
    }
  }

  return [];
}

function _reconstruct(prev, toId) {
  const path = [];
  let node = toId;

  while (node !== null && node !== undefined) {
    path.unshift(node);
    node = prev.get(node);
  }

  return path;
}
