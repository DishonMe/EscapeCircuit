import Link from 'next/link';
import CircuitCanvas from '@/components/ui/circuit-canvas/CircuitCanvas';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#f0f4fb] font-sans overflow-x-hidden">

      {/* ── NAVBAR ── */}
      <nav className="flex items-center justify-between px-8 h-[58px] bg-[rgba(14,22,40,0.97)] border-b border-[rgba(99,179,237,0.15)] sticky top-0 z-50">
        <div className="flex items-center gap-2.5">
          <div className="w-[34px] h-[34px] bg-[#1e3a5f] border border-[rgba(99,179,237,0.3)] rounded-[9px] flex items-center justify-center flex-shrink-0">
            <LogoIcon />
          </div>
          <span className="text-[15px] font-extrabold text-[#f0f4ff] tracking-tight">
            EscapeCircuit
          </span>
        </div>
        <div className="flex gap-2">
          <Link
            href="/auth/login"
            className="bg-transparent border border-[rgba(200,215,255,0.2)] rounded-lg px-[18px] py-[7px] text-[13px] font-medium text-[#c8d7f0] hover:bg-[rgba(255,255,255,0.06)] transition-all"
          >
            Log in
          </Link>
          <Link
            href="/auth/register"
            className="bg-[#63b3ed] border-none rounded-lg px-[18px] py-[7px] text-[13px] font-bold text-[#0e1628] hover:bg-[#90cdf4] hover:scale-[1.03] transition-all"
          >
            Register
          </Link>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="relative overflow-hidden min-h-[520px] flex items-center justify-center bg-[#0a1020]">
        <CircuitCanvas />

        <div className="relative z-10 text-center px-7 py-16">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 bg-[rgba(99,179,237,0.1)] border border-[rgba(99,179,237,0.4)] rounded-full px-[18px] py-[6px] text-[12px] font-semibold text-[#90cdf4] mb-7 tracking-wide animate-fade-up [animation-delay:50ms]">
            <span className="w-2 h-2 rounded-full bg-[#63b3ed] animate-pulse" />
            Now live — start solving today
          </div>

          {/* Tagline */}
          <p className="text-[13px] font-bold tracking-[0.25em] uppercase text-[rgba(104,211,145,0.85)] mb-5 animate-fade-up [animation-delay:150ms]">
            Think fast. Wire smarter. Escape.
          </p>

          {/* Headline */}
          <h1 className="text-[clamp(38px,7vw,58px)] font-black leading-[1.02] text-[#f0f4ff] tracking-[-2px] mb-5 animate-fade-up [animation-delay:250ms]">
            Can you crack
            <br />
            the{' '}
            <em className="not-italic text-[#63b3ed] inline-block animate-accent-pop [animation-delay:500ms]">
              circuit?
            </em>
          </h1>

          {/* Subtitle */}
          <p className="text-[16px] text-[rgba(180,205,240,0.55)] max-w-[400px] mx-auto mb-9 leading-[1.65] animate-fade-up [animation-delay:300ms]">
            Logic puzzles that will bend your brain, reward your skill, and keep you coming back for more.
          </p>

          {/* CTAs */}
          <div className="flex gap-3 justify-center flex-wrap animate-fade-up [animation-delay:420ms]">
            <Link
              href="/auth/login"
              className="bg-[#63b3ed] text-[#0a1020] border-none rounded-[11px] px-8 py-3.5 text-[14px] font-extrabold hover:-translate-y-0.5 hover:bg-[#90cdf4] active:scale-[0.97] transition-all"
            >
              ⚡ Start solving now
            </Link>
            <button className="bg-transparent text-[#e8eeff] border border-[rgba(200,215,255,0.22)] rounded-[11px] px-7 py-3.5 text-[14px] font-medium hover:bg-[rgba(255,255,255,0.05)] hover:border-[rgba(99,179,237,0.4)] transition-all">
              See how it works
            </button>
          </div>

          {/* Scroll hint */}
          <div className="mt-11 animate-fade-up [animation-delay:600ms]">
            <div className="inline-flex flex-col items-center gap-1.5 text-[rgba(150,175,220,0.4)] text-[11px] font-medium tracking-widest uppercase">
              <ScrollArrow />
            </div>
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="py-[60px] px-6 bg-[#f0f4fb]">
        <p className="text-center text-[11px] font-bold tracking-[0.18em] uppercase text-[#63b3ed] mb-2.5">
          What awaits you
        </p>
        <h2 className="text-center text-[30px] font-black text-[#0e1628] tracking-[-0.7px] mb-2">
          Your circuit. Your rules.
        </h2>
        <p className="text-center text-[14px] text-[#7a8ba8] mb-11 leading-relaxed">
          Everything you need to become a master solver — all in one place.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-[900px] mx-auto">
          <FeatureCard
            color="blue"
            iconBg="#EBF4FF"
            icon={<PuzzleIcon />}
            title="Solve puzzles"
            desc="Dozens of logic-circuit challenges across every difficulty — from sparks to full surges."
          />
          <FeatureCard
            color="amber"
            iconBg="#FFFBEB"
            icon={<StarIcon />}
            title="Earn XP & level up"
            desc="Every solved puzzle earns you points. Climb ranks, unlock badges, dominate the board."
          />
          <FeatureCard
            color="green"
            iconBg="#F0FDF4"
            icon={<DiscussIcon />}
            title="Discuss & connect"
            desc="Swap strategies, ask the community, and discover clever solutions you never imagined."
          />
          <FeatureCard
            color="purple"
            iconBg="#FAF5FF"
            icon={<CreateIcon />}
            title="Build your own"
            desc="Design and publish custom circuits. Challenge the community with your own devious puzzles."
          />
        </div>
      </section>

      {/* ── HOW IT WORKS ── */}
      <section className="bg-white border-t border-b border-[#dde5f0] py-[52px] px-6">
        <p className="text-center text-[11px] font-bold tracking-[0.18em] uppercase text-[#63b3ed] mb-2.5">
          How it works
        </p>
        <h2 className="text-center text-[30px] font-black text-[#0e1628] tracking-[-0.7px] mb-2">
          Up and running in 60 seconds
        </h2>
        <p className="text-center text-[14px] text-[#7a8ba8] mb-10">
          No setup, no friction — just puzzles.
        </p>

        <div className="flex items-start justify-center max-w-[580px] mx-auto">
          <Step num={1} title="Register" desc="One click, no credit card" showLine />
          <Step num={2} title="Pick a puzzle" desc="Filter by difficulty or tag" showLine />
          <Step num={3} title="Solve & dominate" desc="Earn XP, rank up, repeat" />
        </div>
      </section>

      {/* ── CTA FOOTER ── */}
      <section className="bg-[#0a1020] py-16 px-6 text-center relative overflow-hidden">
        <CircuitCanvas opacity={0.5} />
        <div className="relative z-10">
          <div className="inline-block bg-[rgba(104,211,145,0.12)] border border-[rgba(104,211,145,0.35)] rounded-full px-4 py-1 text-[11px] font-bold text-[#68d391] tracking-[0.1em] uppercase mb-5">
            Your next challenge is waiting
          </div>
          <h2 className="text-[clamp(28px,5vw,36px)] font-black text-[#f0f4ff] tracking-tight mb-3 leading-tight">
            Stop watching.
            <br />
            Start{' '}
            <em className="not-italic text-[#63b3ed]">escaping.</em>
          </h2>
          <p className="text-[15px] text-[rgba(180,205,240,0.45)] mb-9 leading-relaxed">
            Hundreds of solvers are already wiring away.
            <br />
            Are you next?
          </p>
          <Link
            href="/auth/register"
            className="inline-block bg-[#63b3ed] text-[#0a1020] border-none rounded-xl px-10 py-[15px] text-[15px] font-black tracking-tight hover:bg-[#90cdf4] hover:-translate-y-0.5 active:scale-[0.97] transition-all"
          >
            ⚡ Create Account
          </Link>
        </div>
      </section>

    </div>
  );
}

