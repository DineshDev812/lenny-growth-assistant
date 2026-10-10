import React, { useState, useRef, useEffect } from 'react';
import { Send, Square, Sparkles, HelpCircle, FileText, Code } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (
    content: string,
    intent?: 'qa' | 'essay' | 'artifact' | null,
    artifactFormat?: 'markdown' | 'html' | null
  ) => void;
  onStopStreaming: () => void;
  isStreaming: boolean;
  disabled?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  onStopStreaming,
  isStreaming,
  disabled,
}) => {
  const [content, setContent] = useState('');
  const [intent, setIntent] = useState<'qa' | 'essay' | 'artifact' | null>(null);
  const [artifactFormat, setArtifactFormat] = useState<'markdown' | 'html' | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [content]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!content.trim() || isStreaming || disabled) return;

    onSendMessage(content.trim(), intent, artifactFormat);
    setContent('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const selectIntent = (newIntent: 'qa' | 'essay' | 'artifact' | null) => {
    setIntent(newIntent);
    if (newIntent === 'essay') {
      setArtifactFormat('markdown');
    } else if (newIntent === 'artifact') {
      setArtifactFormat('html');
    } else {
      setArtifactFormat(null);
    }
  };

  return (
    <div className="border-t border-stone-200/90 bg-[#FBF9F5]/90 backdrop-blur-md p-3 md:p-4 sticky bottom-0 z-10">
      <div className="max-w-4xl mx-auto space-y-2.5">
        {/* Intent Pills Selector */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
          <span className="text-[11px] font-semibold text-stone-400 uppercase tracking-wider pl-1 pr-1">
            Intent:
          </span>
          <button
            type="button"
            onClick={() => selectIntent(null)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs transition-colors ${
              intent === null
                ? 'bg-stone-900 text-white font-medium shadow-xs'
                : 'bg-stone-100 hover:bg-stone-200 text-stone-600'
            }`}
          >
            <Sparkles className="w-3 h-3" />
            <span>Auto Detect</span>
          </button>

          <button
            type="button"
            onClick={() => selectIntent('qa')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs transition-colors ${
              intent === 'qa'
                ? 'bg-lenny-600 text-white font-medium shadow-xs'
                : 'bg-stone-100 hover:bg-stone-200 text-stone-600'
            }`}
          >
            <HelpCircle className="w-3 h-3" />
            <span>Grounded Q&A</span>
          </button>

          <button
            type="button"
            onClick={() => selectIntent('essay')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs transition-colors ${
              intent === 'essay'
                ? 'bg-lenny-600 text-white font-medium shadow-xs'
                : 'bg-stone-100 hover:bg-stone-200 text-stone-600'
            }`}
          >
            <FileText className="w-3 h-3" />
            <span>Ship 30 Essay</span>
          </button>

          <button
            type="button"
            onClick={() => selectIntent('artifact')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs transition-colors ${
              intent === 'artifact'
                ? 'bg-lenny-600 text-white font-medium shadow-xs'
                : 'bg-stone-100 hover:bg-stone-200 text-stone-600'
            }`}
          >
            <Code className="w-3 h-3" />
            <span>Interactive HTML</span>
          </button>
        </div>

        {/* Input Textarea Container */}
        <form onSubmit={handleSubmit} className="relative flex items-end bg-white border border-stone-300 rounded-xl shadow-xs focus-within:border-lenny-500 focus-within:ring-2 focus-within:ring-lenny-500/20 transition-all">
          <textarea
            ref={textareaRef}
            rows={1}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              intent === 'essay'
                ? 'Topic for Ship 30 for 30 essay (e.g. activation loops, retention playbook)...'
                : intent === 'artifact'
                ? 'Request an interactive HTML widget or visual tool...'
                : 'Ask Lenny anything about growth, PMF, hiring, or product strategy...'
            }
            disabled={disabled}
            className="w-full resize-none py-3 px-3.5 pr-14 text-xs md:text-sm bg-transparent focus:outline-none placeholder:text-stone-400 text-stone-900 max-h-48"
          />

          <div className="absolute right-2 bottom-2">
            {isStreaming ? (
              <button
                type="button"
                onClick={onStopStreaming}
                className="p-2 rounded-lg bg-stone-900 hover:bg-stone-800 text-white transition-colors"
                title="Stop streaming"
              >
                <Square className="w-4 h-4 fill-current" />
              </button>
            ) : (
              <button
                type="submit"
                disabled={!content.trim() || disabled}
                className="p-2 rounded-lg bg-lenny-600 hover:bg-lenny-700 disabled:opacity-40 disabled:hover:bg-lenny-600 text-white transition-colors shadow-2xs"
                title="Send message (Enter)"
              >
                <Send className="w-4 h-4" />
              </button>
            )}
          </div>
        </form>

        <div className="flex items-center justify-between text-[11px] text-stone-400 px-1">
          <span>Answers strictly grounded in 300+ Lenny's Podcast transcripts.</span>
          <span className="hidden sm:inline">Press Shift + Enter for new line</span>
        </div>
      </div>
    </div>
  );
};
