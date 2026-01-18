import { HttpResponse, http } from 'msw';

import { env } from '@/config/env';

import { db } from '../db';
import { requireAuth, sanitizeUser, networkDelay } from '../utils';

export const puzzlesHandlers = [
  http.get(`${env.API_URL}/puzzles`, async ({ cookies, request }) => {
    await networkDelay();

    try {
      const { error } = requireAuth(cookies, { headers: request.headers });
      if (error) {
        return HttpResponse.json({ message: error }, { status: 401 });
      }

      const url = new URL(request.url);
      const page = Number(url.searchParams.get('page') || 1);

      const total = db.puzzle.count();
      const totalPages = Math.ceil(total / 10);

      const result = db.puzzle
        .findMany({
          take: 10,
          skip: (page - 1) * 10,
        })
        .map((puzzle) => ({
          ...puzzle,
          creator: sanitizeUser(
            db.user.findFirst({
              where: {
                id: {
                  equals: puzzle.creatorId,
                },
              },
            }) || {},
          ),
        }));

      return HttpResponse.json({
        data: result,
        meta: {
          page,
          total,
          totalPages,
        },
      });
    } catch (error) {
      return HttpResponse.json(
        { message: 'Internal server error' },
        { status: 500 },
      );
    }
  }),

  http.get(`${env.API_URL}/puzzles/:id`, async ({ cookies, params, request }) => {
    await networkDelay();

    try {
      const { error } = requireAuth(cookies, { headers: request.headers });
      if (error) {
        return HttpResponse.json({ message: error }, { status: 401 });
      }

      const id = String(params.id);

      const puzzle = db.puzzle.findFirst({
        where: {
          id: {
            equals: id,
          },
        },
      });

      if (!puzzle) {
        return HttpResponse.json({ message: 'Not found' }, { status: 404 });
      }

      const creator = sanitizeUser(
        db.user.findFirst({
          where: {
            id: {
              equals: puzzle.creatorId,
            },
          },
        }) || {},
      );

      const inputs = (() => {
        try {
          return JSON.parse(puzzle.inputs || '[]');
        } catch {
          return [];
        }
      })();

      const outputs = (() => {
        try {
          return JSON.parse(puzzle.outputs || '[]');
        } catch {
          return [];
        }
      })();

      const filteredBasicComponents = (() => {
        try {
          return JSON.parse(puzzle.filteredBasicComponents || '[]');
        } catch {
          return [];
        }
      })();

      const specialComponents = (() => {
        try {
          return JSON.parse(puzzle.specialComponents || '[]');
        } catch {
          return [];
        }
      })();

      return HttpResponse.json({
        data: {
          ...puzzle,
          creator,
          inputs,
          outputs,
          filteredBasicComponents,
          specialComponents,
        },
      });
    } catch (error) {
      return HttpResponse.json(
        { message: 'Internal server error' },
        { status: 500 },
      );
    }
  }),

  http.post(
    `${env.API_URL}/puzzles/:id/validate`,
    async ({ cookies, params, request }) => {
      await networkDelay();

      try {
        const { error } = requireAuth(cookies, { headers: request.headers });
        if (error) {
          return HttpResponse.json({ message: error }, { status: 401 });
        }

        const id = String(params.id);
        const puzzle = db.puzzle.findFirst({
          where: {
            id: {
              equals: id,
            },
          },
        });

        if (!puzzle) {
          return HttpResponse.json({ message: 'Not found' }, { status: 404 });
        }

        const body = (await request.json()) as { solution?: any };
        const solution = body?.solution;
        if (!solution) {
          return HttpResponse.json(
            { message: 'Invalid solution' },
            { status: 400 },
          );
        }

        const inputs = (() => {
          try {
            return JSON.parse(puzzle.inputs || '[]') as string[];
          } catch {
            return [] as string[];
          }
        })();

        const outputs = (() => {
          try {
            return JSON.parse(puzzle.outputs || '[]') as string[];
          } catch {
            return [] as string[];
          }
        })();

        const usedInputs = new Set<string>();
        const usedOutputs = new Set<string>();
        for (const w of solution.wires || []) {
          const from = w?.from?.componentId;
          const to = w?.to?.componentId;
          if (typeof from === 'string' && from.startsWith('IO:IN:')) {
            usedInputs.add(from.replace('IO:IN:', ''));
          }
          if (typeof to === 'string' && to.startsWith('IO:IN:')) {
            usedInputs.add(to.replace('IO:IN:', ''));
          }
          if (typeof from === 'string' && from.startsWith('IO:OUT:')) {
            usedOutputs.add(from.replace('IO:OUT:', ''));
          }
          if (typeof to === 'string' && to.startsWith('IO:OUT:')) {
            usedOutputs.add(to.replace('IO:OUT:', ''));
          }
        }

        const missingInputs = inputs.filter((i) => !usedInputs.has(i));
        const missingOutputs = outputs.filter((o) => !usedOutputs.has(o));

        if (missingInputs.length || missingOutputs.length) {
          return HttpResponse.json({
            solved: false,
            message: `Circuit missing IO usage. Missing inputs: ${missingInputs.join(', ') || 'none'}; missing outputs: ${missingOutputs.join(', ') || 'none'}.`,
          });
        }

        const totalCost = Number(solution.totalCost ?? 0);
        if (totalCost > Number(puzzle.budgetLimit ?? 0)) {
          return HttpResponse.json({
            solved: false,
            message: 'Budget exceeded.',
          });
        }

        return HttpResponse.json({
          solved: true,
          message: 'All essential conditions met. (Mock validation passed.)',
        });
      } catch (error) {
        return HttpResponse.json(
          { message: 'Internal server error' },
          { status: 500 },
        );
      }
    },
  ),
];