/* ── SUB-COMPONENTS ── */

function FeatureCard({
  color, iconBg, icon, title, desc,
}: {
  color: 'blue' | 'amber' | 'green' | 'purple';
  iconBg: string;
  icon: React.ReactNode;
  title: string;
  desc: string;
}) {
  const topColors = {
    blue: 'before:bg-[#63b3ed]',
    amber: 'before:bg-[#f6ad55]',
    green: 'before:bg-[#68d391]',
    purple: 'before:bg-[#b794f4]',
  };

  return (
    <div
      className={`
        bg-white border border-[#dde5f0] rounded-[18px] p-8 transition-all duration-200
        hover:-translate-y-[5px] hover:border-[#b8ceea]
        relative overflow-hidden flex gap-6
        before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:h-[3px]
        before:rounded-t-[18px] before:opacity-0 hover:before:opacity-100 before:transition-opacity
        ${topColors[color]}
      `}
    >
      <div
        className="w-[72px] h-[72px] rounded-[13px] flex items-center justify-center flex-shrink-0"
        style={{ background: iconBg }}
      >
        {icon}
      </div>
      <div className="flex flex-col justify-center">
        <p className="text-[17px] font-extrabold text-[#0e1628] mb-2">{title}</p>
        <p className="text-[13px] text-[#6b7899] leading-[1.55]">{desc}</p>
      </div>
    </div>
  );
}

