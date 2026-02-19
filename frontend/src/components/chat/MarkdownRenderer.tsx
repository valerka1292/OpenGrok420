import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CodeBlock from './CodeBlock';

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="prose prose-invert max-w-none prose-p:my-3 prose-p:text-text-primary prose-p:leading-7 prose-headings:mb-3 prose-headings:mt-6 prose-headings:font-semibold prose-headings:text-text-primary prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg prose-h4:text-base prose-h5:text-sm prose-h6:text-sm prose-h6:text-text-secondary prose-strong:text-text-primary prose-em:text-text-primary prose-del:text-text-tertiary prose-a:text-agent-benjamin prose-a:underline prose-a:underline-offset-2 hover:prose-a:text-agent-grok prose-ul:my-4 prose-ul:list-disc prose-ul:pl-6 prose-ol:my-4 prose-ol:list-decimal prose-ol:pl-6 prose-li:my-1.5 prose-li:marker:text-text-tertiary prose-hr:my-6 prose-hr:border-border-subtle prose-code:rounded prose-code:bg-[rgba(244,63,94,0.1)] prose-code:px-1.5 prose-code:py-0.5 prose-code:text-agent-lucas prose-code:before:content-none prose-code:after:content-none prose-blockquote:my-4 prose-blockquote:border-l-2 prose-blockquote:border-l-border-default prose-blockquote:bg-white/[0.02] prose-blockquote:py-1 prose-blockquote:pl-4 prose-blockquote:text-text-secondary prose-table:my-4 prose-table:w-full prose-thead:border-b prose-thead:border-border-default prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:text-text-primary prose-th:font-semibold prose-td:border-b prose-td:border-border-subtle prose-td:px-3 prose-td:py-2 prose-td:text-text-secondary prose-img:my-4 prose-img:rounded-lg prose-img:border prose-img:border-border-subtle prose-img:shadow-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children }) {
            const match = /language-(\w+)/.exec(className || '');
            const code = String(children).replace(/\n$/, '');
            if (!match) return <code>{children}</code>;
            return <CodeBlock language={match[1]} code={code} />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
