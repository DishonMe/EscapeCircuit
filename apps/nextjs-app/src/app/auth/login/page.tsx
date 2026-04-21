'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { paths } from '@/config/paths';
import { useNavigationLoading } from '@/components/ui/navigation-loading/navigation-loading';
import { useNotifications } from '@/components/ui/notifications';

interface Node {
  x: number; y: number; r: number;
  ph: number; sp: number; hot: boolean;
}
interface Edge { a: number; b: number; s: 'H' | 'V' }
interface Signal { edge: Edge; t: number; sp: number; c: string }

function useCircuitCanvas(ref: React.RefObject<HTMLCanvasElement>) {
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const context = ctx as CanvasRenderingContext2D;
    let nodes: Node[] = [], edges: Edge[] = [], sigs: Signal[] = [];
    let W = 0, H = 0, animId = 0, iid: ReturnType<typeof setInterval>;

    const rnd = (a: number, b: number) => a + Math.random() * (b - a);

    function build() {
      clearInterval(iid);
      const n = Math.max(12, Math.floor(W / 52));
      nodes = Array.from({ length: n }, () => ({
        x: rnd(10, W - 10), y: rnd(10, H - 10),
        r: rnd(1.8, 4), ph: Math.random() * Math.PI * 2,
        sp: rnd(0.018, 0.05), hot: Math.random() > 0.65,
      }));
      edges = [];
      nodes.forEach((a, i) => {
        nodes
          .map((b, j) => {
            if (i === j) return null;
            const d = Math.hypot(a.x - b.x, a.y - b.y);
            return d < 115 ? { j, d } : null;
          })
          .filter((x): x is { j: number; d: number } => x !== null)
          .sort((x, y) => x.d - y.d)
          .slice(0, 2)
          .forEach(({ j }) => {
            if (!edges.find(e => (e.a === i && e.b === j) || (e.a === j && e.b === i)))
              edges.push({ a: i, b: j, s: Math.random() > 0.5 ? 'H' : 'V' });
          });
      });
      sigs = [];
      for (let i = 0; i < 10; i++) setTimeout(spawn, i * 270);
      iid = setInterval(spawn, 540);
    }

    function spawn() {
      if (!edges.length) return;
      const edge = edges[Math.floor(Math.random() * edges.length)];
      sigs.push({
        edge, t: 0, sp: rnd(0.005, 0.013),
        c: Math.random() > 0.3 ? 'rgba(99,179,237,0.72)' : 'rgba(104,211,145,0.65)',
      });
    }

    function pts(a: Node, b: Node, s: 'H' | 'V') {
      return s === 'H'
        ? [{ x: a.x, y: a.y }, { x: b.x, y: a.y }, { x: b.x, y: b.y }]
        : [{ x: a.x, y: a.y }, { x: a.x, y: b.y }, { x: b.x, y: b.y }];
    }

    function lerp(path: { x: number; y: number }[], t: number) {
      const tot = path.reduce((s, p, i) =>
        i === 0 ? 0 : s + Math.hypot(p.x - path[i - 1].x, p.y - path[i - 1].y), 0);
      let tg = t * tot;
      for (let i = 1; i < path.length; i++) {
        const dx = path[i].x - path[i - 1].x, dy = path[i].y - path[i - 1].y;
        const seg = Math.hypot(dx, dy);
        if (tg <= seg) { const r = tg / seg; return { x: path[i - 1].x + dx * r, y: path[i - 1].y + dy * r }; }
        tg -= seg;
      }
      return path[path.length - 1];
    }

    function resize() {
      if (!canvas) return;
      const par = canvas.parentElement;
      if (!par) return;
      W = par.clientWidth; H = par.clientHeight;
      canvas.width = W; canvas.height = H;
      build();
    }

    function draw() {
      context.clearRect(0, 0, W, H);
      edges.forEach(e => {
        const a = nodes[e.a], b = nodes[e.b], p = pts(a, b, e.s);
        context.beginPath(); context.moveTo(p[0].x, p[0].y);
        p.slice(1).forEach(pt => context.lineTo(pt.x, pt.y));
        context.strokeStyle = 'rgba(90,140,200,0.1)'; context.lineWidth = 0.75; context.stroke();
      });
      for (let i = sigs.length - 1; i >= 0; i--) {
        const sg = sigs[i];
        const a = nodes[sg.edge.a], b = nodes[sg.edge.b];
        const p = pts(a, b, sg.edge.s), pos = lerp(p, sg.t);
        context.beginPath(); context.arc(pos.x, pos.y, 2.8, 0, Math.PI * 2);
        context.fillStyle = sg.c; context.fill();
        context.beginPath(); context.arc(pos.x, pos.y, 6, 0, Math.PI * 2);
        context.fillStyle = sg.c.replace('0.72', '0.1').replace('0.65', '0.08'); context.fill();
        sg.t += sg.sp;
        if (sg.t >= 1) sigs.splice(i, 1);
      }
      nodes.forEach(n => {
        n.ph += n.sp;
        const a = n.hot ? 0.38 + 0.62 * Math.sin(n.ph) : 0.13;
        if (n.hot) {
          context.beginPath(); context.arc(n.x, n.y, n.r + 6, 0, Math.PI * 2);
          context.fillStyle = `rgba(99,179,237,${a * 0.12})`; context.fill();
        }
        context.beginPath(); context.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        context.fillStyle = n.hot ? `rgba(99,179,237,${a})` : `rgba(120,160,200,${a * 0.4})`;
        context.fill();
        context.beginPath(); context.arc(n.x, n.y, 1.1, 0, Math.PI * 2);
        context.fillStyle = n.hot ? '#90cdf4' : 'rgba(160,200,230,0.45)'; context.fill();
      });
      animId = requestAnimationFrame(draw);
    }

    resize();
    window.addEventListener('resize', resize);
    animId = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animId);
      clearInterval(iid);
      window.removeEventListener('resize', resize);
    };
  }, [ref]);
}

