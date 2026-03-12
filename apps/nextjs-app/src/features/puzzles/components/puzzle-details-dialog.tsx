'use client';

import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { Puzzle } from '@/types/api';
import { useEffect, useState } from 'react';
import 'katex/dist/katex.min.css';

type PuzzleDetailsDialogProps = {
  puzzle: Puzzle | undefined;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  showLink?: boolean;
};

// Convert LaTeX document structure to Markdown
const latexToMarkdown = (latex: string): string => {
  let markdown = latex;
  
  // Convert tabular environments to markdown tables
  const tabularyRegex = /\\begin\{(?:tabular|array)\}\{[^}]*\}(.*?)\\end\{(?:tabular|array)\}/gs;
  markdown = markdown.replace(tabularyRegex, (_match: string, content: string) => {
    // Split by \\ to get rows
    const rows = content
      .split('\\\\')
      .map((row: string) => row.replace(/\\hline/g, '').trim())
      .filter((row: string) => row.length > 0);
    
    if (rows.length === 0) return '';
    
    // Split each row by & to get cells
    const mdRows = rows.map((row: string) => {
      const cells = row.split('&').map((cell: string) => cell.trim());
      return '| ' + cells.join(' | ') + ' |';
    });
    
    // Add header separator after first row
    if (mdRows.length > 0) {
      const firstRowCells = rows[0].split('&').length;
      const separator = '|' + Array(firstRowCells).fill('---|').join('');
      mdRows.splice(1, 0, separator);
    }
    
    return '\n' + mdRows.join('\n') + '\n';
  });
  
  // Convert \section*{...} to # ...
  markdown = markdown.replace(/\\section\*\s*\{([^}]+)\}/g, '# $1');
  
  // Convert \subsection*{...} to ## ...
  markdown = markdown.replace(/\\subsection\*\s*\{([^}]+)\}/g, '## $1');
  
  // Convert \subsubsection*{...} to ### ...
  markdown = markdown.replace(/\\subsubsection\*\s*\{([^}]+)\}/g, '### $1');
  
  // Convert \textbf{...} to **...**
  markdown = markdown.replace(/\\textbf\s*\{([^}]+)\}/g, '**$1**');
  
  // Convert \textit{...} to *...*
  markdown = markdown.replace(/\\textit\s*\{([^}]+)\}/g, '*$1*');
  
  // Convert \texttt{...} to `...`
  markdown = markdown.replace(/\\texttt\s*\{([^}]+)\}/g, '`$1`');
  
  // Handle \begin{center}...\end{center}  
  markdown = markdown.replace(/\\begin\{center\}(.*?)\\end\{center\}/gs, '$1');
  
  // Handle \begin{itemize}...\end{itemize} - markdown-it handles bullet lists
  markdown = markdown.replace(/\\begin\{itemize\}/g, '');
  markdown = markdown.replace(/\\end\{itemize\}/g, '');
  markdown = markdown.replace(/\\item\s+/g, '- ');
  
  // Handle \begin{enumerate}...\end{enumerate}
  markdown = markdown.replace(/\\begin\{enumerate\}/g, '');
  markdown = markdown.replace(/\\end\{enumerate\}/g, '');
  
  // Remove remaining LaTeX commands that don't need conversion
  markdown = markdown.replace(/\\\\/g, '\n'); // \\ to newline
  
  return markdown;
};

