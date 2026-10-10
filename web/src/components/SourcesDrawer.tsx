import React from 'react';
import { X, ExternalLink, Calendar, User, Film } from 'lucide-react';
import { Source } from '../types';

interface SourcesDrawerProps {
  sources: Source[];
  activeSourceId: string | null;
  isOpen: boolean;
  onClose: () => void;
  onSelectSource: (id: string) => void;
}

export const SourcesDrawer: React.FC<SourcesDrawerProps> = ({
  sources,
  activeSourceId,
  isOpen,
  onClose,
  onSelectSource,
}) => {
  if (!isOpen || sources.length === 0) return null;

  const currentSource = sources.find((s) => s.id === activeSourceId) || sources[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/40 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-white rounded-xl shadow-2xl border border-stone-200 w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-5 py-3.5 border-b border-stone-200 flex items-center justify-between bg-[#FBF9F5]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-lenny-600"></span>
            <h3 className="font-semibold text-stone-900 text-sm">
              Grounded Sources ({sources.length})
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-stone-400 hover:text-stone-700 hover:bg-stone-200/50 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Source Selector Tabs */}
        <div className="flex items-center gap-1.5 px-4 py-2 border-b border-stone-100 bg-stone-50/50 overflow-x-auto">
          {sources.map((s) => {
            const isSelected = s.id === (currentSource?.id);
            return (
              <button
                key={s.id}
                onClick={() => onSelectSource(s.id)}
                className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                  isSelected
                    ? 'bg-lenny-600 text-white shadow-sm'
                    : 'bg-stone-200/70 text-stone-700 hover:bg-stone-300/70'
                }`}
              >
                [{s.id}] {s.guest}
              </button>
            );
          })}
        </div>

        {/* Content Body */}
        {currentSource && (
          <div className="p-6 overflow-y-auto space-y-5">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-lenny-700 mb-1">
                <span>Citation [{currentSource.id}]</span>
                {currentSource.start_ts && (
                  <span className="text-stone-400">· Timestamp {currentSource.start_ts}</span>
                )}
              </div>
              <h2 className="text-base font-bold text-stone-900 leading-snug">
                {currentSource.title}
              </h2>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-stone-600 bg-stone-50 p-3 rounded-lg border border-stone-200/60">
              <div className="flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-stone-400" />
                <span className="font-medium text-stone-800">{currentSource.guest}</span>
              </div>
              {currentSource.publish_date && (
                <div className="flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-stone-400" />
                  <span>{currentSource.publish_date}</span>
                </div>
              )}
              {currentSource.start_ts && (
                <div className="flex items-center gap-1.5">
                  <Film className="w-3.5 h-3.5 text-stone-400" />
                  <span>At {currentSource.start_ts}</span>
                </div>
              )}
            </div>

            {/* Transcript Snippet Quote */}
            <div>
              <div className="text-xs font-medium text-stone-500 mb-2">Transcript Excerpt:</div>
              <blockquote className="text-xs md:text-sm text-stone-800 bg-[#FBF9F5] p-4 rounded-lg border-l-4 border-lenny-500 font-serif leading-relaxed italic whitespace-pre-wrap">
                "{currentSource.snippet}"
              </blockquote>
            </div>

            {/* Deep Link Action */}
            {currentSource.youtube_deep_link || currentSource.youtube_url ? (
              <div className="pt-2 flex justify-end">
                <a
                  href={currentSource.youtube_deep_link || currentSource.youtube_url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-medium shadow-sm transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Watch on YouTube {currentSource.start_ts ? `at ${currentSource.start_ts}` : ''}</span>
                </a>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
};
