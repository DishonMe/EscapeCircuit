'use client';

import { useState, useEffect } from 'react';
import 'katex/dist/katex.min.css';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { usePuzzle } from '@/features/puzzles/api/get-puzzle';
import type { Puzzle } from '@/types/api';

type PuzzleViewDialogProps = {
  puzzle: Puzzle | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

const latexToMarkdown = (latex: string): string => {
  let markdown = latex;
  
  // Convert tabular environments to markdown tables
  const tabularyRegex = /\\begin\{(?:tabular|array)\}\{[^}]*\}(.*?)\\end\{(?:tabular|array)\}/gs;
  markdown = markdown.replace(tabularyRegex, (_match: string, content: string) => {
    const rows = content
      .split('\\\\')
      .map((row: string) => row.replace(/\\hline/g, '').trim())
      .filter((row: string) => row.length > 0);
    
    if (rows.length === 0) return '';
    
    const mdRows = rows.map((row: string) => {
      const cells = row.split('&').map((cell: string) => cell.trim());
      return '| ' + cells.join(' | ') + ' |';
    });
    
    if (mdRows.length > 0) {
      const firstRowCells = rows[0].split('&').length;
      const separator = '|' + Array(firstRowCells).fill('---|').join('');
      mdRows.splice(1, 0, separator);
    }
    
    return '\n' + mdRows.join('\n') + '\n';
  });
  
  markdown = markdown.replace(/\\section\*\s*\{([^}]+)\}/g, '# $1');
  markdown = markdown.replace(/\\subsection\*\s*\{([^}]+)\}/g, '## $1');
  markdown = markdown.replace(/\\subsubsection\*\s*\{([^}]+)\}/g, '### $1');
  markdown = markdown.replace(/\\textbf\s*\{([^}]+)\}/g, '**$1**');
  markdown = markdown.replace(/\\textit\s*\{([^}]+)\}/g, '*$1*');
  markdown = markdown.replace(/\\texttt\s*\{([^}]+)\}/g, '`$1`');
  markdown = markdown.replace(/\\begin\{center\}(.*?)\\end\{center\}/gs, '$1');
  markdown = markdown.replace(/\\begin\{itemize\}/g, '');
  markdown = markdown.replace(/\\end\{itemize\}/g, '');
  markdown = markdown.replace(/\\item\s+/g, '- ');
  markdown = markdown.replace(/\\begin\{enumerate\}/g, '');
  markdown = markdown.replace(/\\end\{enumerate\}/g, '');
  markdown = markdown.replace(/\\\\/g, '\n');
  
  return markdown;
};

