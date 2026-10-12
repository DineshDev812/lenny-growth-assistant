import React, { useState } from 'react';
import { Mic, User, ExternalLink, Sparkles, AlertTriangle, Copy, Check } from 'lucide-react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { Message, Source, ArtifactSummary } from '../types';

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
  onOpenSource: (sourceId: string) => void;
  onOpenArtifact: (artifact: ArtifactSummary) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  isStreaming,
  onOpenSource,
  onOpenArtifact,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  // Process markdown and make [S1], [S2] citations clickable badges
  const renderContent = (content: string) => {
    // Replace citation tags [S1], [S2] with html badges
    const processed = content.replace(/\[S(\d+)\]/gi, (_, num) => {
      const tag = `S${num}`;
      return `<button data-citation="${tag}" class="citation-btn inline-flex items-center px-1.5 py-0.2 mx-0.5 rounded text-[11px] font-bold bg-lenny-100 dark:bg-lenny-950 hover:bg-lenny-200 dark:hover:bg-lenny-900 text-lenny-800 dark:text-lenny-300 border border-lenny-300 dark:border-lenny-800 transition-colors cursor-pointer">[${tag}]</button>`;
    });

    const rawHtml = marked.parse(processed) as string;
    const sanitized = DOMPurify.sanitize(rawHtml, {
      ADD_TAGS: ['button'],
      ADD_ATTR: ['data-citation', 'class'],
    });

    return { __html: sanitized };
  };

  const handleContentClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement;
    const btn = target.closest('button[data-citation]');
    if (btn) {
      const citationId = btn.getAttribute('data-citation');
      if (citationId) {
        onOpenSource(citationId);
      }
    }
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-5">
        <div className="flex items-start gap-2.5 max-w-[85%] md:max-w-[75%] flex-row-reverse">
          <div className="w-8 h-8 rounded-full bg-stone-300 dark:bg-stone-700 text-stone-700 dark:text-stone-200 flex items-center justify-center flex-shrink-0 shadow-2xs">
            <User className="w-4 h-4" />
          </div>
          <div className="bg-stone-900 dark:bg-stone-800 text-stone-50 px-4 py-3 rounded-2xl rounded-tr-sm text-xs md:text-sm shadow-xs whitespace-pre-wrap leading-relaxed border border-stone-800 dark:border-stone-700">
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  // Assistant Message
  return (
    <div className="flex justify-start mb-6 group">
      <div className="flex items-start gap-3 max-w-[95%] md:max-w-[88%] w-full">
        <div className="w-8 h-8 rounded-full bg-lenny-600 dark:bg-lenny-700 text-white flex items-center justify-center flex-shrink-0 shadow-sm mt-0.5">
          <Mic className="w-4 h-4" />
        </div>

        <div className="flex-1 min-w-0">
          {/* Metadata bar */}
          <div className="flex items-center justify-between mb-1.5 text-[11px] text-stone-500 dark:text-stone-400">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-stone-800 dark:text-stone-200">
                Lenny Growth Assistant
              </span>
              {message.provider && (
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 border border-stone-200 dark:border-stone-700">
                  {message.provider} {message.model ? `· ${message.model}` : ''}
                </span>
              )}
              {message.intent && (
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-lenny-50 dark:bg-lenny-950/70 text-lenny-800 dark:text-lenny-300 border border-lenny-200 dark:border-lenny-800 font-medium uppercase tracking-wider">
                  {message.intent}
                </span>
              )}
            </div>

            <button
              onClick={handleCopy}
              className="opacity-0 group-hover:opacity-100 flex items-center gap-1 text-[11px] text-stone-400 hover:text-stone-700 dark:hover:text-stone-200 transition-opacity p-1 rounded"
              title="Copy answer"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-600" />
                  <span className="text-emerald-600">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>

          {/* Message Content Bubble */}
          <div className="bg-white dark:bg-stone-900 border border-stone-200/90 dark:border-stone-800 rounded-2xl rounded-tl-sm p-4 md:p-5 shadow-2xs transition-colors">
            {message.error_class ? (
              <div className="mb-3 p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 rounded-lg flex items-start gap-2 text-rose-800 dark:text-rose-300 text-xs">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-600 dark:text-rose-400 mt-0.5" />
                <div>
                  <strong className="font-semibold block">Notice:</strong>
                  {message.content}
                </div>
              </div>
            ) : (
              <div className="relative">
                <div
                  className="prose prose-lenny max-w-none text-xs md:text-sm"
                  dangerouslySetInnerHTML={renderContent(message.content)}
                  onClick={handleContentClick}
                />
                {isStreaming && <span className="streaming-caret" />}
              </div>
            )}

            {/* Artifact Trigger Banner (if created) */}
            {message.artifact && (
              <div className="mt-4 pt-3 border-t border-stone-100 dark:border-stone-800">
                <div
                  onClick={() => message.artifact && onOpenArtifact(message.artifact)}
                  className="flex items-center justify-between p-3 bg-lenny-50 dark:bg-lenny-950/40 hover:bg-lenny-100/80 dark:hover:bg-lenny-900/40 border border-lenny-200 dark:border-lenny-800/80 rounded-xl cursor-pointer transition-all hover:shadow-2xs group/art"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-lenny-600 dark:bg-lenny-700 text-white flex items-center justify-center flex-shrink-0 group-hover/art:scale-105 transition-transform">
                      <Sparkles className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-lenny-700 dark:text-lenny-400">
                        {message.artifact.format === 'markdown' ? 'Ship 30 Essay' : 'Interactive Artifact'}
                      </div>
                      <div className="text-xs font-bold text-stone-900 dark:text-stone-100 truncate">
                        {message.artifact.title}
                      </div>
                    </div>
                  </div>
                  <button className="px-2.5 py-1 bg-white dark:bg-stone-800 hover:bg-lenny-600 hover:text-white dark:hover:bg-lenny-600 text-stone-800 dark:text-stone-200 text-[11px] font-medium rounded-lg border border-lenny-200 dark:border-stone-700 shadow-2xs transition-colors">
                    View Artifact →
                  </button>
                </div>
              </div>
            )}

            {/* Grounded Citations Bar */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-stone-100 dark:border-stone-800">
                <div className="text-[10px] font-semibold text-stone-500 dark:text-stone-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <span>Cited Sources ({message.sources.length})</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {message.sources.map((src: Source) => (
                    <button
                      key={src.id}
                      onClick={() => onOpenSource(src.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium bg-[#FBF9F5] dark:bg-stone-800/80 hover:bg-lenny-100 dark:hover:bg-stone-700 text-stone-800 dark:text-stone-200 border border-stone-200/80 dark:border-stone-700 transition-colors group/src"
                      title={`${src.title} (${src.guest})`}
                    >
                      <span className="font-bold text-lenny-700 dark:text-lenny-400">[{src.id}]</span>
                      <span className="truncate max-w-[140px] md:max-w-[200px]">{src.guest}</span>
                      {src.youtube_deep_link && (
                        <ExternalLink className="w-2.5 h-2.5 text-stone-400 dark:text-stone-500 group-hover/src:text-lenny-700 dark:group-hover/src:text-lenny-400" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
