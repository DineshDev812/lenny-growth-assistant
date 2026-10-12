import React, { useState } from 'react';
import { Plus, MessageSquare, Edit2, Trash2, Check, X, Sparkles, AlertTriangle } from 'lucide-react';
import { Session } from '../types';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onRenameSession: (id: string, newTitle: string) => Promise<void>;
  onDeleteSession: (id: string) => Promise<void>;
  isOpen: boolean;
  onClose: () => void;
}

function groupSessionsByDate(sessions: Session[]): { label: string; items: Session[] }[] {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterdayStart = todayStart - 86400000;
  const weekStart = todayStart - 6 * 86400000;

  const today: Session[] = [];
  const yesterday: Session[] = [];
  const previous7Days: Session[] = [];
  const older: Session[] = [];

  for (const session of sessions) {
    const sessionTime = new Date(session.updated_at || session.created_at).getTime();
    if (sessionTime >= todayStart) {
      today.push(session);
    } else if (sessionTime >= yesterdayStart) {
      yesterday.push(session);
    } else if (sessionTime >= weekStart) {
      previous7Days.push(session);
    } else {
      older.push(session);
    }
  }

  const groups: { label: string; items: Session[] }[] = [];
  if (today.length > 0) groups.push({ label: 'Today', items: today });
  if (yesterday.length > 0) groups.push({ label: 'Yesterday', items: yesterday });
  if (previous7Days.length > 0) groups.push({ label: 'Previous 7 Days', items: previous7Days });
  if (older.length > 0) groups.push({ label: 'Older', items: older });

  return groups;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewSession,
  onRenameSession,
  onDeleteSession,
  isOpen,
  onClose,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

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

  const handleDeleteConfirm = async () => {
    if (!confirmDeleteId) return;
    try {
      setIsDeleting(true);
      await onDeleteSession(confirmDeleteId);
    } catch (err) {
      console.error('Failed to delete session:', err);
    } finally {
      setIsDeleting(false);
      setConfirmDeleteId(null);
    }
  };

  const grouped = groupSessionsByDate(sessions);
  const isMac = typeof window !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;
  const shortcutLabel = isMac ? '⌘K' : 'Ctrl+K';

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-stone-900/40 backdrop-blur-sm z-30 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Delete Confirmation Modal */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-stone-900/50 backdrop-blur-xs animate-in fade-in duration-100">
          <div className="bg-white dark:bg-stone-900 rounded-xl shadow-2xl border border-stone-200 dark:border-stone-800 p-5 max-w-sm w-full">
            <div className="flex items-center gap-3 mb-3 text-rose-600 dark:text-rose-400">
              <div className="w-9 h-9 rounded-lg bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900/40 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h4 className="font-semibold text-stone-900 dark:text-stone-100 text-sm">
                  Delete conversation?
                </h4>
                <p className="text-xs text-stone-500 dark:text-stone-400">
                  This action cannot be undone.
                </p>
              </div>
            </div>
            <p className="text-xs text-stone-600 dark:text-stone-300 mb-5 leading-relaxed">
              All messages, grounded citations, and generated artifacts in this chat will be permanently removed.
            </p>
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirmDeleteId(null)}
                disabled={isDeleting}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-stone-600 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-rose-600 hover:bg-rose-700 text-white shadow-sm transition-colors disabled:opacity-50"
              >
                {isDeleting ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-72 bg-[#F6F2EB] dark:bg-stone-900 border-r border-stone-200/80 dark:border-stone-800 flex flex-col transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        {/* Top actions */}
        <div className="p-3 border-b border-stone-200/80 dark:border-stone-800 flex items-center gap-2">
          <button
            onClick={() => {
              onNewSession();
              if (window.innerWidth < 768) onClose();
            }}
            className="flex-1 flex items-center justify-between py-2 px-3 bg-lenny-600 hover:bg-lenny-700 text-white rounded-lg font-medium text-xs shadow-sm transition-all active:scale-[0.98] group"
          >
            <div className="flex items-center gap-2">
              <Plus className="w-4 h-4" />
              <span>New Chat</span>
            </div>
            <kbd className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-lenny-700/60 text-lenny-100 border border-lenny-500/40 opacity-80 group-hover:opacity-100">
              {shortcutLabel}
            </kbd>
          </button>
          <button
            onClick={onClose}
            className="p-2 text-stone-500 dark:text-stone-400 hover:text-stone-800 dark:hover:text-stone-200 rounded-lg md:hidden"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-4">
          {sessions.length === 0 ? (
            <div className="text-center py-12 px-4 text-xs text-stone-400 dark:text-stone-500">
              No conversations yet.<br />Click "New Chat" to begin.
            </div>
          ) : (
            grouped.map((group) => (
              <div key={group.label} className="space-y-1">
                <div className="px-2 py-1 text-[10px] font-bold tracking-wider text-stone-400 dark:text-stone-500 uppercase">
                  {group.label}
                </div>

                {group.items.map((session) => {
                  const isActive = session.id === activeSessionId;
                  const isEditing = session.id === editingId;

                  if (isEditing) {
                    return (
                      <form
                        key={session.id}
                        onSubmit={(e) => handleRenameSubmit(session.id, e)}
                        className="flex items-center gap-1 p-1 bg-white dark:bg-stone-800 rounded-lg border border-lenny-400 dark:border-lenny-500 shadow-sm"
                      >
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          autoFocus
                          className="flex-1 text-xs px-2 py-1 bg-transparent focus:outline-none text-stone-900 dark:text-stone-100"
                        />
                        <button
                          type="submit"
                          className="p-1 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-stone-700 rounded"
                          title="Save title"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={cancelRename}
                          className="p-1 text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-700 rounded"
                          title="Cancel"
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
                      className={`group relative flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition-colors ${
                        isActive
                          ? 'bg-stone-200/80 dark:bg-stone-800 text-stone-900 dark:text-stone-100 font-medium shadow-[inset_0_1px_2px_rgba(0,0,0,0.04)]'
                          : 'text-stone-600 dark:text-stone-400 hover:bg-stone-200/50 dark:hover:bg-stone-800/60 hover:text-stone-900 dark:hover:text-stone-200'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 min-w-0 pr-2">
                        <MessageSquare
                          className={`w-3.5 h-3.5 flex-shrink-0 ${
                            isActive
                              ? 'text-lenny-600 dark:text-lenny-400'
                              : 'text-stone-400 dark:text-stone-500'
                          }`}
                        />
                        <span className="truncate">{session.title}</span>
                      </div>

                      <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                        <button
                          onClick={(e) => startRename(session, e)}
                          className="p-1 text-stone-400 hover:text-stone-700 dark:hover:text-stone-200 hover:bg-stone-300/40 dark:hover:bg-stone-700/60 rounded"
                          title="Rename conversation"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmDeleteId(session.id);
                          }}
                          className="p-1 text-stone-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-100/50 dark:hover:bg-rose-950/40 rounded"
                          title="Delete conversation"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Footer info */}
        <div className="p-3 border-t border-stone-200/80 dark:border-stone-800 bg-stone-100/50 dark:bg-stone-900/60 text-[11px] text-stone-500 dark:text-stone-400 flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-lenny-800 dark:text-lenny-300 font-medium">
            <Sparkles className="w-3.5 h-3.5 text-lenny-600 dark:text-lenny-400" />
            <span>Lenny's Growth Agent</span>
          </div>
          <span className="text-[10px] text-stone-400 dark:text-stone-500 font-mono">v1.2</span>
        </div>
      </aside>
    </>
  );
};
