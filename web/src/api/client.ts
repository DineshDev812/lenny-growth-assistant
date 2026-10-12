import { Artifact, ArtifactSummary, MetaResponse, Session, Source, Message } from '../types';

export class ApiError extends Error {
  code: string;
  requestId?: string;

  constructor(message: string, code: string = 'internal_error', requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.requestId = requestId;
  }
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    },
  });

  if (!res.ok) {
    let errMsg = `Request failed with status ${res.status}`;
    let errCode = 'http_error';
    let reqId = res.headers.get('x-request-id') || undefined;

    try {
      const data = await res.json();
      if (data?.error) {
        errMsg = data.error.message || errMsg;
        errCode = data.error.code || errCode;
        reqId = data.error.request_id || reqId;
      }
    } catch {
      // not JSON
    }

    throw new ApiError(errMsg, errCode, reqId);
  }

  return (await res.json()) as T;
}

export const api = {
  async getMeta(): Promise<MetaResponse> {
    return request<MetaResponse>('/api/meta');
  },

  async listSessions(): Promise<Session[]> {
    return request<Session[]>('/api/sessions');
  },

  async createSession(title?: string): Promise<Session> {
    return request<Session>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify(title ? { title } : {}),
    });
  },

  async getSession(id: string): Promise<Session> {
    return request<Session>(`/api/sessions/${id}`);
  },

  async renameSession(id: string, title: string): Promise<Session> {
    return request<Session>(`/api/sessions/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    });
  },

  async deleteSession(id: string): Promise<void> {
    const res = await fetch(`/api/sessions/${id}`, {
      method: 'DELETE',
      credentials: 'include',
    });
    if (!res.ok) {
      throw new ApiError(`Failed to delete session (status ${res.status})`, 'delete_failed');
    }
  },

  async getArtifact(id: string): Promise<Artifact> {
    return request<Artifact>(`/api/artifacts/${id}`);
  },

  async streamMessage(
    sessionId: string,
    payload: {
      content: string;
      intent?: 'qa' | 'essay' | 'artifact' | 'general' | null;
      artifact_format?: 'markdown' | 'html' | null;
    },
    callbacks: {
      onStart?: (data: { user_message_id: string; intent?: string; route?: string; provider?: string; model?: string }) => void;
      onSources?: (sources: Source[]) => void;
      onToken?: (token: string) => void;
      onArtifact?: (art: { id: string; format: 'markdown' | 'html'; title: string }) => void;
      onError?: (err: { code: string; message: string; request_id?: string; retryable?: boolean }) => void;
      onDone?: (doneData: {
        message_id?: string;
        intent?: string;
        route?: string;
        sources?: Source[];
        actions?: any[];
        artifact?: ArtifactSummary | null;
        error_class?: string | null;
        assistant_message?: Message;
      }) => void;
    },
    signal?: AbortSignal
  ): Promise<void> {
    const res = await fetch(`/api/sessions/${sessionId}/messages`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!res.ok) {
      let errMsg = `Streaming request failed with status ${res.status}`;
      let errCode = 'http_error';
      let reqId = res.headers.get('x-request-id') || undefined;
      try {
        const data = await res.json();
        if (data?.error) {
          errMsg = data.error.message || errMsg;
          errCode = data.error.code || errCode;
          reqId = data.error.request_id || reqId;
        }
      } catch {
        // ignore
      }
      throw new ApiError(errMsg, errCode, reqId);
    }

    const reader = res.body?.getReader();
    if (!reader) {
      throw new Error('Response body has no readable stream');
    }

    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    const processBlock = (block: string) => {
      if (!block.trim()) return;
      let eventType = 'message';
      const dataLines: string[] = [];

      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) {
          eventType = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trim());
        }
      }

      if (dataLines.length === 0) return;
      const eventData = dataLines.join('\n');

      try {
        const parsed = JSON.parse(eventData);
        if (eventType === 'start') {
          callbacks.onStart?.(parsed);
        } else if (eventType === 'sources') {
          callbacks.onSources?.(parsed.sources || []);
        } else if (eventType === 'token') {
          callbacks.onToken?.(parsed.text || '');
        } else if (eventType === 'artifact') {
          callbacks.onArtifact?.(parsed);
        } else if (eventType === 'error') {
          callbacks.onError?.({
            code: parsed.error?.code || 'internal_error',
            message: parsed.error?.message || 'Unknown error occurred',
            request_id: parsed.error?.request_id,
            retryable: parsed.retryable,
          });
        } else if (eventType === 'done') {
          callbacks.onDone?.(parsed);
        }
      } catch (e) {
        console.warn('Failed to parse SSE JSON block:', block, e);
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        if (buffer.trim()) {
          processBlock(buffer);
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const normalized = buffer.replace(/\r\n/g, '\n');
      const blocks = normalized.split('\n\n');
      buffer = blocks.pop() || '';

      for (const block of blocks) {
        processBlock(block);
      }
    }
  },
};
