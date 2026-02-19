import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CodeBlock from './CodeBlock';

export default function MarkdownRenderer({ content }: { content: string }) {
  return (
    <div className="markdown-body">
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
