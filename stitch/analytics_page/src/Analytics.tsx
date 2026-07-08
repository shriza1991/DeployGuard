import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Shield,
  LayoutDashboard,
  Rocket,
  Bot,
  History,
  BarChart3,
  Settings,
  Search,
  Bell,
  HelpCircle,
  Calendar,
  SlidersHorizontal,
  Download,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  ShieldCheck,
  Ban,
  Eye,
  X,
  Plus,
  Loader2,
  CheckCircle2,
  ChevronRight,
  Sparkles,
  Info
} from 'lucide-react';
import {
  BarChart as ReBarChart,
  Bar as ReBar,
  XAxis as ReXAxis,
  YAxis as ReYAxis,
  Tooltip as ReTooltip,
  ResponsiveContainer as ReResponsiveContainer,
  PieChart as RePieChart,
  Pie as RePie,
  Cell as ReCell,
  AreaChart as ReAreaChart,
  Area as ReArea
} from 'recharts';

// --- TS Interfaces ---
interface DeploymentBlock {
  id: string;
  time: string;
  repository: string;
  riskScore: number;
  primaryThreat: string;
  agentDetails: {
    codeRisk: number;
    infraRisk: number;
    incidentRisk: number;
  };
  details: string;
  recommendations: string[];
}

export default function Analytics() {
  // --- States ---
  const [timeRange, setTimeRange] = useState<'7d' | '14d' | '30d' | '90d'>('30d');
  const [searchQuery, setSearchQuery] = useState('');
  const [isFilterDropdownOpen, setIsFilterDropdownOpen] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM'>('ALL');
  
  // Modals & Triggers
  const [selectedBlock, setSelectedBlock] = useState<DeploymentBlock | null>(null);
  const [showNewDeploymentModal, setShowNewDeploymentModal] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [csvToast, setCsvToast] = useState<string | null>(null);

  // Form state for custom simulation
  const [newRepo, setNewRepo] = useState('payment-gateway');
  const [newBranch, setNewBranch] = useState('main');
  const [newThreatType, setNewThreatType] = useState('Hardcoded Stripe API Secret');
  const [newRiskScore, setNewRiskScore] = useState(84);

  // --- Initial Mock Data ---
  const [blocks, setBlocks] = useState<DeploymentBlock[]>([
    {
      id: 'block-1',
      time: '14:22:10',
      repository: 'payment-gateway / main',
      riskScore: 84,
      primaryThreat: 'Hardcoded Stripe API Secret',
      agentDetails: { codeRisk: 95, infraRisk: 42, incidentRisk: 30 },
      details: 'A live Stripe API Secret key was detected in configuration file config/production.json. This exposes live customer payment processing gateways to unauthorized extraction.',
      recommendations: ['Revoke the leaked Stripe token immediately in your Stripe Dashboard.', 'Migrate secrets handling to Google Secret Manager.', 'Add config/production.json to gitignore and sweep historical git refs with Trufflehog.']
    },
    {
      id: 'block-2',
      time: '13:05:45',
      repository: 'auth-service / feat-oauth',
      riskScore: 78,
      primaryThreat: 'Wildcard (*) IAM Policy',
      agentDetails: { codeRisk: 30, infraRisk: 92, incidentRisk: 40 },
      details: 'Terraform resources define an AWS IAM policy or GCP Role Binding with AdministratorAccess or wildcards on resources ("*"). This violates the Principle of Least Privilege.',
      recommendations: ['Refine IAM policy resource bindings to target specific ARN buckets.', 'Audit all users granted permission by this specific policy.', 'Enable strict permission boundaries.']
    },
    {
      id: 'block-3',
      time: '11:12:30',
      repository: 'data-warehouse / airflow',
      riskScore: 92,
      primaryThreat: 'Inbound Public 0.0.0.0/0 on Port 22',
      agentDetails: { codeRisk: 10, infraRisk: 98, incidentRisk: 90 },
      details: 'Security group rule ingress port 22 is open to the entire internet (0.0.0.0/0). This allows global brute force and SSH exploitation attempts directly on your orchestration cluster.',
      recommendations: ['Restrict Port 22 SSH ingress to corporate VPN CIDR blocks only.', 'Implement Cloud Identity-Aware Proxy (IAP) or AWS Systems Manager for secure access.', 'Close internet-facing port ranges.']
    }
  ]);

  // --- Multi-Timeframe Responsive Dataset ---
  const statsByTimeRange = useMemo(() => {
    switch (timeRange) {
      case '7d':
        return {
          totalAnalyzed: '2,941',
          totalAnalyzedTrend: '+9.4%',
          avgRiskScore: '21.4',
          avgRiskTrend: '-6.2%',
          avgConfidence: '95.6%',
          avgConfidenceTrend: '+1.4%',
          totalBlocked: '38',
          totalBlockedTrend: '+14%',
          decisionDistribution: [
            { name: 'SAFE', value: 2310, color: '#4edea3' },
            { name: 'REVIEW', value: 432, color: '#ffb95f' },
            { name: 'BLOCK', value: 199, color: '#ffb4ab' },
          ],
          volumeData: [
            { date: 'Mon', Safe: 320, Blocked: 12 },
            { date: 'Tue', Safe: 290, Blocked: 8 },
            { date: 'Wed', Safe: 410, Blocked: 15 },
            { date: 'Thu', Safe: 380, Blocked: 10 },
            { date: 'Fri', Safe: 440, Blocked: 9 },
            { date: 'Sat', Safe: 150, Blocked: 4 },
            { date: 'Sun', Safe: 180, Blocked: 5 },
          ],
          confidenceTrend: [
            { name: 'Day 1', value: 94.2 },
            { name: 'Day 2', value: 94.8 },
            { name: 'Day 3', value: 95.1 },
            { name: 'Day 4', value: 95.0 },
            { name: 'Day 5', value: 95.5 },
            { name: 'Day 6', value: 95.4 },
            { name: 'Day 7', value: 95.6 },
          ]
        };
      case '14d':
        return {
          totalAnalyzed: '5,892',
          totalAnalyzedTrend: '+10.8%',
          avgRiskScore: '22.9',
          avgRiskTrend: '-5.1%',
          avgConfidence: '94.9%',
          avgConfidenceTrend: '+0.9%',
          totalBlocked: '82',
          totalBlockedTrend: '+18%',
          decisionDistribution: [
            { name: 'SAFE', value: 4520, color: '#4edea3' },
            { name: 'REVIEW', value: 890, color: '#ffb95f' },
            { name: 'BLOCK', value: 482, color: '#ffb4ab' },
          ],
          volumeData: [
            { date: 'Week 1', Safe: 1890, Blocked: 42 },
            { date: 'Week 2', Safe: 2110, Blocked: 35 },
            { date: 'Week 3', Safe: 1720, Blocked: 29 },
            { date: 'Week 4', Safe: 1940, Blocked: 41 },
          ],
          confidenceTrend: [
            { name: 'Day 1', value: 94.0 },
            { name: 'Day 3', value: 94.2 },
            { name: 'Day 5', value: 94.6 },
            { name: 'Day 7', value: 94.5 },
            { name: 'Day 9', value: 94.8 },
            { name: 'Day 11', value: 95.1 },
            { name: 'Day 14', value: 94.9 },
          ]
        };
      case '90d':
        return {
          totalAnalyzed: '38,912',
          totalAnalyzedTrend: '+14.5%',
          avgRiskScore: '26.1',
          avgRiskTrend: '-2.8%',
          avgConfidence: '93.5%',
          avgConfidenceTrend: '+2.8%',
          totalBlocked: '592',
          totalBlockedTrend: '+26%',
          decisionDistribution: [
            { name: 'SAFE', value: 29810, color: '#4edea3' },
            { name: 'REVIEW', value: 5812, color: '#ffb95f' },
            { name: 'BLOCK', value: 3290, color: '#ffb4ab' },
          ],
          volumeData: [
            { date: 'Jul', Safe: 9800, Blocked: 180 },
            { date: 'Aug', Safe: 11200, Blocked: 210 },
            { date: 'Sep', Safe: 12100, Blocked: 240 },
          ],
          confidenceTrend: [
            { name: 'Jul 1', value: 92.4 },
            { name: 'Jul 15', value: 92.8 },
            { name: 'Aug 1', value: 93.1 },
            { name: 'Aug 15', value: 93.2 },
            { name: 'Sep 1', value: 93.4 },
            { name: 'Sep 15', value: 93.7 },
            { name: 'Sep 30', value: 93.5 },
          ]
        };
      case '30d':
      default:
        return {
          totalAnalyzed: '12,482',
          totalAnalyzedTrend: '+12%',
          avgRiskScore: '24.8',
          avgRiskTrend: '-4%',
          avgConfidence: '94.2%',
          avgConfidenceTrend: '+0.8%',
          totalBlocked: '184',
          totalBlockedTrend: '+22%',
          decisionDistribution: [
            { name: 'SAFE', value: 9361, color: '#4edea3' },
            { name: 'REVIEW', value: 1872, color: '#ffb95f' },
            { name: 'BLOCK', value: 1249, color: '#ffb4ab' },
          ],
          volumeData: [
            { date: '01 Oct', Safe: 450, Blocked: 35 },
            { date: '04 Oct', Safe: 380, Blocked: 20 },
            { date: '08 Oct', Safe: 620, Blocked: 45 },
            { date: '12 Oct', Safe: 540, Blocked: 38 },
            { date: '15 Oct', Safe: 710, Blocked: 52 },
            { date: '19 Oct', Safe: 490, Blocked: 28 },
            { date: '22 Oct', Safe: 580, Blocked: 40 },
            { date: '26 Oct', Safe: 820, Blocked: 60 },
            { date: '30 Oct', Safe: 650, Blocked: 48 },
          ],
          confidenceTrend: [
            { name: 'Oct 1', value: 93.5 },
            { name: 'Oct 5', value: 93.9 },
            { name: 'Oct 10', value: 93.8 },
            { name: 'Oct 15', value: 94.1 },
            { name: 'Oct 20', value: 94.3 },
            { name: 'Oct 25', value: 94.0 },
            { name: 'Oct 30', value: 94.2 },
          ]
        };
    }
  }, [timeRange]);

  // --- Filtering Blocks Table ---
  const filteredBlocks = useMemo(() => {
    return blocks.filter(b => {
      const matchesSearch = b.repository.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            b.primaryThreat.toLowerCase().includes(searchQuery.toLowerCase());
      
      let matchesSeverity = true;
      if (severityFilter === 'CRITICAL') matchesSeverity = b.riskScore >= 90;
      else if (severityFilter === 'HIGH') matchesSeverity = b.riskScore >= 75 && b.riskScore < 90;
      else if (severityFilter === 'MEDIUM') matchesSeverity = b.riskScore >= 50 && b.riskScore < 75;

      return matchesSearch && matchesSeverity;
    });
  }, [blocks, searchQuery, severityFilter]);

  // --- Simulate Export CSV ---
  const handleExportCSV = () => {
    const csvContent = "data:text/csv;charset=utf-8," 
      + ["Time,Repository,Risk Score,Primary Threat,Details"].join(",") + "\n"
      + blocks.map(b => `"${b.time}","${b.repository}",${b.riskScore},"${b.primaryThreat}","${b.details.replace(/"/g, '""')}"`).join("\n");
    
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `deployguard_security_analytics_${timeRange}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setCsvToast(`Successfully generated and downloaded analytics export for ${timeRange}!`);
    setTimeout(() => setCsvToast(null), 4000);
  };

  // --- Simulate Active Deployment Scan ---
  const handleStartScanSimulation = (e: React.FormEvent) => {
    e.preventDefault();
    setIsScanning(true);
    setScanStep(0);

    const steps = [
      "Initializing DeployGuard pipeline hook...",
      "Cloning branch and resolving infrastructure manifests...",
      "Running Code Risk Agent scanner...",
      "Running Infrastructure Configuration validator...",
      "Executing Incident History validation matching...",
      "DeployGuard threat analysis report calculated successfully!"
    ];

    const timer = setInterval(() => {
      setScanStep(prev => {
        if (prev < steps.length - 1) {
          return prev + 1;
        } else {
          clearInterval(timer);
          // Append new scanned risk block to table
          const newBlockId = `block-${Date.now()}`;
          const now = new Date();
          const timeStr = now.toTimeString().split(' ')[0];

          const newScannedBlock: DeploymentBlock = {
            id: newBlockId,
            time: timeStr,
            repository: `${newRepo} / ${newBranch}`,
            riskScore: Number(newRiskScore),
            primaryThreat: newThreatType,
            agentDetails: {
              codeRisk: Math.min(100, Math.round(Number(newRiskScore) * 1.1)),
              infraRisk: Math.min(100, Math.round(Number(newRiskScore) * 0.9)),
              incidentRisk: Math.min(100, Math.round(Number(newRiskScore) * 0.8)),
            },
            details: `A high-risk security issue was intercepted during the automated pre-deployment check of ${newRepo}/${newBranch}. DeployGuard actively blocked deployment progression.`,
            recommendations: [
              `Review policy configuration flags in repository's source code.`,
              `Apply immediate patches recommended by internal agent engines.`,
              `Ensure all static check passes conform to strict organizational rules.`
            ]
          };

          setBlocks(prevBlocks => [newScannedBlock, ...prevBlocks]);
          setIsScanning(false);
          setShowNewDeploymentModal(false);
          return 0;
        }
      });
    }, 1200);
  };

  return (
    <div className="bg-surface text-on-surface font-sans selection:bg-primary/30 selection:text-white min-h-screen">
      {/* --- Core Screen Body --- */}
      <div className="p-6 lg:p-8 max-w-[1600px] w-full mx-auto space-y-6">
        
        {/* --- Toast Overlay (simulation check) --- */}
        <AnimatePresence>
          {csvToast && (
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              className="fixed top-20 right-8 z-50 flex items-center gap-3 bg-surface-container-highest border border-secondary text-on-surface py-3 px-5 rounded-lg shadow-2xl"
            >
              <CheckCircle2 className="w-5 h-5 text-secondary" />
              <span className="text-body-md font-medium">{csvToast}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* --- Title & Dashboard Filter Bar --- */}
        <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4 border-b border-outline-variant/30 pb-6">
          <div>
            <h2 className="text-headline-lg font-semibold tracking-tight text-on-surface">Security Analytics</h2>
            <p className="text-on-surface-variant text-body-md mt-1">Holistic view of deployment security posture and agent performance.</p>
          </div>
          
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Search Box */}
            <div className="relative max-w-xs w-full sm:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant w-4 h-4" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-surface-container-low border border-outline-variant rounded py-1.5 pl-10 pr-8 text-body-md text-on-surface placeholder:text-on-surface-variant/60 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary transition-all"
                placeholder="Search analytics data..."
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Range select */}
            <div className="relative">
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value as any)}
                className="appearance-none bg-surface-container-low border border-outline-variant rounded pl-10 pr-8 py-2 text-label-md font-medium focus:border-primary focus:outline-none transition-colors cursor-pointer text-on-surface hover:border-primary/80"
              >
                <option value="7d">Last 7 Days</option>
                <option value="14d">Last 14 Days</option>
                <option value="30d">Last 30 Days</option>
                <option value="90d">Last 90 Days</option>
              </select>
              <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 text-primary w-4 h-4 pointer-events-none" />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant font-mono text-xs">▼</span>
            </div>

            {/* Advanced Filter Popover button */}
            <div className="relative">
              <button
                onClick={() => setIsFilterDropdownOpen(!isFilterDropdownOpen)}
                className={`flex items-center bg-surface-container-low border rounded px-3 py-2 gap-2 text-label-md font-medium hover:border-primary transition-colors cursor-pointer ${isFilterDropdownOpen ? 'border-primary text-primary' : 'border-outline-variant text-on-surface'}`}
              >
                <SlidersHorizontal className="w-4 h-4 text-on-surface-variant" />
                <span>Filters</span>
                {severityFilter !== 'ALL' && (
                  <span className="ml-1 bg-primary text-on-primary text-[9px] px-1.5 py-0.5 rounded-full font-bold">
                    {severityFilter}
                  </span>
                )}
              </button>

              {/* Filter Popover panel */}
              <AnimatePresence>
                {isFilterDropdownOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setIsFilterDropdownOpen(false)} />
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 10 }}
                      className="absolute right-0 mt-2 w-56 bg-surface-container-high border border-outline-variant rounded-lg p-4 shadow-2xl z-50 space-y-3"
                    >
                      <h5 className="text-label-sm font-bold uppercase text-on-surface-variant border-b border-outline-variant/30 pb-1">Filter Severity</h5>
                      <div className="space-y-1.5">
                        {(['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'] as const).map((sev) => (
                          <button
                            key={sev}
                            onClick={() => {
                              setSeverityFilter(sev);
                              setIsFilterDropdownOpen(false);
                            }}
                            className={`w-full text-left px-2 py-1.5 rounded text-body-md flex items-center justify-between transition-colors ${severityFilter === sev ? 'bg-primary/10 text-primary font-bold' : 'hover:bg-surface-container text-on-surface-variant hover:text-on-surface'}`}
                          >
                            <span>{sev === 'ALL' ? 'All Risks' : sev}</span>
                            {severityFilter === sev && <span className="w-1.5 h-1.5 rounded-full bg-primary" />}
                          </button>
                        ))}
                      </div>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>

            <button
              onClick={handleExportCSV}
              className="bg-surface-container-high border border-outline-variant text-on-surface px-4 py-2 rounded text-label-md font-medium hover:bg-surface-container-highest hover:border-primary transition-all duration-150 cursor-pointer flex items-center gap-2 shadow-sm"
            >
              <Download className="w-4 h-4 text-on-surface-variant" />
              Export CSV
            </button>

            <button
              onClick={() => setShowNewDeploymentModal(true)}
              className="bg-primary text-on-primary px-4 py-2 rounded text-label-md font-bold hover:bg-primary-container hover:text-on-primary-container transition-all duration-150 cursor-pointer flex items-center gap-1.5 shadow-sm shadow-primary/10"
            >
              <Plus className="w-4 h-4 stroke-[3px]" />
              Simulate Scan
            </button>
          </div>
        </div>

          {/* --- 4 Key Metric Overview Cards --- */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* TOTAL ANALYZED */}
            <div className="bg-surface-container-low border border-outline-variant p-5 rounded relative overflow-hidden group hover:border-primary/50 transition-colors duration-200">
              <div className="flex justify-between items-start mb-3">
                <p className="text-on-surface-variant font-mono text-[11px] uppercase tracking-wider">Total Analyzed</p>
                <div className="p-1.5 bg-primary/5 rounded border border-primary/10 group-hover:bg-primary/15 transition-colors">
                  <BarChart3 className="w-4 h-4 text-primary" />
                </div>
              </div>
              <h3 className="text-headline-lg font-bold text-on-surface tracking-tight">{statsByTimeRange.totalAnalyzed}</h3>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-secondary font-mono text-xs flex items-center gap-0.5">
                  <TrendingUp className="w-3.5 h-3.5" /> {statsByTimeRange.totalAnalyzedTrend}
                </span>
                <span className="text-on-surface-variant/60 text-xs">vs last month</span>
              </div>
              <div className="absolute bottom-0 left-0 w-full h-[3px] bg-primary opacity-30 group-hover:opacity-100 transition-opacity" />
            </div>

            {/* AVG. RISK SCORE */}
            <div className="bg-surface-container-low border border-outline-variant p-5 rounded relative overflow-hidden group hover:border-tertiary/50 transition-colors duration-200">
              <div className="flex justify-between items-start mb-3">
                <p className="text-on-surface-variant font-mono text-[11px] uppercase tracking-wider">Avg. Risk Score</p>
                <div className="p-1.5 bg-tertiary/5 rounded border border-tertiary/10 group-hover:bg-tertiary/15 transition-colors">
                  <AlertTriangle className="w-4 h-4 text-tertiary" />
                </div>
              </div>
              <h3 className="text-headline-lg font-bold text-on-surface tracking-tight">{statsByTimeRange.avgRiskScore}</h3>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-secondary font-mono text-xs flex items-center gap-0.5">
                  <TrendingDown className="w-3.5 h-3.5" /> {statsByTimeRange.avgRiskTrend}
                </span>
                <span className="text-on-surface-variant/60 text-xs">vs last month</span>
              </div>
              <div className="absolute bottom-0 left-0 w-full h-[3px] bg-tertiary opacity-30 group-hover:opacity-100 transition-opacity" />
            </div>

            {/* AVG. CONFIDENCE */}
            <div className="bg-surface-container-low border border-outline-variant p-5 rounded relative overflow-hidden group hover:border-secondary/50 transition-colors duration-200">
              <div className="flex justify-between items-start mb-3">
                <p className="text-on-surface-variant font-mono text-[11px] uppercase tracking-wider">Avg. Confidence</p>
                <div className="p-1.5 bg-secondary/5 rounded border border-secondary/10 group-hover:bg-secondary/15 transition-colors">
                  <ShieldCheck className="w-4 h-4 text-secondary" />
                </div>
              </div>
              <h3 className="text-headline-lg font-bold text-on-surface tracking-tight">{statsByTimeRange.avgConfidence}</h3>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-secondary font-mono text-xs flex items-center gap-0.5">
                  <TrendingUp className="w-3.5 h-3.5" /> {statsByTimeRange.avgConfidenceTrend}
                </span>
                <span className="text-on-surface-variant/60 text-xs">vs last month</span>
              </div>
              <div className="absolute bottom-0 left-0 w-full h-[3px] bg-secondary opacity-30 group-hover:opacity-100 transition-opacity" />
            </div>

            {/* TOTAL BLOCKED */}
            <div className="bg-surface-container-low border border-outline-variant p-5 rounded relative overflow-hidden group hover:border-error/50 transition-colors duration-200">
              <div className="flex justify-between items-start mb-3">
                <p className="text-on-surface-variant font-mono text-[11px] uppercase tracking-wider">Total Blocked</p>
                <div className="p-1.5 bg-error/5 rounded border border-error/10 group-hover:bg-error/15 transition-colors">
                  <Ban className="w-4 h-4 text-error" />
                </div>
              </div>
              <h3 className="text-headline-lg font-bold text-on-surface tracking-tight">{statsByTimeRange.totalBlocked}</h3>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-error font-mono text-xs flex items-center gap-0.5">
                  <TrendingUp className="w-3.5 h-3.5" /> {statsByTimeRange.totalBlockedTrend}
                </span>
                <span className="text-on-surface-variant/60 text-xs">vs last month</span>
              </div>
              <div className="absolute bottom-0 left-0 w-full h-[3px] bg-error opacity-30 group-hover:opacity-100 transition-opacity" />
            </div>
          </div>

          {/* --- Row 1: Deployment Volume & Decision Distribution Donut --- */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Deployment Volume Chart */}
            <div className="lg:col-span-8 bg-surface-container-low border border-outline-variant p-5 rounded-lg flex flex-col justify-between">
              <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2 mb-4">
                <div>
                  <h4 className="text-headline-sm font-semibold text-on-surface tracking-tight">Deployment Volume &amp; Decisions</h4>
                  <p className="text-xs text-on-surface-variant mt-0.5">Visualizing blocked vs clean pipelines over time</p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-secondary" />
                    <span className="text-xs font-mono font-medium text-on-surface-variant">Safe</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-error" />
                    <span className="text-xs font-mono font-medium text-on-surface-variant">Blocked</span>
                  </div>
                </div>
              </div>

              <div className="h-[280px] w-full">
                <ReResponsiveContainer width="100%" height="100%">
                  <ReBarChart
                    data={statsByTimeRange.volumeData}
                    margin={{ top: 10, right: 10, left: -20, bottom: 5 }}
                    barGap={6}
                  >
                    <ReXAxis
                      dataKey="date"
                      stroke="#908fa0"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      fontFamily="JetBrains Mono"
                    />
                    <ReYAxis
                      stroke="#908fa0"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      fontFamily="JetBrains Mono"
                    />
                    <ReTooltip
                      cursor={{ fill: 'rgba(78,222,163,0.03)' }}
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          return (
                            <div className="bg-surface-container border border-outline-variant p-2.5 rounded shadow-2xl">
                              <p className="text-xs font-bold text-on-surface border-b border-outline-variant/30 pb-1 mb-1">{payload[0].payload.date}</p>
                              <p className="text-xs text-secondary flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
                                Safe: {payload[0].value}
                              </p>
                              <p className="text-xs text-error flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-error" />
                                Blocked: {payload[1]?.value}
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <ReBar dataKey="Safe" fill="#4edea3" radius={[4, 4, 0, 0]} maxBarSize={30} />
                    <ReBar dataKey="Blocked" fill="#ffb4ab" radius={[4, 4, 0, 0]} maxBarSize={30} />
                  </ReBarChart>
                </ReResponsiveContainer>
              </div>
            </div>

            {/* Decision Distribution Donut Chart */}
            <div className="lg:col-span-4 bg-surface-container-low border border-outline-variant p-5 rounded-lg flex flex-col justify-between">
              <div>
                <h4 className="text-headline-sm font-semibold text-on-surface tracking-tight mb-1">Decision Distribution</h4>
                <p className="text-xs text-on-surface-variant">Breakdown of classification results</p>
              </div>

              <div className="relative h-44 w-full flex items-center justify-center my-2">
                <ReResponsiveContainer width="100%" height="100%">
                  <RePieChart>
                    <RePie
                      data={statsByTimeRange.decisionDistribution}
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={75}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {statsByTimeRange.decisionDistribution.map((entry, index) => (
                        <ReCell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </RePie>
                  </RePieChart>
                </ReResponsiveContainer>
                
                {/* Center overlay of the donut */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="text-2xl font-bold font-sans tracking-tight text-on-surface">75%</span>
                  <span className="text-[9px] text-on-surface-variant font-mono uppercase tracking-widest mt-0.5">Safe Rate</span>
                </div>
              </div>

              {/* Legend with total counts */}
              <div className="space-y-2 border-t border-outline-variant/30 pt-3">
                {statsByTimeRange.decisionDistribution.map((entry, idx) => (
                  <div key={idx} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded" style={{ backgroundColor: entry.color }} />
                      <span className="font-mono text-on-surface-variant uppercase">{entry.name}</span>
                    </div>
                    <span className="font-mono font-bold text-on-surface">
                      {entry.value.toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* --- Row 2: Risk Score Distribution & Agent Performance --- */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
            {/* Risk Score Distribution Histogram */}
            <div className="md:col-span-6 bg-surface-container-low border border-outline-variant p-5 rounded-lg flex flex-col justify-between">
              <div>
                <h4 className="text-headline-sm font-semibold text-on-surface tracking-tight mb-1">Risk Score Distribution</h4>
                <p className="text-xs text-on-surface-variant">Cluster density across security risk categories</p>
              </div>

              {/* Histogram bars */}
              <div className="flex items-end gap-1.5 h-44 px-2 mt-4 relative">
                <div className="flex-1 bg-secondary hover:brightness-110 rounded-t transition-all group relative" style={{ height: '12%' }}>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-surface border border-outline-variant text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">Vol: 12%</div>
                </div>
                <div className="flex-1 bg-secondary hover:brightness-110 rounded-t transition-all group relative" style={{ height: '32%' }}>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-surface border border-outline-variant text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">Vol: 32%</div>
                </div>
                <div className="flex-1 bg-secondary hover:brightness-110 rounded-t transition-all group relative border-t-2 border-primary/20" style={{ height: '82%' }}>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-surface border border-outline-variant text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">Vol: 82%</div>
                </div>
                <div className="flex-1 bg-secondary hover:brightness-110 rounded-t transition-all group relative" style={{ height: '62%' }}>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-surface border border-outline-variant text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">Vol: 62%</div>
                </div>
                <div className="flex-1 bg-tertiary hover:brightness-110 rounded-t transition-all group relative" style={{ height: '42%' }}>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-surface border border-outline-variant text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">Vol: 42%</div>
                </div>
                <div className="flex-1 bg-tertiary hover:brightness-110 rounded-t transition-all group relative" style={{ height: '28%' }}>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-surface border border-outline-variant text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">Vol: 28%</div>
                </div>
                <div className="flex-1 bg-error hover:brightness-110 rounded-t transition-all group relative" style={{ height: '18%' }}>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-surface border border-outline-variant text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">Vol: 18%</div>
                </div>
                <div className="flex-1 bg-error hover:brightness-110 rounded-t transition-all group relative" style={{ height: '11%' }}>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-surface border border-outline-variant text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">Vol: 11%</div>
                </div>
                <div className="flex-1 bg-error hover:brightness-110 rounded-t transition-all group relative" style={{ height: '6%' }}>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-surface border border-outline-variant text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">Vol: 6%</div>
                </div>
                <div className="flex-1 bg-error hover:brightness-110 rounded-t transition-all group relative" style={{ height: '3%' }}>
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 bg-surface border border-outline-variant text-[10px] px-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10 whitespace-nowrap">Vol: 3%</div>
                </div>
              </div>

              {/* Labels */}
              <div className="flex justify-between text-xs text-on-surface-variant font-mono px-2 mt-3 border-t border-outline-variant/20 pt-2">
                <span>0-10</span>
                <span>25</span>
                <span>50</span>
                <span>75</span>
                <span>100</span>
              </div>

              <div className="mt-5 border-l-2 border-primary/30 pl-4 py-1 bg-primary/2 rounded-r">
                <p className="text-xs italic text-on-surface-variant/90 leading-relaxed">
                  "Majority of deployments cluster in the 20-30 risk range, indicating stable infrastructure patterns."
                </p>
              </div>
            </div>

            {/* Agent Performance Metrics */}
            <div className="md:col-span-6 bg-surface-container-low border border-outline-variant p-5 rounded-lg flex flex-col justify-between">
              <div>
                <h4 className="text-headline-sm font-semibold text-on-surface tracking-tight mb-1">Agent Performance Metrics</h4>
                <p className="text-xs text-on-surface-variant">Real-time health of pre-deployment inspection bots</p>
              </div>

              <div className="space-y-4 my-3">
                {/* Code Risk Agent */}
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="font-semibold text-on-surface flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-secondary" />
                      Code Risk Agent
                    </span>
                    <span className="font-mono text-secondary font-bold">88.4 Score</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-2 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: '88.4%' }}
                      transition={{ duration: 1, ease: 'easeOut' }}
                      className="bg-secondary h-full rounded-full"
                    />
                  </div>
                </div>

                {/* Infrastructure Agent */}
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="font-semibold text-on-surface flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-tertiary" />
                      Infrastructure Agent
                    </span>
                    <span className="font-mono text-tertiary font-bold">72.1 Score</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-2 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: '72.1%' }}
                      transition={{ duration: 1, ease: 'easeOut' }}
                      className="bg-tertiary h-full rounded-full"
                    />
                  </div>
                </div>

                {/* Incident History Agent */}
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="font-semibold text-on-surface flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-primary" />
                      Incident History Agent
                    </span>
                    <span className="font-mono text-primary font-bold">92.9 Score</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-2 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: '92.9%' }}
                      transition={{ duration: 1, ease: 'easeOut' }}
                      className="bg-primary h-full rounded-full"
                    />
                  </div>
                </div>
              </div>

              {/* Bot stats footer row */}
              <div className="mt-4 grid grid-cols-3 gap-2 text-center border-t border-outline-variant/30 pt-4">
                <div className="p-2 rounded hover:bg-surface-container transition-colors">
                  <p className="text-[10px] text-on-surface-variant font-mono uppercase tracking-wider mb-0.5">Latency</p>
                  <p className="text-body-md font-bold font-mono text-on-surface">1.2s</p>
                </div>
                <div className="p-2 rounded hover:bg-surface-container transition-colors">
                  <p className="text-[10px] text-on-surface-variant font-mono uppercase tracking-wider mb-0.5">Accuracy</p>
                  <p className="text-body-md font-bold font-mono text-on-surface">96%</p>
                </div>
                <div className="p-2 rounded hover:bg-surface-container transition-colors">
                  <p className="text-[10px] text-on-surface-variant font-mono uppercase tracking-wider mb-0.5">Uptime</p>
                  <p className="text-body-md font-bold font-mono text-on-surface">99.9%</p>
                </div>
              </div>
            </div>
          </div>

          {/* --- Row 3: Confidence Trend & Risks & Recommendations --- */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
            {/* Confidence Trend */}
            <div className="lg:col-span-4 bg-surface-container-low border border-outline-variant p-5 rounded-lg flex flex-col justify-between group">
              <div>
                <h4 className="text-headline-sm font-semibold text-on-surface tracking-tight mb-0.5">Confidence Trend</h4>
                <p className="text-xs text-on-surface-variant">Model stability over {timeRange === '7d' ? '7 days' : timeRange === '14d' ? '14 days' : timeRange === '90d' ? '90 days' : '30 days'}</p>
              </div>

              {/* Sparkline line-chart */}
              <div className="h-28 w-full mt-3 relative">
                <ReResponsiveContainer width="100%" height="100%">
                  <ReAreaChart
                    data={statsByTimeRange.confidenceTrend}
                    margin={{ top: 5, right: 5, left: -40, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="colorConfidence" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#c0c1ff" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#c0c1ff" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <ReTooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          return (
                            <div className="bg-surface-container border border-outline-variant p-1.5 rounded shadow text-[10px] font-mono">
                              {payload[0].value}%
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <ReArea
                      type="monotone"
                      dataKey="value"
                      stroke="#c0c1ff"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorConfidence)"
                    />
                  </ReAreaChart>
                </ReResponsiveContainer>
              </div>

              <div className="flex justify-between items-center mt-3 pt-2.5 border-t border-outline-variant/20">
                <span className="text-xs font-mono font-bold text-on-surface-variant">Avg: {statsByTimeRange.avgConfidence}</span>
                <div className="flex items-center text-secondary gap-1">
                  <TrendingUp className="w-3.5 h-3.5" />
                  <span className="text-xs font-mono font-semibold">+2.1% improvement</span>
                </div>
              </div>
            </div>

            {/* Common Deployment Risks */}
            <div className="lg:col-span-4 bg-surface-container-low border border-outline-variant p-5 rounded-lg flex flex-col justify-between">
              <div>
                <h4 className="text-headline-sm font-semibold text-on-surface tracking-tight mb-1">Common Deployment Risks</h4>
                <p className="text-xs text-on-surface-variant">Highest frequency threat vectors classified</p>
              </div>

              <div className="space-y-3.5 my-4">
                {/* Row 1 */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono uppercase text-on-surface-variant">
                    <span className="truncate">IAM OVER-PROVISIONING</span>
                    <span className="font-bold text-on-surface ml-1">342</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-1.5 rounded-full overflow-hidden">
                    <div className="bg-error h-full rounded-full" style={{ width: '85%' }} />
                  </div>
                </div>

                {/* Row 2 */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono uppercase text-on-surface-variant">
                    <span className="truncate">SECRET LEAKAGE</span>
                    <span className="font-bold text-on-surface ml-1">215</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-1.5 rounded-full overflow-hidden">
                    <div className="bg-error/80 h-full rounded-full" style={{ width: '65%' }} />
                  </div>
                </div>

                {/* Row 3 */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono uppercase text-on-surface-variant">
                    <span className="truncate">UNENCRYPTED S3</span>
                    <span className="font-bold text-on-surface ml-1">188</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-1.5 rounded-full overflow-hidden">
                    <div className="bg-error/60 h-full rounded-full" style={{ width: '55%' }} />
                  </div>
                </div>

                {/* Row 4 */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono uppercase text-on-surface-variant">
                    <span className="truncate">PUBLIC SSH KEYS</span>
                    <span className="font-bold text-on-surface ml-1">104</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-1.5 rounded-full overflow-hidden">
                    <div className="bg-error/40 h-full rounded-full" style={{ width: '30%' }} />
                  </div>
                </div>
              </div>
            </div>

            {/* Top Recommendations */}
            <div className="lg:col-span-4 bg-surface-container-low border border-outline-variant p-5 rounded-lg flex flex-col justify-between">
              <div>
                <h4 className="text-headline-sm font-semibold text-on-surface tracking-tight mb-1">Top Recommendations</h4>
                <p className="text-xs text-on-surface-variant">Urgent operational task volume identified</p>
              </div>

              <div className="space-y-3.5 my-4">
                {/* Row 1 */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono uppercase text-on-surface-variant">
                    <span className="truncate">UPDATE DEPENDENCIES</span>
                    <span className="font-bold text-on-surface ml-1">1,402</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-1.5 rounded-full overflow-hidden">
                    <div className="bg-primary h-full rounded-full" style={{ width: '90%' }} />
                  </div>
                </div>

                {/* Row 2 */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono uppercase text-on-surface-variant">
                    <span className="truncate">ROTATE API KEYS</span>
                    <span className="font-bold text-on-surface ml-1">894</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-1.5 rounded-full overflow-hidden">
                    <div className="bg-primary/80 h-full rounded-full" style={{ width: '70%' }} />
                  </div>
                </div>

                {/* Row 3 */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono uppercase text-on-surface-variant">
                    <span className="truncate">ENFORCE MFA</span>
                    <span className="font-bold text-on-surface ml-1">652</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-1.5 rounded-full overflow-hidden">
                    <div className="bg-primary/60 h-full rounded-full" style={{ width: '50%' }} />
                  </div>
                </div>

                {/* Row 4 */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono uppercase text-on-surface-variant">
                    <span className="truncate">AUDIT VPC PEERING</span>
                    <span className="font-bold text-on-surface ml-1">412</span>
                  </div>
                  <div className="w-full bg-surface-container-highest h-1.5 rounded-full overflow-hidden">
                    <div className="bg-primary/40 h-full rounded-full" style={{ width: '35%' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* --- Row 4: Recent High-Risk Blocks Table --- */}
          <div className="bg-surface-container border border-outline-variant rounded-lg overflow-hidden shadow-xl">
            <div className="px-6 py-4 border-b border-outline-variant flex justify-between items-center gap-4 flex-wrap bg-surface-container-high/60">
              <div>
                <h4 className="text-headline-sm font-semibold text-on-surface tracking-tight">Recent High-Risk Blocks</h4>
                <p className="text-xs text-on-surface-variant mt-0.5">Interventions triggered by automated safety guardrails</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setSeverityFilter('CRITICAL')}
                  className="bg-error/10 text-error hover:bg-error/20 border border-error/20 text-xs px-2.5 py-1 rounded-full font-bold cursor-pointer transition-colors"
                >
                  View High Risk Only
                </button>
                {severityFilter !== 'ALL' && (
                  <button
                    onClick={() => setSeverityFilter('ALL')}
                    className="text-on-surface-variant hover:text-on-surface text-xs font-medium cursor-pointer underline transition-colors"
                  >
                    Clear Filter
                  </button>
                )}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-surface-container-high border-b border-outline-variant/60 font-mono text-[11px] text-on-surface-variant uppercase tracking-wider">
                  <tr>
                    <th className="px-6 py-3.5 font-semibold">Time</th>
                    <th className="px-6 py-3.5 font-semibold">Repository</th>
                    <th className="px-6 py-3.5 font-semibold">Risk Score</th>
                    <th className="px-6 py-3.5 font-semibold">Primary Threat</th>
                    <th className="px-6 py-3.5 font-semibold text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/40 bg-surface-container-low/40">
                  {filteredBlocks.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-6 py-10 text-center text-on-surface-variant font-mono text-xs">
                        No recent blocked logs matching the current criteria.
                      </td>
                    </tr>
                  ) : (
                    filteredBlocks.map((block) => (
                      <tr
                        key={block.id}
                        className="hover:bg-surface-container-high/40 transition-colors group cursor-pointer"
                        onClick={() => setSelectedBlock(block)}
                      >
                        <td className="px-6 py-4 font-mono text-xs text-on-surface-variant/80 group-hover:text-on-surface transition-colors">{block.time}</td>
                        <td className="px-6 py-4 font-semibold text-body-md text-on-surface group-hover:text-primary transition-colors">{block.repository}</td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center gap-1.5 bg-error/10 text-error px-2.5 py-1 rounded text-xs font-mono font-bold border border-error/20 group-hover:scale-105 transition-transform duration-150">
                            <span className="w-1.5 h-1.5 rounded-full bg-error" />
                            {block.riskScore}/100
                          </span>
                        </td>
                        <td className="px-6 py-4 text-body-md text-on-surface-variant/90">{block.primaryThreat}</td>
                        <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => setSelectedBlock(block)}
                            className="text-on-surface-variant hover:text-primary hover:bg-primary/10 p-1.5 rounded transition-all cursor-pointer inline-flex items-center gap-1.5"
                            title="Inspect Block Log"
                          >
                            <Eye className="w-4 h-4" />
                            <span className="text-xs font-mono font-semibold hidden sm:inline">Inspect</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            
            <div className="px-6 py-3 border-t border-outline-variant flex justify-between items-center text-xs text-on-surface-variant">
              <span>Showing {filteredBlocks.length} threat records</span>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSeverityFilter('ALL');
                }}
                className="hover:text-primary font-medium hover:underline cursor-pointer"
              >
                Reset Table View
              </button>
            </div>
          </div>

          {/* --- Bottom Footer Info --- */}
          <footer className="pt-10 pb-6 border-t border-outline-variant/30 flex flex-col sm:flex-row justify-between items-center gap-4 text-on-surface-variant text-xs font-mono">
            <p>© 2026 DeployGuard Security Inc. All rights reserved.</p>
            <div className="flex gap-6">
              <a href="#" className="hover:text-primary transition-colors">Documentation</a>
              <a href="#" className="hover:text-primary transition-colors">Status</a>
              <a href="#" className="hover:text-primary transition-colors">API</a>
            </div>
          </footer>
        </div>

        {/* --- MODAL 1: Threat Inspection Details Overlay --- */}
        <AnimatePresence>
          {selectedBlock && (
            <>
              {/* Backdrop */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.6 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black z-50 cursor-pointer"
                onClick={() => setSelectedBlock(null)}
              />
              
              {/* Modal Card */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 30 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 30 }}
                className="fixed inset-x-4 bottom-4 sm:inset-auto sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 max-w-lg w-full bg-surface-container-high border border-outline-variant rounded-xl p-6 shadow-2xl z-50 overflow-hidden space-y-4"
              >
                {/* Header */}
                <div className="flex justify-between items-start gap-4 border-b border-outline-variant/30 pb-3">
                  <div>
                    <span className="text-[10px] font-mono uppercase bg-error/10 text-error px-2 py-0.5 rounded border border-error/20 font-bold">
                      DeployGuard Threat Intervention
                    </span>
                    <h3 className="font-bold text-headline-sm text-on-surface tracking-tight mt-1">
                      {selectedBlock.primaryThreat}
                    </h3>
                  </div>
                  <button
                    onClick={() => setSelectedBlock(null)}
                    className="p-1 hover:bg-surface-container-highest rounded text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                {/* Scope Metadata */}
                <div className="grid grid-cols-3 gap-2 py-2 text-center bg-surface-container rounded border border-outline-variant/20 font-mono text-xs">
                  <div>
                    <p className="text-on-surface-variant text-[10px] uppercase">Risk Level</p>
                    <p className="font-bold text-error mt-0.5">{selectedBlock.riskScore}/100</p>
                  </div>
                  <div>
                    <p className="text-on-surface-variant text-[10px] uppercase">Repository</p>
                    <p className="font-bold text-on-surface mt-0.5 truncate px-1">{selectedBlock.repository.split(' ')[0]}</p>
                  </div>
                  <div>
                    <p className="text-on-surface-variant text-[10px] uppercase">Timestamp</p>
                    <p className="font-bold text-on-surface mt-0.5">{selectedBlock.time}</p>
                  </div>
                </div>

                {/* Threat description */}
                <div className="space-y-1.5">
                  <h4 className="text-xs font-mono uppercase font-bold text-on-surface-variant flex items-center gap-1">
                    <Info className="w-3.5 h-3.5 text-primary" />
                    Detailed Security Report
                  </h4>
                  <p className="text-body-md text-on-surface-variant leading-relaxed">
                    {selectedBlock.details}
                  </p>
                </div>

                {/* Sub-Agent Individual Risk Scoring */}
                <div className="space-y-2 bg-surface-container p-3.5 rounded border border-outline-variant/30">
                  <h4 className="text-xs font-mono uppercase font-bold text-on-surface-variant">Sub-Agent Assessment Breakdown</h4>
                  <div className="grid grid-cols-3 gap-4 text-center mt-1">
                    <div>
                      <p className="text-[10px] text-on-surface-variant">Code Risk</p>
                      <p className={`text-sm font-mono font-bold ${selectedBlock.agentDetails.codeRisk > 75 ? 'text-error' : 'text-secondary'}`}>
                        {selectedBlock.agentDetails.codeRisk}%
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-on-surface-variant">Infra Risk</p>
                      <p className={`text-sm font-mono font-bold ${selectedBlock.agentDetails.infraRisk > 75 ? 'text-error' : 'text-secondary'}`}>
                        {selectedBlock.agentDetails.infraRisk}%
                      </p>
                    </div>
                    <div>
                      <p className="text-[10px] text-on-surface-variant">Incident History</p>
                      <p className={`text-sm font-mono font-bold ${selectedBlock.agentDetails.incidentRisk > 75 ? 'text-error' : 'text-secondary'}`}>
                        {selectedBlock.agentDetails.incidentRisk}%
                      </p>
                    </div>
                  </div>
                </div>

                {/* Recommendations */}
                <div className="space-y-2">
                  <h4 className="text-xs font-mono uppercase font-bold text-secondary">Remediation Steps Required</h4>
                  <ul className="space-y-1.5">
                    {selectedBlock.recommendations.map((rec, i) => (
                      <li key={i} className="text-xs text-on-surface-variant flex items-start gap-2 leading-relaxed">
                        <ChevronRight className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Dismiss Button */}
                <div className="pt-2 border-t border-outline-variant/30 flex justify-end">
                  <button
                    onClick={() => setSelectedBlock(null)}
                    className="bg-primary text-on-primary font-mono text-xs font-bold py-2 px-5 rounded hover:bg-primary-container hover:text-on-primary-container transition-all cursor-pointer"
                  >
                    Acknowledge Assessment
                  </button>
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>

        {/* --- MODAL 2: New Deployment Simulation Trigger --- */}
        <AnimatePresence>
          {showNewDeploymentModal && (
            <>
              {/* Backdrop */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.6 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black z-50 cursor-pointer"
                onClick={() => !isScanning && setShowNewDeploymentModal(false)}
              />
              
              {/* Modal Container */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: 30 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 30 }}
                className="fixed inset-x-4 bottom-4 sm:inset-auto sm:top-1/2 sm:left-1/2 sm:-translate-x-1/2 sm:-translate-y-1/2 max-w-md w-full bg-surface-container-high border border-outline-variant rounded-xl p-6 shadow-2xl z-50 overflow-hidden space-y-4"
              >
                {/* Header */}
                <div className="flex justify-between items-center border-b border-outline-variant/30 pb-3">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-primary" />
                    <h3 className="font-bold text-headline-sm text-on-surface tracking-tight">
                      DeployGuard Pipeline Scanner
                    </h3>
                  </div>
                  {!isScanning && (
                    <button
                      onClick={() => setShowNewDeploymentModal(false)}
                      className="p-1 hover:bg-surface-container-highest rounded text-on-surface-variant hover:text-on-surface transition-colors cursor-pointer"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  )}
                </div>

                {isScanning ? (
                  /* Live scan steps indicator animation */
                  <div className="py-8 text-center space-y-5">
                    <div className="relative inline-flex items-center justify-center">
                      <Loader2 className="w-14 h-14 text-primary animate-spin" />
                      <Shield className="w-6 h-6 text-primary absolute animate-pulse" />
                    </div>
                    
                    <div className="space-y-1.5 max-w-sm mx-auto">
                      <p className="text-body-md font-bold text-on-surface animate-pulse">
                        Scanning code deployment commits...
                      </p>
                      
                      {/* Interactive scanning logs console */}
                      <div className="bg-surface-container-lowest border border-outline-variant/40 p-3 rounded font-mono text-left text-[10px] text-primary/90 space-y-1 h-24 overflow-y-auto">
                        <p className="text-secondary">► pipeline: triggered via branch commit</p>
                        {scanStep >= 1 && <p className="text-primary-container">► system: code check initiated</p>}
                        {scanStep >= 2 && <p className="text-tertiary">► agent-code: scanning static configs...</p>}
                        {scanStep >= 3 && <p className="text-error">► agent-infra: checking ports & firewalls...</p>}
                        {scanStep >= 4 && <p className="text-on-surface-variant">► agent-incident: comparing previous threat maps...</p>}
                        {scanStep >= 5 && <p className="text-secondary font-bold">► done: evaluation report generated</p>}
                      </div>
                    </div>
                  </div>
                ) : (
                  /* Setup form */
                  <form onSubmit={handleStartScanSimulation} className="space-y-4">
                    <p className="text-xs text-on-surface-variant leading-relaxed">
                      Select repository context to simulate a GitHub commit hook. DeployGuard security agents will automatically inspect code configurations and compute risk telemetry.
                    </p>

                    <div className="space-y-3">
                      {/* Repo select */}
                      <div>
                        <label className="block text-label-sm font-bold uppercase text-on-surface-variant mb-1">Target Repository</label>
                        <select
                          value={newRepo}
                          onChange={(e) => setNewRepo(e.target.value)}
                          className="w-full bg-surface-container-low border border-outline-variant rounded p-2 text-body-md focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                        >
                          <option value="payment-gateway">payment-gateway</option>
                          <option value="auth-service">auth-service</option>
                          <option value="data-warehouse">data-warehouse</option>
                          <option value="web-frontend">web-frontend</option>
                          <option value="reporting-engine">reporting-engine</option>
                        </select>
                      </div>

                      {/* Branch input */}
                      <div>
                        <label className="block text-label-sm font-bold uppercase text-on-surface-variant mb-1">Branch Name</label>
                        <input
                          type="text"
                          required
                          value={newBranch}
                          onChange={(e) => setNewBranch(e.target.value)}
                          className="w-full bg-surface-container-low border border-outline-variant rounded p-2 text-body-md focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary font-mono text-on-surface"
                          placeholder="e.g. main, fix/auth"
                        />
                      </div>

                      {/* Threat trigger selection */}
                      <div>
                        <label className="block text-label-sm font-bold uppercase text-on-surface-variant mb-1">Simulate Threat Trigger</label>
                        <select
                          value={newThreatType}
                          onChange={(e) => {
                            setNewThreatType(e.target.value);
                            // Assign corresponding high risk score automatically
                            if (e.target.value.includes('AWS')) setNewRiskScore(91);
                            else if (e.target.value.includes('Token')) setNewRiskScore(82);
                            else if (e.target.value.includes('Public')) setNewRiskScore(95);
                            else setNewRiskScore(76);
                          }}
                          className="w-full bg-surface-container-low border border-outline-variant rounded p-2 text-body-md focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                        >
                          <option value="Hardcoded Slack Webhook Token">Hardcoded Slack Webhook Token (High)</option>
                          <option value="Plaintext AWS Credentials in Commit">Plaintext AWS Credentials in Commit (Critical)</option>
                          <option value="Public ElasticSearch Node Exposure">Public ElasticSearch Node Exposure (Critical)</option>
                          <option value="Outdated vulnerable Log4j dependency">Outdated vulnerable Log4j dependency (Medium)</option>
                        </select>
                      </div>

                      {/* Risk score slider */}
                      <div>
                        <div className="flex justify-between text-label-sm font-bold uppercase text-on-surface-variant mb-1">
                          <span>Simulated Risk Score</span>
                          <span className="font-mono text-error">{newRiskScore}/100</span>
                        </div>
                        <input
                          type="range"
                          min="45"
                          max="99"
                          value={newRiskScore}
                          onChange={(e) => setNewRiskScore(Number(e.target.value))}
                          className="w-full h-1 bg-surface-container-highest rounded-lg appearance-none cursor-pointer accent-primary"
                        />
                      </div>
                    </div>

                    <div className="pt-3 border-t border-outline-variant/30 flex justify-end gap-2.5">
                      <button
                        type="button"
                        onClick={() => setShowNewDeploymentModal(false)}
                        className="bg-surface-container border border-outline-variant text-on-surface font-mono text-xs font-bold py-2.5 px-4 rounded hover:bg-surface-container-highest transition-colors cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        type="submit"
                        className="bg-primary text-on-primary font-mono text-xs font-bold py-2.5 px-5 rounded hover:bg-primary-container hover:text-on-primary-container transition-all cursor-pointer shadow-lg shadow-primary/10 flex items-center gap-2"
                      >
                        <Shield className="w-4 h-4 fill-on-primary stroke-none" />
                        Trigger Scan Hook
                      </button>
                    </div>
                  </form>
                )}
              </motion.div>
            </>
          )}
        </AnimatePresence>
    </div>
  );
}
