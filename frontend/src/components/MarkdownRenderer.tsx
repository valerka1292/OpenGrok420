import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

export default function MarkdownRenderer({ content, className = "" }: MarkdownRendererProps) {
    return (
        <div className={`prose prose-invert max-w-none 
      prose-p:leading-relaxed prose-pre:p-0 prose-pre:bg-transparent 
      prose-code:text-accent-blue prose-code:bg-white/5 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none
      prose-headings:text-text-primary prose-strong:text-text-primary prose-a:text-accent-blue
      ${className}`}
        >
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    code({ node, inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline && match ? (
                            <div className="rounded-lg overflow-hidden border border-border-subtle my-4">
                                <div className="bg-[#1e1e1e] px-4 py-2 text-xs text-text-muted border-b border-border-subtle flex justify-between items-center">
                                    <span>{match[1]}</span>
                                    {/* Copy button could go here */}
                                </div>
                                <SyntaxHighlighter
                                    style={oneDark}
                                    language={match[1]}
                                    PreTag="div"
                                    customStyle={{ margin: 0, borderRadius: 0, background: '#0d1117' }}
                                    {...props}
                                >
                                    {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                            </div>
                        ) : (
                            <code className={className} {...props}>
                                {children}
                            </code>
                        );
                    }
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
