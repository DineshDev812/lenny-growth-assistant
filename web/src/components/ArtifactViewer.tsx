import React, { useState } from 'react';
import { X, Copy, Check, Code, Eye, ShieldCheck, FileText, Sparkles } from 'lucide-react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { Artifact } from '../types';

interface ArtifactViewerProps {
  artifact: Artifact | null;
  isOpen: boolean;
  onClose: () => void;
}

export const ArtifactViewer: React.FC<ArtifactViewerProps> = ({ artifact, isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'preview' | 'code'>('preview');
  const [copied, setCopied] = useState(false);

  if (!isOpen || !artifact) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy artifact content:', err);
    }
  };

  const renderMarkdown = (content: string) => {
    const rawHtml = marked.parse(content) as string;
    const sanitized = DOMPurify.sanitize(rawHtml);
    return { __html: sanitized };
  };

  return (
    <div className="w-full md:w-[480px] lg:w-[560px] h-full flex flex-col bg-white border-l border-stone-200/90 shadow-xl z-20 transition-all duration-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-stone-200/90 flex items-center justify-between bg-[#FBF9F5]">
        <div className="flex items-center gap-2 min-w-0 pr-2">
          <div className="w-7 h-7 rounded-lg bg-lenny-100 border border-lenny-200 flex items-center justify-center text-lenny-700 flex-shrink-0">
            {artifact.format === 'markdown' ? (
              <FileText className="w-4 h-4" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
          </div>
          <div className="min-w-0">
            <h2 className="text-xs md:text-sm font-bold text-stone-900 truncate">
              {artifact.title}
            </h2>
            <div className="flex items-center gap-2 text-[10px] text-stone-500">
              <span className="uppercase font-semibold tracking-wider text-lenny-700">
                {artifact.format}
              </span>
              <span>· Generated Artifact</span>
            </div>
          </div>
        </div>

        {/* Tab Controls & Actions */}
        <div className="flex items-center gap-1.5">
          <div className="flex items-center bg-stone-100 p-0.5 rounded-lg border border-stone-200/70">
            <button
              onClick={() => setActiveTab('preview')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                activeTab === 'preview'
                  ? 'bg-white text-stone-900 shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
              title="Visual preview"
            >
              <Eye className="w-3.5 h-3.5" />
              <span>Preview</span>
            </button>
            <button
              onClick={() => setActiveTab('code')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                activeTab === 'code'
                  ? 'bg-white text-stone-900 shadow-xs'
                  : 'text-stone-600 hover:text-stone-900'
              }`}
              title="View raw source code"
            >
              <Code className="w-3.5 h-3.5" />
              <span>Source</span>
            </button>
          </div>

          <button
            onClick={handleCopy}
            className="p-1.5 text-stone-600 hover:text-stone-900 hover:bg-stone-100 rounded-lg transition-colors"
            title="Copy artifact content"
          >
            {copied ? (
              <Check className="w-4 h-4 text-emerald-600" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>

          <button
            onClick={onClose}
            className="p-1.5 text-stone-400 hover:text-stone-800 hover:bg-stone-100 rounded-lg transition-colors"
            title="Close viewer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Security callout for HTML */}
      {artifact.format === 'html' && activeTab === 'preview' && (
        <div className="px-4 py-2 bg-emerald-50/70 border-b border-emerald-100 flex items-center gap-2 text-[11px] text-emerald-800">
          <ShieldCheck className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>
            <strong>Isolated Sandbox:</strong> Sanitized server-side with <code>nh3</code> and isolated in a sandboxed iframe.
          </span>
        </div>
      )}

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-5 bg-white">
        {activeTab === 'preview' ? (
          artifact.format === 'markdown' ? (
            <div
              className="prose prose-lenny max-w-none text-xs md:text-sm"
              dangerouslySetInnerHTML={renderMarkdown(artifact.content)}
            />
          ) : (
            <div className="w-full h-full min-h-[450px] border border-stone-200 rounded-lg overflow-hidden bg-white shadow-inner">
              <iframe
                title={artifact.title}
                srcDoc={artifact.content}
                sandbox="allow-scripts"
                className="w-full h-full min-h-[450px] border-none"
              />
            </div>
          )
        ) : (
          <pre className="text-[11px] font-mono p-4 bg-stone-900 text-stone-100 rounded-lg overflow-x-auto whitespace-pre-wrap leading-relaxed">
            {artifact.content}
          </pre>
        )}
      </div>
    </div>
  );
};
