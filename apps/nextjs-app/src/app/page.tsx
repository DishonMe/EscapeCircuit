import { Button } from '@/components/ui/button';
import { Link } from '@/components/ui/link';
import { paths } from '@/config/paths';
import { checkLoggedIn } from '@/utils/auth';

const HomePage = () => {
  const isLoggedIn = checkLoggedIn();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            EscapeCircuit
          </h1>
          <p className="text-xl text-gray-600 mb-8">Circuit Design Puzzles</p>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">
            Design electronic circuits, solve challenging puzzles, and compete
            with players worldwide in our circuit design puzzle platform.
          </p>
        </div>

        {/* Main Actions */}
        <div className="flex justify-center gap-4 mb-16">
          <Link
            href={
              isLoggedIn
                ? paths.app.puzzles.getHref()
                : paths.auth.login.getHref()
            }
          >
            <Button className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-3 text-lg">
              {isLoggedIn ? 'Browse Puzzles' : 'Get Started'}
            </Button>
          </Link>

          {isLoggedIn && (
            <Link href={paths.auth.register.getHref()}>
              <Button
                variant="outline"
                className="border-gray-300 text-gray-700 hover:bg-gray-50 px-8 py-3 text-lg"
              >
                Create Puzzle
              </Button>
            </Link>
          )}
        </div>

        {/* Feature Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div className="bg-white border border-gray-300 rounded-lg p-6">
            <div className="text-2xl mb-4">🔌</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Design Circuits
            </h3>
            <p className="text-gray-600">
              Drag and drop electronic components to build functional circuits
            </p>
          </div>

          <div className="bg-white border border-gray-300 rounded-lg p-6">
            <div className="text-2xl mb-4">⏱️</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Beat the Clock
            </h3>
            <p className="text-gray-600">
              Solve puzzles within time limits and budget constraints
            </p>
          </div>

          <div className="bg-white border border-gray-300 rounded-lg p-6">
            <div className="text-2xl mb-4">🏆</div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Compete & Learn
            </h3>
            <p className="text-gray-600">
              Challenge friends and improve your circuit design skills
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
