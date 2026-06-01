'use client';

import { useEffect, useRef } from 'react';

interface Node {
  x: number;
  y: number;
  r: number;
  phase: number;
  speed: number;
  hot: boolean;
}

interface Edge {
  a: number;
  b: number;
  style: 'H' | 'V';
}

interface Signal {
  edge: Edge;
  t: number;
  speed: number;
  color: string;
}

interface Point {
  x: number;
  y: number;
}

interface CircuitCanvasProps {
  className?: string;
  opacity?: number;
}

export default function CircuitCanvas({
  className = '',
  opacity = 1,
}: CircuitCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const stateRef = useRef<{
    nodes: Node[];
    edges: Edge[];
    signals: Signal[];
    W: number;
    H: number;
    intervalId?: ReturnType<typeof setInterval>;
  }>({ nodes: [], edges: [], signals: [], W: 0, H: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const context = ctx as CanvasRenderingContext2D;

    function rnd(a: number, b: number) {
      return a + Math.random() * (b - a);
    }

    function buildGraph(W: number, H: number) {
      const count = Math.max(16, Math.floor(W / 48));
      const nodes: Node[] = Array.from({ length: count }, () => ({
        x: rnd(10, W - 10),
        y: rnd(10, H - 10),
        r: rnd(2, 4.5),
        phase: Math.random() * Math.PI * 2,
        speed: rnd(0.018, 0.055),
        hot: Math.random() > 0.68,
      }));

      const edges: Edge[] = [];
      nodes.forEach((a, i) => {
        const near = nodes
          .map((b, j) => {
            if (i === j) return null;
            const d = Math.hypot(a.x - b.x, a.y - b.y);
            return d < 115 ? { j, d } : null;
          })
          .filter((x): x is { j: number; d: number } => x !== null)
          .sort((x, y) => x.d - y.d)
          .slice(0, 2);

        near.forEach(({ j }) => {
          if (
            !edges.find(
              (e) => (e.a === i && e.b === j) || (e.a === j && e.b === i),
            )
          ) {
            edges.push({ a: i, b: j, style: Math.random() > 0.5 ? 'H' : 'V' });
          }
        });
      });

      return { nodes, edges };
    }

    function getPathPoints(nodes: Node[], edge: Edge): Point[] {
      const a = nodes[edge.a];
      const b = nodes[edge.b];
      return edge.style === 'H'
        ? [
            { x: a.x, y: a.y },
            { x: b.x, y: a.y },
            { x: b.x, y: b.y },
          ]
        : [
            { x: a.x, y: a.y },
            { x: a.x, y: b.y },
            { x: b.x, y: b.y },
          ];
    }

    function lerpAlongPath(pts: Point[], t: number): Point {
      const total = pts.reduce(
        (s, p, i) =>
          i === 0 ? 0 : s + Math.hypot(p.x - pts[i - 1].x, p.y - pts[i - 1].y),
        0,
      );
      let target = t * total;
      for (let i = 1; i < pts.length; i++) {
        const dx = pts[i].x - pts[i - 1].x;
        const dy = pts[i].y - pts[i - 1].y;
        const seg = Math.hypot(dx, dy);
        if (target <= seg) {
          const r = target / seg;
          return { x: pts[i - 1].x + dx * r, y: pts[i - 1].y + dy * r };
        }
        target -= seg;
      }
      return pts[pts.length - 1];
    }

    function spawnSignal(edges: Edge[], signals: Signal[]) {
      if (!edges.length) return;
      const edge = edges[Math.floor(Math.random() * edges.length)];
      signals.push({
        edge,
        t: 0,
        speed: rnd(0.005, 0.014),
        color:
          Math.random() > 0.35
            ? 'rgba(99,179,237,0.75)'
            : 'rgba(104,211,145,0.75)',
      });
    }

    function resize() {
      if (!canvas) return;
      const parent = canvas.parentElement;
      if (!parent) return;
      const W = parent.clientWidth;
      const H = parent.clientHeight;
      canvas.width = W;
      canvas.height = H;

      const { nodes, edges } = buildGraph(W, H);
      const signals: Signal[] = [];

      if (stateRef.current.intervalId) {
        clearInterval(stateRef.current.intervalId);
      }

      for (let i = 0; i < 12; i++) {
        setTimeout(() => spawnSignal(edges, signals), i * 250);
      }

      const intervalId = setInterval(() => spawnSignal(edges, signals), 480);
      stateRef.current = { nodes, edges, signals, W, H, intervalId };
    }

    function draw() {
      const { nodes, edges, signals, W, H } = stateRef.current;
      context.clearRect(0, 0, W, H);

      // Draw edges
      edges.forEach((edge) => {
        const pts = getPathPoints(nodes, edge);
        context.beginPath();
        context.moveTo(pts[0].x, pts[0].y);
        pts.slice(1).forEach((pt) => context.lineTo(pt.x, pt.y));
        context.strokeStyle = 'rgba(100,140,200,0.08)';
        context.lineWidth = 0.8;
        context.stroke();
      });

      // Draw & advance signals
      for (let i = signals.length - 1; i >= 0; i--) {
        const sig = signals[i];
        const pts = getPathPoints(nodes, sig.edge);
        const pos = lerpAlongPath(pts, sig.t);

        context.beginPath();
        context.arc(pos.x, pos.y, 3.2, 0, Math.PI * 2);
        context.fillStyle = sig.color;
        context.fill();

        context.beginPath();
        context.arc(pos.x, pos.y, 7, 0, Math.PI * 2);
        context.fillStyle = sig.color.replace('0.75', '0.1');
        context.fill();

        sig.t += sig.speed;
        if (sig.t >= 1) signals.splice(i, 1);
      }

      // Draw nodes
      nodes.forEach((n) => {
        n.phase += n.speed;
        const alpha = n.hot ? 0.4 + 0.6 * Math.sin(n.phase) : 0.15;

        if (n.hot) {
          context.beginPath();
          context.arc(n.x, n.y, n.r + 7, 0, Math.PI * 2);
          context.fillStyle = `rgba(99,179,237,${alpha * 0.12})`;
          context.fill();
        }

        context.beginPath();
        context.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        context.fillStyle = n.hot
          ? `rgba(99,179,237,${alpha})`
          : `rgba(140,170,210,${alpha * 0.45})`;
        context.fill();

        context.beginPath();
        context.arc(n.x, n.y, 1.3, 0, Math.PI * 2);
        context.fillStyle = n.hot ? '#90cdf4' : 'rgba(180,210,240,0.5)';
        context.fill();
      });

      animRef.current = requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener('resize', resize);
    animRef.current = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animRef.current);
      if (stateRef.current.intervalId) {
        clearInterval(stateRef.current.intervalId);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className={className}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        opacity,
      }}
    />
  );
}