function Step({ num, title, desc, showLine }: {
  num: number; title: string; desc: string; showLine?: boolean;
}) {
  return (
    <div className="flex-1 text-center px-2.5 relative">
      {showLine && (
        <div className="absolute top-[19px] left-[calc(50%+24px)] right-[calc(-50%+24px)] h-px bg-[#d0daea]" />
      )}
      <div className="w-[38px] h-[38px] rounded-full bg-[#0e1628] border-2 border-[rgba(99,179,237,0.25)] text-[#63b3ed] text-[13px] font-black flex items-center justify-center mx-auto mb-3.5">
        {num}
      </div>
      <p className="text-[13px] font-extrabold text-[#0e1628] mb-1">{title}</p>
      <p className="text-[12px] text-[#8a96b0] leading-relaxed">{desc}</p>
    </div>
  );
}

/* ── ICONS ── */
function LogoIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="2" fill="#63b3ed" />
      <line x1="9" y1="2" x2="9" y2="7" stroke="#63b3ed" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="9" y1="11" x2="9" y2="16" stroke="#63b3ed" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="2" y1="9" x2="7" y2="9" stroke="#63b3ed" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="11" y1="9" x2="16" y2="9" stroke="#63b3ed" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="9" cy="2" r="1.3" fill="#f6ad55" />
      <circle cx="9" cy="16" r="1.3" fill="#68d391" />
      <circle cx="2" cy="9" r="1.3" fill="#fc8181" />
      <circle cx="16" cy="9" r="1.3" fill="#b794f4" />
    </svg>
  );
}
function PuzzleIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#2b7bc8" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="12" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="12" width="7" height="7" rx="1.5" />
      <path d="M12 15.5h7M15.5 12v7" />
    </svg>
  );
}
function StarIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#c07e10" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="11,2 13.5,8.5 20.5,8.5 14.8,12.5 17,19 11,15 5,19 7.2,12.5 1.5,8.5 8.5,8.5" />
    </svg>
  );
}
function DiscussIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#22863a" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 6h14M4 10h9M4 14h11" />
      <circle cx="18" cy="14" r="2.5" />
      <path d="M17 16.5L20 19" />
    </svg>
  );
}
function CreateIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="#7c3aed" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="4" width="18" height="14" rx="2" />
      <path d="M7 9l3 3-3 3M12 15h3" />
    </svg>
  );
}
function ScrollArrow() {
  return (
    <svg
      width="20" height="20" viewBox="0 0 20 20" fill="none"
      stroke="rgba(150,175,220,0.4)" strokeWidth="1.5" strokeLinecap="round"
      className="animate-bounce"
    >
      <path d="M10 4v12M5 11l5 5 5-5" />
    </svg>
  );
}
