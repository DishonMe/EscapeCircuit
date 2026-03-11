'use client';

import { useUser } from '@/lib/auth';
import Link from 'next/link';
import { paths } from '@/config/paths';
import { EditBio } from '@/features/users/components/edit-bio';

type EntryProps = {
  label: string;
  value: string;
};
const Entry = ({ label, value }: EntryProps) => (
  <div className="py-4 sm:grid sm:grid-cols-3 sm:gap-4 sm:px-6 sm:py-5">
    <dt className="text-sm font-medium text-slate-500">{label}</dt>
    <dd className="mt-1 text-sm text-slate-700 sm:col-span-2 sm:mt-0">
      {value}
    </dd>
  </div>
);

export const Profile = () => {
  const user = useUser();

  if (!user || !user.data) return null;

  const formatDateOnly = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const displayName = user.data.username ?? 'Operator';
  const initials = displayName.slice(0, 2).toUpperCase();
  const arsenalCount = user.data.arsenal_count ?? 0;
  const medalsTotal = user.data.medals?.total ?? 0;
  const savedPuzzleCount = user.data.saved_puzzles?.length ?? 0;
  const loadoutSlots = Math.min(12, arsenalCount);

  return (
    <div className="space-y-6 rounded-3xl border border-slate-200/70 bg-white/80 p-5 shadow-[0_8px_30px_rgb(0,0,0,0.04)] backdrop-blur-xl sm:p-6">
      <div className="rounded-3xl border border-slate-200/60 bg-slate-50/80 p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="relative floating-avatar flex size-16 items-center justify-center rounded-full border-4 border-white/70 bg-slate-200 text-xl font-semibold text-slate-700 shadow-sm">
                {initials}
              </div>
            </div>
            <div>
              <h1 className="text-3xl font-semibold tracking-tight text-slate-800">
                {displayName}
              </h1>
              <p className="text-sm font-medium text-slate-500">
                Player profile
              </p>
            </div>
          </div>
          <EditBio />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200/70 bg-slate-100/60 p-4">
          <div className="text-sm font-medium text-slate-500">Level</div>
          <div className="text-3xl font-semibold text-slate-700">{user.data.level ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-slate-200/70 bg-slate-100/60 p-4">
          <div className="text-sm font-medium text-slate-500">XP</div>
          <div className="text-3xl font-semibold text-slate-700">{user.data.xp ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-slate-200/70 bg-slate-100/60 p-4">
          <div className="text-sm font-medium text-slate-500">Medals</div>
          <div className="text-3xl font-semibold text-slate-700">{medalsTotal}</div>
        </div>
        <div className="rounded-2xl border border-slate-200/70 bg-slate-100/60 p-4">
          <div className="text-sm font-medium text-slate-500">Saved Puzzles</div>
          <div className="text-3xl font-semibold text-slate-700">{savedPuzzleCount}</div>
        </div>
      </div>

      {/* User Information */}
      <div className="overflow-hidden rounded-3xl border border-slate-200/70 bg-white/70 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
        <div className="px-4 py-5 sm:px-6">
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-lg font-semibold leading-6 text-slate-800">
                User Information
              </h3>
              <p className="mt-1 max-w-2xl text-sm text-slate-500">
                Personal details of the user.
              </p>
            </div>
          </div>
        </div>
        <div className="border-t border-slate-200/70 px-4 py-5 sm:p-0">
          <dl className="sm:divide-y sm:divide-slate-200/70">
            <Entry label="Username" value={user.data.username ?? ''} />
            <Entry label="Email Address" value={user.data.email ?? ''} />
            <Entry label="Role" value={user.data.role ?? ''} />
            <Entry label="User Since" value={formatDateOnly(user.data.created_at ?? '')} />
            {user.data.is_experienced && <Entry label="Status" value="Experienced" />}
            {user.data.is_discussion_banned && (
              <Entry label="Discussion Status" value="Banned" />
            )}
            {user.data.bio && <Entry label="Bio" value={user.data.bio} />}
          </dl>
        </div>
      </div>

      {/* Medals */}
      {user.data.medals && (
        <div className="overflow-hidden rounded-3xl border border-slate-200/70 bg-white/70 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg font-semibold leading-6 text-slate-800">
              Medals
            </h3>
          </div>
          <div className="border-t border-slate-200/70 px-4 py-5 sm:p-0">
            <dl className="sm:divide-y sm:divide-slate-200/70">
              <Entry label="Gold" value={String(user.data.medals.gold ?? 0)} />
              <Entry label="Silver" value={String(user.data.medals.silver ?? 0)} />
              <Entry label="Bronze" value={String(user.data.medals.bronze ?? 0)} />
              <Entry label="Total" value={String(user.data.medals.total ?? 0)} />
            </dl>
          </div>
        </div>
      )}

      {/* Arsenal */}
      {user.data.arsenal_count !== undefined && (
        <div className="overflow-hidden rounded-3xl border border-slate-200/70 bg-white/70 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg font-semibold leading-6 text-slate-800">
              Arsenal
            </h3>
          </div>
          <div className="border-t border-slate-200/70 px-4 py-5">
            <div className="mb-3 text-sm font-medium text-slate-500">
              Saved Circuits: {user.data.arsenal_count}
            </div>
            {arsenalCount > 0 ? (
              <div className="grid grid-cols-4 gap-2 sm:grid-cols-6">
                {Array.from({ length: loadoutSlots }).map((_, index) => (
                  <div
                    key={index}
                    className="aspect-square rounded-xl border border-slate-200/60 bg-white/60 p-2 transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-105 hover:shadow-lg"
                  >
                    <div className="flex h-full items-end justify-between text-[10px] text-slate-500">
                      <span>#{index + 1}</span>
                      <span className="size-1.5 rounded-full bg-slate-300" />
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* Saved Puzzles */}
      {user.data.saved_puzzles !== undefined && (
        <div className="overflow-hidden rounded-3xl border border-slate-200/70 bg-white/70 shadow-[0_8px_30px_rgb(0,0,0,0.04)]">
          <div className="px-4 py-5 sm:px-6">
            <h3 className="text-lg font-semibold leading-6 text-slate-800">
              Saved Puzzles
            </h3>
            <p className="mt-1 max-w-2xl text-sm text-slate-500">
              Puzzles you have saved.
            </p>
          </div>
          <div className="border-t border-slate-200/70 px-4 py-5 sm:p-0">
            {user.data.saved_puzzles.length > 0 ? (
              <ul className="grid gap-2 px-4 sm:grid-cols-2">
                {user.data.saved_puzzles.map((puzzle: any) => (
                  <li
                    key={puzzle.id}
                    className="rounded-xl border border-slate-200/60 bg-white/60 p-3 transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-105 hover:shadow-lg"
                  >
                    <Link
                      href={`${paths.app.puzzles.getHref()}/${puzzle.id}`}
                      className="text-sm font-medium text-slate-700 hover:text-slate-900 underline"
                    >
                      {puzzle.name}
                    </Link>
                    <span className="ml-2 text-xs text-slate-500">
                      ({puzzle.status})
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="px-4 py-5 text-sm text-slate-500">
                No saved puzzles
              </p>
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        .floating-avatar {
          animation: profile-float 4s ease-in-out infinite;
        }

        @keyframes profile-float {
          0%,
          100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-4px);
          }
        }
      `}</style>
    </div>
  );
};
