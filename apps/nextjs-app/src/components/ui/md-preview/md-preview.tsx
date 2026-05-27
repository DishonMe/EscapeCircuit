'use client';

import { parse } from 'marked';
import { useEffect, useState } from 'react';

export type MDPreviewProps = {
  value: string;
};

export const MDPreview = ({ value = '' }: MDPreviewProps) => {
  const [renderedHtml, setRenderedHtml] = useState('');

  useEffect(() => {
    let isMounted = true;

    const renderMarkdown = async () => {
      const { default: DOMPurify } = await import('dompurify');
      const clean = DOMPurify.sanitize(parse(value) as string);
      if (isMounted) {
        setRenderedHtml(clean);
      }
    };

    renderMarkdown().catch(() => {
      if (isMounted) {
        setRenderedHtml('');
      }
    });

    return () => {
      isMounted = false;
    };
  }, [value]);

  return (
    <div
      className="prose prose-slate w-full p-2"
      dangerouslySetInnerHTML={{
        __html: renderedHtml,
      }}
    />
  );
};
