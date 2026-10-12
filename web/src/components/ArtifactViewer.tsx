import React, { useState } from 'react';
import { X, Copy, Check, Code, Eye, ShieldCheck, FileText, Sparkles, Download, Maximize2, Minimize2 } from 'lucide-react';
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
  const [isFullscreen, setIsFullscreen] = useState(false);

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

  const handleDownload = () => {
    const ext = artifact.format === 'markdown' ? 'md' : 'html';
    const mime = artifact.format === 'markdown' ? 'text/markdown' : 'text/html';
    const filename = `${artifact.title.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'artifact'}.${ext}`;

    const blob = new Blob([artifact.content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderMarkdown = (content: string) => {
    const rawHtml = marked.parse(content) as string;
    const sanitized = DOMPurify.sanitize(rawHtml);
    return { __html: sanitized };
  };

  const prepareSandboxedHtml = (content: string) => {
    const cspMeta = `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src https: ; style-src 'unsafe-inline';">`;
    if (content.includes('<head>')) {
      return content.replace('<head>', `<head>${cspMeta}`);
    }
    if (content.includes('<html>')) {
      return content.replace('<html>', `<html><head>${cspMeta}</head>`);
    }
    return `<!DOCTYPE html><html><head>${cspMeta}</head><body>${content}</body></html>`;
  };

  const containerClasses = isFullscreen
    ? 'fixed inset-0 z-50 flex flex-col bg-white dark:bg-stone-900 animate-in fade-in zoom-in-95 duration-150'
    : 'w-full md:w-[480px] lg:w-[580px] xl:w-[640px] h-full flex flex-col bg-white dark:bg-stone-900 border-l border-stone-200/90 dark:border-stone-800 shadow-xl z-20 transition-all duration-200';

  return (
    <div className={containerClasses}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-stone-200/90 dark:border-stone-800 flex items-center justify-between bg-[#FBF9F5] dark:bg-stone-900">
        <div className="flex items-center gap-2 min-w-0 pr-2">
          <div className="w-7 h-7 rounded-lg bg-lenny-100 dark:bg-lenny-950 border border-lenny-200 dark:border-lenny-800 flex items-center justify-center text-lenny-700 dark:text-lenny-400 flex-shrink-0">
            {artifact.format === 'markdown' ? (
              <FileText className="w-4 h-4" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
          </div>
          <div className="min-w-0">
            <h2 className="text-xs md:text-sm font-bold text-stone-900 dark:text-stone-100 truncate">
              {artifact.title}
            </h2>
            <div className="flex items-center gap-2 text-[10px] text-stone-500 dark:text-stone-400">
              <span className="uppercase font-semibold tracking-wider text-lenny-700 dark:text-lenny-400">
                {artifact.format}
              </span>
              <span>· Generated Artifact</span>
            </div>
          </div>
        </div>

        {/* Tab Controls & Actions */}
        <div className="flex items-center gap-1">
          {/* Tab buttons */}
          <div className="flex items-center bg-stone-100 dark:bg-stone-800 p-0.5 rounded-lg border border-stone-200/70 dark:border-stone-700">
            <button
              onClick={() => setActiveTab('preview')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                activeTab === 'preview'
                  ? 'bg-white dark:bg-stone-700 text-stone-900 dark:text-stone-100 shadow-2xs'
                  : 'text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-200'
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
                  ? 'bg-white dark:bg-stone-700 text-stone-900 dark:text-stone-100 shadow-2xs'
                  : 'text-stone-600 dark:text-stone-400 hover:text-stone-900 dark:hover:text-stone-200'
              }`}
              title="View source code"
            >
              <Code className="w-3.5 h-3.5" />
              <span>Source</span>
            </button>
          </div>

          {/* Copy button */}
          <button
            onClick={handleCopy}
            className="p-1.5 text-stone-600 dark:text-stone-300 hover:text-stone-900 dark:hover:text-stone-100 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-lg transition-colors"
            title="Copy content"
          >
            {copied ? (
              <Check className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>

          {/* Download button */}
          <button
            onClick={handleDownload}
            className="p-1.5 text-stone-600 dark:text-stone-300 hover:text-stone-900 dark:hover:text-stone-100 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-lg transition-colors"
            title={`Download as .${artifact.format === 'markdown' ? 'md' : 'html'}`}
          >
            <Download className="w-4 h-4" />
          </button>

          {/* Fullscreen toggle */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 text-stone-600 dark:text-stone-300 hover:text-stone-900 dark:hover:text-stone-100 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-lg transition-colors hidden sm:block"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          {/* Close button */}
          <button
            onClick={onClose}
            className="p-1.5 text-stone-400 hover:text-stone-800 dark:hover:text-stone-200 hover:bg-stone-100 dark:hover:bg-stone-800 rounded-lg transition-colors ml-0.5"
            title="Close artifact viewer (Esc)"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Security callout for HTML */}
      {artifact.format === 'html' && activeTab === 'preview' && (
        <div className="px-4 py-2 bg-emerald-50/70 dark:bg-emerald-950/40 border-b border-emerald-100 dark:border-emerald-900/40 flex items-center gap-2 text-[11px] text-emerald-800 dark:text-emerald-300">
          <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 flex-shrink-0" />
          <span>
            <strong>Isolated Sandbox:</strong> Sanitized with <code>nh3</code>, restricted CSP, and enclosed in an empty <code>sandbox=&quot;&quot;</code> iframe.
          </span>
        </div>
      )}

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-5 bg-white dark:bg-stone-900">
        {activeTab === 'preview' ? (
          artifact.format === 'markdown' ? (
            <div
              className="prose prose-lenny max-w-none text-xs md:text-sm"
              dangerouslySetInnerHTML={renderMarkdown(artifact.content)}
            />
          ) : (
            <div className="w-full h-full min-h-[480px] border border-stone-200 dark:border-stone-800 rounded-lg overflow-hidden bg-white shadow-inner">
              <iframe
                title={artifact.title}
                srcDoc={prepareSandboxedHtml(artifact.content)}
                sandbox=""
                className="w-full h-full min-h-[480px] border-none"
              />
            </div>
          )
        ) : (
          <pre className="text-[11px] font-mono p-4 bg-stone-900 dark:bg-stone-950 text-stone-100 rounded-lg overflow-x-auto whitespace-pre-wrap leading-relaxed border border-stone-800">
            {artifact.content}
          </pre>
        )}
      </div>
    </div>
  );
};
