import { useState } from 'react';
import { Play, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface DebugPanelProps {
  outputs: string[];
  onSuccess: () => void;
}

interface TestCase {
  id: number;
  inputs: boolean[];
  expectedOutputs: boolean[];
  passed?: boolean;
}

export function DebugPanel({ outputs, onSuccess }: DebugPanelProps) {
  const [currentOutputs, setCurrentOutputs] = useState<boolean[]>(
    outputs.map(() => false)
  );
  const [testResults, setTestResults] = useState<TestCase[]>([]);
  const [hasRun, setHasRun] = useState(false);
  const [errorMessages, setErrorMessages] = useState<string[]>([]);

  const runEvaluation = () => {
    // Mock test cases
    const mockTestCases: TestCase[] = [
      { id: 1, inputs: [false, false], expectedOutputs: [false, false], passed: true },
      { id: 2, inputs: [false, true], expectedOutputs: [true, false], passed: true },
      { id: 3, inputs: [true, false], expectedOutputs: [true, false], passed: true },
      { id: 4, inputs: [true, true], expectedOutputs: [false, true], passed: true },
    ];

    setTestResults(mockTestCases);
    setHasRun(true);

    // Mock error messages
    const errors: string[] = [];
    const failedTests = mockTestCases.filter((t) => !t.passed);
    if (failedTests.length > 0) {
      errors.push(`${failedTests.length} test case(s) failed`);
    } else {
      // All tests passed - show success modal
      setTimeout(() => {
        onSuccess();
      }, 500);
    }
    setErrorMessages(errors);

    // Update current outputs based on first test case
    setCurrentOutputs([false, false]);
  };

  const passedTests = testResults.filter((t) => t.passed).length;
  const totalTests = testResults.length;

  return (
    <div className="w-64 bg-gray-50 border-l border-gray-300 overflow-y-auto flex flex-col">
      <div className="p-4 flex-1">
        <h2 className="text-gray-900 mb-4">Debug Panel</h2>

        {/* Output Indicators */}
        <div className="mb-6">
          <h3 className="text-sm text-gray-700 mb-2">Output Indicators</h3>
          <div className="space-y-2">
            {outputs.map((output, index) => (
              <div
                key={output}
                className="flex items-center justify-between bg-white border border-gray-300 rounded p-2"
              >
                <span className="text-xs text-gray-700">{output}</span>
                <div
                  className={`w-4 h-4 rounded-full ${
                    currentOutputs[index] ? 'bg-green-500' : 'bg-gray-300'
                  }`}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Test Evaluation */}
        <div className="mb-6">
          <button
            onClick={runEvaluation}
            className="w-full px-3 py-2 bg-green-500 hover:bg-green-600 text-white rounded flex items-center justify-center gap-2 transition-colors"
          >
            <Play className="w-4 h-4" />
            <span className="text-sm">Run Evaluation</span>
          </button>
        </div>

        {/* Test Results */}
        {hasRun && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm text-gray-700">Test Results</h3>
              <span className="text-xs text-gray-600">
                {passedTests}/{totalTests} passed
              </span>
            </div>
            <div className="space-y-2">
              {testResults.map((test) => (
                <div
                  key={test.id}
                  className={`flex items-center gap-2 p-2 rounded text-xs ${
                    test.passed ? 'bg-green-50' : 'bg-red-50'
                  }`}
                >
                  {test.passed ? (
                    <CheckCircle className="w-3.5 h-3.5 text-green-600 flex-shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-red-600 flex-shrink-0" />
                  )}
                  <span className={test.passed ? 'text-green-700' : 'text-red-700'}>
                    Test {test.id}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error Messages */}
        {errorMessages.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm text-gray-700 mb-2 flex items-center gap-1">
              <AlertCircle className="w-4 h-4 text-orange-500" />
              Feedback
            </h3>
            <div className="space-y-2">
              {errorMessages.map((message, index) => (
                <div
                  key={index}
                  className="bg-orange-50 border border-orange-200 rounded p-2"
                >
                  <p className="text-xs text-orange-700">{message}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Success Message */}
        {hasRun && passedTests === totalTests && (
          <div className="bg-green-50 border border-green-200 rounded p-3">
            <div className="flex items-start gap-2">
              <CheckCircle className="w-4 h-4 text-green-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm text-green-700">All tests passed!</p>
                <p className="text-xs text-green-600 mt-1">
                  Your circuit is working correctly.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}