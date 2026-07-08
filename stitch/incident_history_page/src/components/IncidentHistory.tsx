/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import { 
  History, 
  Search, 
  Plus, 
  AlertTriangle, 
  AlertCircle, 
  Info, 
  Clock, 
  FileCode, 
  Package, 
  CloudOff, 
  Sparkles, 
  ChevronDown, 
  ExternalLink, 
  Printer, 
  Check, 
  CheckCircle2, 
  ChevronLeft, 
  ChevronRight, 
  X, 
  Terminal, 
  TrendingUp, 
  FilterX
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

// --- TYPES ---
export type Severity = 'CRIT' | 'HIGH' | 'MED' | 'LOW';
export type IncidentStatus = 'BLOCKED' | 'MITIGATED' | 'RESOLVED';

export interface LinkedDeployment {
  id: string;
  triggeredBy: string;
}

export interface Incident {
  id: string;
  title: string;
  severity: Severity;
  status: IncidentStatus;
  timestamp: string; // ISO format
  repository: string;
  version: string;
  similarity: number; // 0-100 percentage
  aiSummary: string;
  vulnerabilityType: string;
  detectedPattern: string;
  mitigationActions: string[];
  linkedDeployment?: LinkedDeployment;
  affectedClusters: string[];
  rollbackRequired: boolean;
}

// --- INITIAL INCIDENTS MOCK DATA ---
const INITIAL_INCIDENTS: Incident[] = [
  {
    id: 'INC-001',
    title: 'Hardcoded Stripe API Secret in payment-gateway',
    severity: 'CRIT',
    status: 'BLOCKED',
    timestamp: '2023-10-12T14:22:00Z',
    repository: 'payment-gateway',
    version: 'v.1.4.2-alpha',
    similarity: 94,
    aiSummary: 'The deployment for payment-gateway@v.1.4.2 was automatically intercepted by the Secret-Scan Agent. A live production Stripe API key was detected in config/env.production.ts line 42. This pattern matches existing historical data for "Secret Leakage" incidents with 94% confidence. Deployment was halted immediately to prevent key exposure.',
    vulnerabilityType: 'Secret Exposure (CWE-798)',
    detectedPattern: 'sk_live_*************************',
    mitigationActions: [
      'Rotate the Stripe API key immediately via the Stripe Dashboard.',
      'Purge commit 7a2e81f from the repository history.',
      'Inject secrets via Vault/Environment Variables instead of local config files.'
    ],
    linkedDeployment: {
      id: 'DEP-0092841',
      triggeredBy: '@jenkins-bot'
    },
    affectedClusters: ['us-east-1', 'eu-west-3', 'asia-south-2'],
    rollbackRequired: true
  },
  {
    id: 'INC-002',
    title: 'Unexpected Outbound Traffic from auth-service',
    severity: 'HIGH',
    status: 'MITIGATED',
    timestamp: '2023-10-11T09:15:00Z',
    repository: 'auth-service',
    version: 'auth-svc-prod',
    similarity: 42,
    aiSummary: 'A sudden traffic spike of 4.2 GB was detected originating from the auth-service container towards an unrecognized external IP address (198.51.100.12). This anomaly was flagged by our Network Anomaly Detection agent with 42% similarity to historical C2 beaconing. The egress filter automatically restricted the traffic rate to avoid further potential data exfiltration.',
    vulnerabilityType: 'Unusual Egress Volume / Potential C2 (CWE-319)',
    detectedPattern: 'Outbound egress spike -> IP 198.51.100.12 (Port 443)',
    mitigationActions: [
      'Verify if the external IP is a newly introduced legitimate OAuth provider or endpoint.',
      'Quarantine the affected auth-service replica pod to perform forensic traffic analysis.',
      'Apply updated egress network policy rules to restrict unwhitelisted outbound connections.'
    ],
    linkedDeployment: {
      id: 'DEP-0083104',
      triggeredBy: '@deploy-bot'
    },
    affectedClusters: ['us-east-1', 'us-west-2'],
    rollbackRequired: false
  },
  {
    id: 'INC-003',
    title: 'Dependency Vulnerability: axios v0.21.1',
    severity: 'MED',
    status: 'RESOLVED',
    timestamp: '2023-10-10T11:05:00Z',
    repository: 'analytics-dashboard',
    version: 'analytics-dashboard-v3',
    similarity: 88,
    aiSummary: 'Static application security testing (SAST) flagged a high-severity Server-Side Request Forgery (SSRF) vulnerability in axios v0.21.1 (CVE-2020-28168). This vulnerability allows attackers to bypass server SSRF mitigations via specially crafted headers. This aligns with standard dependency drift with 88% structural risk similarity.',
    vulnerabilityType: 'Server-Side Request Forgery (CVE-2020-28168)',
    detectedPattern: 'axios@0.21.1 package.json dependency',
    mitigationActions: [
      'Upgrade axios package to version 0.21.2 or higher in package.json.',
      'Run npm audit fix --force to resolve sub-dependency nested vulnerabilities.',
      'Configure egress API gateways to reject host headers resolving to internal metadata services.'
    ],
    linkedDeployment: {
      id: 'DEP-0075193',
      triggeredBy: '@github-actions'
    },
    affectedClusters: ['eu-west-3'],
    rollbackRequired: false
  },
  {
    id: 'INC-004',
    title: 'Mass Resource Deletion Triggered in dev-cluster-01',
    severity: 'CRIT',
    status: 'BLOCKED',
    timestamp: '2023-10-08T23:45:00Z',
    repository: 'Terraform Cloud',
    version: 'tf-plan-main',
    similarity: 12,
    aiSummary: 'An automated Terraform execution plan attempted to destroy 14 active security groups, 3 database subnets, and 2 VPC peering connections. The automated pipeline was blocked by the safety sentinel because the resource destruction count exceeded the 5% threshold limits of total environment state.',
    vulnerabilityType: 'Excessive Resource Destruction (CWE-285)',
    detectedPattern: 'tf-plan: -14 Security Groups, -3 Subnets',
    mitigationActions: [
      'Audit the active git branch for unintentional configuration overrides or state loss.',
      'Require senior engineer approvals for any plan that deletes core infrastructure.',
      'Ensure backend Terraform state is synchronized and locked to prevent race conditions.'
    ],
    linkedDeployment: {
      id: 'DEP-0062489',
      triggeredBy: '@lead-ops'
    },
    affectedClusters: ['asia-south-2'],
    rollbackRequired: true
  },
  {
    id: 'INC-005',
    title: 'Kubernetes API Server Bruteforce Attack',
    severity: 'HIGH',
    status: 'MITIGATED',
    timestamp: '2023-10-06T18:30:00Z',
    repository: 'kube-api-gateway',
    version: 'k8s-core-v1.27',
    similarity: 79,
    aiSummary: 'A flood of over 15,000 authentication failure logs was recorded on the master Kubernetes API server within 2 minutes. The anomaly resembles past brute-forcing campaigns with 79% fingerprint similarity. Automated IP rate limiting has blacklisted the attacking CIDR block at the Edge Cloud Armor firewall.',
    vulnerabilityType: 'Credential Stuffing / Bruteforce (CWE-307)',
    detectedPattern: '15k+ consecutive 401 Unauthorized API requests',
    mitigationActions: [
      'Disable public-facing access to the Kubernetes API server; restrict to VPN CIDR.',
      'Enforce multi-factor webhook authentication or client certificate rotation.',
      'Review IAM roles assigned to service accounts to verify minimal privilege compliance.'
    ],
    linkedDeployment: {
      id: 'DEP-0051280',
      triggeredBy: '@system-monitor'
    },
    affectedClusters: ['us-east-1', 'asia-south-2'],
    rollbackRequired: false
  },
  {
    id: 'INC-006',
    title: 'Docker Base Image Malware Signature Detected',
    severity: 'CRIT',
    status: 'BLOCKED',
    timestamp: '2023-10-04T08:12:00Z',
    repository: 'notification-service',
    version: 'docker-alpine-node18',
    similarity: 91,
    aiSummary: 'Trivy container image scanning detected a malicious binary signature matching "XMRig Monero Miner" embedded inside a nested base layer of a public docker hub image. The build process was immediately halted and the container image was deleted from the local artifact registry.',
    vulnerabilityType: 'Supply Chain Compromise (CWE-912)',
    detectedPattern: 'sha256:7f9c... (Malicious Monero Miner Signature)',
    mitigationActions: [
      'Switch base image to an officially vetted, private, minimal distroless image.',
      'Verify source repository commits of public upstream container suppliers.',
      'Establish a strict registry pull-through proxy with mandatory vulnerability gates.'
    ],
    linkedDeployment: {
      id: 'DEP-0043194',
      triggeredBy: '@circleci-agent'
    },
    affectedClusters: ['eu-west-3'],
    rollbackRequired: true
  },
  {
    id: 'INC-007',
    title: 'Leaked SSH Private Key in deployment config',
    severity: 'MED',
    status: 'RESOLVED',
    timestamp: '2023-10-01T10:00:00Z',
    repository: 'billing-system',
    version: 'v.2.1.0-release',
    similarity: 85,
    aiSummary: 'An unencrypted PEM-formatted private SSH key was found inside an environment variables payload in production configurations. Scan Agent flagged this with 85% structural similarity to previous secret-leak patterns. The credentials have been blacklisted and rotated automatically inside AWS Secrets Manager.',
    vulnerabilityType: 'Plaintext Storage of Secrets (CWE-522)',
    detectedPattern: '-----BEGIN OPENSSH PRIVATE KEY-----',
    mitigationActions: [
      'Deactivate the leaked key from all target servers and remove authorized_keys entry.',
      'Regenerate active SSH keypair and store exclusively within AWS Secrets Manager or Vault.',
      'Enable automated config scanning inside local git pre-commit hooks.'
    ],
    linkedDeployment: {
      id: 'DEP-0031945',
      triggeredBy: '@github-actions'
    },
    affectedClusters: ['us-east-1'],
    rollbackRequired: false
  }
];

export interface IncidentHistoryProps {
  initialIncidents?: Incident[];
  onExportReport?: (incident: Incident) => void;
}

export default function IncidentHistory({ initialIncidents, onExportReport }: IncidentHistoryProps) {
  // --- States ---
  const [incidents, setIncidents] = useState<Incident[]>(initialIncidents || INITIAL_INCIDENTS);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set(['INC-001'])); // Pre-expand the first one like mockup
  
  // Search & Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [repoFilter, setRepoFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('All Severities');
  const [dateRangeFilter, setDateRangeFilter] = useState('Last 30 Days');
  const [similarityThreshold, setSimilarityThreshold] = useState(0); 
  const [showStats, setShowStats] = useState(true); 

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 4;

  // Manual Report Form Modal
  const [showReportModal, setShowReportModal] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' } | null>(null);

  // New Incident Form State
  const [newTitle, setNewTitle] = useState('');
  const [newRepo, setNewRepo] = useState('');
  const [newSeverity, setNewSeverity] = useState<Severity>('HIGH');
  const [newStatus, setNewStatus] = useState<IncidentStatus>('BLOCKED');
  const [newVersion, setNewVersion] = useState('v1.0.0');
  const [newAiSummary, setNewAiSummary] = useState('');
  const [newVulnType, setNewVulnType] = useState('Secret Exposure (CWE-798)');
  const [newPattern, setNewPattern] = useState('sk_live_*******************');
  const [newClusters, setNewClusters] = useState('us-east-1, eu-west-3');
  const [newMitigation, setNewMitigation] = useState('Rotate credentials immediately.');

  // Trigger brief toast alerts
  const triggerToast = (message: string, type: 'success' | 'info' = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  // Toggle Single Incident Card Expand state
  const toggleIncident = (id: string) => {
    const newExpanded = new Set(expandedIds);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedIds(newExpanded);
  };

  // Reset Filters to defaults
  const resetFilters = () => {
    setSearchQuery('');
    setRepoFilter('');
    setSeverityFilter('All Severities');
    setDateRangeFilter('Last 30 Days');
    setSimilarityThreshold(0);
    setCurrentPage(1);
    triggerToast('All filters have been reset.', 'info');
  };

  // --- Filter and Search logic ---
  const filteredIncidents = useMemo(() => {
    return incidents.filter((incident) => {
      const query = searchQuery.toLowerCase();
      const matchesSearch = 
        !query ||
        incident.title.toLowerCase().includes(query) ||
        incident.repository.toLowerCase().includes(query) ||
        incident.vulnerabilityType.toLowerCase().includes(query) ||
        incident.aiSummary.toLowerCase().includes(query);

      const matchesRepo = 
        !repoFilter || 
        incident.repository.toLowerCase().includes(repoFilter.toLowerCase());

      const matchesSeverity = 
        severityFilter === 'All Severities' || 
        (severityFilter === 'Critical' && incident.severity === 'CRIT') ||
        (severityFilter === 'High' && incident.severity === 'HIGH') ||
        (severityFilter === 'Medium' && incident.severity === 'MED') ||
        (severityFilter === 'Low' && incident.severity === 'LOW');

      const matchesSimilarity = incident.similarity >= similarityThreshold;

      let matchesDate = true;
      if (dateRangeFilter === 'Last 24 Hours') {
        matchesDate = incident.id === 'INC-001';
      } else if (dateRangeFilter === 'Last 7 Days') {
        matchesDate = ['INC-001', 'INC-002', 'INC-003'].includes(incident.id);
      }

      return matchesSearch && matchesRepo && matchesSeverity && matchesSimilarity && matchesDate;
    });
  }, [incidents, searchQuery, repoFilter, severityFilter, similarityThreshold, dateRangeFilter]);

  // --- Pagination calculations ---
  const totalPages = Math.ceil(filteredIncidents.length / itemsPerPage) || 1;
  const paginatedIncidents = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredIncidents.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredIncidents, currentPage, itemsPerPage]);

  React.useEffect(() => {
    if (currentPage > totalPages) {
      setCurrentPage(1);
    }
  }, [totalPages, currentPage]);

  // --- Live Metrics calculations ---
  const stats = useMemo(() => {
    const total = filteredIncidents.length;
    const critCount = filteredIncidents.filter(i => i.severity === 'CRIT').length;
    const highCount = filteredIncidents.filter(i => i.severity === 'HIGH').length;
    const medCount = filteredIncidents.filter(i => i.severity === 'MED').length;
    const blockedCount = filteredIncidents.filter(i => i.status === 'BLOCKED').length;
    const averageSimilarity = total > 0 
      ? Math.round(filteredIncidents.reduce((sum, i) => sum + i.similarity, 0) / total)
      : 0;

    return { total, critCount, highCount, medCount, blockedCount, averageSimilarity };
  }, [filteredIncidents]);

  // --- Handlers ---
  const handleExportPDF = (incident: Incident, e: React.MouseEvent) => {
    e.stopPropagation();
    if (onExportReport) {
      onExportReport(incident);
      return;
    }
    
    triggerToast(`Exporting security report for ${incident.id} as PDF...`, 'success');
    
    // Simulate text report generation and client-side download
    const reportText = `
--------------------------------------------------
DEPLOYGUARD ENTERPRISE SECURITY REPORT
Incident ID: ${incident.id}
Severity: ${incident.severity}
Status: ${incident.status}
Timestamp: ${new Date(incident.timestamp).toLocaleString()}
Repository: ${incident.repository} @ ${incident.version}
--------------------------------------------------
SUMMARY:
${incident.aiSummary}

VULNERABILITY DETAILS:
Type: ${incident.vulnerabilityType}
Detected Pattern: ${incident.detectedPattern}

MITIGATION STEPS TAKEN / REQUIRED:
${incident.mitigationActions.map((act, i) => `${i + 1}. [ ] ${act}`).join('\n')}

AFFECTED CLUSTERS:
${incident.affectedClusters.join(', ')}
--------------------------------------------------
Generated by DeployGuard SecOps Intelligence Portal.
    `;
    
    const blob = new Blob([reportText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `DeployGuard-Report-${incident.id}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCreateIncident = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newRepo) {
      triggerToast('Please provide a title and repository.', 'info');
      return;
    }

    const created: Incident = {
      id: `INC-00${incidents.length + 1}`,
      title: newTitle,
      severity: newSeverity,
      status: newStatus,
      timestamp: new Date().toISOString(),
      repository: newRepo,
      version: newVersion || 'v1.0.0',
      similarity: Math.floor(Math.random() * 40) + 55, // 55% - 95%
      aiSummary: newAiSummary || `Anomalous deployment detected in ${newRepo}. Automated scanners intercepted security patterns inside container configuration files. Threat profile matched with standard indicators.`,
      vulnerabilityType: newVulnType || 'Configuration Vulnerability (CWE-16)',
      detectedPattern: newPattern || 'Matching pattern found in codebase signature',
      mitigationActions: newMitigation 
        ? newMitigation.split('\n').filter(line => line.trim().length > 0)
        : ['Perform direct credential rotation.', 'Audit deployment trigger variables.'],
      linkedDeployment: {
        id: `DEP-00${Math.floor(Math.random() * 90000) + 10000}`,
        triggeredBy: '@manual-report'
      },
      affectedClusters: newClusters.split(',').map(c => c.trim()).filter(c => c.length > 0),
      rollbackRequired: newStatus === 'BLOCKED'
    };

    setIncidents([created, ...incidents]);
    setShowReportModal(false);

    // Reset Form Fields
    setNewTitle('');
    setNewRepo('');
    setNewSeverity('HIGH');
    setNewStatus('BLOCKED');
    setNewVersion('v1.0.0');
    setNewAiSummary('');
    setNewMitigation('Rotate credentials immediately.');

    triggerToast(`Manual incident report ${created.id} generated!`, 'success');
  };

  return (
    <div className="w-full bg-[#0d0d15] text-[#e4e1ed] font-sans selection:bg-indigo-500/30 selection:text-white p-4 sm:p-6 md:p-8">
      {/* Toast Overlay */}
      <AnimatePresence>
        {toast && (
          <motion.div 
            initial={{ opacity: 0, y: -15, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -15, scale: 0.95 }}
            className="fixed top-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 bg-[#1b1b23] border-l-4 border-indigo-400 border border-[#464554] rounded-lg shadow-2xl"
          >
            <Terminal className="w-4 h-4 text-indigo-400 animate-pulse" />
            <span className="text-xs text-white font-medium">{toast.message}</span>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="max-w-7xl mx-auto space-y-6">
        {/* --- PAGE HEADER --- */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-[#464554]">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-2">
                <History className="w-7 h-7 text-[#c0c1ff]" />
                Incident History
              </h2>
              <button 
                onClick={() => setShowStats(!showStats)}
                className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#1f1f27] hover:bg-[#34343d] text-[#c7c4d7] hover:text-white border border-[#464554] transition-colors"
              >
                {showStats ? 'HIDE METRICS' : 'SHOW METRICS'}
              </button>
            </div>
            <p className="text-[#c7c4d7]/80 text-xs sm:text-sm max-w-2xl">
              Archive of security incidents and deployment anomalies across production clusters.
            </p>
          </div>
          
          <button 
            onClick={() => setShowReportModal(true)}
            className="flex items-center gap-2 bg-[#c0c1ff] hover:bg-white text-[#1000a9] font-mono text-xs font-bold px-4 py-2.5 rounded-md hover:scale-[1.02] active:scale-95 transition-all shadow-lg shadow-indigo-500/15 cursor-pointer shrink-0"
          >
            <Plus className="w-4 h-4 stroke-[3]" />
            REPORT MANUAL INCIDENT
          </button>
        </div>

        {/* --- METRICS PANEL (Timeline / Stats visualizer) --- */}
        <AnimatePresence>
          {showStats && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4 p-4 bg-[#1b1b23]/40 border border-[#464554] rounded-xl">
                <div className="space-y-1">
                  <p className="text-[10px] font-mono text-[#c7c4d7]/50 tracking-wider uppercase">Active Audited</p>
                  <p className="text-2xl font-bold font-mono text-white">{stats.total}</p>
                  <span className="text-[10px] text-[#4edea3] flex items-center gap-0.5">
                    <TrendingUp className="w-3 h-3 inline" /> 100% scoped
                  </span>
                </div>
                <div className="space-y-1 border-l border-zinc-800/80 pl-4">
                  <p className="text-[10px] font-mono text-rose-400 tracking-wider uppercase">Critical (CRIT)</p>
                  <p className="text-2xl font-bold font-mono text-rose-400">{stats.critCount}</p>
                  <span className="text-[10px] text-zinc-500 block">Needs rollback</span>
                </div>
                <div className="space-y-1 border-l border-zinc-800/80 pl-4">
                  <p className="text-[10px] font-mono text-amber-400 tracking-wider uppercase">High Severity</p>
                  <p className="text-2xl font-bold font-mono text-amber-400">{stats.highCount}</p>
                  <span className="text-[10px] text-zinc-500 block">Egress & proxy</span>
                </div>
                <div className="space-y-1 border-l border-zinc-800/80 pl-4">
                  <p className="text-[10px] font-mono text-indigo-300 tracking-wider uppercase">Medium/Low</p>
                  <p className="text-2xl font-bold font-mono text-indigo-300">{stats.medCount}</p>
                  <span className="text-[10px] text-zinc-500 block">Resolved / Normal</span>
                </div>
                <div className="space-y-1 border-l border-zinc-800/80 pl-4">
                  <p className="text-[10px] font-mono text-rose-500 tracking-wider uppercase">Halted/Blocked</p>
                  <p className="text-2xl font-bold font-mono text-rose-400">{stats.blockedCount}</p>
                  <span className="text-[10px] text-zinc-500 block">CI halted</span>
                </div>
                <div className="space-y-1 border-l border-zinc-800/80 pl-4">
                  <p className="text-[10px] font-mono text-[#c0c1ff] tracking-wider uppercase">Avg Similarity</p>
                  <div className="flex items-baseline gap-1">
                    <p className="text-2xl font-bold font-mono text-[#c0c1ff]">{stats.averageSimilarity}%</p>
                    <Sparkles className="w-3 h-3 text-[#c0c1ff] animate-pulse" />
                  </div>
                  <span className="text-[10px] text-zinc-500 block">Threat index</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* --- DYNAMIC FILTER / CONTROLS PANEL --- */}
        <div className="bg-[#1f1f27] border border-[#464554] p-4 rounded-xl space-y-4 md:space-y-0 md:flex md:flex-wrap md:gap-4 items-end">
          
          {/* Main Global Search */}
          <div className="flex-1 min-w-[200px] relative">
            <label className="block text-[10px] font-mono text-[#c7c4d7] uppercase tracking-wider mb-1">SEARCH KEYWORDS</label>
            <div className="relative group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#908fa0] w-4 h-4 group-focus-within:text-[#c0c1ff] transition-colors" />
              <input 
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg pl-10 pr-8 py-1.5 text-xs text-[#e4e1ed] placeholder-[#908fa0] focus:outline-none focus:border-[#c0c1ff] transition-colors" 
                placeholder="Search repo, hash, title, or CWE..." 
                type="text"
              />
              {searchQuery && (
                <button 
                  onClick={() => setSearchQuery('')}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 hover:bg-zinc-800 rounded-full text-[#908fa0] hover:text-white"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </div>

          {/* Repository Entity filter */}
          <div className="flex-1 min-w-[180px] relative">
            <label className="block text-[10px] font-mono text-[#c7c4d7] uppercase tracking-wider mb-1">REPOSITORY / ENTITY</label>
            <div className="relative">
              <input 
                value={repoFilter}
                onChange={(e) => {
                  setRepoFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3 py-1.5 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#c0c1ff]"
                placeholder="Filter by repo name..."
                type="text"
              />
              {repoFilter && (
                <button onClick={() => setRepoFilter('')} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-white text-xs font-mono">×</button>
              )}
            </div>
          </div>

          {/* Severity Dropdown */}
          <div className="w-full md:w-40">
            <label className="block text-[10px] font-mono text-[#c7c4d7] uppercase tracking-wider mb-1">SEVERITY</label>
            <select 
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#c0c1ff] cursor-pointer"
            >
              <option value="All Severities">All Severities</option>
              <option value="Critical">Critical (CRIT)</option>
              <option value="High">High</option>
              <option value="Medium">Medium (MED)</option>
              <option value="Low">Low (LOW)</option>
            </select>
          </div>

          {/* Date range dropdown */}
          <div className="w-full md:w-40">
            <label className="block text-[10px] font-mono text-[#c7c4d7] uppercase tracking-wider mb-1">DATE RANGE</label>
            <select 
              value={dateRangeFilter}
              onChange={(e) => {
                setDateRangeFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#c0c1ff] cursor-pointer"
            >
              <option value="All Time">All Time</option>
              <option value="Last 24 Hours">Last 24 Hours</option>
              <option value="Last 7 Days">Last 7 Days</option>
              <option value="Last 30 Days">Last 30 Days</option>
            </select>
          </div>

          {/* Similarity range slider */}
          <div className="w-full md:w-48">
            <div className="flex justify-between items-center mb-1">
              <label className="text-[10px] font-mono text-[#c7c4d7] uppercase tracking-wider">THREAT SIMILARITY</label>
              <span className="text-[10px] font-mono font-bold text-[#c0c1ff]">{similarityThreshold}%+</span>
            </div>
            <div className="flex items-center gap-3 bg-[#0d0d15] border border-[#464554] rounded-lg px-3 py-1.5 h-[34px]">
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={similarityThreshold}
                onChange={(e) => {
                  setSimilarityThreshold(Number(e.target.value));
                  setCurrentPage(1);
                }}
                className="w-full accent-[#c0c1ff] bg-zinc-800 h-1 rounded-lg appearance-none cursor-pointer"
              />
            </div>
          </div>

          {/* Reset button */}
          <div className="flex justify-end">
            <button 
              onClick={resetFilters}
              className="p-2 border border-[#464554] rounded-lg hover:bg-[#34343d] text-[#c7c4d7] hover:text-white transition-colors cursor-pointer"
              title="Reset All Filters"
            >
              <FilterX className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* --- INCIDENTS CARDS LIST --- */}
        <div className="space-y-4">
          <AnimatePresence mode="popLayout">
            {paginatedIncidents.length === 0 ? (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center p-16 bg-[#1b1b23]/20 border border-dashed border-[#464554] rounded-xl text-center"
              >
                <CloudOff className="w-12 h-12 text-[#908fa0] mb-4 stroke-[1.5]" />
                <h3 className="text-base font-bold text-white mb-1">No Incidents Found</h3>
                <p className="text-xs text-[#c7c4d7]/70 max-w-md mb-4">
                  No security anomalies match your current filters or criteria. Try adjusting the query range.
                </p>
                <button 
                  onClick={resetFilters}
                  className="px-4 py-1.5 bg-[#1b1b23] border border-[#464554] hover:bg-zinc-800 rounded font-mono text-[10px] font-semibold text-white transition-all cursor-pointer"
                >
                  RESET FILTERS
                </button>
              </motion.div>
            ) : (
              paginatedIncidents.map((incident) => {
                const isExpanded = expandedIds.has(incident.id);
                
                // Severity styling mappings
                const severityConfig = {
                  CRIT: { bg: 'bg-rose-500/10', border: 'border-rose-500/30', text: 'text-rose-400', label: 'CRIT', icon: AlertTriangle },
                  HIGH: { bg: 'bg-amber-500/10', border: 'border-amber-500/30', text: 'text-amber-400', label: 'HIGH', icon: AlertCircle },
                  MED: { bg: 'bg-indigo-500/10', border: 'border-indigo-500/30', text: 'text-indigo-400', label: 'MED', icon: Info },
                  LOW: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', label: 'LOW', icon: CheckCircle2 }
                }[incident.severity];

                // Status tag styling mappings
                const statusStyles = {
                  BLOCKED: 'bg-rose-500/10 text-rose-400 border border-rose-500/20',
                  MITIGATED: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
                  RESOLVED: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                }[incident.status];

                return (
                  <motion.div
                    layout="position"
                    key={incident.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.98 }}
                    transition={{ duration: 0.2 }}
                    className={`border border-[#464554] rounded-xl overflow-hidden transition-all duration-200 ${isExpanded ? 'bg-[#1b1b23] shadow-2xl' : 'bg-[#13131b] hover:bg-[#1f1f27]'}`}
                  >
                    {/* CARD COMPACT HEADER ROW */}
                    <div 
                      onClick={() => toggleIncident(incident.id)}
                      className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer select-none group"
                    >
                      <div className="flex items-center gap-4">
                        {/* Severity Indicator badge */}
                        <div className={`flex flex-col items-center justify-center w-12 py-1.5 rounded-lg border ${severityConfig.border} ${severityConfig.bg}`}>
                          <severityConfig.icon className={`w-4 h-4 ${severityConfig.text}`} />
                          <span className={`text-[9px] font-mono font-bold mt-1 ${severityConfig.text}`}>{severityConfig.label}</span>
                        </div>

                        {/* Title and Repository info */}
                        <div>
                          <h3 className="text-sm font-bold text-white group-hover:text-[#c0c1ff] transition-colors leading-snug">
                            {incident.title}
                          </h3>
                          <div className="flex flex-wrap items-center gap-2 mt-1 text-[11px] text-[#c7c4d7]/70 font-mono">
                            <span className="flex items-center gap-1">
                              <Clock className="w-3.5 h-3.5" />
                              {new Date(incident.timestamp).toLocaleString()}
                            </span>
                            <span className="w-1 h-1 bg-zinc-600 rounded-full" />
                            <span className="flex items-center gap-1">
                              <FileCode className="w-3.5 h-3.5" />
                              {incident.repository} @ {incident.version}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Right Hand similarity score indicator & Action options */}
                      <div className="flex items-center justify-between md:justify-end gap-4 ml-16 md:ml-0">
                        {/* Similarity indicator */}
                        <div className="flex items-center gap-1.5 bg-indigo-500/5 px-2.5 py-1 rounded border border-indigo-500/20">
                          <span className="text-[10px] font-mono font-bold text-[#c0c1ff]">{incident.similarity}% SIMILARITY</span>
                          <Sparkles className="w-3 h-3 text-[#c0c1ff]" />
                        </div>

                        {/* Actions group */}
                        <div className="flex items-center gap-3">
                          <span className={`px-2.5 py-1 rounded text-[10px] font-mono font-bold uppercase ${statusStyles}`}>
                            {incident.status}
                          </span>
                          
                          {/* Rollback badge status */}
                          <div 
                            className={`flex items-center justify-center p-1.5 rounded-full ${incident.rollbackRequired ? 'bg-rose-500/10 text-rose-400' : 'bg-zinc-800 text-zinc-500'}`}
                            title={incident.rollbackRequired ? 'Rollback Active / Required' : 'Operational Status Intact'}
                          >
                            {incident.rollbackRequired ? <History className="w-3.5 h-3.5 animate-spin" style={{ animationDuration: '4s' }} /> : <Check className="w-3.5 h-3.5" />}
                          </div>

                          <ChevronDown className={`w-4 h-4 text-[#c7c4d7] transition-transform duration-200 ${isExpanded ? 'rotate-180 text-white' : ''}`} />
                        </div>
                      </div>
                    </div>

                    {/* EXPANDED INSIGHTS PANEL */}
                    <AnimatePresence initial={false}>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2, ease: 'easeInOut' }}
                          className="border-t border-[#464554] bg-[#0d0d15] overflow-hidden"
                        >
                          <div className="p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
                            
                            {/* Detailed Diagnostics (8/12 Columns) */}
                            <div className="lg:col-span-8 space-y-6">
                              {/* Summary info from AI */}
                              <div>
                                <h4 className="text-xs font-mono font-bold text-[#c0c1ff] uppercase tracking-widest flex items-center gap-2 mb-2">
                                  <span className="w-4 h-[1px] bg-[#c0c1ff]" /> AI Summary
                                </h4>
                                <p className="text-xs sm:text-sm text-[#c7c4d7] leading-relaxed">
                                  {incident.aiSummary}
                                </p>
                              </div>

                              {/* Primary threat pattern breakdown */}
                              <div>
                                <h4 className="text-xs font-mono font-bold text-rose-400 uppercase tracking-widest flex items-center gap-2 mb-2.5">
                                  <span className="w-4 h-[1px] bg-rose-400" /> Primary Threat Details
                                </h4>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                  <div className="bg-[#1b1b23] p-4 rounded-lg border border-[#464554]">
                                    <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider mb-1">Vulnerability Type</p>
                                    <p className="text-xs font-bold text-white font-mono">{incident.vulnerabilityType}</p>
                                  </div>
                                  <div className="bg-[#1b1b23] p-4 rounded-lg border border-[#464554]">
                                    <p className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider mb-1">Detected Pattern</p>
                                    <p className="text-xs font-bold text-amber-400 font-mono tracking-tight break-all">{incident.detectedPattern}</p>
                                  </div>
                                </div>
                              </div>

                              {/* Actions / Mitigations checkbox log */}
                              <div className="p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-lg">
                                <h4 className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-widest mb-3">Mitigation Actions Required</h4>
                                <ul className="space-y-2.5">
                                  {incident.mitigationActions.map((action, index) => (
                                    <li key={index} className="flex items-start gap-2.5 text-xs text-[#c7c4d7] leading-relaxed">
                                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                                      <span>{action}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </div>

                            {/* Infrastructure Mapping & Actions (4/12 Columns) */}
                            <div className="lg:col-span-4 space-y-6 lg:border-l lg:border-[#464554] lg:pl-6">
                              {/* Linked deployment source */}
                              {incident.linkedDeployment && (
                                <div>
                                  <h4 className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider mb-2">Linked Deployment</h4>
                                  <div className="group flex items-center justify-between p-3.5 bg-[#1b1b23] rounded-lg border border-[#464554] hover:border-[#c0c1ff] transition-all">
                                    <div>
                                      <p className="text-xs font-bold font-mono text-white flex items-center gap-1.5">
                                        <Package className="w-3.5 h-3.5 text-indigo-400" />
                                        {incident.linkedDeployment.id}
                                      </p>
                                      <p className="text-[10px] text-zinc-500 font-mono mt-0.5">Triggered: {incident.linkedDeployment.triggeredBy}</p>
                                    </div>
                                    <div className="p-1.5 bg-[#0d0d15] rounded text-zinc-500">
                                      <ExternalLink className="w-3.5 h-3.5" />
                                    </div>
                                  </div>
                                </div>
                              )}

                              {/* Target cluster lists */}
                              <div>
                                <h4 className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider mb-2">Affected Clusters</h4>
                                <div className="flex flex-wrap gap-1.5">
                                  {incident.affectedClusters.map((cluster) => (
                                    <span key={cluster} className="text-[10px] font-mono font-semibold px-2 py-1 bg-[#1b1b23] border border-[#464554] rounded text-[#c7c4d7]">
                                      {cluster}
                                    </span>
                                  ))}
                                </div>
                              </div>

                              {/* Manual Report download panel trigger */}
                              <div className="pt-4 border-t border-[#464554]">
                                <button 
                                  onClick={(e) => handleExportPDF(incident, e)}
                                  className="w-full py-2.5 bg-zinc-800 hover:bg-[#34343d] active:scale-[0.98] transition-all rounded-md font-mono text-xs font-bold flex items-center justify-center gap-2 text-white border border-[#464554] cursor-pointer"
                                >
                                  <Printer className="w-4 h-4" />
                                  EXPORT REPORT (PDF)
                                </button>
                              </div>
                            </div>

                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                );
              })
            )}
          </AnimatePresence>
        </div>

        {/* --- PAGINATION CONTROLS --- */}
        {filteredIncidents.length > 0 && (
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4 border-t border-[#464554] pt-6">
            <p className="text-[11px] font-mono text-[#c7c4d7] uppercase tracking-widest">
              SHOWING {Math.min(currentPage * itemsPerPage, filteredIncidents.length)} OF {filteredIncidents.length} INCIDENTS
            </p>
            
            <div className="flex items-center gap-2">
              <button 
                onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
                disabled={currentPage === 1}
                className="p-2 border border-[#464554] rounded bg-transparent hover:bg-[#1f1f27] disabled:opacity-35 text-[#c7c4d7] disabled:hover:bg-transparent transition-all cursor-pointer"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => setCurrentPage(p)}
                  className={`px-3 py-1.5 rounded font-mono text-xs font-bold transition-all cursor-pointer ${currentPage === p ? 'bg-[#c0c1ff] text-[#1000a9]' : 'border border-[#464554] text-[#c7c4d7] hover:bg-[#1f1f27]'}`}
                >
                  {p}
                </button>
              ))}

              <button 
                onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="p-2 border border-[#464554] rounded bg-transparent hover:bg-[#1f1f27] disabled:opacity-35 text-[#c7c4d7] disabled:hover:bg-transparent transition-all cursor-pointer"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* --- REPORT MANUAL INCIDENT FORM MODAL --- */}
      <AnimatePresence>
        {showReportModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Modal Overlay backdrop */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowReportModal(false)}
              className="fixed inset-0 bg-[#0d0d15]/80 backdrop-blur-sm"
            />

            {/* Modal container content */}
            <motion.div 
              initial={{ scale: 0.95, opacity: 0, y: 15 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 15 }}
              className="bg-[#1f1f27] border border-[#464554] rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl relative z-10 flex flex-col max-h-[90vh]"
            >
              <div className="p-6 bg-[#1b1b23] border-b border-[#464554] flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Terminal className="w-5 h-5 text-[#c0c1ff]" />
                    MANUAL ANOMALY TRIGGER
                  </h3>
                  <p className="text-xs text-[#c7c4d7]/70 mt-0.5">Force inject an audited incident threat profile directly into production state.</p>
                </div>
                <button 
                  onClick={() => setShowReportModal(false)}
                  className="p-1 hover:bg-[#34343d] text-[#c7c4d7] hover:text-white rounded-lg transition-colors cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateIncident} className="p-6 overflow-y-auto custom-scrollbar flex-1 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="sm:col-span-2">
                    <label className="block text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">Incident Title / Threat Signature</label>
                    <input 
                      required
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      placeholder="e.g. Unencrypted AWS credentials inside checkout service"
                      className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3.5 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#c0c1ff]"
                      type="text"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">Repository Name</label>
                    <input 
                      required
                      value={newRepo}
                      onChange={(e) => setNewRepo(e.target.value)}
                      placeholder="e.g. checkout-service"
                      className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3.5 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#c0c1ff]"
                      type="text"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">Software Version / Git Ref</label>
                    <input 
                      value={newVersion}
                      onChange={(e) => setNewVersion(e.target.value)}
                      placeholder="e.g. v2.1.4-beta"
                      className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3.5 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#c0c1ff]"
                      type="text"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">Severity Tier</label>
                    <select 
                      value={newSeverity}
                      onChange={(e) => setNewSeverity(e.target.value as Severity)}
                      className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-[#c0c1ff]"
                    >
                      <option value="CRIT">Critical (CRIT)</option>
                      <option value="HIGH">High</option>
                      <option value="MED">Medium (MED)</option>
                      <option value="LOW">Low (LOW)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">Intercept Status</label>
                    <select 
                      value={newStatus}
                      onChange={(e) => setNewStatus(e.target.value as IncidentStatus)}
                      className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3.5 py-2 text-xs text-white focus:outline-none focus:border-[#c0c1ff]"
                    >
                      <option value="BLOCKED">BLOCKED</option>
                      <option value="MITIGATED">MITIGATED</option>
                      <option value="RESOLVED">RESOLVED</option>
                    </select>
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">Affected Clusters (comma-separated)</label>
                    <input 
                      value={newClusters}
                      onChange={(e) => setNewClusters(e.target.value)}
                      placeholder="us-east-1, eu-west-3, asia-south-2"
                      className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3.5 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#c0c1ff]"
                      type="text"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">AI Diagnostic Summary</label>
                    <textarea 
                      value={newAiSummary}
                      onChange={(e) => setNewAiSummary(e.target.value)}
                      placeholder="Provide security summary overview, threat impact, and root cause..."
                      rows={3}
                      className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3.5 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#c0c1ff]"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">Vulnerability CWE/Type</label>
                    <input 
                      value={newVulnType}
                      onChange={(e) => setNewVulnType(e.target.value)}
                      placeholder="Secret Exposure (CWE-798)"
                      className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3.5 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#c0c1ff]"
                      type="text"
                    />
                  </div>

                  <div>
                    <label className="block text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">Detected Pattern signature</label>
                    <input 
                      value={newPattern}
                      onChange={(e) => setNewPattern(e.target.value)}
                      placeholder="sk_live_*******************"
                      className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3.5 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#c0c1ff]"
                      type="text"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block text-[10px] font-mono text-zinc-400 uppercase tracking-wider mb-1">Required Mitigations (one per line)</label>
                    <textarea 
                      value={newMitigation}
                      onChange={(e) => setNewMitigation(e.target.value)}
                      placeholder="Rotate Stripe API keys.&#10;Deactivate commit signature.&#10;Configure AWS KMS parameters."
                      rows={3}
                      className="w-full bg-[#0d0d15] border border-[#464554] rounded-lg px-3.5 py-2 text-xs text-white placeholder-zinc-600 focus:outline-none focus:border-[#c0c1ff]"
                    />
                  </div>
                </div>

                <div className="pt-4 border-t border-[#464554] flex items-center justify-end gap-3 mt-6">
                  <button 
                    type="button"
                    onClick={() => setShowReportModal(false)}
                    className="px-4 py-2 bg-transparent hover:bg-zinc-800 text-zinc-400 hover:text-white font-mono text-xs font-bold rounded border border-[#464554] transition-colors cursor-pointer"
                  >
                    CANCEL
                  </button>
                  <button 
                    type="submit"
                    className="px-5 py-2 bg-[#c0c1ff] hover:bg-white text-[#1000a9] font-mono text-xs font-bold rounded hover:scale-[1.01] active:scale-95 transition-all cursor-pointer"
                  >
                    DEPLOY MANUAL REPORT
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
