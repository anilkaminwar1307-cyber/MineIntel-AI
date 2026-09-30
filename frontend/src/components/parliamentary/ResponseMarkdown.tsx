import React from 'react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface ResponseMarkdownProps {
  content: string;
}

export const ResponseMarkdown: React.FC<ResponseMarkdownProps> = ({ content }) => {
  return (
    <div className="prose-chatgpt text-slate-800 text-xs md:text-sm leading-relaxed max-w-none">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-base md:text-lg font-bold text-slate-900 border-b border-slate-200 pb-2 mb-3 mt-4 first:mt-0 tracking-tight flex items-center space-x-2">
              <span>{children}</span>
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm md:text-base font-bold text-slate-900 mt-4 mb-2 tracking-tight">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs md:text-sm font-bold text-slate-800 mt-3 mb-1.5 text-rose-900 flex items-center space-x-1.5">
              <span>{children}</span>
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-[11px] md:text-xs font-bold text-slate-700 uppercase tracking-wider mt-2 mb-1">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="my-2 leading-relaxed text-slate-700 font-normal">
              {children}
            </p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-slate-950">
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em className="italic text-slate-700">
              {children}
            </em>
          ),
          ul: ({ children }) => (
            <ul className="my-2 ml-4 list-disc space-y-1 text-slate-700 marker:text-rose-600">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-2 ml-4 list-decimal space-y-1 text-slate-700 marker:text-rose-700 marker:font-semibold">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed pl-1">
              {children}
            </li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-3 border-rose-500 bg-rose-50/40 rounded-r-lg px-4 py-2.5 my-3 text-slate-700 italic">
              {children}
            </blockquote>
          ),
          hr: () => (
            <hr className="my-4 border-t border-slate-200" />
          ),
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-xl border border-slate-200 shadow-xs bg-white">
              <table className="w-full text-left border-collapse text-xs">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-slate-50/90 text-[11px] font-semibold text-slate-700 uppercase tracking-wider border-b border-slate-200">
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th className="py-2.5 px-3.5 text-left font-semibold text-slate-800">
              {children}
            </th>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-slate-50/60 transition-colors">
              {children}
            </tr>
          ),
          td: ({ children }) => (
            <td className="py-2.5 px-3.5 align-middle">
              {children}
            </td>
          ),
          code: ({ children, className }) => {
            const isBlock = className?.includes('language-');
            if (isBlock) {
              return (
                <div className="my-2.5 rounded-lg bg-slate-900 text-slate-100 p-3 text-xs font-mono overflow-x-auto shadow-inner">
                  <code>{children}</code>
                </div>
              );
            }
            return (
              <code className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 font-mono text-[11px] text-slate-800 font-medium">
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </Markdown>
    </div>
  );
};
