import { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Check, Copy } from 'lucide-react';

interface MarkdownRendererProps {
    content: string;
    className?: string;
}

function CodeBlock({
    language,
    code,
}: {
    language: string;
    code: string;
}) {
    const [isCopied, setIsCopied] = useState(false);

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(code);
            setIsCopied(true);
            setTimeout(() => setIsCopied(false), 1200);
        } catch {
            setIsCopied(false);
        }
    };

    return (
        <div className="rounded-xl overflow-hidden border border-border-subtle my-4 shadow-sm">
            <div className="bg-[#1a1f2a] px-3 py-2 text-[11px] text-text-muted border-b border-border-subtle flex justify-between items-center uppercase tracking-wide">
                <span>{language || 'code'}</span>
                <button
                    type="button"
                    onClick={handleCopy}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-white/5 hover:bg-white/10 text-text-secondary hover:text-text-primary transition-colors"
                    title="Копировать код"
                >
                    {isCopied ? <Check size={13} /> : <Copy size={13} />}
                    <span>{isCopied ? 'Скопировано' : 'Копировать'}</span>
                </button>
            </div>
            <SyntaxHighlighter
                style={oneDark}
                language={language}
                PreTag="div"
                customStyle={{ margin: 0, borderRadius: 0, background: '#0d1117', fontSize: '0.85rem' }}
            >
                {code}
            </SyntaxHighlighter>
        </div>
    );
}

export default function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
    const normalizedContent = useMemo(
        () => content.replace(/\r\n/g, '\n').trimEnd(),
        [content],
    );

    return (
        <div
            className={`prose prose-invert max-w-none prose-sm md:prose-base
            prose-p:leading-relaxed prose-p:text-text-secondary prose-p:my-3
            prose-pre:p-0 prose-pre:bg-transparent
            prose-code:text-accent-blue prose-code:bg-white/5 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none
            prose-headings:text-text-primary prose-strong:text-text-primary prose-a:text-accent-blue prose-a:no-underline hover:prose-a:underline
            prose-ul:my-3 prose-ol:my-3 prose-li:my-1
            prose-blockquote:border-l-accent-blue prose-blockquote:text-text-secondary prose-blockquote:italic
            prose-table:my-0 prose-th:text-text-primary prose-td:text-text-secondary
            ${className}`}
        >
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                    code({ className: codeClassName, children, ...props }) {
                        const match = /language-([\w-]+)/.exec(codeClassName || '');
                        const code = String(children).replace(/\n$/, '');

                        if (match) {
                            return <CodeBlock language={match[1]} code={code} />;
                        }

                        return (
                            <code className={codeClassName} {...props}>
                                {children}
                            </code>
                        );
                    },
                    table({ children }) {
                        return (
                            <div className="my-5 overflow-x-auto rounded-xl border border-border-subtle bg-bg-surface/40 shadow-[0_8px_20px_rgba(0,0,0,0.2)]">
                                <table className="w-full min-w-[560px] border-collapse text-sm">{children}</table>
                            </div>
                        );
                    },
                    thead({ children }) {
                        return (
                            <thead className="bg-bg-hover/60 border-b border-border-subtle">
                                {children}
                            </thead>
                        );
                    },
                    tbody({ children }) {
                        return <tbody className="divide-y divide-border-subtle/60">{children}</tbody>;
                    },
                    tr({ children }) {
                        return <tr className="even:bg-white/[0.02]">{children}</tr>;
                    },
                    th({ children }) {
                        return (
                            <th className="px-4 py-3 text-left text-xs uppercase tracking-wider font-semibold text-text-primary/90">
                                {children}
                            </th>
                        );
                    },
                    td({ children }) {
                        return <td className="px-4 py-3 align-top leading-relaxed">{children}</td>;
                    },
                }}
            >
                {normalizedContent}
            </ReactMarkdown>
        </div>
    );
}
