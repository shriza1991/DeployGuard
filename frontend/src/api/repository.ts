import { repoContextClient } from './http';

export interface RepoStatusResponse {
  status: 'indexed' | 'indexing' | 'failed' | 'not_indexed';
  branch: string;
  error?: string;
  last_indexed_at?: string;
}

export interface RepoManifestResponse {
  repository: string;
  branch: string;
  size_bytes?: number;
  lines_of_code?: number;
  file_count?: number;
  service_count?: number;
  test_count?: number;
  config_count?: number;
  docker_images?: string[];
  terraform_modules?: string[];
  helm_charts?: string[];
  frameworks?: string[];
  dependency_graph?: Record<string, string[]>;
  architecture_summary?: Record<string, any>;
  last_indexed_at?: string;
}

export interface SearchHit {
  id: string;
  score: number;
  ranking_score: number;
  retrieval_reason: string;
  payload: {
    relative_path: string;
    filename: string;
    directory: string;
    kind: string;
    text: string;
    language: string;
    start_line: number;
    end_line: number;
  };
}

export interface SearchResponse {
  results: SearchHit[];
  query: string;
  repository: string;
  branch: string;
}

export interface RepoStatsResponse {
  repository: string;
  branch: string;
  number_of_files: number;
  number_of_chunks: number;
  lines_of_code: number;
  detected_languages: string[];
  test_count: number;
  configuration_count: number;
  number_of_services: number;
  repository_size_bytes: number;
  docker_images: string[];
  terraform_modules: string[];
  helm_charts: string[];
}

export async function getRepositoryStatus(
  repository: string,
  branch: string = 'main'
): Promise<RepoStatusResponse> {
  const normRepo = repository.split('/').pop() ?? repository;
  const { data } = await repoContextClient.get<RepoStatusResponse>(
    `/repository/status/${encodeURIComponent(normRepo)}`,
    { params: { branch } }
  );
  return data;
}

export async function getRepositoryManifest(
  repository: string,
  branch: string = 'main'
): Promise<RepoManifestResponse> {
  const normRepo = repository.split('/').pop() ?? repository;
  const { data } = await repoContextClient.get<RepoManifestResponse>(
    `/repository/manifest/${encodeURIComponent(normRepo)}`,
    { params: { branch } }
  );
  return data;
}

export async function getRepositoryStats(
  repository: string,
  branch: string = 'main'
): Promise<RepoStatsResponse> {
  const normRepo = repository.split('/').pop() ?? repository;
  const { data } = await repoContextClient.get<RepoStatsResponse>(
    `/repository/stats/${encodeURIComponent(normRepo)}`,
    { params: { branch } }
  );
  return data;
}

function normalizeSearchHit(rawHit: any, index: number): SearchHit {
  const metadata = rawHit?.metadata ?? {};
  const payloadSrc = rawHit?.payload ?? metadata;

  const relativePath = payloadSrc?.relative_path ?? metadata?.relative_path ?? '';
  const filename =
    payloadSrc?.filename ??
    metadata?.filename ??
    (relativePath ? relativePath.split('/').pop() ?? '' : 'Untitled');
  const directory = payloadSrc?.directory ?? metadata?.directory ?? '';
  const kind = payloadSrc?.kind ?? metadata?.kind ?? 'source';
  const text = rawHit?.text ?? payloadSrc?.text ?? metadata?.text ?? '';
  const language = payloadSrc?.language ?? metadata?.language ?? 'unknown';
  const startLine = payloadSrc?.start_line ?? metadata?.start_line ?? 0;
  const endLine = payloadSrc?.end_line ?? metadata?.end_line ?? 0;

  const id =
    rawHit?.id ??
    (relativePath
      ? `${relativePath}:${startLine}-${endLine}:${index}`
      : `chunk-${index}`);
  const score = typeof rawHit?.score === 'number' ? rawHit.score : 0.0;
  const rankingScore =
    typeof rawHit?.ranking_score === 'number' ? rawHit.ranking_score : score;
  const retrievalReason =
    rawHit?.retrieval_reason ?? rawHit?.reason_for_match ?? 'Semantic Similarity';

  return {
    id,
    score,
    ranking_score: rankingScore,
    retrieval_reason: retrievalReason,
    payload: {
      relative_path: relativePath,
      filename,
      directory,
      kind,
      text,
      language,
      start_line: startLine,
      end_line: endLine,
    },
  };
}

export async function searchRepository(
  repository: string,
  query: string,
  branch: string = 'main',
  top_k: number = 5
): Promise<SearchResponse> {
  const normRepo = repository.split('/').pop() ?? repository;
  const { data } = await repoContextClient.post<any>(
    '/repository/search',
    { repository: normRepo, query, branch, top_k }
  );

  const rawResults: any[] = Array.isArray(data?.results) ? data.results : [];
  const normalizedResults: SearchHit[] = rawResults.map((hit, idx) =>
    normalizeSearchHit(hit, idx)
  );

  return {
    results: normalizedResults,
    query: data?.query ?? query,
    repository: data?.repository ?? repository,
    branch: data?.branch ?? branch,
  };
}

