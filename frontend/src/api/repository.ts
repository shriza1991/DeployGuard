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

export async function searchRepository(
  repository: string,
  query: string,
  branch: string = 'main',
  top_k: number = 5
): Promise<SearchResponse> {
  const normRepo = repository.split('/').pop() ?? repository;
  const { data } = await repoContextClient.post<SearchResponse>(
    '/repository/search',
    { repository: normRepo, query, branch, top_k }
  );
  return data;
}
