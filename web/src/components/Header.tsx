import React from 'react';
import { Mic, Activity, AlertCircle, CheckCircle2, HelpCircle, Sun, Moon } from 'lucide-react';
import { MetaResponse } from '../types';

interface HeaderProps {
  meta: MetaResponse | null;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
  darkMode: boolean;
  onToggleDarkMode: () => void;
  onNewChat: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  meta,
  sidebarOpen,
  onToggleSidebar,
  darkMode,
  onToggleDarkMode,
  onNewChat,
}) => {
  const isMac = typeof window !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const shortcut = isMac ? '⌘K' : 'Ctrl+K';

  const getStatusBadge = () => {
    if (!meta) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-300 border border-stone-200 dark:border-stone-700">
          <Activity className="w-3.5 h-3.5 animate-pulse text-stone-400" />
          <span>Connecting...</span>
        </span>
      );
    }

    const { provider, model, provider_status } = meta;
    const providerLabel = provider === 'ollama' ? 'Ollama (Local)' : 'Claude';

    if (provider_status === 'ok') {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 shadow-2xs"
          title={`Provider: ${providerLabel}\nModel: ${model}\nStatus: Ready`}
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
          <span className="font-semibold">{providerLabel}</span>
          <span className="text-emerald-600/80 dark:text-emerald-400/80">· {model}</span>
        </span>
      );
    }

    if (provider_status === 'unconfigured') {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800/60 shadow-2xs"
          title="Anthropic API key is missing. Set ANTHROPIC_API_KEY in .env or switch to Ollama."
        >
          <AlertCircle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
          <span className="font-semibold">{providerLabel}</span>
          <span className="text-amber-600/80 dark:text-amber-400/80">· Key Missing</span>
        </span>
      );
    }

    if (provider_status === 'unavailable') {
      return (
        <span
          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800/60 shadow-2xs"
          title="Model host is unreachable. Verify Ollama or network connection."
        >
          <AlertCircle className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
          <span className="font-semibold">{providerLabel}</span>
          <span className="text-rose-600/80 dark:text-rose-400/80">· Host Unreachable</span>
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 border border-stone-200 dark:border-stone-700">
        <HelpCircle className="w-3.5 h-3.5 text-stone-500" />
        <span>{providerLabel}</span>
      </span>
    );
  };

  return (
    <header className="h-14 border-b border-stone-200 dark:border-stone-800 bg-[#FBF9F5]/90 dark:bg-stone-900/90 backdrop-blur-md px-4 flex items-center justify-between z-20 sticky top-0 transition-colors">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          aria-expanded={sidebarOpen}
          className="p-1.5 text-stone-600 dark:text-stone-300 hover:text-stone-900 dark:hover:text-stone-100 hover:bg-stone-200/50 dark:hover:bg-stone-800 rounded-lg transition-colors md:hidden"
          title="Toggle Sessions Sidebar"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-lenny-600 dark:bg-lenny-700 text-white flex items-center justify-center shadow-sm">
            <Mic className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-stone-900 dark:text-stone-100 text-sm md:text-base tracking-tight leading-none">
                The Lenny Growth Assistant
              </h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded bg-lenny-100 dark:bg-lenny-950/80 text-lenny-800 dark:text-lenny-300 border border-lenny-200 dark:border-lenny-800/80 hidden sm:inline-block">
                Grounded
              </span>
            </div>
            <p className="text-[11px] text-stone-500 dark:text-stone-400 hidden sm:block leading-none mt-1">
              300+ Lenny's Podcast episodes & transcripts
            </p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Model status pill */}
        {getStatusBadge()}

        {/* New chat shortcut hint button */}
        <button
          onClick={onNewChat}
          className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium text-stone-600 dark:text-stone-300 hover:text-stone-900 dark:hover:text-stone-100 hover:bg-stone-200/50 dark:hover:bg-stone-800 rounded-lg transition-colors border border-transparent hover:border-stone-300 dark:hover:border-stone-700"
          title={`New chat (${shortcut})`}
        >
          <span>New</span>
          <kbd className="text-[10px] font-mono px-1 py-0.2 rounded bg-stone-200/80 dark:bg-stone-800 text-stone-700 dark:text-stone-300">
            {shortcut}
          </kbd>
        </button>

        {/* Dark mode toggle */}
        <button
          onClick={onToggleDarkMode}
          className="p-2 text-stone-600 dark:text-stone-300 hover:text-stone-900 dark:hover:text-stone-100 hover:bg-stone-200/50 dark:hover:bg-stone-800 rounded-lg transition-colors"
          title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {darkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-stone-600" />}
        </button>
      </div>
    </header>
  );
};
