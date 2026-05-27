import Link from 'next/link';

import CircuitCanvas from '@/components/ui/circuit-canvas/circuit-canvas';

export default function HomePage() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-[#f0f4fb] font-sans">
      {/* ── NAVBAR ── */}
      <nav className="sticky top-0 z-50 flex h-[58px] items-center justify-between border-b border-[rgba(99,179,237,0.15)] bg-[rgba(14,22,40,0.97)] px-8">
        <div className="flex items-center gap-2.5">
          <div className="flex size-[34px] shrink-0 items-center justify-center rounded-[9px] border border-[rgba(99,179,237,0.3)] bg-[#1e3a5f]">
            <LogoIcon />
          </div>
          <span className="text-[15px] font-extrabold tracking-tight text-[#f0f4ff]">
            EscapeCircuit
          </span>
        </div>
        <div className="flex gap-2">
          <Link
            href="/auth/login"
            className="rounded-lg border border-[rgba(200,215,255,0.2)] bg-transparent px-[18px] py-[7px] text-[13px] font-medium text-[#c8d7f0] transition-all hover:bg-[rgba(255,255,255,0.06)]"
          >
            Log in
          </Link>
          <Link
            href="/auth/register"
            className="rounded-lg border-none bg-[#63b3ed] px-[18px] py-[7px] text-[13px] font-bold text-[#0e1628] transition-all hover:scale-[1.03] hover:bg-[#90cdf4]"
          >
            Register
          </Link>
        </div>
      </nav>

      {/* ── HERO ── */}
      <section className="relative flex min-h-[520px] items-center justify-center overflow-hidden bg-[#0a1020]">
        <CircuitCanvas />

        <div className="relative z-10 px-7 py-16 text-center">
          {/* Badge */}
          <div className="mb-7 inline-flex animate-fade-up items-center gap-2 rounded-full border border-[rgba(99,179,237,0.4)] bg-[rgba(99,179,237,0.1)] px-[18px] py-[6px] text-[12px] font-semibold tracking-wide text-[#90cdf4] [animation-delay:50ms]">
            <span className="size-2 animate-pulse rounded-full bg-[#63b3ed]" />
            Now live — start solving today
          </div>

          {/* Tagline */}
          <p className="mb-5 animate-fade-up text-[13px] font-bold uppercase tracking-[0.25em] text-[rgba(104,211,145,0.85)] [animation-delay:150ms]">
            Think fast. Wire smarter. Escape.
          </p>

          {/* Headline */}
          <h1 className="mb-5 animate-fade-up text-[clamp(38px,7vw,58px)] font-black leading-[1.02] tracking-[-2px] text-[#f0f4ff] [animation-delay:250ms]">
            Can you crack
            <br />
            the{' '}
            <em className="inline-block animate-accent-pop not-italic text-[#63b3ed] [animation-delay:500ms]">
              circuit?
            </em>
          </h1>

          {/* Subtitle */}
          <p className="mx-auto mb-9 max-w-[400px] animate-fade-up text-[16px] leading-[1.65] text-[rgba(180,205,240,0.55)] [animation-delay:300ms]">
            Logic puzzles that will bend your brain, reward your skill, and keep
            you coming back for more.
          </p>

          {/* CTAs */}
          <div className="flex animate-fade-up flex-wrap justify-center gap-3 [animation-delay:420ms]">
            <Link
              href="/auth/login"
              className="rounded-[11px] border-none bg-[#63b3ed] px-8 py-3.5 text-[14px] font-extrabold text-[#0a1020] transition-all hover:-translate-y-0.5 hover:bg-[#90cdf4] active:scale-[0.97]"
            >
              ⚡ Start solving now
            </Link>
            <Link
              href="#section-2"
              className="rounded-[11px] border border-[rgba(200,215,255,0.22)] bg-transparent px-7 py-3.5 text-[14px] font-medium text-[#e8eeff] transition-all hover:border-[rgba(99,179,237,0.4)] hover:bg-[rgba(255,255,255,0.05)]"
            >
              See how it works
            </Link>
          </div>

          {/* Scroll hint */}
          <div className="mt-11 animate-fade-up [animation-delay:600ms]">
            <div className="inline-flex flex-col items-center gap-1.5 text-[11px] font-medium uppercase tracking-widest text-[rgba(150,175,220,0.4)]">
              <ScrollArrow />
            </div>
          </div>
        </div>
      </section>

      {/* ── FEATURES ── */}
      <section className="bg-[#f0f4fb] px-6 py-[60px]">
        <p className="mb-2.5 text-center text-[11px] font-bold uppercase tracking-[0.18em] text-[#63b3ed]">
          What awaits you
        </p>
        <h2 className="mb-2 text-center text-[30px] font-black tracking-[-0.7px] text-[#0e1628]">
          Your circuit. Your rules.
        </h2>
        <p className="mb-11 text-center text-[14px] leading-relaxed text-[#7a8ba8]">
          Everything you need to become a master solver — all in one place.
        </p>

        <div className="mx-auto grid max-w-[900px] grid-cols-1 gap-8 md:grid-cols-2">
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
      <section
        id="section-2"
        className="scroll-mt-20 border-y border-[#dde5f0] bg-white px-6 py-[52px]"
      >
        <p className="mb-2.5 text-center text-[11px] font-bold uppercase tracking-[0.18em] text-[#63b3ed]">
          How it works
        </p>
        <h2 className="mb-2 text-center text-[30px] font-black tracking-[-0.7px] text-[#0e1628]">
          Up and running in 60 seconds
        </h2>
        <p className="mb-10 text-center text-[14px] text-[#7a8ba8]">
          No setup, no friction — just puzzles.
        </p>

        <div className="mx-auto flex max-w-[580px] items-start justify-center">
          <Step
            num={1}
            title="Register"
            desc="One click, no credit card"
            showLine
          />
          <Step
            num={2}
            title="Pick a puzzle"
            desc="Filter by difficulty or tag"
            showLine
          />
          <Step
            num={3}
            title="Solve & dominate"
            desc="Earn XP, rank up, repeat"
          />
        </div>
      </section>

      {/* ── CTA FOOTER ── */}
      <section className="relative overflow-hidden bg-[#0a1020] px-6 py-16 text-center">
        <CircuitCanvas opacity={0.5} />
        <div className="relative z-10">
          <div className="mb-5 inline-block rounded-full border border-[rgba(104,211,145,0.35)] bg-[rgba(104,211,145,0.12)] px-4 py-1 text-[11px] font-bold uppercase tracking-widest text-[#68d391]">
            Your next challenge is waiting
          </div>
          <h2 className="mb-3 text-[clamp(28px,5vw,36px)] font-black leading-tight tracking-tight text-[#f0f4ff]">
            Stop watching.
            <br />
            Start <em className="not-italic text-[#63b3ed]">escaping.</em>
          </h2>
          <p className="mb-9 text-[15px] leading-relaxed text-[rgba(180,205,240,0.45)]">
            Hundreds of solvers are already wiring away.
            <br />
            Are you next?
          </p>
          <Link
            href="/auth/register"
            className="inline-block rounded-xl border-none bg-[#63b3ed] px-10 py-[15px] text-[15px] font-black tracking-tight text-[#0a1020] transition-all hover:-translate-y-0.5 hover:bg-[#90cdf4] active:scale-[0.97]"
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
  color,
  iconBg,
  icon,
  title,
  desc,
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
        relative flex gap-6 overflow-hidden rounded-[18px] border border-[#dde5f0]
        bg-white p-8
        transition-all duration-200 before:absolute before:inset-x-0
        before:top-0 before:h-[3px] before:rounded-t-[18px] before:opacity-0 before:transition-opacity before:content-['']
        hover:translate-y-[-5px] hover:border-[#b8ceea] hover:before:opacity-100
        ${topColors[color]}
      `}
    >
      <div
        className="flex size-[72px] shrink-0 items-center justify-center rounded-[13px]"
        style={{ background: iconBg }}
      >
        {icon}
      </div>
      <div className="flex flex-col justify-center">
        <p className="mb-2 text-[17px] font-extrabold text-[#0e1628]">
          {title}
        </p>
        <p className="text-[13px] leading-[1.55] text-[#6b7899]">{desc}</p>
      </div>
    </div>
  );
}

function Step({
  num,
  title,
  desc,
  showLine,
}: {
  num: number;
  title: string;
  desc: string;
  showLine?: boolean;
}) {
  return (
    <div className="relative flex-1 px-2.5 text-center">
      {showLine && (
        <div className="absolute left-[calc(50%+24px)] right-[calc(-50%+24px)] top-[19px] h-px bg-[#d0daea]" />
      )}
      <div className="mx-auto mb-3.5 flex size-[38px] items-center justify-center rounded-full border-2 border-[rgba(99,179,237,0.25)] bg-[#0e1628] text-[13px] font-black text-[#63b3ed]">
        {num}
      </div>
      <p className="mb-1 text-[13px] font-extrabold text-[#0e1628]">{title}</p>
      <p className="text-[12px] leading-relaxed text-[#8a96b0]">{desc}</p>
    </div>
  );
}

/* ── ICONS ── */
function LogoIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
      <circle cx="9" cy="9" r="2" fill="#63b3ed" />
      <line
        x1="9"
        y1="2"
        x2="9"
        y2="7"
        stroke="#63b3ed"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <line
        x1="9"
        y1="11"
        x2="9"
        y2="16"
        stroke="#63b3ed"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <line
        x1="2"
        y1="9"
        x2="7"
        y2="9"
        stroke="#63b3ed"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <line
        x1="11"
        y1="9"
        x2="16"
        y2="9"
        stroke="#63b3ed"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <circle cx="9" cy="2" r="1.3" fill="#f6ad55" />
      <circle cx="9" cy="16" r="1.3" fill="#68d391" />
      <circle cx="2" cy="9" r="1.3" fill="#fc8181" />
      <circle cx="16" cy="9" r="1.3" fill="#b794f4" />
    </svg>
  );
}
function PuzzleIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 22 22"
      fill="none"
      stroke="#2b7bc8"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="12" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="12" width="7" height="7" rx="1.5" />
      <path d="M12 15.5h7M15.5 12v7" />
    </svg>
  );
}
function StarIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 22 22"
      fill="none"
      stroke="#c07e10"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polygon points="11,2 13.5,8.5 20.5,8.5 14.8,12.5 17,19 11,15 5,19 7.2,12.5 1.5,8.5 8.5,8.5" />
    </svg>
  );
}
function DiscussIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 22 22"
      fill="none"
      stroke="#22863a"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M4 6h14M4 10h9M4 14h11" />
      <circle cx="18" cy="14" r="2.5" />
      <path d="M17 16.5L20 19" />
    </svg>
  );
}
function CreateIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 22 22"
      fill="none"
      stroke="#7c3aed"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="2" y="4" width="18" height="14" rx="2" />
      <path d="M7 9l3 3-3 3M12 15h3" />
    </svg>
  );
}
function ScrollArrow() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      stroke="rgba(150,175,220,0.4)"
      strokeWidth="1.5"
      strokeLinecap="round"
      className="animate-bounce"
    >
      <path d="M10 4v12M5 11l5 5 5-5" />
    </svg>
  );
}
