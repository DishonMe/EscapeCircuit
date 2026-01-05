import { Button } from '@/components/ui/button';
import { Link } from '@/components/ui/link';
import { paths } from '@/config/paths';
import { checkLoggedIn } from '@/utils/auth';

const HomePage = () => {
  const isLoggedIn = checkLoggedIn();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-7xl px-4 py-16">
        {/* Header */}
        <div className="mb-16 text-center">
          <h1 className="mb-4 text-4xl font-bold text-gray-900">
            EscapeCircuit
          </h1>
          <p className="mb-8 text-xl text-gray-600">Circuit Design Puzzles</p>
          <p className="mx-auto max-w-2xl text-lg text-gray-500">
            Design electronic circuits, solve challenging puzzles, and compete
            with players worldwide in our circuit design puzzle platform.
          </p>
        </div>

        {/* Main Actions */}
        <div className="mb-16 flex justify-center gap-4">
          <Link
            href={
              isLoggedIn
                ? paths.app.puzzles.getHref()
                : paths.auth.login.getHref()
            }
          >
            <Button className="bg-blue-600 px-8 py-3 text-lg text-white hover:bg-blue-700">
              {isLoggedIn ? 'Browse Puzzles' : 'Get Started'}
            </Button>
          </Link>

          {isLoggedIn && (
            <Link href={paths.auth.register.getHref()}>
              <Button
                variant="outline"
                className="border-gray-300 px-8 py-3 text-lg text-gray-700 hover:bg-gray-50"
              >
                Create Puzzle
              </Button>
            </Link>
          )}
        </div>

        {/* Feature Cards */}
        <div className="mx-auto grid max-w-4xl grid-cols-1 gap-8 md:grid-cols-3">
          <div className="rounded-lg border border-gray-300 bg-white p-6">
            <div className="mb-4 text-2xl">🔌</div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">
              Design Circuits
            </h3>
            <p className="text-gray-600">
              Drag and drop electronic components to build functional circuits
            </p>
          </div>

          <div className="rounded-lg border border-gray-300 bg-white p-6">
            <div className="mb-4 text-2xl">⏱️</div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">
              Beat the Clock
            </h3>
            <p className="text-gray-600">
              Solve puzzles within time limits and budget constraints
            </p>
          </div>

          <div className="rounded-lg border border-gray-300 bg-white p-6">
            <div className="mb-4 text-2xl">🏆</div>
            <h3 className="mb-2 text-lg font-semibold text-gray-900">
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