export const PuzzleDetailsDialog = ({
  puzzle,
  open,
  onOpenChange,
  showLink = true,
}: PuzzleDetailsDialogProps) => {
  // Render markdown on the client only. These libraries (markdown-it,
  // markdown-it-katex, isomorphic-dompurify) crash during SSR, so we
  // dynamically import them inside useEffect and store the rendered HTML.
  const [renderedHtml, setRenderedHtml] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'instructions' | 'custom'>('instructions');

  useEffect(() => {
    if (!puzzle?.instructions) {
      setRenderedHtml(null);
      return;
    }

    Promise.all([
      import('markdown-it'),
      import('markdown-it-katex'),
      import('dompurify'),
    ]).then(([MarkdownItMod, katexMod, DOMPurifyMod]) => {
      const MarkdownIt = MarkdownItMod.default;
      const markdownItKatex = katexMod.default;
      const DOMPurify = DOMPurifyMod.default || DOMPurifyMod;

      const md = new MarkdownIt({ html: true }).use(markdownItKatex);
      const markdown = latexToMarkdown(puzzle.instructions!);
      const html = md.render(markdown);

      setRenderedHtml(DOMPurify.sanitize(html, {
        ALLOWED_TAGS: [
          'p', 'strong', 'em', 'u', 'code', 'pre', 'blockquote',
          'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
          'ul', 'ol', 'li',
          'table', 'thead', 'tbody', 'tr', 'th', 'td',
          'a', 'span', 'div', 'i', 'br', 'sup', 'sub',
          'annotation', 'semantics', 'mrow', 'mi', 'mn', 'mo', 'mtext',
          'mfrac', 'msup', 'msub', 'mroot', 'msqrt'
        ],
        ALLOWED_ATTR: ['class', 'style', 'href', 'data-*']
      }));
    });
  }, [puzzle?.instructions]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{puzzle?.title ?? 'Puzzle details'}</DialogTitle>
          <DialogDescription>
            Key information before you start solving.
          </DialogDescription>
        </DialogHeader>

        {puzzle ? (
          <div className="max-h-[60vh] overflow-y-auto">
            {/* Tabs */}
            {puzzle.customComponents && puzzle.customComponents.length > 0 ? (
              <div className="flex gap-2 mb-4 border-b border-border">
                <button
                  onClick={() => setActiveTab('instructions')}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'instructions'
                      ? 'text-foreground border-b-2 border-foreground -mb-[2px]'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Instructions
                </button>
                <button
                  onClick={() => setActiveTab('custom')}
                  className={`px-3 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'custom'
                      ? 'text-foreground border-b-2 border-foreground -mb-[2px]'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Custom Pieces ({puzzle.customComponents.length})
                </button>
              </div>
            ) : null}

            {/* Instructions Tab */}
            {activeTab === 'instructions' && (
              <>
                {puzzle.instructions && renderedHtml ? (
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
                ) : null}
                {puzzle.instructions && renderedHtml ? (
                  <div
                    className="prose prose-sm max-w-none rounded-md border border-slate-300 bg-white p-4 text-slate-900 [&_*]:text-slate-900"
                    dangerouslySetInnerHTML={{ __html: renderedHtml }}
                  />
                ) : (
                  <div className="text-muted-foreground text-[13px]">No instructions provided.</div>
                )}
              </>
            )}

            {/* Custom Pieces Tab */}
            {activeTab === 'custom' && puzzle.customComponents && puzzle.customComponents.length > 0 && (
              <div className="space-y-4">
                {puzzle.customComponents.map((piece) => {
                  const truthTable = piece.truth_table 
                    ? (typeof piece.truth_table === 'string' 
                        ? JSON.parse(piece.truth_table) 
                        : piece.truth_table)
                    : {};
                  
                  return (
                    <div key={piece.id} className="border border-border rounded-lg p-4 bg-card">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="text-sm font-semibold text-foreground">{piece.type}</h3>
                          <p className="text-xs text-muted-foreground mt-1">
                            Cost: {piece.cost} • Inputs: {piece.num_inputs} • Outputs: {piece.num_outputs}
                          </p>
                        </div>
                      </div>
                      
                      {Object.keys(truthTable).length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="w-full border-collapse text-xs text-slate-900 dark:text-slate-100">
                            <thead>
                              <tr>
                                {Object.keys(truthTable[Object.keys(truthTable)[0]] || {}).map((key) => (
                                  <th key={key} className="border border-border bg-secondary px-2 py-1 text-left font-medium">
                                    {key}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(truthTable).map(([input, outputs]: [string, any]) => (
                                <tr key={input}>
                                  <td className="border border-border px-2 py-1 font-mono">{input}</td>
                                  {Object.values(outputs).map((value: any, idx: number) => (
                                    <td key={idx} className="border border-border px-2 py-1 font-mono text-center">
                                      {String(value)}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground">No truth table data available.</p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {showLink && puzzle ? (
            <Link
              href={`/app/puzzles/${puzzle.id}`}
              className="rounded-lg bg-foreground px-4 py-2 text-[13px] font-medium text-background hover:bg-foreground/90 transition-colors"
            >
              Go to puzzle
            </Link>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
