import { useState, useEffect, useCallback, useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { api } from "../lib/api.js";
import "../styles/mindmap.css";

const EDGE_COLOR = {
  character: "#d8765a",
  scene: "#8f9aa3",
  camera_angle: "#5fa88a",
  custom: "#9b87c4",
};

function ClipNode({ data }) {
  return (
    <div className="mm-node" onClick={() => data.onSelect(data.id)}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
      <div className="mm-node-thumb">
        {data.thumbnail_path ? (
          <img src={data.thumbnailUrl} alt="" />
        ) : (
          <div className="mm-node-thumb-empty" />
        )}
      </div>
      <div className="mm-node-label" title={data.label}>
        {data.label}
      </div>
      <div className="mm-node-tags">
        {data.tags.slice(0, 3).map((t) => (
          <span
            key={t.id}
            className="mm-node-dot"
            style={{ background: EDGE_COLOR[t.kind] || "#888" }}
            title={t.value}
          />
        ))}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { clipNode: ClipNode };

// Simple force-ish layout: cluster nodes by their primary scene tag in a
// radial arrangement, since we don't have real x/y positions from the
// backend (it returns logical graph data, not coordinates - layout is the
// frontend's job).
function layoutNodes(rawNodes) {
  const clusters = new Map();
  for (const n of rawNodes) {
    const key = n.primary_scene || "unsorted";
    if (!clusters.has(key)) clusters.set(key, []);
    clusters.get(key).push(n);
  }

  const clusterKeys = Array.from(clusters.keys());
  const clusterRadius = 420;
  const positioned = [];

  clusterKeys.forEach((key, ci) => {
    const angleStep = (2 * Math.PI) / clusterKeys.length;
    const cx = Math.cos(ci * angleStep) * clusterRadius * (clusterKeys.length > 1 ? 1 : 0);
    const cy = Math.sin(ci * angleStep) * clusterRadius * (clusterKeys.length > 1 ? 1 : 0);
    const members = clusters.get(key);
    const innerRadius = 140;
    members.forEach((n, mi) => {
      const a = (2 * Math.PI * mi) / Math.max(members.length, 1);
      positioned.push({
        ...n,
        x: cx + Math.cos(a) * innerRadius,
        y: cy + Math.sin(a) * innerRadius,
      });
    });
  });

  return positioned;
}

export default function MindMapView({ onSelectClip }) {
  const [rawData, setRawData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [activeKinds, setActiveKinds] = useState({
    character: true,
    scene: true,
    camera_angle: true,
    custom: true,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getMindmap();
      setRawData(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filteredEdges = useMemo(
    () => rawData.edges.filter((e) => activeKinds[e.via_tag_kind]),
    [rawData.edges, activeKinds]
  );

  useEffect(() => {
    const positioned = layoutNodes(rawData.nodes);
    setNodes(
      positioned.map((n) => ({
        id: n.id,
        type: "clipNode",
        position: { x: n.x, y: n.y },
        data: {
          id: n.id,
          label: n.label,
          thumbnail_path: n.thumbnail_path,
          thumbnailUrl: api.thumbnailUrl(n.id),
          tags: n.tags,
          onSelect: onSelectClip,
        },
      }))
    );
    setEdges(
      filteredEdges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        animated: false,
        style: { stroke: EDGE_COLOR[e.via_tag_kind] || "#888", strokeWidth: 1.5, opacity: 0.55 },
        label: e.via_tag_value,
        labelStyle: { fill: "#7a7058", fontSize: 9 },
        labelBgStyle: { fill: "#1c1a15", fillOpacity: 0.8 },
      }))
    );
  }, [rawData.nodes, filteredEdges, onSelectClip, setNodes, setEdges]);

  const toggleKind = (kind) => {
    setActiveKinds((prev) => ({ ...prev, [kind]: !prev[kind] }));
  };

  if (!loading && rawData.nodes.length === 0) {
    return (
      <div className="mindmap-empty">
        <div className="empty-glyph">◈</div>
        <h2>Nothing to map yet</h2>
        <p>
          Import footage and tag a few clips by character, scene, or camera
          angle in the Bin — clips sharing a tag will connect here
          automatically.
        </p>
      </div>
    );
  }

  return (
    <div className="mindmap-view">
      <div className="mindmap-toolbar">
        <span className="mm-toolbar-label">connections:</span>
        {Object.keys(EDGE_COLOR).map((kind) => (
          <button
            key={kind}
            className={`mm-toggle ${activeKinds[kind] ? "active" : ""}`}
            style={{ "--toggle-color": EDGE_COLOR[kind] }}
            onClick={() => toggleKind(kind)}
          >
            <span className="mm-toggle-dot" />
            {kind.replace("_", " ")}
          </button>
        ))}
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        minZoom={0.15}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#3a3327" gap={28} size={1} />
        <Controls showInteractive={false} />
        <MiniMap
          pannable
          zoomable
          maskColor="rgba(21,19,15,0.75)"
          style={{ background: "#1c1a15", border: "1px solid #3a3327" }}
        />
      </ReactFlow>
    </div>
  );
}
