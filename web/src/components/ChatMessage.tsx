import React from 'react';
import { Mic, User, ExternalLink, Sparkles, AlertTriangle } from 'lucide-react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { Message, Source, ArtifactSummary } from '../types';

interface ChatMessageProps {
  message: Message;
  onOpenSource: (sourceId: string) => void;
  onOpenArtifact: (artifact: ArtifactSummary) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onOpenSource,
  onOpenArtifact,
}) => {
  const isUser = message.role === 'user';

  // Process markdown and make [S1], [S2] citations clickable badges
  const renderContent = (content: string) => {
    // Replace citation tags [S1], [S2] with html badges
    const processed = content.replace(/\[S(\d+)\]/g, (match, num) => {
      return `<button data-citation="S${num}" class="citation-btn inline-flex items-center px-1.5 py-0.2 mx-0.5 rounded text-[11px] font-bold bg-lenny-100 hover:bg-lenny-200 text-lenny-800 border border-lenny-300 transition-colors cursor-pointer">${match}</button>`;
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
          <div className="w-8 h-8 rounded-full bg-stone-300 text-stone-700 flex items-center justify-center flex-shrink-0 shadow-xs">
            <User className="w-4 h-4" />
          </div>
          <div className="bg-stone-900 text-stone-50 px-4 py-3 rounded-2xl rounded-tr-sm text-xs md:text-sm shadow-sm whitespace-pre-wrap leading-relaxed">
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  // Assistant Message
  return (
    <div className="flex justify-start mb-6">
      <div className="flex items-start gap-3 max-w-[95%] md:max-w-[88%] w-full">
        <div className="w-8 h-8 rounded-full bg-lenny-600 text-white flex items-center justify-center flex-shrink-0 shadow-sm mt-0.5">
          <Mic className="w-4 h-4" />
        </div>

        <div className="flex-1 min-w-0">
          {/* Metadata bar */}
          <div className="flex items-center gap-2 mb-1 text-[11px] text-stone-500">
            <span className="font-semibold text-stone-800">Lenny Growth Assistant</span>
            {message.provider && (
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-stone-100 border border-stone-200">
                {message.provider} {message.model ? `· ${message.model}` : ''}
              </span>
            )}
            {message.intent && (
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-lenny-50 text-lenny-800 border border-lenny-200 font-medium uppercase tracking-wider">
                {message.intent}
              </span>
            )}
          </div>

          {/* Message Content Bubble */}
          <div className="bg-white border border-stone-200/90 rounded-2xl rounded-tl-sm p-4 md:p-5 shadow-xs">
            {message.error_class ? (
              <div className="mb-3 p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-start gap-2 text-rose-800 text-xs">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 text-rose-600 mt-0.5" />
                <div>
                  <strong className="font-semibold block">Generation notice:</strong>
                  {message.content}
                </div>
              </div>
            ) : (
              <div
                className="prose prose-lenny max-w-none text-xs md:text-sm"
                dangerouslySetInnerHTML={renderContent(message.content)}
                onClick={handleContentClick}
              />
            )}

            {/* Artifact Trigger Banner (if created) */}
            {message.artifact && (
              <div className="mt-4 pt-3 border-t border-stone-100">
                <div
                  onClick={() => message.artifact && onOpenArtifact(message.artifact)}
                  className="flex items-center justify-between p-3 bg-lenny-50 hover:bg-lenny-100/80 border border-lenny-200 rounded-xl cursor-pointer transition-all hover:shadow-xs group"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-lenny-600 text-white flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
                      <Sparkles className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-lenny-700">
                        {message.artifact.format === 'markdown' ? 'Ship 30 Essay' : 'Interactive Artifact'}
                      </div>
                      <div className="text-xs font-bold text-stone-900 truncate">
                        {message.artifact.title}
                      </div>
                    </div>
                  </div>
                  <button className="px-2.5 py-1 bg-white hover:bg-lenny-600 hover:text-white text-stone-800 text-[11px] font-medium rounded-lg border border-lenny-200 shadow-2xs transition-colors">
                    View Artifact →
                  </button>
                </div>
              </div>
            )}

            {/* Grounded Citations Bar */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-4 pt-3 border-t border-stone-100">
                <div className="text-[11px] font-semibold text-stone-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <span>Cited Transcript Sources ({message.sources.length})</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {message.sources.map((src: Source) => (
                    <button
                      key={src.id}
                      onClick={() => onOpenSource(src.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium bg-[#FBF9F5] hover:bg-lenny-100 text-stone-800 border border-stone-200/80 transition-colors group"
                      title={`${src.title} (${src.guest})`}
                    >
                      <span className="font-bold text-lenny-700">[{src.id}]</span>
                      <span className="truncate max-w-[140px] md:max-w-[200px]">{src.guest}</span>
                      {src.youtube_deep_link && (
                        <ExternalLink className="w-2.5 h-2.5 text-stone-400 group-hover:text-lenny-700" />
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
