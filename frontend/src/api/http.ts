import axios, { type AxiosInstance } from 'axios';

const gatewayBaseUrl =
  import.meta.env.VITE_GATEWAY_API_URL ?? '/api/gateway';

const aggregatorBaseUrl =
  import.meta.env.VITE_AGGREGATOR_API_URL ?? '/api/aggregator';

const incidentHistoryBaseUrl =
  import.meta.env.VITE_INCIDENT_HISTORY_API_URL ?? '/api/incident-history';

export const gatewayClient: AxiosInstance = axios.create({
  baseURL: gatewayBaseUrl,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

export const aggregatorClient: AxiosInstance = axios.create({
  baseURL: aggregatorBaseUrl,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

/** Optional proxy to incident-history agent health (not exposed in docker-compose today). */
export const incidentHistoryClient: AxiosInstance = axios.create({
  baseURL: incidentHistoryBaseUrl,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
});
