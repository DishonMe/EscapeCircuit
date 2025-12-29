import { useState } from 'react';
import { PuzzleBrowserHeader } from './PuzzleBrowserHeader';
import { SearchFilters } from './SearchFilters';
import { PuzzleGrid } from './PuzzleGrid';
import { Pagination } from './Pagination';

export interface Puzzle {
  id: string;
  title: string;
  creator: string;
  difficulty: 'Easy' | 'Medium' | 'Hard';
  experiencedOnly: boolean;
  timeLimit: number; // in seconds
  medal: 'gold' | 'silver' | 'bronze' | null; // null if not solved
  solved: boolean;
  rating: number;
  popular: boolean;
  solvedCount: number; // number of people who solved it
}

export interface PuzzleBrowserProps {
  onProfileClick?: () => void;
  onPuzzleSelect?: (puzzleId: string) => void;
  onAdminClick?: () => void;
}

export function PuzzleBrowser({ onProfileClick, onPuzzleSelect, onAdminClick }: PuzzleBrowserProps = {}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState<string>('All');
  const [timeLimitFilter, setTimeLimitFilter] = useState<string>('All');
  const [solvedFilter, setSolvedFilter] = useState<string>('All');
  const [ratingFilter, setRatingFilter] = useState<string>('All');
  const [popularOnly, setPopularOnly] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  // Mock puzzle data
  const allPuzzles: Puzzle[] = [
    {
      id: '1',
      title: 'Binary Adder',
      creator: 'LogicMaster',
      difficulty: 'Medium',
      experiencedOnly: false,
      timeLimit: 300,
      medal: 'gold',
      solved: true,
      rating: 4.8,
      popular: true,
      solvedCount: 28,
    },
    {
      id: '2',
      title: 'XOR Challenge',
      creator: 'CircuitGuru',
      difficulty: 'Easy',
      experiencedOnly: false,
      timeLimit: 120,
      medal: null,
      solved: false,
      rating: 4.5,
      popular: true,
      solvedCount: 15,
    },
    {
      id: '3',
      title: 'Advanced Multiplexer',
      creator: 'TechWizard',
      difficulty: 'Hard',
      experiencedOnly: true,
      timeLimit: 600,
      medal: null,
      solved: false,
      rating: 4.9,
      popular: true,
      solvedCount: 3,
    },
    {
      id: '4',
      title: 'Simple NOT Gates',
      creator: 'BeginnerFriend',
      difficulty: 'Easy',
      experiencedOnly: false,
      timeLimit: 60,
      medal: 'silver',
      solved: true,
      rating: 4.2,
      popular: false,
      solvedCount: 22,
    },
    {
      id: '5',
      title: 'Flip-Flop Master',
      creator: 'SequentialPro',
      difficulty: 'Hard',
      experiencedOnly: true,
      timeLimit: 900,
      medal: null,
      solved: false,
      rating: 4.7,
      popular: true,
      solvedCount: 7,
    },
    {
      id: '6',
      title: 'OR Gate Basics',
      creator: 'LogicStarter',
      difficulty: 'Easy',
      experiencedOnly: false,
      timeLimit: 90,
      medal: 'bronze',
      solved: true,
      rating: 4.0,
      popular: false,
      solvedCount: 18,
    },
  ];

  // Filter puzzles
  const filteredPuzzles = allPuzzles.filter((puzzle) => {
    // Search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (
        !puzzle.title.toLowerCase().includes(query) &&
        !puzzle.creator.toLowerCase().includes(query)
      ) {
        return false;
      }
    }

    // Difficulty filter
    if (difficultyFilter !== 'All' && puzzle.difficulty !== difficultyFilter) {
      return false;
    }

    // Time limit filter
    if (timeLimitFilter !== 'All') {
      if (timeLimitFilter === 'Under 60s' && puzzle.timeLimit > 60) {
        return false;
      }
      if (timeLimitFilter === 'Under 2m' && puzzle.timeLimit > 120) {
        return false;
      }
      if (timeLimitFilter === 'Under 5m' && puzzle.timeLimit > 300) {
        return false;
      }
    }

    // Solved filter
    if (solvedFilter !== 'All') {
      if (solvedFilter === 'Solved' && !puzzle.solved) return false;
      if (solvedFilter === 'Unsolved' && puzzle.solved) return false;
    }

    // Rating filter
    if (ratingFilter !== 'All') {
      const minRating = parseFloat(ratingFilter.replace('+', ''));
      if (puzzle.rating < minRating) return false;
    }

    // Popular filter
    if (popularOnly && !puzzle.popular) {
      return false;
    }

    return true;
  });

  // Pagination
  const puzzlesPerPage = 6;
  const totalPages = Math.ceil(filteredPuzzles.length / puzzlesPerPage);
  const startIndex = (currentPage - 1) * puzzlesPerPage;
  const endIndex = startIndex + puzzlesPerPage;
  const currentPuzzles = filteredPuzzles.slice(startIndex, endIndex);

  return (
    <div className="min-h-screen bg-gray-100">
      <PuzzleBrowserHeader onProfileClick={onProfileClick} onAdminClick={onAdminClick} isAdminMode={true} />

      <div className="max-w-7xl mx-auto px-6 py-6">
        <SearchFilters
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          difficultyFilter={difficultyFilter}
          setDifficultyFilter={setDifficultyFilter}
          timeLimitFilter={timeLimitFilter}
          setTimeLimitFilter={setTimeLimitFilter}
          solvedFilter={solvedFilter}
          setSolvedFilter={setSolvedFilter}
          ratingFilter={ratingFilter}
          setRatingFilter={setRatingFilter}
          popularOnly={popularOnly}
          setPopularOnly={setPopularOnly}
        />

        <PuzzleGrid puzzles={currentPuzzles} onPuzzleSelect={onPuzzleSelect} />

        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={setCurrentPage}
        />
      </div>
    </div>
  );
}