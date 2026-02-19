import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CodeBlock from './CodeBlock';

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="prose prose-invert max-w-none prose-p:text-text-primary prose-headings:text-text-primary prose-p:leading-7 prose-code:text-agent-lucas prose-code:bg-[rgba(244,63,94,0.1)] prose-blockquote:border-l-border-default prose-blockquote:text-text-secondary">
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
