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
import { useMemo } from 'react';
import MarkdownIt from 'markdown-it';
import markdownItKatex from 'markdown-it-katex';
import DOMPurify from 'isomorphic-dompurify';
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
  markdown = markdown.replace(tabularyRegex, (match, content) => {
    // Split by \\ to get rows
    const rows = content
      .split('\\\\')
      .map(row => row.replace(/\\hline/g, '').trim())
      .filter(row => row.length > 0);
    
    if (rows.length === 0) return '';
    
    // Split each row by & to get cells
    const mdRows = rows.map(row => {
      const cells = row.split('&').map(cell => cell.trim());
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
  const renderedHtml = useMemo(() => {
    if (!puzzle?.instructions) return null;
    
    // Convert LaTeX to Markdown
    const markdown = latexToMarkdown(puzzle.instructions);
    
    // Use markdown-it with katex plugin
    const md = new MarkdownIt({ html: true }).use(markdownItKatex);
    const html = md.render(markdown);
    
    // Sanitize the resulting HTML
    return DOMPurify.sanitize(html, {
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
                className="prose prose-sm max-w-none dark:prose-invert text-foreground [&_*]:text-foreground"
                dangerouslySetInnerHTML={{ __html: renderedHtml }}
              />
            ) : (
              <div className="text-muted-foreground text-[13px]">No instructions provided.</div>
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
