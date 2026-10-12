import React from 'react';
import { Mic, Sparkles, BookOpen, Layers, Flame } from 'lucide-react';

interface EmptyStateProps {
  onSelectPrompt: (
    prompt: string,
    intent?: 'qa' | 'essay' | 'artifact' | null,
    format?: 'markdown' | 'html' | null
  ) => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ onSelectPrompt }) => {
  const suggestions = [
    {
      icon: Flame,
      intent: 'qa' as const,
      format: null,
      title: 'Finding Product-Market Fit',
      prompt: 'What are the most reliable indicators of product-market fit according to Lenny’s guests?',
      tag: 'Grounded QA',
    },
    {
      icon: BookOpen,
      intent: 'essay' as const,
      format: 'markdown' as const,
      title: 'Ship 30 for 30 Essay',
      prompt: 'Write a Ship 30 for 30 essay on how onboarding determines long-term user retention',
      tag: 'Ship 30 Skill',
    },
    {
      icon: Sparkles,
      intent: 'qa' as const,
      format: null,
      title: 'Founder Mode & Management',
      prompt: 'What did Brian Chesky explain about founder mode and hands-on leadership?',
      tag: 'Guest Insights',
    },
    {
      icon: Layers,
      intent: 'artifact' as const,
      format: 'html' as const,
      title: 'Interactive HTML Widget',
      prompt: 'Build an interactive HTML unit economics and churn calculator tool',
      tag: 'HTML Artifact',
    },
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-2xl mx-auto">
      <div className="w-14 h-14 rounded-2xl bg-lenny-600 dark:bg-lenny-700 text-white flex items-center justify-center shadow-md mb-4 animate-in zoom-in-95 duration-200">
        <Mic className="w-7 h-7" />
      </div>

      <h1 className="text-xl md:text-2xl font-bold text-stone-900 dark:text-stone-100 tracking-tight mb-2">
        The Lenny Growth Assistant
      </h1>
      <p className="text-xs md:text-sm text-stone-600 dark:text-stone-400 max-w-md mb-8 leading-relaxed">
        Grounded directly in 300+ episodes of Lenny's Podcast. Ask questions, generate Ship 30 essays, or build interactive artifacts with verified citations.
      </p>

      <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
        {suggestions.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              onClick={() => onSelectPrompt(item.prompt, item.intent, item.format)}
              className="p-3.5 bg-white dark:bg-stone-900 hover:bg-stone-50 dark:hover:bg-stone-850 border border-stone-200/90 dark:border-stone-800 hover:border-lenny-300 dark:hover:border-lenny-700 rounded-xl transition-all shadow-2xs hover:shadow-xs group flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-lenny-700 dark:text-lenny-400 bg-lenny-50 dark:bg-lenny-950/70 px-2 py-0.5 rounded border border-lenny-200 dark:border-lenny-800/80">
                    {item.tag}
                  </span>
                  <Icon className="w-4 h-4 text-stone-400 dark:text-stone-500 group-hover:text-lenny-600 dark:group-hover:text-lenny-400 transition-colors" />
                </div>
                <div className="font-semibold text-xs text-stone-900 dark:text-stone-100 mb-1">
                  {item.title}
                </div>
                <div className="text-[11px] text-stone-500 dark:text-stone-400 line-clamp-2 leading-relaxed">
                  "{item.prompt}"
                </div>
              </div>
              <div className="text-[11px] text-lenny-600 dark:text-lenny-400 font-medium mt-3 flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                <span>Ask this</span>
                <span>→</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
