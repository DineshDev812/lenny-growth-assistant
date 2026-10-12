export interface Source {
  id: string; // e.g. "S1", "S2"
  chunk_id: string;
  episode_id: string;
  slug: string;
  title: string;
  guest: string;
  publish_date: string | null;
  youtube_url: string | null;
  youtube_deep_link: string | null;
  start_ts: string | null;
  start_seconds: number | null;
  snippet: string;
}

export interface ArtifactSummary {
  id: string;
  format: 'markdown' | 'html';
  title: string;
}

export interface Artifact {
  id: string;
  session_id: string;
  message_id: string;
  format: 'markdown' | 'html';
  title: string;
  content: string;
  created_at: string;
}

export interface Message {
  id: string;
  session_id: string;
  seq?: number;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  provider?: string | null;
  model?: string | null;
  intent?: 'qa' | 'essay' | 'artifact' | null;
  error_class?: string | null;
  artifact?: ArtifactSummary | null;
  created_at: string;
}

export interface Session {
  id: string;
  title: string;
  user_metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface MetaResponse {
  app_name: string;
  provider: string;
  model: string;
  fallback_provider: string | null;
  provider_status: 'ok' | 'unconfigured' | 'unavailable' | 'unknown';
  episodes_loaded?: number;
  chunks_loaded?: number;
}

export interface HealthResponse {
  status: string;
  db: string;
  provider: string;
  model: string;
  provider_status: 'ok' | 'unconfigured' | 'unavailable' | 'unknown';
}
