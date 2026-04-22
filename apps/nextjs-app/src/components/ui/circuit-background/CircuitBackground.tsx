"use client";

import { useEffect, useRef } from "react";

const GRID = 48;
const NODE_COLOR = "rgba(56,189,248,";

interface Node {
  x: number;
  y: number;
  baseAlpha: number;
  pulseAlpha: number;
  size: number;
  col: number;
}
interface Edge {
  a: number;
  b: number;
  alpha: number;
}
interface Pulse {
  edge: Edge;
  t: number;
  speed: number;
}

export function CircuitBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let nodes: Node[] = [];
    let edges: Edge[] = [];
    let pulses: Pulse[] = [];
    let animId: number;
    let spawnId: ReturnType<typeof setInterval>;
    let last = 0;

    function resize() {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      init();
    }

    function init() {
      nodes = [];
      edges = [];
      pulses = [];
      const cols = Math.ceil(canvas.width / GRID) + 1;
      const rows = Math.ceil(canvas.height / GRID) + 1;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          nodes.push({
            x: c * GRID + (Math.random() - 0.5) * 10,
            y: r * GRID + (Math.random() - 0.5) * 10,
            col: c,
            baseAlpha: 0.08 + Math.random() * 0.12,
            pulseAlpha: 0,
            size: Math.random() < 0.15 ? 2.5 : 1.5,
          });
        }
      }

      const totalCols = Math.ceil(canvas.width / GRID) + 1;
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i + 1] && nodes[i].col < totalCols - 1 && Math.random() > 0.25) {
          edges.push({ a: i, b: i + 1, alpha: 0.06 + Math.random() * 0.06 });
        }
        if (nodes[i + totalCols] && Math.random() > 0.25) {
          edges.push({ a: i, b: i + totalCols, alpha: 0.06 + Math.random() * 0.06 });
        }
      }
    }

    function spawnPulse() {
      if (!edges.length) return;
      const edge = edges[Math.floor(Math.random() * edges.length)];
      pulses.push({ edge, t: 0, speed: 0.004 + Math.random() * 0.006 });
    }

    function draw(ts: number) {
      const dt = ts - last;
      last = ts;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      for (const n of nodes) {
        if (n.pulseAlpha > 0) n.pulseAlpha -= dt * 0.002;
      }

      for (const e of edges) {
        const a = nodes[e.a];
        const b = nodes[e.b];
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = NODE_COLOR + e.alpha + ")";
        ctx.lineWidth = 0.5;
        ctx.stroke();
      }

      pulses = pulses.filter((p) => {
        p.t += p.speed * dt;
        if (p.t > 1) {
          nodes[p.edge.b].pulseAlpha = 0.7;
          if (Math.random() < 0.6) {
            const next = edges.filter((e) => e.a === p.edge.b || e.b === p.edge.b);
            if (next.length) {
              pulses.push({
                edge: next[Math.floor(Math.random() * next.length)],
                t: 0,
                speed: 0.004 + Math.random() * 0.006,
              });
            }
          }
          return false;
        }
        const a = nodes[p.edge.a];
        const b = nodes[p.edge.b];
        ctx.beginPath();
        ctx.arc(a.x + (b.x - a.x) * p.t, a.y + (b.y - a.y) * p.t, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = NODE_COLOR + 0.8 * (1 - Math.abs(p.t - 0.5) * 1.5) + ")";
        ctx.fill();
        return true;
      });

      for (const n of nodes) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.size, 0, Math.PI * 2);
        ctx.fillStyle = NODE_COLOR + Math.min(n.baseAlpha + n.pulseAlpha, 1) + ")";
        ctx.fill();
      }

      animId = requestAnimationFrame(draw);
    }

    resize();
    spawnId = setInterval(spawnPulse, 120);
    animId = requestAnimationFrame((ts) => {
      last = ts;
      draw(ts);
    });

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    return () => {
      cancelAnimationFrame(animId);
      clearInterval(spawnId);
      ro.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none absolute inset-0 h-full w-full"
      aria-hidden="true"
    />
  );
}
