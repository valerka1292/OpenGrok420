import { Bug, FileText, Palette, Search, Server, BarChart3 } from 'lucide-react';

const prompts = [
  { text: 'Draft a blog post', Icon: FileText },
  { text: 'Analyze market data', Icon: Search },
  { text: 'Build REST API', Icon: Server },
  { text: 'Design system colors', Icon: Palette },
  { text: 'Debug this code', Icon: Bug },
  { text: 'Create report', Icon: BarChart3 },
];

export default function EmptyState({ onPick }: { onPick: (text: string) => void }) {
  return (
    <section className="text-center py-10 md:py-16">
      <h1 className="text-3xl font-semibold">Welcome to Mission Control</h1>
      <p className="text-text-secondary mt-3">Your AI team is standing by. What's the mission?</p>
      <div className="mt-8 grid grid-cols-2 md:grid-cols-3 gap-3">
        {prompts.map(({ text, Icon }) => (
          <button key={text} type="button" onClick={() => onPick(text)} className="text-left p-3 rounded-2xl bg-bg-surface-2 border border-border-subtle hover:border-agent-grok transition-all hover:-translate-y-0.5">
            <Icon size={14} className="mb-2 text-text-secondary" />
            {text}
          </button>
        ))}
      </div>
    </section>
  );
}