export default function LoginPage() {
  const router = useRouter();
  const { startNavigation } = useNavigationLoading();
  const searchParams = useSearchParams();
  const redirectTo = searchParams?.get('redirectTo');
  const { addNotification } = useNotifications();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useCircuitCanvas(canvasRef);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password) {
      setError('Please fill in all fields.');
      return;
    }
    setLoading(true);
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.message ?? 'Login failed. Please try again.');
      }
      addNotification({
        type: 'success',
        title: 'Login Successful',
        message: 'Welcome back!',
      });
      const destination = redirectTo ? decodeURIComponent(redirectTo) : paths.app.puzzles.getHref();
      startNavigation(destination);
      router.push(destination);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative flex h-screen items-start justify-center overflow-hidden pt-8">
      {/* Animated Background */}
      <canvas
        ref={canvasRef}
        className="pointer-events-none absolute inset-0"
      />

      {/* Form Card */}
      <div className="relative z-10 w-full rounded-xl border border-[#e8edf5] bg-white p-6 shadow-lg sm:w-[380px]">
        {/* Header section */}
        <div className="mb-3">
          <h1 className="mb-0.5 text-[22px] font-black leading-tight tracking-tight text-[#0e1628]">
            Welcome back
          </h1>
          <p className="text-[13px] leading-relaxed text-[#8a96b0]">
            Don't have an account?{' '}
            <Link href={paths.auth.register.getHref(redirectTo)} className="font-semibold text-[#2a7fc9] hover:underline">
              Sign up
            </Link>
          </p>
        </div>

        {/* Form section */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-3" noValidate>
          {/* username */}
          <div className="flex flex-col gap-1.5">
            <label className="block text-[12px] font-bold tracking-[0.01em] text-[#2d3a52]">
              Username
            </label>
            <div className="relative">
              <FieldIcon><UserIcon /></FieldIcon>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="your_handle"
                autoComplete="username"
                className="h-10 w-full rounded-[9px] border border-[#dce4ef] bg-[#f7f9fc] pl-[34px] pr-3 text-[13px] text-[#0e1628] placeholder-[#b8c5d3] outline-none transition-all focus:border-[#63b3ed] focus:bg-white focus:shadow-[0_0_0_3px_rgba(99,179,237,0.13)]"
              />
            </div>
          </div>

          {/* password */}
          <div className="flex flex-col gap-1.5">
            <label className="block text-[12px] font-bold tracking-[0.01em] text-[#2d3a52]">
              Password
            </label>
            <div className="relative">
              <FieldIcon><LockIcon /></FieldIcon>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="your password"
                autoComplete="current-password"
                className="h-10 w-full rounded-[9px] border border-[#dce4ef] bg-[#f7f9fc] pl-[34px] pr-3 text-[13px] text-[#0e1628] placeholder-[#b8c5d3] outline-none transition-all focus:border-[#63b3ed] focus:bg-white focus:shadow-[0_0_0_3px_rgba(99,179,237,0.13)]"
              />
            </div>
          </div>

          {/* error */}
          {error && (
            <p className="rounded-[8px] border border-[#fcc] bg-[#fff5f5] px-3 py-2 text-[12px] font-medium text-[#c0392b]">
              {error}
            </p>
          )}

          {/* submit */}
          <button
            type="submit"
            disabled={loading}
            className="mt-1 flex h-[42px] w-full items-center justify-center gap-2 rounded-[9px] bg-[#0e1628] text-[13px] font-black tracking-[0.01em] text-white transition-all hover:bg-[#1a2a46] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? (
              <LoadingSpinner />
            ) : (
              <>
                <KeyIcon />
                Log in
              </>
            )}
          </button>
        </form>

        {/* --- Motivational Section --- */}
        <div className="mt-8 flex flex-col items-center justify-center border-t border-[#e8edf5] pt-6">
          <span className="mb-2 text-[10px] font-extrabold uppercase tracking-[0.25em] text-[#8a96b0]">
            Welcome to the challenge
          </span>
          <h2 className="text-center text-[20px] font-black leading-tight text-[#0e1628]">
            Logic dictates the rules. <br />
            <span className="animate-pulse bg-gradient-to-r from-[#63b3ed] to-[#2a7fc9] bg-clip-text text-transparent drop-shadow-sm">
              You dictate the escape.
            </span>
          </h2>
        </div>

      </div>
    </div>
  );
}

/* ── tiny sub-components ── */

function FieldIcon({ children }: { children: React.ReactNode }) {
  return (
    <div className="pointer-events-none absolute left-[11px] top-1/2 flex -translate-y-1/2 items-center">
      {children}
    </div>
  );
}

function LoadingSpinner() {
  return (
    <svg className="h-4 w-4 animate-spin text-[#63b3ed]" viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 100 16v-4l-3 3 3 3v-4a8 8 0 01-8-8z" />
    </svg>
  );
}

/* ── icons ── */
function UserIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="#9aabbf" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="4.5" r="2.5" />
      <path d="M1.5 13c0-3 2.5-5 5.5-5s5.5 2 5.5 5" />
    </svg>
  );
}
function LockIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="#9aabbf" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="6" width="8" height="6.5" rx="1.5" />
      <path d="M5 6V4.5a2 2 0 014 0V6" />
    </svg>
  );
}
function KeyIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="#63b3ed" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="4.5" cy="10" r="2.5" />
      <path d="M7 7.5l4-4M10.5 3.5l1 1" />
    </svg>
  );
}
