import { HttpResponse, http } from 'msw';

import { env } from '@/config/env';

import { db } from '../db';
import { requireAuth, sanitizeUser, networkDelay } from '../utils';

export const puzzlesHandlers = [
  http.get(`${env.API_URL}/puzzles`, async ({ cookies, request }) => {
    await networkDelay();

    try {
      const { error } = requireAuth(cookies);
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
];
