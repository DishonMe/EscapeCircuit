'use client';

import {
  BookOpen,
  Bug,
  ChevronDown,
  CircuitBoard,
  Code,
  Download,
  ExternalLink,
  FileCheck,
  FileText,
  GraduationCap,
  Home,
  Menu,
  Presentation,
  Puzzle,
  Users,
  X,
  Zap,
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import CircuitCanvas from '@/components/ui/circuit-canvas/circuit-canvas';

/* ── Data ── */

const GITHUB_URL = 'https://github.com/DishonMe/EscapeCircuit';

const NAV_LINKS = [
  { href: '#about', label: 'About' },
  { href: '#demo', label: 'Demo' },
  { href: '#manual', label: 'Manual' },
  { href: '#docs', label: 'Docs' },
  { href: '#team', label: 'Team' },
];

const STATS = [
  { value: '550+', label: 'Commits' },
  { value: '150+', label: 'Pull requests merged' },
  { value: '12', label: 'Built-in riddles' },
  { value: '3', label: 'Test frameworks' },
];

const TECH_STACK = [
  'Next.js 14',
  'TypeScript',
  'Tailwind CSS',
  'Zustand',
  'React Query',
  'Radix UI',
  'FastAPI',
  'Python',
  'SQLite',
  'JWT + Google OAuth',
  'Vitest',
  'Playwright',
  'Pytest',
];

const TEAM = [
  { name: 'Dor Steinlauf', role: 'Software Engineering Student' },
  { name: 'Noam Shlomo Yosef', role: 'Software Engineering Student' },
  { name: 'Mendy Dishon', role: 'Software Engineering Student' },
  { name: 'Yuval Zarmi', role: 'Software Engineering Student' },
];

const MANUAL_STEPS = [
  {
    step: '01',
    title: 'Register & pick a puzzle',
    body: 'Create an account or sign in with Google, then browse the puzzle arena. Filter by difficulty, pick a riddle, and read what your circuit needs to do.',
    icon: <Puzzle className="size-7" aria-hidden="true" />,
    label: 'Puzzle arena',
  },
  {
    step: '02',
    title: 'Wire your circuit',
    body: 'Drag logic gates from the toolbox onto the workstation canvas and connect output pins to input pins. AND, OR, NOT, XOR and flip-flops are all available, so any truth table can be built.',
    icon: <CircuitBoard className="size-7" aria-hidden="true" />,
    label: 'Workstation',
  },
  {
    step: '03',
    title: 'Debug & submit',
    body: 'Step through your circuit tick by tick with the built-in debugger. Signal states are colour-coded live, so you can trace exactly where the logic breaks. When every output matches, submit to earn XP.',
    icon: <Bug className="size-7" aria-hidden="true" />,
    label: 'Debugger',
  },
  {
    step: '04',
    title: 'Level up & build your own',
    body: 'Earn XP, climb the leaderboard, and unlock advanced gates in your arsenal. You can also create your own riddles and publish them for the community to solve.',
    icon: <Zap className="size-7" aria-hidden="true" />,
    label: 'Arsenal & creator',
  },
];

const DOCS = [
  {
    title: 'Architecture Design Document',
    tag: 'Design',
    size: '5.4 MB',
    description:
      'System architecture, component diagrams, and the technology decisions behind the platform.',
    icon: <FileText className="size-5" aria-hidden="true" />,
    href: '/portfolio/EscapeCircuit_ADD.pdf',
  },
  {
    title: 'Comprehensive User Guide',
    tag: 'Manual',
    size: '1.3 MB',
    description:
      'The full manual, with interface screenshots and instructions for the workstation, puzzles, and every core feature.',
    icon: <BookOpen className="size-5" aria-hidden="true" />,
    href: '/portfolio/EscapeCircuit_User_Guide.pdf',
  },
  {
    title: 'Maintainer & Extension Guide',
    tag: 'Maintenance',
    size: '0.5 MB',
    description:
      'System maintenance, database setup, deployment, and how to extend the platform with new puzzles.',
    icon: <FileCheck className="size-5" aria-hidden="true" />,
    href: '/portfolio/EscapeCircuit_Maintainer_Guide.pdf',
  },
  {
    title: 'Release Notes',
    tag: 'Release',
    size: '0.1 MB',
    description:
      'What shipped in the final iteration: new puzzles, the clue system, admin tools, and more.',
    icon: <Presentation className="size-5" aria-hidden="true" />,
    href: '/portfolio/EscapeCircuit_Release_Notes.pdf',
  },
];

/* ── Small building blocks ── */

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2.5 text-center text-[11px] font-bold uppercase tracking-[0.18em] text-[#63b3ed]">
      {children}
    </p>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-3 text-center text-[clamp(26px,4.5vw,34px)] font-black tracking-[-0.7px] text-[#f0f4ff]">
      {children}
    </h2>
  );
}

function MonogramAvatar({ name }: { name: string }) {
  const initials = name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
  return (
    <div className="mx-auto mb-4 flex size-20 items-center justify-center rounded-full border-2 border-[rgba(99,179,237,0.35)] bg-[#1e3a5f]">
      <span className="text-xl font-black tracking-widest text-[#90cdf4]">
        {initials}
      </span>
    </div>
  );
}

/* ── Navbar ── */

function PortfolioNavbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'border-b border-[rgba(99,179,237,0.15)] bg-[rgba(10,16,32,0.95)] backdrop-blur-md'
          : 'bg-transparent'
      }`}
    >
      <a
        href="#main-content"
        className="sr-only z-[100] rounded-md bg-[#63b3ed] px-4 py-2 text-xs font-bold text-[#0a1020] focus:not-sr-only focus:absolute focus:left-4 focus:top-4"
      >
        Skip to main content
      </a>

      <nav
        className="mx-auto flex h-[58px] max-w-6xl items-center justify-between px-6"
        aria-label="Portfolio navigation"
      >
        <a
          href="#hero"
          className="flex items-center gap-2 text-[15px] font-extrabold tracking-tight text-[#f0f4ff]"
        >
          <CircuitBoard className="size-5 text-[#63b3ed]" aria-hidden="true" />
          EscapeCircuit
          <span className="ml-1 hidden rounded-full border border-[rgba(104,211,145,0.35)] bg-[rgba(104,211,145,0.12)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest text-[#68d391] sm:inline">
            Project Day
          </span>
        </a>

        <ul className="hidden items-center gap-7 lg:flex">
          {NAV_LINKS.map((l) => (
            <li key={l.href}>
              <a
                href={l.href}
                className="text-[12px] font-semibold uppercase tracking-widest text-[rgba(180,205,240,0.6)] transition-colors hover:text-[#90cdf4]"
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="hidden items-center gap-2 lg:flex">
          <Link
            href="/"
            className="flex items-center gap-1.5 rounded-lg bg-[#63b3ed] px-4 py-[7px] text-[13px] font-bold text-[#0a1020] transition-all hover:bg-[#90cdf4]"
          >
            <Zap className="size-3.5" aria-hidden="true" />
            Launch app
          </Link>
        </div>

        <button
          className="rounded p-1 text-[rgba(180,205,240,0.7)] transition-colors hover:text-[#90cdf4] lg:hidden"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          aria-expanded={menuOpen}
          aria-controls="portfolio-mobile-nav"
        >
          {menuOpen ? (
            <X className="size-5" aria-hidden="true" />
          ) : (
            <Menu className="size-5" aria-hidden="true" />
          )}
        </button>
      </nav>

      {menuOpen && (
        <div
          id="portfolio-mobile-nav"
          className="border-b border-[rgba(99,179,237,0.15)] bg-[rgba(10,16,32,0.97)] px-6 pb-4 lg:hidden"
        >
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setMenuOpen(false)}
              className="block py-2 text-[13px] font-semibold uppercase tracking-widest text-[rgba(180,205,240,0.6)] hover:text-[#90cdf4]"
            >
              {l.label}
            </a>
          ))}
          <div className="mt-3 flex gap-2">
            <Link
              href="/"
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#63b3ed] px-4 py-2 text-[13px] font-bold text-[#0a1020]"
            >
              <Zap className="size-3.5" aria-hidden="true" />
              Launch app
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

/* ── Page ── */

export default function PortfolioContent() {
  return (
    <div className="min-h-screen overflow-x-hidden bg-[#0a1020] font-sans text-[rgba(180,205,240,0.75)]">
      <PortfolioNavbar />

      <main id="main-content">
        {/* ── HERO ── */}
        <section
          id="hero"
          className="relative flex min-h-[88vh] items-center justify-center overflow-hidden"
        >
          <CircuitCanvas />

          <div className="relative z-10 max-w-3xl px-7 pb-20 pt-28 text-center">
            <div className="mb-7 inline-flex animate-fade-up items-center gap-2 rounded-full border border-[rgba(99,179,237,0.4)] bg-[rgba(99,179,237,0.1)] px-[18px] py-[6px] text-[12px] font-semibold tracking-wide text-[#90cdf4] [animation-delay:50ms]">
              <GraduationCap className="size-3.5" aria-hidden="true" />
              Final-Year Project · Ben-Gurion University · 2026
            </div>

            <h1 className="mb-5 animate-fade-up text-[clamp(40px,8vw,72px)] font-black leading-[1.02] tracking-[-2px] text-[#f0f4ff] [animation-delay:150ms]">
              Escape<em className="not-italic text-[#63b3ed]">Circuit</em>
            </h1>

            <p className="mx-auto mb-9 max-w-[440px] animate-fade-up text-[17px] leading-[1.65] text-[rgba(180,205,240,0.6)] [animation-delay:250ms]">
              An interactive logic-circuit puzzle platform. Wire gates, crack
              riddles, and learn digital logic by building it.
            </p>

            <div className="flex animate-fade-up flex-wrap justify-center gap-3 [animation-delay:400ms]">
              <Link
                href="/"
                className="flex items-center gap-2 rounded-[11px] bg-[#63b3ed] px-8 py-3.5 text-[14px] font-extrabold text-[#0a1020] transition-all hover:-translate-y-0.5 hover:bg-[#90cdf4] active:scale-[0.97]"
              >
                <Zap className="size-4" aria-hidden="true" />
                Launch the app
              </Link>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded-[11px] border border-[rgba(200,215,255,0.22)] px-7 py-3.5 text-[14px] font-medium text-[#e8eeff] transition-all hover:border-[rgba(99,179,237,0.4)] hover:bg-[rgba(255,255,255,0.05)]"
              >
                <Code className="size-4" aria-hidden="true" />
                View source on GitHub
                <ExternalLink
                  className="size-3 opacity-60"
                  aria-hidden="true"
                />
                <span className="sr-only">(opens in a new tab)</span>
              </a>
            </div>

            <a
              href="#about"
              className="mt-14 inline-block animate-fade-up text-[rgba(150,175,220,0.4)] transition-colors [animation-delay:600ms] hover:text-[#90cdf4]"
              aria-label="Scroll to the About section"
            >
              <ChevronDown
                className="size-6 animate-bounce"
                aria-hidden="true"
              />
            </a>
          </div>
        </section>

        {/* ── ABOUT ── */}
        <section
          id="about"
          className="scroll-mt-16 border-t border-[rgba(99,179,237,0.12)] bg-[#0d1528] px-6 py-[72px]"
        >
          <div className="mx-auto max-w-5xl">
            <SectionLabel>About the project</SectionLabel>
            <SectionHeading>What is EscapeCircuit?</SectionHeading>
            <p className="mx-auto mb-12 max-w-2xl text-center text-[15px] leading-[1.75]">
              Digital-logic fundamentals are usually taught on paper, with truth
              tables, Karnaugh maps, and static diagrams. EscapeCircuit turns
              them into a game. Students wire simulated logic gates to solve
              riddles like binary adders, palindrome detectors, and synchronous
              counters, and get instant feedback from a live circuit simulation.
              Players earn XP, climb the leaderboard, discuss strategies, and
              publish puzzles of their own.
            </p>

            {/* Stats */}
            <div className="mb-12 grid grid-cols-2 gap-4 md:grid-cols-4">
              {STATS.map((s) => (
                <div
                  key={s.label}
                  className="rounded-[14px] border border-[rgba(99,179,237,0.14)] bg-[#111b30] px-4 py-6 text-center"
                >
                  <p className="mb-1 text-[28px] font-black tracking-tight text-[#63b3ed]">
                    {s.value}
                  </p>
                  <p className="text-[12px] font-semibold uppercase tracking-wider text-[rgba(150,175,220,0.55)]">
                    {s.label}
                  </p>
                </div>
              ))}
            </div>

            {/* Tech stack */}
            <p className="mb-4 text-center text-[11px] font-bold uppercase tracking-[0.18em] text-[rgba(150,175,220,0.5)]">
              Built with
            </p>
            <div className="mx-auto flex max-w-3xl flex-wrap justify-center gap-2">
              {TECH_STACK.map((t) => (
                <span
                  key={t}
                  className="rounded-full border border-[rgba(99,179,237,0.2)] bg-[rgba(99,179,237,0.07)] px-3.5 py-1.5 text-[12px] font-semibold text-[#a8c6ec]"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* ── DEMO VIDEO ── */}
        <section id="demo" className="scroll-mt-16 bg-[#0a1020] px-6 py-[72px]">
          <div className="mx-auto max-w-4xl">
            <SectionLabel>Demo</SectionLabel>
            <SectionHeading>See it in action</SectionHeading>
            <p className="mx-auto mb-10 max-w-md text-center text-[14px] leading-relaxed">
              A short walkthrough of EscapeCircuit, from placing your first gate
              to solving full sequential circuits.
            </p>

            <div className="overflow-hidden rounded-[18px] border border-[rgba(99,179,237,0.18)] bg-[#0d1528] shadow-2xl shadow-black/40">
              <div className="flex items-center gap-2 border-b border-[rgba(99,179,237,0.12)] bg-[#111b30] px-5 py-3">
                <span
                  className="size-3 rounded-full bg-[#fc8181]/80"
                  aria-hidden="true"
                />
                <span
                  className="size-3 rounded-full bg-[#f6ad55]/80"
                  aria-hidden="true"
                />
                <span
                  className="size-3 rounded-full bg-[#68d391]/80"
                  aria-hidden="true"
                />
                <span className="ml-3 text-[11px] font-semibold tracking-wider text-[rgba(150,175,220,0.5)]">
                  escapecircuit/demo.mp4
                </span>
              </div>
              {/* eslint-disable-next-line jsx-a11y/media-has-caption -- no caption track exists for the demo video */}
              <video
                className="aspect-video w-full bg-black"
                src="/portfolio/escapecircuit-promo.mp4"
                poster="/portfolio/promo-poster.png"
                controls
                preload="none"
                aria-label="EscapeCircuit demo video"
              >
                Your browser does not support the video tag.
              </video>
            </div>
          </div>
        </section>

        {/* ── MANUAL ── */}
        <section
          id="manual"
          className="scroll-mt-16 border-t border-[rgba(99,179,237,0.12)] bg-[#0d1528] px-6 py-[72px]"
        >
          <div className="mx-auto max-w-5xl">
            <SectionLabel>User manual</SectionLabel>
            <SectionHeading>How to use EscapeCircuit</SectionHeading>
            <p className="mx-auto mb-12 max-w-md text-center text-[14px] leading-relaxed">
              Four steps from signing up to publishing your own riddles. The
              full illustrated manual is in the user guide below.
            </p>

            <div className="grid gap-5 md:grid-cols-2">
              {MANUAL_STEPS.map((s) => (
                <div
                  key={s.step}
                  className="relative overflow-hidden rounded-[16px] border border-[rgba(99,179,237,0.14)] bg-[#111b30] p-7 transition-all hover:-translate-y-1 hover:border-[rgba(99,179,237,0.35)]"
                >
                  <span
                    className="absolute right-5 top-3 text-[56px] font-black leading-none text-[rgba(99,179,237,0.1)]"
                    aria-hidden="true"
                  >
                    {s.step}
                  </span>
                  <div className="mb-4 flex items-center gap-3">
                    <div className="flex size-12 items-center justify-center rounded-[12px] border border-[rgba(99,179,237,0.25)] bg-[rgba(99,179,237,0.08)] text-[#63b3ed]">
                      {s.icon}
                    </div>
                    <span className="rounded-full border border-[rgba(99,179,237,0.2)] bg-[rgba(99,179,237,0.07)] px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-[#90cdf4]">
                      {s.label}
                    </span>
                  </div>
                  <h3 className="mb-2 text-[16px] font-extrabold text-[#f0f4ff]">
                    {s.title}
                  </h3>
                  <p className="text-[13.5px] leading-[1.7]">{s.body}</p>
                </div>
              ))}
            </div>

            <div className="mt-14 text-center">
              <a
                href="/portfolio/EscapeCircuit_User_Guide.pdf"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-[11px] border border-[rgba(99,179,237,0.35)] bg-[rgba(99,179,237,0.08)] px-7 py-3 text-[13px] font-bold text-[#90cdf4] transition-all hover:bg-[rgba(99,179,237,0.16)]"
              >
                <BookOpen className="size-4" aria-hidden="true" />
                Read the full user guide (PDF)
              </a>
            </div>
          </div>
        </section>

        {/* ── DOCUMENTATION ── */}
        <section id="docs" className="scroll-mt-16 bg-[#0a1020] px-6 py-[72px]">
          <div className="mx-auto max-w-5xl">
            <SectionLabel>Documentation</SectionLabel>
            <SectionHeading>Deliverables &amp; reports</SectionHeading>
            <p className="mx-auto mb-12 max-w-md text-center text-[14px] leading-relaxed">
              The documents we submitted during the year, from the architecture
              design to the final release.
            </p>

            <div className="grid gap-5 sm:grid-cols-2">
              {DOCS.map((doc) => (
                <div
                  key={doc.title}
                  className="flex flex-col rounded-[16px] border border-[rgba(99,179,237,0.14)] bg-[#111b30] p-6 transition-all hover:-translate-y-1 hover:border-[rgba(99,179,237,0.35)]"
                >
                  <div className="mb-4 flex items-center justify-between">
                    <div className="flex size-10 items-center justify-center rounded-[10px] border border-[rgba(99,179,237,0.25)] bg-[rgba(99,179,237,0.1)] text-[#63b3ed]">
                      {doc.icon}
                    </div>
                    <span className="rounded-full border border-[rgba(104,211,145,0.3)] bg-[rgba(104,211,145,0.1)] px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest text-[#68d391]">
                      {doc.tag}
                    </span>
                  </div>
                  <h3 className="mb-1.5 text-[15px] font-extrabold leading-snug text-[#f0f4ff]">
                    {doc.title}
                  </h3>
                  <p className="mb-5 flex-1 text-[13px] leading-[1.6] text-[rgba(150,175,220,0.6)]">
                    {doc.description}
                  </p>
                  <a
                    href={doc.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 self-start rounded-lg border border-[rgba(200,215,255,0.2)] px-4 py-2 text-[12px] font-bold uppercase tracking-wider text-[#c8d7f0] transition-all hover:border-[rgba(99,179,237,0.45)] hover:text-[#90cdf4]"
                    aria-label={`Open ${doc.title} PDF in a new tab`}
                  >
                    <Download className="size-3.5" aria-hidden="true" />
                    Open PDF
                    <span className="text-[10px] font-semibold normal-case tracking-normal text-[rgba(150,175,220,0.45)]">
                      {doc.size}
                    </span>
                  </a>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── TEAM ── */}
        <section
          id="team"
          className="scroll-mt-16 border-t border-[rgba(99,179,237,0.12)] bg-[#0d1528] px-6 py-[72px]"
        >
          <div className="mx-auto max-w-5xl">
            <SectionLabel>The team</SectionLabel>
            <SectionHeading>Built by four students</SectionHeading>
            <p className="mx-auto mb-12 max-w-xl text-center text-[14px] leading-relaxed">
              EscapeCircuit is the final-year capstone project of four Software
              Engineering students at Ben-Gurion University of the Negev, class
              of 2026.
            </p>

            <div className="mb-12 grid grid-cols-2 gap-4 md:grid-cols-4">
              {TEAM.map((member) => (
                <div
                  key={member.name}
                  className="rounded-[16px] border border-[rgba(99,179,237,0.14)] bg-[#111b30] p-6 text-center transition-all hover:-translate-y-1 hover:border-[rgba(99,179,237,0.35)]"
                >
                  <MonogramAvatar name={member.name} />
                  <p className="mb-1 text-[14px] font-extrabold text-[#f0f4ff]">
                    {member.name}
                  </p>
                  <p className="text-[12px] leading-relaxed text-[rgba(150,175,220,0.55)]">
                    {member.role}
                  </p>
                </div>
              ))}
            </div>

            {/* Leadership */}
            <div className="rounded-[18px] border border-[rgba(99,179,237,0.14)] bg-[rgba(17,27,48,0.6)] p-8">
              <p className="mb-6 text-center text-[11px] font-bold uppercase tracking-[0.18em] text-[rgba(150,175,220,0.5)]">
                Academic supervision
              </p>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-[14px] border border-[rgba(99,179,237,0.2)] bg-[rgba(99,179,237,0.06)] p-5 text-center">
                  <BookOpen
                    className="mx-auto mb-3 size-5 text-[#63b3ed]"
                    aria-hidden="true"
                  />
                  <p className="mb-0.5 text-[11px] font-bold uppercase tracking-widest text-[#63b3ed]">
                    Academic advisor
                  </p>
                  <p className="text-[14px] font-extrabold text-[#f0f4ff]">
                    Niv Gilboa
                  </p>
                </div>
                {['Gera Weiss', 'Oded Margalit'].map((name) => (
                  <div
                    key={name}
                    className="rounded-[14px] border border-[rgba(200,215,255,0.12)] bg-[rgba(255,255,255,0.02)] p-5 text-center"
                  >
                    <Users
                      className="mx-auto mb-3 size-5 text-[rgba(180,205,240,0.6)]"
                      aria-hidden="true"
                    />
                    <p className="mb-0.5 text-[11px] font-bold uppercase tracking-widest text-[rgba(150,175,220,0.55)]">
                      Client
                    </p>
                    <p className="text-[14px] font-extrabold text-[#f0f4ff]">
                      {name}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ── CTA FOOTER ── */}
        <section className="relative overflow-hidden bg-[#0a1020] px-6 py-16 text-center">
          <CircuitCanvas opacity={0.5} />
          <div className="relative z-10">
            <h2 className="mb-3 text-[clamp(26px,5vw,34px)] font-black leading-tight tracking-tight text-[#f0f4ff]">
              Ready to crack the{' '}
              <em className="not-italic text-[#63b3ed]">circuit?</em>
            </h2>
            <p className="mb-8 text-[14px] leading-relaxed text-[rgba(180,205,240,0.5)]">
              Try the live platform, browse the source code, or read the
              documentation.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Link
                href="/"
                className="inline-flex items-center gap-2 rounded-xl bg-[#63b3ed] px-9 py-[14px] text-[14px] font-black tracking-tight text-[#0a1020] transition-all hover:-translate-y-0.5 hover:bg-[#90cdf4] active:scale-[0.97]"
              >
                <Zap className="size-4" aria-hidden="true" />
                Launch the app
              </Link>
              <a
                href={GITHUB_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-[rgba(200,215,255,0.22)] px-8 py-[14px] text-[14px] font-medium text-[#e8eeff] transition-all hover:border-[rgba(99,179,237,0.4)] hover:bg-[rgba(255,255,255,0.05)]"
              >
                <Code className="size-4" aria-hidden="true" />
                GitHub
              </a>
            </div>
          </div>
        </section>
      </main>

      {/* ── FOOTER ── */}
      <footer className="border-t border-[rgba(99,179,237,0.12)] bg-[#080d1a] px-6 py-10">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-6 text-center md:flex-row md:text-left">
          <div>
            <div className="mb-1 flex items-center justify-center gap-2 md:justify-start">
              <CircuitBoard
                className="size-4 text-[#63b3ed]"
                aria-hidden="true"
              />
              <span className="text-[14px] font-extrabold text-[#f0f4ff]">
                EscapeCircuit
              </span>
            </div>
            <p className="text-[12px] text-[rgba(150,175,220,0.45)]">
              Interactive logic-circuit puzzle platform
            </p>
          </div>

          <div className="text-[12px] leading-relaxed text-[rgba(150,175,220,0.45)]">
            <p className="font-semibold text-[rgba(180,205,240,0.65)]">
              Ben-Gurion University of the Negev
            </p>
            <p>B.Sc. Software Engineering · Final-Year Project · 2025-2026</p>
          </div>

          <div className="flex items-center gap-3">
            <a
              href={GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex size-9 items-center justify-center rounded-lg border border-[rgba(200,215,255,0.15)] text-[rgba(150,175,220,0.55)] transition-all hover:border-[rgba(99,179,237,0.4)] hover:text-[#90cdf4]"
            >
              <Code className="size-4" aria-hidden="true" />
              <span className="sr-only">
                GitHub repository (opens in a new tab)
              </span>
            </a>
            <Link
              href="/"
              className="flex size-9 items-center justify-center rounded-lg border border-[rgba(200,215,255,0.15)] text-[rgba(150,175,220,0.55)] transition-all hover:border-[rgba(99,179,237,0.4)] hover:text-[#90cdf4]"
            >
              <Home className="size-4" aria-hidden="true" />
              <span className="sr-only">
                Back to the EscapeCircuit home page
              </span>
            </Link>
          </div>
        </div>

        <p className="mt-8 text-center text-[11px] text-[rgba(150,175,220,0.35)]">
          © 2026 EscapeCircuit Team · Ben-Gurion University of the Negev
        </p>
      </footer>
    </div>
  );
}
