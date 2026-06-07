"use client";

import "@xyflow/react/dist/style.css";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
  type Node,
  type Edge,
  type NodeProps,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { GraphNode as GNode, GraphEdge as GEdge } from "@/lib/types";

const NODE_W = 240;
const NODE_H = 88;

type PaperData = {
  arxivId: string;
  title: string;
  year: number;
  shortCitation: string;
};

type PaperNodeType = Node<PaperData, "paper">;

function PaperNodeComponent({ data }: NodeProps<PaperNodeType>) {
  return (
    <>
      <Handle
        type="target"
        position={Position.Top}
        className="!size-2 !border-0 !bg-border"
      />
      <div
        className="bg-card border border-border rounded-lg p-3 shadow-sm"
        style={{ width: NODE_W }}
      >
        <Link
          href={`/papers/${data.arxivId}`}
          className="block text-sm font-medium leading-snug line-clamp-2 text-foreground hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          {data.title}
        </Link>
        <div className="mt-2 flex items-center gap-2">
          <Badge variant="secondary" className="shrink-0 font-mono text-xs">
            {data.year}
          </Badge>
          <span className="truncate text-xs text-muted-foreground">
            {data.shortCitation}
          </span>
        </div>
      </div>
      <Handle
        type="source"
        position={Position.Bottom}
        className="!size-2 !border-0 !bg-border"
      />
    </>
  );
}

const nodeTypes = { paper: PaperNodeComponent };

const EDGE_COLOR = "oklch(0.556 0 0)";

function buildLayout(gNodes: GNode[], gEdges: GEdge[]): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", nodesep: 60, ranksep: 80 });

  gNodes.forEach(({ id }) => g.setNode(id, { width: NODE_W, height: NODE_H }));
  gEdges.forEach(({ source, target }) => g.setEdge(source, target));

  dagre.layout(g);

  const nodes: Node[] = gNodes.map((n) => {
    const pos = g.node(n.id) as { x: number; y: number };
    return {
      id: n.id,
      type: "paper",
      data: {
        arxivId: n.id,
        title: n.title,
        year: n.year,
        shortCitation: n.short_citation,
      },
      position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 },
    };
  });

  const edges: Edge[] = gEdges.map((e, i) => ({
    id: `e-${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
    type: "smoothstep",
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 12,
      height: 12,
      color: EDGE_COLOR,
    },
    style: { stroke: EDGE_COLOR, strokeWidth: 1.5, opacity: 0.5 },
  }));

  return { nodes, edges };
}

export default function GraphPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState({ nodes: 0, edges: 0 });

  useEffect(() => {
    api
      .getGraph()
      .then(({ nodes: gn, edges: ge }) => {
        const { nodes: ln, edges: le } = buildLayout(gn, ge);
        setNodes(ln);
        setEdges(le);
        setCounts({ nodes: gn.length, edges: ge.length });
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-svh items-center justify-center text-sm text-muted-foreground">
        Building citation graph…
      </div>
    );
  }

  return (
    <div className="flex h-svh flex-col overflow-hidden">
      <div className="flex shrink-0 items-center gap-3 border-b border-border px-6 py-3">
        <h1 className="text-sm font-semibold">Citation Graph</h1>
        <span className="text-xs text-muted-foreground">
          {counts.nodes} papers · {counts.edges} citation links
        </span>
      </div>

      <div className="min-h-0 flex-1">
        {counts.nodes === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            No papers ingested yet.{" "}
            <Link href="/papers" className="ml-1 underline">
              Go to Research Library
            </Link>{" "}
            to add some.
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            nodesDraggable={false}
            nodesConnectable={false}
            fitView
            fitViewOptions={{ padding: 0.15 }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1.2}
              color="oklch(0.922 0 0)"
            />
            <Controls showInteractive={false} />
            <MiniMap
              nodeColor="oklch(0.922 0 0)"
              maskColor="rgba(0,0,0,0.04)"
              style={{ border: "1px solid oklch(0.922 0 0)" }}
            />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
