import React from 'react';
import { Mic, Activity, AlertCircle, CheckCircle2, HelpCircle } from 'lucide-react';
import { MetaResponse } from '../types';

interface HeaderProps {
  meta: MetaResponse | null;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({ meta, sidebarOpen, onToggleSidebar }) => {
  const getStatusBadge = () => {
    if (!meta) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-stone-100 text-stone-600 border border-stone-200">
          <Activity className="w-3.5 h-3.5 animate-pulse text-stone-400" />
          Connecting...
        </span>
      );
    }

    const { provider, model, provider_status } = meta;
    const providerLabel = provider === 'ollama' ? 'Ollama (Local)' : 'Anthropic Claude';

    if (provider_status === 'ok') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-sm" title={`Provider: ${providerLabel}\nModel: ${model}\nStatus: Ready`}>
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span className="font-semibold">{providerLabel}</span>
          <span className="text-emerald-600/70">· {model}</span>
        </span>
      );
    }

    if (provider_status === 'unconfigured') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200 shadow-sm" title="Anthropic API key is missing. Set ANTHROPIC_API_KEY in .env or switch to Ollama.">
          <AlertCircle className="w-3.5 h-3.5 text-amber-600" />
          <span className="font-semibold">{providerLabel}</span>
          <span className="text-amber-600/80">· Key Missing</span>
        </span>
      );
    }

    if (provider_status === 'unavailable') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-50 text-rose-800 border border-rose-200 shadow-sm" title="Ollama host is unreachable. Please start Ollama on your host machine.">
          <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
          <span className="font-semibold">{providerLabel}</span>
          <span className="text-rose-600/80">· Host Unreachable</span>
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-stone-100 text-stone-700 border border-stone-200">
        <HelpCircle className="w-3.5 h-3.5 text-stone-500" />
        <span>{providerLabel}</span>
      </span>
    );
  };

  return (
    <header className="h-14 border-b border-stone-200 bg-[#FBF9F5]/90 backdrop-blur-md px-4 flex items-center justify-between z-20 sticky top-0">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          aria-expanded={sidebarOpen}
          className="p-1.5 text-stone-600 hover:text-stone-900 hover:bg-stone-200/50 rounded-lg transition-colors md:hidden"
          title="Toggle Sessions Sidebar"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-lenny-600 text-white flex items-center justify-center shadow-sm">
            <Mic className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-stone-900 text-sm md:text-base tracking-tight leading-none">
                The Lenny Growth Assistant
              </h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-lenny-100 text-lenny-800 border border-lenny-200 hidden sm:inline-block">
                Grounded
              </span>
            </div>
            <p className="text-[11px] text-stone-500 hidden sm:block leading-none mt-1">
              300+ Lenny's Podcast episodes & transcripts
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        {getStatusBadge()}
      </div>
    </header>
  );
};
