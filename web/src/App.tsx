import React, { useState, useEffect, useRef } from 'react';
import { ArrowDown } from 'lucide-react';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { ChatMessage } from './components/ChatMessage';
import { ChatInput } from './components/ChatInput';
import { EmptyState } from './components/EmptyState';
import { ArtifactViewer } from './components/ArtifactViewer';
import { SourcesDrawer } from './components/SourcesDrawer';
import { api } from './api/client';
import { Session, Message, MetaResponse, Artifact, ArtifactSummary, Source } from './types';

export const App: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Dark mode
  const [darkMode, setDarkMode] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('lenny_dark_mode');
      if (stored !== null) return stored === 'true';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  });

  // Artifact Viewer state
  const [activeArtifact, setActiveArtifact] = useState<Artifact | null>(null);
  const [artifactViewerOpen, setArtifactViewerOpen] = useState(false);

  // Sources Drawer state
  const [activeSources, setActiveSources] = useState<Source[]>([]);
  const [activeSourceId, setActiveSourceId] = useState<string | null>(null);
  const [sourcesDrawerOpen, setSourcesDrawerOpen] = useState(false);

  // Scroll state
  const [showScrollBottom, setShowScrollBottom] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Sync dark mode class with HTML element
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('lenny_dark_mode', String(darkMode));
  }, [darkMode]);

  const handleToggleDarkMode = () => {
    setDarkMode((prev) => !prev);
  };

  // Auto-scroll to bottom
  const scrollToBottom = (smooth = true) => {
    messagesEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
  };

  useEffect(() => {
    if (!showScrollBottom) {
      scrollToBottom(false);
    }
  }, [messages, showScrollBottom]);

  // Monitor scroll position to show floating scroll button
  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    setShowScrollBottom(distanceFromBottom > 160);
  };

  // Global Keyboard Shortcuts (Cmd+K / Ctrl+K and Esc)
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        handleNewSession();
      } else if (e.key === 'Escape') {
        if (artifactViewerOpen) setArtifactViewerOpen(false);
        if (sourcesDrawerOpen) setSourcesDrawerOpen(false);
        if (sidebarOpen) setSidebarOpen(false);
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, [artifactViewerOpen, sourcesDrawerOpen, sidebarOpen, isStreaming]);

  // Initial load: Meta and Sessions
  useEffect(() => {
    async function init() {
      try {
        const metaRes = await api.getMeta();
        setMeta(metaRes);
      } catch (err) {
        console.error('Failed to load system meta:', err);
      }

      try {
        const sessionList = await api.listSessions();
        setSessions(sessionList);
        if (sessionList.length > 0) {
          loadSession(sessionList[0].id);
        } else {
          // Create initial session
          const newSess = await api.createSession();
          setSessions([newSess]);
          setActiveSessionId(newSess.id);
          setMessages([]);
        }
      } catch (err) {
        console.error('Failed to load sessions:', err);
      }
    }

    init();
  }, []);

  const loadSession = async (id: string) => {
    try {
      setActiveSessionId(id);
      const detail = await api.getSession(id);
      setMessages(detail.messages || []);
      // Close artifact viewer if opened from another session
      setArtifactViewerOpen(false);
      setActiveArtifact(null);
    } catch (err) {
      console.error(`Failed to load session ${id}:`, err);
    }
  };

  const handleNewSession = async () => {
    if (isStreaming) {
      handleStopStreaming();
    }
    try {
      const created = await api.createSession();
      setSessions((prev) => [created, ...prev]);
      setActiveSessionId(created.id);
      setMessages([]);
      setArtifactViewerOpen(false);
      setActiveArtifact(null);
    } catch (err) {
      console.error('Failed to create new session:', err);
    }
  };

  const handleRenameSession = async (id: string, newTitle: string) => {
    try {
      const updated = await api.renameSession(id, newTitle);
      setSessions((prev) =>
        prev.map((s) => (s.id === id ? { ...s, title: updated.title } : s))
      );
    } catch (err) {
      console.error('Failed to rename session:', err);
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await api.deleteSession(id);
      const updated = sessions.filter((s) => s.id !== id);
      setSessions(updated);

      if (activeSessionId === id) {
        if (updated.length > 0) {
          loadSession(updated[0].id);
        } else {
          const fresh = await api.createSession();
          setSessions([fresh]);
          setActiveSessionId(fresh.id);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error(`Failed to delete session ${id}:`, err);
    }
  };

  const handleOpenArtifact = async (summary: ArtifactSummary) => {
    try {
      const fullArt = await api.getArtifact(summary.id);
      setActiveArtifact(fullArt);
      setArtifactViewerOpen(true);
    } catch (err) {
      console.error('Failed to load artifact:', err);
    }
  };

  const handleOpenSource = (sourceId: string) => {
    const allSources = messages.flatMap((m) => m.sources || []);
    const unique = Array.from(new Map(allSources.map((s) => [s.id, s])).values());
    setActiveSources(unique);
    setActiveSourceId(sourceId);
    setSourcesDrawerOpen(true);
  };

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
  };

  const handleSendMessage = async (
    content: string,
    intent?: 'qa' | 'essay' | 'artifact' | null,
    artifactFormat?: 'markdown' | 'html' | null
  ) => {
    let currentSessionId = activeSessionId;

    if (!currentSessionId) {
      const created = await api.createSession();
      setSessions([created]);
      currentSessionId = created.id;
      setActiveSessionId(currentSessionId);
    }

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      session_id: currentSessionId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    const tempAssistantId = `asst-${Date.now()}`;
    const initialAssistantMsg: Message = {
      id: tempAssistantId,
      session_id: currentSessionId,
      role: 'assistant',
      content: '',
      sources: [],
      provider: meta?.provider,
      model: meta?.model,
      intent,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg, initialAssistantMsg]);
    setIsStreaming(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await api.streamMessage(
        currentSessionId,
        { content, intent, artifact_format: artifactFormat },
        {
          onStart: (data) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? {
                      ...m,
                      provider: data.provider || m.provider,
                      model: data.model || m.model,
                      intent: (data.intent as any) || m.intent,
                    }
                  : m
              )
            );
          },
          onSources: (sources) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId ? { ...m, sources } : m
              )
            );
          },
          onToken: (token) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? { ...m, content: m.content + token }
                  : m
              )
            );
          },
          onArtifact: async (artSummary) => {
            try {
              const fullArt = await api.getArtifact(artSummary.id);
              setActiveArtifact(fullArt);
              setArtifactViewerOpen(true);
            } catch (err) {
              console.error('Error fetching artifact on SSE event:', err);
            }
          },
          onError: (err) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === tempAssistantId
                  ? {
                      ...m,
                      error_class: err.code,
                      content:
                        m.content ||
                        `An error occurred: ${err.message}. Please verify provider settings.`,
                    }
                  : m
              )
            );
          },
          onDone: (doneData) => {
            const asst = doneData.assistant_message;
            setMessages((prev) =>
              prev.map((m) =>
                m && m.id === tempAssistantId
                  ? {
                      ...m,
                      id: asst?.id || doneData.message_id || m.id,
                      content: asst?.content || m.content || '',
                      sources:
                        asst?.sources && asst.sources.length > 0
                          ? asst.sources
                          : doneData.sources && doneData.sources.length > 0
                            ? doneData.sources
                            : m.sources || [],
                      error_class: asst?.error_class ?? doneData.error_class ?? m.error_class ?? null,
                      artifact: asst?.artifact || doneData.artifact || m.artifact || null,
                    }
                  : m
              ).filter(Boolean)
            );
            const artId = doneData.artifact?.id || asst?.artifact?.id;
            if (artId) {
              api.getArtifact(artId).then((fullArt) => {
                setActiveArtifact(fullArt);
                setArtifactViewerOpen(true);
              }).catch(console.error);
            }
            setIsStreaming(false);
            abortControllerRef.current = null;
            api.listSessions().then(setSessions).catch(console.error);
          },
        },
        controller.signal
      );
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        console.error('Streaming failed:', err);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === tempAssistantId
              ? {
                  ...m,
                  error_class: err.code || 'stream_error',
                  content:
                    m.content ||
                    `Error generating response: ${err.message || 'Connection lost'}`,
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#FBF9F5] dark:bg-stone-950 text-stone-900 dark:text-stone-100 transition-colors">
      {/* Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={loadSession}
        onNewSession={handleNewSession}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Chat + Artifact View Container */}
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden relative">
        <Header
          meta={meta}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          darkMode={darkMode}
          onToggleDarkMode={handleToggleDarkMode}
          onNewChat={handleNewSession}
        />

        {meta && meta.episodes_loaded === 0 && (
          <div className="bg-amber-50 dark:bg-amber-950/40 border-b border-amber-200 dark:border-amber-800/60 px-4 py-2 text-xs text-amber-800 dark:text-amber-300 flex items-center justify-between">
            <span>No transcripts loaded yet. See README: Get the transcripts.</span>
            <span className="text-[11px] opacity-75">Corpus: 0 episodes</span>
          </div>
        )}

        {/* Content Area (Split Pane when Artifact is Open) */}
        <div className="flex-1 flex min-h-0 overflow-hidden relative">
          {/* Messages Pane */}
          <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden relative">
            <div
              ref={scrollContainerRef}
              onScroll={handleScroll}
              className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4"
            >
              {messages.length === 0 ? (
                <EmptyState onSelectPrompt={handleSendMessage} />
              ) : (
                <div className="max-w-4xl mx-auto w-full">
                  {messages.filter(Boolean).map((message, idx) => {
                    const isLastMessage = idx === messages.length - 1;
                    return (
                      <ChatMessage
                        key={message.id}
                        message={message}
                        isStreaming={isStreaming && isLastMessage && message.role === 'assistant'}
                        onOpenSource={handleOpenSource}
                        onOpenArtifact={handleOpenArtifact}
                      />
                    );
                  })}
                  {isStreaming && (
                    <div className="flex items-center gap-2 text-xs text-stone-400 dark:text-stone-500 py-2">
                      <span className="w-2 h-2 rounded-full bg-lenny-600 dark:bg-lenny-400 animate-ping" />
                      <span>Grounded reasoning in progress...</span>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            {/* Floating Scroll to Bottom Button */}
            {showScrollBottom && (
              <button
                onClick={() => scrollToBottom(true)}
                className="absolute bottom-24 right-6 z-20 p-2.5 rounded-full bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 shadow-lg hover:scale-105 active:scale-95 transition-all flex items-center justify-center opacity-90 hover:opacity-100"
                title="Scroll to latest message"
              >
                <ArrowDown className="w-4 h-4" />
              </button>
            )}

            {/* Input Bar */}
            <ChatInput
              onSendMessage={handleSendMessage}
              onStopStreaming={handleStopStreaming}
              isStreaming={isStreaming}
            />
          </div>

          {/* Artifact Viewer Side Pane */}
          {artifactViewerOpen && activeArtifact && (
            <ArtifactViewer
              artifact={activeArtifact}
              isOpen={artifactViewerOpen}
              onClose={() => setArtifactViewerOpen(false)}
            />
          )}
        </div>
      </div>

      {/* Sources Drawer Modal */}
      <SourcesDrawer
        sources={activeSources}
        activeSourceId={activeSourceId}
        isOpen={sourcesDrawerOpen}
        onClose={() => setSourcesDrawerOpen(false)}
        onSelectSource={setActiveSourceId}
      />
    </div>
  );
};
