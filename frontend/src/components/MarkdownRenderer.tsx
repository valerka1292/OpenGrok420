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
        <div className={`markdown-body ${className}`}>
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
                            <div className="my-5 overflow-x-auto rounded-xl border border-border-subtle bg-bg-surface-2/20">
                                <table className="min-w-[560px]">{children}</table>
                            </div>
                        );
                    },
                }}
            >
                {normalizedContent}
            </ReactMarkdown>
        </div>
    );
}
