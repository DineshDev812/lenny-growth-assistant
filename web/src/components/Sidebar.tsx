import React, { useState } from 'react';
import { Plus, MessageSquare, Edit2, Check, X, Sparkles } from 'lucide-react';
import { Session } from '../types';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onRenameSession: (id: string, newTitle: string) => Promise<void>;
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onRenameSession,
  isOpen,
  onClose,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const startRename = (session: Session, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(session.id);
    setEditTitle(session.title);
  };

  const handleRenameSubmit = async (id: string, e: React.FormEvent) => {
    e.preventDefault();
    if (editTitle.trim()) {
      await onRenameSession(id, editTitle.trim());
    }
    setEditingId(null);
  };

  const cancelRename = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingId(null);
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-stone-900/30 backdrop-blur-sm z-30 md:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-72 bg-[#F6F2EB] border-r border-stone-200/80 flex flex-col transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Top actions */}
        <div className="p-3 border-b border-stone-200/80 flex items-center gap-2">
          <button
            onClick={() => {
              onNewSession();
              if (window.innerWidth < 768) onClose();
            }}
            className="flex-1 flex items-center justify-center gap-2 py-2 px-3 bg-lenny-600 hover:bg-lenny-700 text-white rounded-lg font-medium text-xs shadow-sm transition-all active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
          </button>
          <button
            onClick={onClose}
            className="p-2 text-stone-500 hover:text-stone-800 rounded-lg md:hidden"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <div className="px-2 py-1.5 text-[11px] font-semibold tracking-wider text-stone-400 uppercase">
            Conversations
          </div>

          {sessions.length === 0 ? (
            <div className="text-center py-8 px-4 text-xs text-stone-400">
              No conversations yet.<br />Click "New Chat" to begin.
            </div>
          ) : (
            sessions.map((session) => {
              const isActive = session.id === activeSessionId;
              const isEditing = session.id === editingId;

              if (isEditing) {
                return (
                  <form
                    key={session.id}
                    onSubmit={(e) => handleRenameSubmit(session.id, e)}
                    className="flex items-center gap-1 p-1 bg-white rounded-lg border border-lenny-400 shadow-sm"
                  >
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      autoFocus
                      className="flex-1 text-xs px-2 py-1 bg-transparent focus:outline-none text-stone-800"
                    />
                    <button
                      type="submit"
                      className="p-1 text-emerald-600 hover:bg-emerald-50 rounded"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={cancelRename}
                      className="p-1 text-stone-400 hover:bg-stone-100 rounded"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </form>
                );
              }

              return (
                <div
                  key={session.id}
                  onClick={() => {
                    onSelectSession(session.id);
                    if (window.innerWidth < 768) onClose();
                  }}
                  className={`group relative flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-colors ${
                    isActive
                      ? 'bg-stone-200/70 text-stone-900 font-medium shadow-[inset_0_1px_2px_rgba(0,0,0,0.03)]'
                      : 'text-stone-600 hover:bg-stone-200/40 hover:text-stone-900'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0 pr-2">
                    <MessageSquare className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? 'text-lenny-600' : 'text-stone-400'}`} />
                    <span className="truncate">{session.title}</span>
                  </div>

                  <button
                    onClick={(e) => startRename(session, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-stone-400 hover:text-stone-700 hover:bg-stone-300/40 rounded transition-opacity"
                    title="Rename session"
                  >
                    <Edit2 className="w-3 h-3" />
                  </button>
                </div>
              );
            })
          )}
        </div>

        {/* Footer info */}
        <div className="p-3 border-t border-stone-200/80 bg-stone-100/50 text-[11px] text-stone-500 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-lenny-800 font-medium">
            <Sparkles className="w-3.5 h-3.5 text-lenny-600" />
            <span>Lenny's Growth Agent</span>
          </div>
          <span className="text-[10px] text-stone-400 font-mono">v1.0</span>
        </div>
      </aside>
    </>
  );
};
