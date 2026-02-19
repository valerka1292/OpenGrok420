import { Check, Copy } from 'lucide-react';
import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

export default function CodeBlock({ language, code }: { language: string; code: string }) {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-border-default rounded-md overflow-hidden my-4">
      <div className="px-3 py-2 bg-white/5 border-b border-border-subtle text-xs text-text-tertiary flex items-center justify-between">
        <span>{language || 'code'}</span>
        <button type="button" onClick={onCopy} className="inline-flex items-center gap-1 hover:text-text-primary">
          {copied ? <Check size={12} /> : <Copy size={12} />} {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <SyntaxHighlighter style={oneDark} language={language} customStyle={{ margin: 0, background: '#0d1117' }}>
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
