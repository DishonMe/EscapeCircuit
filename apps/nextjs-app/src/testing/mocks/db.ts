import { factory, primaryKey } from '@mswjs/data';
import { nanoid } from 'nanoid';

import { hash } from './hash';

const models = {
  user: {
    id: primaryKey(nanoid),
    firstName: String,
    lastName: String,
    email: String,
    password: String,
    teamId: String,
    role: String,
    bio: String,
    createdAt: Date.now,
  },
  team: {
    id: primaryKey(nanoid),
    name: String,
    description: String,
    createdAt: Date.now,
  },
  discussion: {
    id: primaryKey(nanoid),
    title: String,
    body: String,
    authorId: String,
    teamId: String,
    createdAt: Date.now,
    public: Boolean,
  },
  comment: {
    id: primaryKey(nanoid),
    body: String,
    authorId: String,
    discussionId: String,
    createdAt: Date.now,
  },
  room: {
    id: primaryKey(nanoid),
    title: String,
    description: String,
    difficulty: String,
    timeLimit: Number,
    maxPlayers: Number,
    isPublic: Boolean,
    gameMasterId: String,
    createdAt: Date.now,
  },
  puzzle: {
    id: primaryKey(nanoid),
    title: String,
    description: String,
    difficulty: String,
    timeLimit: Number,
    budgetLimit: Number,
    tightBudgetLimit: Number,
    inputs: String, // JSON string
    outputs: String, // JSON string
    creatorComment: String,
    filteredBasicComponents: String, // JSON string
    allowArsenal: Boolean,
    specialComponents: String, // JSON string
    creatorId: String,
    rating: Number,
    solvedCount: Number,
    isPublic: Boolean,
    createdAt: Date.now,
  },
};

export const db = factory(models);

export type Model = keyof typeof models;

const dbFilePath = 'mocked-db.json';

export const loadDb = async () => {
  // If we are running in a Node.js environment
  if (typeof window === 'undefined') {
    const { readFile, writeFile } = await import('fs/promises');
    try {
      const data = await readFile(dbFilePath, 'utf8');
      return JSON.parse(data);
    } catch (error: any) {
      if (error?.code === 'ENOENT') {
        const emptyDB = {};
        await writeFile(dbFilePath, JSON.stringify(emptyDB, null, 2));
        return emptyDB;
      } else {
        console.error('Error loading mocked DB:', error);
        return null;
      }
    }
  }
  // If we are running in a browser environment
  return Object.assign(
    JSON.parse(window.localStorage.getItem('msw-db') || '{}'),
  );
};

export const storeDb = async (data: string) => {
  // If we are running in a Node.js environment
  if (typeof window === 'undefined') {
    const { writeFile } = await import('fs/promises');
    await writeFile(dbFilePath, data);
  } else {
    // If we are running in a browser environment
    window.localStorage.setItem('msw-db', data);
  }
};

export const persistDb = async (model: Model) => {
  if (process.env.NODE_ENV === 'test') return;
  const data = await loadDb();
  data[model] = db[model].getAll();
  await storeDb(JSON.stringify(data));
};

export const initializeDb = async () => {
  const database = await loadDb();
  Object.entries(db).forEach(([key, model]) => {
    const dataEntres = database[key];
    if (dataEntres) {
      dataEntres?.forEach((entry: Record<string, any>) => {
        try {
          model.create(entry);
        } catch (error) {
          // Ignore duplicate key errors
        }
      });
    }
  });

  // Seed some initial data if database is empty
  if (db.puzzle.count() === 0) {
    // Create a sample team and users (passwords are hashed)
    const defaultTeam = db.team.create({
      name: 'Default Team',
      description: 'Default seeded team',
    });

    const creator = db.user.create({
      firstName: 'Circuit',
      lastName: 'Master',
      email: 'circuitmaster@example.com',
      password: hash('password'),
      teamId: defaultTeam.id,
      role: 'PLAYER',
      bio: 'Professional circuit designer',
    });

    // Create sample puzzles
    db.puzzle.create({
      title: 'Binary Adder',
      description: 'Create a circuit that adds two binary numbers',
      difficulty: 'MEDIUM',
      timeLimit: 300,
      budgetLimit: 100,
      tightBudgetLimit: 140,
      inputs: JSON.stringify(['IN0', 'IN1', 'IN2', 'IN3']),
      outputs: JSON.stringify(['OUT0', 'OUT1']),
      creatorComment: 'Remember: use all inputs and drive both outputs.',
      filteredBasicComponents: JSON.stringify(['XOR']),
      allowArsenal: true,
      specialComponents: JSON.stringify([
        { id: 'FULL_ADDER_BLOCK', type: 'FULL_ADDER_BLOCK', cost: 30, pins: 5 },
      ]),
      creatorId: creator.id,
      rating: 4.8,
      solvedCount: 28,
      isPublic: true,
    });

    db.puzzle.create({
      title: 'Logic Gate OR',
      description: 'Build an OR gate using basic components',
      difficulty: 'EASY',
      timeLimit: 180,
      budgetLimit: 50,
      tightBudgetLimit: 65,
      inputs: JSON.stringify(['A', 'B']),
      outputs: JSON.stringify(['OUT']),
      creatorComment:
        'Try a minimal-cost design to earn the tight budget medal.',
      filteredBasicComponents: JSON.stringify([]),
      allowArsenal: false,
      specialComponents: JSON.stringify([]),
      creatorId: creator.id,
      rating: 4.2,
      solvedCount: 156,
      isPublic: true,
    });

    db.puzzle.create({
      title: 'Full Adder Circuit',
      description: 'Design a full adder with carry-in and carry-out',
      difficulty: 'HARD',
      timeLimit: 600,
      budgetLimit: 200,
      tightBudgetLimit: 260,
      inputs: JSON.stringify(['A', 'B', 'CIN']),
      outputs: JSON.stringify(['SUM', 'COUT']),
      creatorComment: 'You will likely need multiple gates. Budget is strict.',
      filteredBasicComponents: JSON.stringify(['NAND']),
      allowArsenal: true,
      specialComponents: JSON.stringify([]),
      creatorId: creator.id,
      rating: 4.9,
      solvedCount: 12,
      isPublic: true,
    });

    // Persist seeded data
    await storeDb(
      JSON.stringify(
        {
          user: db.user.getAll(),
          team: db.team.getAll(),
          puzzle: db.puzzle.getAll(),
        },
        null,
        2,
      ),
    );
  }
  // Ensure default admin always exists
  const adminEmail = 'admin@mail.com';
  const existingAdmin = db.user.findFirst({
    where: {
      email: {
        equals: adminEmail,
      },
    },
  });

  if (!existingAdmin) {
    const defaultTeam =
      db.team.findFirst({
        where: {
          name: {
            equals: 'Default Team',
          },
        },
      }) ||
      db.team.create({
        name: 'Default Team',
        description: 'Default seeded team',
      });

    db.user.create({
      firstName: 'Admin',
      lastName: 'User',
      email: adminEmail,
      password: hash('admin'),
      teamId: defaultTeam.id,
      role: 'ADMIN',
      bio: 'Default admin account',
    });
  }
};

export const resetDb = () => {
  window.localStorage.clear();
};