export const PuzzleViewDialog = ({
  puzzle,
  open,
  onOpenChange,
}: PuzzleViewDialogProps) => {
  const [tab, setTab] = useState<'base' | 'test' | 'ratings' | 'instructions'>('base');
  const [renderedHtml, setRenderedHtml] = useState<string | null>(null);
  
  // Fetch full puzzle details when dialog opens
  const { data: fullPuzzle, isLoading: isPuzzleLoading } = usePuzzle({
    id: String(puzzle?.id || ''),
    config: {
      enabled: open && !!puzzle?.id,
    },
  });
  
  // Use full puzzle if available, otherwise use the passed puzzle
  const displayPuzzle = fullPuzzle || puzzle;

  useEffect(() => {
    if (!open || !displayPuzzle || tab !== 'instructions') {
      setRenderedHtml(null);
      return;
    }

    const renderMarkdown = async () => {
      try {
        const [markdown] = await Promise.all([
          import('markdown-it'),
          import('markdown-it-katex'),
        ]);
        
        const mdit = markdown.default();
        const katex = (await import('markdown-it-katex')).default;
        mdit.use(katex);
        
        const instructions = displayPuzzle.instructions || '';
        const processedMarkdown = latexToMarkdown(instructions);
        const html = mdit.render(processedMarkdown);
        
        const { default: DOMPurify } = await import('isomorphic-dompurify');
        const clean = DOMPurify.sanitize(html);
        setRenderedHtml(clean);
      } catch (error) {
        console.error('Failed to render markdown:', error);
        setRenderedHtml('<p>Error rendering instructions</p>');
      }
    };

    renderMarkdown();
  }, [open, displayPuzzle, tab]);

  if (!displayPuzzle) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[80vh] max-w-2xl bg-card flex flex-col">
        <DialogHeader>
          <DialogTitle className="text-foreground">{displayPuzzle.title}</DialogTitle>
        </DialogHeader>

        {/* Tabs */}
        <div className="flex border-b border-border">
          <button
            onClick={() => setTab('base')}
            className={`px-4 py-2 text-[13px] font-medium transition-colors ${
              tab === 'base'
                ? 'border-b-2 border-foreground text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Base Data
          </button>
          <button
            onClick={() => setTab('test')}
            className={`px-4 py-2 text-[13px] font-medium transition-colors ${
              tab === 'test'
                ? 'border-b-2 border-foreground text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Test Cases
          </button>
          <button
            onClick={() => setTab('ratings')}
            className={`px-4 py-2 text-[13px] font-medium transition-colors ${
              tab === 'ratings'
                ? 'border-b-2 border-foreground text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Solving and Rating
          </button>
          <button
            onClick={() => setTab('instructions')}
            className={`px-4 py-2 text-[13px] font-medium transition-colors ${
              tab === 'instructions'
                ? 'border-b-2 border-foreground text-foreground'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Instructions
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto space-y-4 py-4 px-4">
          {tab === 'base' && (
            <div className="space-y-4">
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Title</p>
                <p className="text-[13px] text-foreground">{displayPuzzle.title}</p>
              </div>
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Description</p>
                <p className="text-[13px] text-foreground">{displayPuzzle.description || 'No description'}</p>
              </div>
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Creator</p>
                <p className="text-[13px] text-foreground">{displayPuzzle.creator?.username || 'Unknown'}</p>
              </div>
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Difficulty</p>
                <p className="text-[13px] text-foreground">{displayPuzzle.difficulty}</p>
              </div>
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Status</p>
                <p className="text-[13px] text-foreground capitalize">
                  {(displayPuzzle as any).status || ((displayPuzzle as any).isPublished ? 'Published' : 'Unpublished')}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Visibility</p>
                <p className="text-[13px] text-foreground">{displayPuzzle.isPublic ? 'Public' : 'Private'}</p>
              </div>
              {displayPuzzle.creatorComment && (
                <div>
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Creator Comment</p>
                  <p className="text-[13px] text-foreground bg-secondary p-2 rounded">{displayPuzzle.creatorComment}</p>
                </div>
              )}
              {displayPuzzle.defaultGateSet && (
                <div>
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Default Gate Set</p>
                  <p className="text-[13px] text-foreground">{(displayPuzzle.defaultGateSet as any).join?.(',') || displayPuzzle.defaultGateSet}</p>
                </div>
              )}
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Arsenal Allowed</p>
                <p className="text-[13px] text-foreground">{displayPuzzle.allowArsenal ? 'Yes' : 'No'}</p>
              </div>
            </div>
          )}

          {tab === 'test' && (
            <div className="space-y-4">
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Time Limit</p>
                <p className="text-[13px] text-foreground bg-secondary p-2 rounded">{displayPuzzle.timeLimit} seconds</p>
              </div>
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Budget Limit</p>
                <p className="text-[13px] text-foreground bg-secondary p-2 rounded">{displayPuzzle.budgetLimit || displayPuzzle.budget}</p>
              </div>
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Test Cases</p>
                <div className="border border-border rounded overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-secondary">
                        <th className="px-3 py-2 text-left text-foreground">Inputs</th>
                        <th className="px-3 py-2 text-left text-foreground">Expected Outputs</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(displayPuzzle as any).test_cases && (displayPuzzle as any).test_cases.length > 0 ? (
                        (displayPuzzle as any).test_cases
                          .filter((tc: any) => {
                            const hasInputs = tc.inputs && Object.keys(tc.inputs).length > 0;
                            const hasOutputs = tc.outputs && Object.keys(tc.outputs).length > 0;
                            const hasInputStreams = Array.isArray(tc.input_stream) && tc.input_stream.length > 0;
                            const hasOutputStreams = Array.isArray(tc.expected_output_stream) && tc.expected_output_stream.length > 0;
                            return hasInputs || hasOutputs || hasInputStreams || hasOutputStreams;
                          })
                          .map((tc: any, idx: number) => (
                            <tr key={idx} className="border-b border-border hover:bg-secondary/50">
                              <td className="px-3 py-2 text-muted-foreground text-[11px]"><pre className="font-mono text-wrap break-words">{JSON.stringify(tc.inputs || tc.input_stream || {})}</pre></td>
                              <td className="px-3 py-2 text-muted-foreground text-[11px]"><pre className="font-mono text-wrap break-words">{JSON.stringify(tc.outputs || tc.expected_output_stream || {})}</pre></td>
                            </tr>
                          ))
                      ) : (
                        <tr>
                          <td colSpan={2} className="px-3 py-2 text-center text-muted-foreground">No test cases specified</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Gate Limits (Allowed Gates)</p>
                <div className="bg-secondary p-3 rounded text-[13px] text-foreground">
                  {(displayPuzzle as any).gateLimits && Object.keys((displayPuzzle as any).gateLimits).length > 0 ? (
                    Object.entries((displayPuzzle as any).gateLimits)
                      .map(([gate, limit]: [string, any]) => `${gate}-${limit === null ? 'unlimited' : limit}`)
                      .join(', ')
                  ) : (
                    "No gates allowed"
                  )}
                </div>
              </div>
              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Arsenal Pieces</p>
                <p className="text-[12px] text-foreground">
                  {displayPuzzle.allowArsenal !== false ? "✓ Allowed" : "✗ Not allowed - Only basic gates permitted"}
                </p>
              </div>
              {displayPuzzle.allowArsenal !== false && displayPuzzle.specialComponents && displayPuzzle.specialComponents.length > 0 && (
                <div>
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Available Arsenal</p>
                  <div className="space-y-2">
                    {displayPuzzle.specialComponents.map((comp: any, idx: number) => (
                      <div key={idx} className="bg-secondary p-3 rounded text-[12px]">
                        <p className="text-foreground"><strong>{comp.type}</strong> - Cost: {comp.cost}, Pins: {comp.pins}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {tab === 'ratings' && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Total Solves</p>
                  <p className="text-[13px] text-foreground bg-secondary p-2 rounded">{displayPuzzle.solvedCount || 0}</p>
                </div>
                <div>
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Times Saved</p>
                  <p className="text-[13px] text-foreground bg-secondary p-2 rounded">{(displayPuzzle as any).timesSaved || 0}</p>
                </div>
              </div>

              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Average Ratings</p>
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-secondary p-3 rounded">
                    <p className="text-[11px] text-muted-foreground mb-1">Difficulty</p>
                    <p className="text-[16px] font-semibold text-foreground">{Math.round((displayPuzzle.rating_metrics?.avg_difficulty || 0) * 10) / 10}/5</p>
                  </div>
                  <div className="bg-secondary p-3 rounded">
                    <p className="text-[11px] text-muted-foreground mb-1">Fun</p>
                    <p className="text-[16px] font-semibold text-foreground">{Math.round((displayPuzzle.rating_metrics?.avg_fun || 0) * 10) / 10}/5</p>
                  </div>
                  <div className="bg-secondary p-3 rounded">
                    <p className="text-[11px] text-muted-foreground mb-1">Clearness</p>
                    <p className="text-[16px] font-semibold text-foreground">{Math.round((displayPuzzle.rating_metrics?.avg_clearness || 0) * 10) / 10}/5</p>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Rating Distribution</p>
                <div className="border border-border rounded overflow-hidden">
                  <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border bg-secondary">
                          <th className="px-3 py-2 text-left text-foreground">Stars</th>
                          <th className="px-3 py-2 text-center text-foreground">Difficulty</th>
                          <th className="px-3 py-2 text-center text-foreground">Fun</th>
                          <th className="px-3 py-2 text-center text-foreground">Clearness</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[5, 4, 3, 2, 1].map((stars) => {
                          const distribution = (displayPuzzle.rating_metrics as any)?.rating_distribution;
                          const diffCount = distribution?.difficulty?.[stars - 1] || 0;
                          const funCount = distribution?.fun?.[stars - 1] || 0;
                          const clearCount = distribution?.clearness?.[stars - 1] || 0;
                          return (
                            <tr key={stars} className="border-b border-border hover:bg-secondary/50">
                              <td className="px-3 py-2 text-foreground">{stars} ⭐</td>
                              <td className="px-3 py-2 text-center text-muted-foreground">{diffCount}</td>
                              <td className="px-3 py-2 text-center text-muted-foreground">{funCount}</td>
                              <td className="px-3 py-2 text-center text-muted-foreground">{clearCount}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div>
                  <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide mb-2">Medal Distribution</p>
                  <div className="border border-border rounded overflow-hidden">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border bg-secondary">
                          <th className="px-3 py-2 text-left text-foreground">Medal</th>
                          <th className="px-3 py-2 text-center text-foreground">Count</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b border-border hover:bg-secondary/50">
                          <td className="px-3 py-2 text-foreground">🥇 Gold</td>
                          <td className="px-3 py-2 text-center text-muted-foreground">{(displayPuzzle as any).medalDistribution?.gold || 0}</td>
                        </tr>
                        <tr className="border-b border-border hover:bg-secondary/50">
                          <td className="px-3 py-2 text-foreground">🥈 Silver</td>
                          <td className="px-3 py-2 text-center text-muted-foreground">{(displayPuzzle as any).medalDistribution?.silver || 0}</td>
                        </tr>
                        <tr className="border-b border-border hover:bg-secondary/50">
                          <td className="px-3 py-2 text-foreground">🥉 Bronze</td>
                          <td className="px-3 py-2 text-center text-muted-foreground">{(displayPuzzle as any).medalDistribution?.bronze || 0}</td>
                        </tr>
                        <tr className="hover:bg-secondary/50">
                          <td className="px-3 py-2 text-foreground">- Unsolved</td>
                          <td className="px-3 py-2 text-center text-muted-foreground">{(displayPuzzle as any).medalDistribution?.none || 0}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
            </div>
          )}

          {tab === 'instructions' && (
            <div>
              {displayPuzzle.instructions && renderedHtml ? (
                <>
                  <style>{`
                    .prose .katex {
                      vertical-align: baseline !important;
                      margin: 0 !important;
                      padding: 0 !important;
                      line-height: 1 !important;
                      font-size: inherit;
                      display: inline-block !important;
                      white-space: nowrap;
                      position: relative;
                      top: -0.35em;
                    }
                    .prose .katex-html {
                      vertical-align: baseline !important;
                    }
                    .prose .katex-display {
                      margin: 0.5em 0;
                      vertical-align: baseline;
                      position: static;
                      top: auto;
                    }
                    .prose table {
                      border-collapse: collapse;
                      width: 100%;
                      margin: 1em 0;
                    }
                    .prose table td,
                    .prose table th {
                      border: 1px solid currentColor;
                      padding: 0.5em;
                      text-align: center;
                      vertical-align: middle;
                      line-height: 1.4;
                    }
                    .prose table th {
                      font-weight: bold;
                      background-color: rgba(0, 0, 0, 0.05);
                    }
                    .prose u {
                      text-decoration: underline;
                      text-underline-offset: 4px;
                    }
                  `}</style>
                  <div
                    className="prose prose-sm max-w-none dark:prose-invert text-foreground [&_*]:text-foreground"
                    dangerouslySetInnerHTML={{ __html: renderedHtml }}
                  />
                </>
              ) : (
                <div className="text-muted-foreground text-[13px]">No instructions provided.</div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
