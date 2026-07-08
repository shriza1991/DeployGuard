import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Shield,
  Search,
  Bell,
  Calendar,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Filter,
  ArrowUpDown,
  X,
  Activity,
  Globe,
  Check,
  RotateCw,
  Sliders,
  ChevronDown,
  Rocket,
  ArrowRight
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

// Types
export interface Deployment {
  id: string;
  repository: string;
  branch: string;
  time: string;
  timestamp: Date; // For sorting and active time filtering
  decision: "SAFE" | "REVIEW" | "BLOCK";
  risk: number;
  confidence: number;
}

export interface ProjectData {
  id: string;
  name: string;
  description: string;
  metrics: {
    total: number;
    safe: number;
    review: number;
    blocked: number;
    avgRisk: number;
    avgConfidence: number;
  };
  deployments: Deployment[];
  policyRules: {
    id: string;
    name: string;
    category: string;
    active: boolean;
    description: string;
  }[];
}

// Initial Mock Data matching the original design's metrics and records
const INITIAL_PROJECTS: ProjectData[] = [
  {
    id: "alpha",
    name: "Project Alpha",
    description: "Active enterprise portal and API services gateway.",
    metrics: {
      total: 1284,
      safe: 1102,
      review: 124,
      blocked: 58,
      avgRisk: 24,
      avgConfidence: 94.2
    },
    policyRules: [
      { id: "p1", name: "Hardcoded Secrets Scanner", category: "Static Analysis", active: true, description: "Blocks commits containing raw API keys, tokens, or private certificates." },
      { id: "p2", name: "Dependency Vulnerability Audit", category: "SCA", active: true, description: "Validates third-party packages against active CVE databases." },
      { id: "p3", name: "SQL Injection Detection Guard", category: "AST", active: true, description: "Analyzes AST structures for untrusted parameters in database queries." },
      { id: "p4", name: "Least Privilege IAM Evaluator", category: "Cloud Config", active: true, description: "Flags oversized credentials or wildcards in deployment templates." },
      { id: "p5", name: "TLS 1.3 Enforcement Rule", category: "Network", active: true, description: "Requires end-to-end transport layer security protocol v1.3." },
      { id: "p6", name: "Malicious Package Watchdog", category: "SecOps", active: false, description: "Scans packages for known supply-chain cryptojacking or exfiltration payloads." }
    ],
    deployments: [
      { id: "dep-8f2a", repository: "dg-api", branch: "main", time: "2m ago", timestamp: new Date(Date.now() - 2 * 60000), decision: "SAFE", risk: 12, confidence: 98 },
      { id: "dep-9c1b", repository: "dg-frontend", branch: "staging", time: "15m ago", timestamp: new Date(Date.now() - 15 * 60000), decision: "REVIEW", risk: 45, confidence: 82 },
      { id: "dep-7e3f", repository: "auth-service", branch: "main", time: "1h ago", timestamp: new Date(Date.now() - 60 * 60000), decision: "BLOCK", risk: 88, confidence: 91 },
      { id: "dep-5d4g", repository: "infra-db", branch: "prod-patch", time: "3h ago", timestamp: new Date(Date.now() - 180 * 60000), decision: "SAFE", risk: 8, confidence: 99 },
      { id: "dep-2k9m", repository: "gateway", branch: "main", time: "5h ago", timestamp: new Date(Date.now() - 300 * 60000), decision: "SAFE", risk: 15, confidence: 95 },
      { id: "dep-4x9t", repository: "dg-api", branch: "main", time: "7h ago", timestamp: new Date(Date.now() - 420 * 60000), decision: "SAFE", risk: 10, confidence: 97 },
      { id: "dep-1p3k", repository: "auth-service", branch: "dev", time: "12h ago", timestamp: new Date(Date.now() - 720 * 60000), decision: "SAFE", risk: 20, confidence: 94 },
      { id: "dep-3q9v", repository: "dg-frontend", branch: "staging", time: "18h ago", timestamp: new Date(Date.now() - 1080 * 60000), decision: "REVIEW", risk: 50, confidence: 79 },
      { id: "dep-7m1a", repository: "billing-service", branch: "main", time: "1d ago", timestamp: new Date(Date.now() - 1440 * 60000), decision: "SAFE", risk: 11, confidence: 96 },
      { id: "dep-6z2r", repository: "infra-db", branch: "main", time: "2d ago", timestamp: new Date(Date.now() - 2880 * 60000), decision: "SAFE", risk: 6, confidence: 98 },
      { id: "dep-5y4n", repository: "gateway", branch: "staging", time: "3d ago", timestamp: new Date(Date.now() - 4320 * 60000), decision: "BLOCK", risk: 94, confidence: 92 }
    ]
  },
  {
    id: "beta",
    name: "Project Beta",
    description: "Core ledger services and secure transaction pipelines.",
    metrics: {
      total: 843,
      safe: 780,
      review: 42,
      blocked: 21,
      avgRisk: 16,
      avgConfidence: 96.8
    },
    policyRules: [
      { id: "p1", name: "Hardcoded Secrets Scanner", category: "Static Analysis", active: true, description: "Blocks commits containing raw API keys, tokens, or private certificates." },
      { id: "p2", name: "Dependency Vulnerability Audit", category: "SCA", active: true, description: "Validates third-party packages against active CVE databases." },
      { id: "p3", name: "SQL Injection Detection Guard", category: "AST", active: true, description: "Analyzes AST structures for untrusted parameters in database queries." }
    ],
    deployments: [
      { id: "dep-b101", repository: "billing-engine", branch: "main", time: "12m ago", timestamp: new Date(Date.now() - 12 * 60000), decision: "SAFE", risk: 4, confidence: 99 },
      { id: "dep-b102", repository: "ledger-db", branch: "main", time: "32m ago", timestamp: new Date(Date.now() - 32 * 60000), decision: "SAFE", risk: 8, confidence: 98 },
      { id: "dep-b103", repository: "payout-worker", branch: "staging", time: "2h ago", timestamp: new Date(Date.now() - 120 * 60000), decision: "SAFE", risk: 14, confidence: 97 },
      { id: "dep-b104", repository: "billing-engine", branch: "hotfix-decimal", time: "4h ago", timestamp: new Date(Date.now() - 240 * 60000), decision: "REVIEW", risk: 38, confidence: 85 },
      { id: "dep-b105", repository: "tax-calculator", branch: "main", time: "7h ago", timestamp: new Date(Date.now() - 420 * 60000), decision: "SAFE", risk: 2, confidence: 100 }
    ]
  },
  {
    id: "gamma",
    name: "Project Gamma",
    description: "External client integration widgets & notification handlers.",
    metrics: {
      total: 456,
      safe: 380,
      review: 48,
      blocked: 28,
      avgRisk: 31,
      avgConfidence: 91.5
    },
    policyRules: [
      { id: "p1", name: "Hardcoded Secrets Scanner", category: "Static Analysis", active: true, description: "Blocks commits containing raw API keys, tokens, or private certificates." }
    ],
    deployments: [
      { id: "dep-g901", repository: "notification-router", branch: "main", time: "5m ago", timestamp: new Date(Date.now() - 5 * 60000), decision: "SAFE", risk: 15, confidence: 94 },
      { id: "dep-g902", repository: "email-delivery", branch: "staging", time: "28m ago", timestamp: new Date(Date.now() - 28 * 60000), decision: "REVIEW", risk: 48, confidence: 81 },
      { id: "dep-g903", repository: "push-worker", branch: "main", time: "3h ago", timestamp: new Date(Date.now() - 180 * 60000), decision: "BLOCK", risk: 82, confidence: 90 }
    ]
  }
];

export default function Dashboard() {
  const [projects, setProjects] = useState<ProjectData[]>(INITIAL_PROJECTS);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("alpha");
  const [timePeriod, setTimePeriod] = useState<"24h" | "7d" | "30d">("24h");
  
  // Dropdown states
  const [isProjectDropdownOpen, setIsProjectDropdownOpen] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  
  // Table search & filters
  const [tableSearchQuery, setTableSearchQuery] = useState("");
  const [branchFilter, setBranchFilter] = useState<string>("all");
  const [decisionFilter, setDecisionFilter] = useState<string>("all");
  
  // Sorting state
  const [sortField, setSortField] = useState<keyof Deployment>("timestamp");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Modals & Popovers
  const [isNewDeploymentOpen, setIsNewDeploymentOpen] = useState(false);
  const [isPolicyModalOpen, setIsPolicyModalOpen] = useState(false);
  const [isCustomDateOpen, setIsCustomDateOpen] = useState(false);
  
  // Custom Date range state
  const [startDate, setStartDate] = useState("2026-07-01");
  const [endDate, setEndDate] = useState("2026-07-08");

  // New Deployment Form state
  const [newRepo, setNewRepo] = useState("dg-api");
  const [newBranch, setNewBranch] = useState("main");
  const [newDecision, setNewDecision] = useState<"SAFE" | "REVIEW" | "BLOCK">("SAFE");
  const [newRisk, setNewRisk] = useState<number>(12);
  const [newConfidence, setNewConfidence] = useState<number>(98);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Selected project reference
  const currentProject = useMemo(() => {
    return projects.find((p) => p.id === selectedProjectId) || projects[0];
  }, [projects, selectedProjectId]);

  // Notifications alert system
  const [notifications, setNotifications] = useState([
    { id: 1, message: "Critical block on auth-service", time: "1h ago", unread: true, type: "block" },
    { id: 2, message: "Policy evaluation completed for dg-api", time: "2h ago", unread: true, type: "safe" },
    { id: 3, message: "High latency spike detected US-East-1", time: "4h ago", unread: false, type: "alert" }
  ]);

  // Simulated live agent latency updates
  const [agentLatencies, setAgentLatencies] = useState({
    usEast: 0.02,
    euWest: 0.08,
    apSouth: 0.12
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setAgentLatencies((prev) => ({
        usEast: Math.max(0.01, +(prev.usEast + (Math.random() - 0.5) * 0.003).toFixed(3)),
        euWest: Math.max(0.04, +(prev.euWest + (Math.random() - 0.5) * 0.008).toFixed(3)),
        apSouth: Math.max(0.07, +(prev.apSouth + (Math.random() - 0.5) * 0.012).toFixed(3))
      }));
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleTogglePolicyRule = (ruleId: string) => {
    setProjects((prevProjects) => {
      return prevProjects.map((proj) => {
        if (proj.id === selectedProjectId) {
          const updatedRules = proj.policyRules.map((rule) => {
            if (rule.id === ruleId) {
              return { ...rule, active: !rule.active };
            }
            return rule;
          });
          return {
            ...proj,
            policyRules: updatedRules
          };
        }
        return proj;
      });
    });
  };

  // Simulate threat analysis on New Deployment creation
  const handleAIEvaluation = () => {
    setIsAnalyzing(true);
    setTimeout(() => {
      const decisionVal = Math.random();
      let decision: "SAFE" | "REVIEW" | "BLOCK" = "SAFE";
      let risk = Math.floor(Math.random() * 20) + 5;
      let confidence = Math.floor(Math.random() * 8) + 92;

      if (decisionVal > 0.8) {
        decision = "BLOCK";
        risk = Math.floor(Math.random() * 15) + 80;
        confidence = Math.floor(Math.random() * 10) + 88;
      } else if (decisionVal > 0.55) {
        decision = "REVIEW";
        risk = Math.floor(Math.random() * 25) + 35;
        confidence = Math.floor(Math.random() * 12) + 80;
      }

      setNewDecision(decision);
      setNewRisk(risk);
      setNewConfidence(confidence);
      setIsAnalyzing(false);
    }, 1200);
  };

  // Create new deployment handler
  const handleCreateDeployment = (e: React.FormEvent) => {
    e.preventDefault();
    const generatedId = `dep-${Math.random().toString(16).substring(2, 6)}`;
    const newDep: Deployment = {
      id: generatedId,
      repository: newRepo,
      branch: newBranch,
      time: "Just now",
      timestamp: new Date(),
      decision: newDecision,
      risk: newRisk,
      confidence: newConfidence
    };

    setProjects((prevProjects) => {
      return prevProjects.map((proj) => {
        if (proj.id === selectedProjectId) {
          const updatedDeps = [newDep, ...proj.deployments];
          const newTotal = proj.metrics.total + 1;
          const newSafe = proj.metrics.safe + (newDecision === "SAFE" ? 1 : 0);
          const newReview = proj.metrics.review + (newDecision === "REVIEW" ? 1 : 0);
          const newBlocked = proj.metrics.blocked + (newDecision === "BLOCK" ? 1 : 0);

          const totalRisk = updatedDeps.reduce((sum, d) => sum + d.risk, 0);
          const avgRisk = Math.round(totalRisk / updatedDeps.length);

          const totalConf = updatedDeps.reduce((sum, d) => sum + d.confidence, 0);
          const avgConfidence = +(totalConf / updatedDeps.length).toFixed(1);

          return {
            ...proj,
            metrics: {
              total: newTotal,
              safe: newSafe,
              review: newReview,
              blocked: newBlocked,
              avgRisk,
              avgConfidence
            },
            deployments: updatedDeps
          };
        }
        return proj;
      });
    });

    setNotifications((prev) => [
      {
        id: Date.now(),
        message: `New deployment ${generatedId} evaluated for ${newRepo}`,
        time: "Just now",
        unread: true,
        type: newDecision.toLowerCase()
      },
      ...prev
    ]);

    setIsNewDeploymentOpen(false);
    setNewRepo("dg-api");
    setNewBranch("main");
    setNewDecision("SAFE");
    setNewRisk(12);
    setNewConfidence(98);
  };

  // Filter list of deployments based on user search queries and selector values
  const filteredDeployments = useMemo(() => {
    let list = [...currentProject.deployments];

    if (tableSearchQuery.trim() !== "") {
      const query = tableSearchQuery.toLowerCase();
      list = list.filter(
        (d) =>
          d.id.toLowerCase().includes(query) ||
          d.repository.toLowerCase().includes(query)
      );
    }

    if (branchFilter !== "all") {
      list = list.filter((d) => d.branch === branchFilter);
    }

    if (decisionFilter !== "all") {
      list = list.filter((d) => d.decision === decisionFilter);
    }

    // Sort the list
    list.sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (valA instanceof Date && valB instanceof Date) {
        return sortDirection === "desc"
          ? valB.getTime() - valA.getTime()
          : valA.getTime() - valB.getTime();
      }

      if (typeof valA === "string") {
        valA = (valA as string).toLowerCase();
        valB = (valB as string).toLowerCase();
      }

      if (valA < valB) return sortDirection === "asc" ? -1 : 1;
      if (valA > valB) return sortDirection === "asc" ? 1 : -1;
      return 0;
    });

    return list;
  }, [currentProject, tableSearchQuery, branchFilter, decisionFilter, sortField, sortDirection]);

  // Current paginated view items
  const paginatedDeployments = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredDeployments.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredDeployments, currentPage]);

  const totalPages = Math.ceil(filteredDeployments.length / itemsPerPage) || 1;

  // Set of all unique branches for dynamic dropdown filters
  const uniqueBranches = useMemo(() => {
    const branches = new Set<string>();
    currentProject.deployments.forEach((d) => branches.add(d.branch));
    return Array.from(branches);
  }, [currentProject]);

  // Derived Policy Health score based on active policy rules
  const policyHealthScore = useMemo(() => {
    const rules = currentProject.policyRules;
    const total = rules.length;
    if (total === 0) return 100;
    const active = rules.filter((r) => r.active).length;
    return Math.round((active / total) * 100);
  }, [currentProject]);

  // Ref triggers for dropdown clicks outside
  const projectMenuRef = useRef<HTMLDivElement>(null);
  const alertsMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (projectMenuRef.current && !projectMenuRef.current.contains(event.target as Node)) {
        setIsProjectDropdownOpen(false);
      }
      if (alertsMenuRef.current && !alertsMenuRef.current.contains(event.target as Node)) {
        setIsAlertsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="w-full min-h-screen bg-brand-background text-brand-on-surface p-6 lg:p-8 font-sans">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* ==================== DASHBOARD HEADER WITH CONTROLS ==================== */}
        <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-6 border-b border-brand-outline-variant/10 pb-6">
          {/* Title & Description */}
          <div>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded bg-brand-primary flex items-center justify-center">
                <Shield className="w-4.5 h-4.5 text-brand-background stroke-[2.5]" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight text-white font-sans">DeployGuard</h1>
            </div>
            <p className="text-sm text-brand-on-surface-variant mt-2 max-w-xl">
              Real-time security monitoring and deployment oversight. Switching projects filters metrics, policies, and deployments dynamically.
            </p>
          </div>

          {/* Controls Group */}
          <div className="flex flex-wrap items-center gap-4">
            {/* Project Selection Dropdown */}
            <div className="relative" ref={projectMenuRef}>
              <button
                onClick={() => setIsProjectDropdownOpen(!isProjectDropdownOpen)}
                className="flex items-center gap-2 px-3 py-2 rounded border border-brand-outline-variant/30 bg-brand-surface-low hover:bg-brand-surface-high text-brand-primary hover:text-white transition-all font-mono text-xs font-semibold focus:outline-none"
              >
                <span>{currentProject.name}</span>
                <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isProjectDropdownOpen ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {isProjectDropdownOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    className="absolute left-0 mt-2 w-72 bg-brand-surface-high border border-brand-outline-variant/30 rounded shadow-xl overflow-hidden z-50"
                  >
                    <div className="p-3 border-b border-brand-outline-variant/10 bg-brand-surface-lowest">
                      <p className="text-[10px] uppercase font-mono tracking-widest text-brand-on-surface-variant font-semibold">Change Active Project</p>
                    </div>
                    <div className="divide-y divide-brand-outline-variant/10 font-mono">
                      {projects.map((proj) => (
                        <button
                          key={proj.id}
                          onClick={() => {
                            setSelectedProjectId(proj.id);
                            setIsProjectDropdownOpen(false);
                            setCurrentPage(1);
                          }}
                          className={`w-full text-left p-3 flex flex-col gap-1 transition-colors hover:bg-brand-surface-highest ${selectedProjectId === proj.id ? 'bg-brand-primary/5' : ''}`}
                        >
                          <div className="flex items-center justify-between">
                            <span className={`text-xs font-semibold ${selectedProjectId === proj.id ? 'text-brand-primary' : 'text-white'}`}>
                              {proj.name}
                            </span>
                            {selectedProjectId === proj.id && <Check className="w-3.5 h-3.5 text-brand-primary" />}
                          </div>
                          <p className="text-[11px] text-brand-on-surface-variant line-clamp-1">{proj.description}</p>
                          <div className="flex items-center gap-3 mt-1 text-[10px] text-brand-on-surface-variant">
                            <span>🚀 {proj.metrics.total} Deps</span>
                            <span className="text-brand-secondary">🛡️ {proj.metrics.safe} Safe</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Notifications Bell */}
            <div className="relative" ref={alertsMenuRef}>
              <button
                onClick={() => setIsAlertsOpen(!isAlertsOpen)}
                className="w-10 h-10 flex items-center justify-center rounded border border-brand-outline-variant/25 bg-brand-surface-low hover:bg-brand-surface-high transition-colors text-brand-on-surface-variant hover:text-white relative"
              >
                <Bell className="w-4.5 h-4.5" />
                {notifications.some(n => n.unread) && (
                  <span className="absolute top-2.5 right-2.5 w-2.5 h-2.5 bg-brand-error rounded-full border border-brand-background animate-pulse" />
                )}
              </button>

              <AnimatePresence>
                {isAlertsOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 8 }}
                    className="absolute right-0 mt-2 w-80 bg-brand-surface-high border border-brand-outline-variant/30 rounded shadow-xl overflow-hidden z-50"
                  >
                    <div className="p-3 border-b border-brand-outline-variant/10 bg-brand-surface-lowest flex items-center justify-between">
                      <p className="text-[10px] uppercase font-mono tracking-widest text-brand-on-surface-variant font-semibold">Security Log</p>
                      <button
                        onClick={() => setNotifications(prev => prev.map(n => ({ ...n, unread: false })))}
                        className="text-[10px] text-brand-primary hover:underline font-mono"
                      >
                        Mark all read
                      </button>
                    </div>
                    <div className="divide-y divide-brand-outline-variant/10 max-h-80 overflow-y-auto font-mono">
                      {notifications.length === 0 ? (
                        <div className="p-4 text-center text-xs text-brand-on-surface-variant">No new alerts.</div>
                      ) : (
                        notifications.map((n) => (
                          <div key={n.id} className={`p-3 text-xs flex flex-col gap-1 hover:bg-brand-surface-highest transition-colors ${n.unread ? 'bg-brand-primary/5' : ''}`}>
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] text-brand-on-surface-variant">{n.time}</span>
                              <span className={`w-1.5 h-1.5 rounded-full ${n.type === 'block' ? 'bg-brand-error' : n.type === 'review' ? 'bg-brand-tertiary' : 'bg-brand-secondary'}`} />
                            </div>
                            <p className="text-brand-on-surface font-medium pr-4">{n.message}</p>
                          </div>
                        ))
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Time / Date Controls */}
            <div className="flex items-center gap-2 bg-brand-surface-low p-1 rounded border border-brand-outline-variant/15 font-mono text-xs">
              <button
                onClick={() => setTimePeriod("24h")}
                className={`px-3 py-1.5 rounded transition-all ${timePeriod === "24h" ? 'bg-brand-surface-highest text-white font-medium shadow' : 'text-brand-on-surface-variant hover:text-white'}`}
              >
                24h
              </button>
              <button
                onClick={() => setTimePeriod("7d")}
                className={`px-3 py-1.5 rounded transition-all ${timePeriod === "7d" ? 'bg-brand-surface-highest text-white font-medium shadow' : 'text-brand-on-surface-variant hover:text-white'}`}
              >
                7d
              </button>
              <button
                onClick={() => setTimePeriod("30d")}
                className={`px-3 py-1.5 rounded transition-all ${timePeriod === "30d" ? 'bg-brand-surface-highest text-white font-medium shadow' : 'text-brand-on-surface-variant hover:text-white'}`}
              >
                30d
              </button>
              
              <div className="h-4 w-px bg-brand-outline-variant/20 mx-1" />
              
              <div className="relative">
                <button
                  onClick={() => setIsCustomDateOpen(!isCustomDateOpen)}
                  className="px-2 py-1.5 flex items-center gap-1.5 text-brand-on-surface-variant hover:text-white transition-colors"
                >
                  <Calendar className="w-3.5 h-3.5 text-brand-primary" />
                  <span className="hidden sm:inline">{timePeriod === "24h" ? "Oct 12 - Oct 13, 2023" : timePeriod === "7d" ? "Oct 06 - Oct 13, 2023" : "Sep 13 - Oct 13, 2023"}</span>
                </button>

                <AnimatePresence>
                  {isCustomDateOpen && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: 8 }}
                      className="absolute right-0 mt-2 p-4 bg-brand-surface-high border border-brand-outline-variant/40 rounded shadow-2xl z-40 w-72"
                    >
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-[10px] uppercase font-mono tracking-wider font-semibold text-brand-on-surface-variant">Custom Timeframe</span>
                        <button onClick={() => setIsCustomDateOpen(false)} className="text-brand-on-surface-variant hover:text-white">
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                      <div className="space-y-3 font-mono text-[11px]">
                        <div>
                          <label className="block text-brand-on-surface-variant mb-1">Start Date</label>
                          <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="w-full bg-brand-background border border-brand-outline-variant/30 rounded p-1.5 text-white focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-brand-on-surface-variant mb-1">End Date</label>
                          <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="w-full bg-brand-background border border-brand-outline-variant/30 rounded p-1.5 text-white focus:outline-none"
                          />
                        </div>
                        <button
                          onClick={() => {
                            setTimePeriod("30d");
                            setIsCustomDateOpen(false);
                          }}
                          className="w-full bg-brand-primary text-brand-background py-1.5 rounded font-bold text-center mt-2 hover:bg-white transition-colors"
                        >
                          Apply Filter
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {/* New Deployment Button */}
            <button
              onClick={() => setIsNewDeploymentOpen(true)}
              className="bg-brand-primary hover:bg-white text-brand-background font-mono text-xs font-bold px-4 py-2.5 rounded transition-colors tracking-wide shadow-lg shadow-brand-primary/10 hover:shadow-brand-primary/25 cursor-pointer"
            >
              New Deployment
            </button>

          </div>
        </div>

        {/* ==================== METRIC CARDS GRID ==================== */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          
          {/* 1. Total Deployments */}
          <div className="bg-brand-surface-low border border-brand-outline-variant/20 p-5 rounded hover:border-brand-primary/35 transition-all duration-300 relative group overflow-hidden">
            <div className="flex justify-between items-start mb-4">
              <span className="text-[10px] uppercase tracking-widest text-brand-on-surface-variant font-mono font-medium">TOTAL DEPLOYMENTS</span>
              <span className="text-brand-secondary flex items-center font-mono text-[10px] font-bold bg-brand-secondary/10 px-1.5 py-0.5 rounded-full">
                <TrendingUp className="w-3 h-3 mr-0.5" />
                12%
              </span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-bold text-white font-mono">{currentProject.metrics.total.toLocaleString()}</span>
            </div>
            
            {/* Decorative progress representation */}
            <div className="mt-4 h-1.5 w-full bg-brand-surface-highest rounded overflow-hidden">
              <div className="bg-brand-primary h-full w-[80%] rounded-full opacity-60" />
            </div>
          </div>

          {/* 2. Safe */}
          <div className="bg-brand-surface-low border border-brand-outline-variant/20 p-5 rounded hover:border-brand-secondary/35 transition-all duration-300 relative group overflow-hidden">
            <span className="text-[10px] uppercase tracking-widest text-brand-on-surface-variant font-mono font-medium block mb-4">SAFE</span>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-brand-secondary font-mono">{currentProject.metrics.safe.toLocaleString()}</span>
              <span className="text-[10px] text-brand-on-surface-variant font-mono">
                {((currentProject.metrics.safe / currentProject.metrics.total) * 100).toFixed(1)}%
              </span>
            </div>
            
            <div className="mt-4 h-1.5 w-full bg-brand-surface-highest rounded overflow-hidden">
              <div 
                className="bg-brand-secondary h-full rounded-full transition-all duration-500" 
                style={{ width: `${(currentProject.metrics.safe / currentProject.metrics.total) * 100}%` }}
              />
            </div>
          </div>

          {/* 3. Review */}
          <div className="bg-brand-surface-low border border-brand-outline-variant/20 p-5 rounded hover:border-brand-tertiary/35 transition-all duration-300 relative group overflow-hidden">
            <span className="text-[10px] uppercase tracking-widest text-brand-on-surface-variant font-mono font-medium block mb-4">REVIEW</span>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-brand-tertiary font-mono">{currentProject.metrics.review.toLocaleString()}</span>
              <span className="text-[10px] text-brand-on-surface-variant font-mono">
                {((currentProject.metrics.review / currentProject.metrics.total) * 100).toFixed(1)}%
              </span>
            </div>
            
            <div className="mt-4 h-1.5 w-full bg-brand-surface-highest rounded overflow-hidden">
              <div 
                className="bg-brand-tertiary h-full rounded-full transition-all duration-500" 
                style={{ width: `${(currentProject.metrics.review / currentProject.metrics.total) * 100}%` }}
              />
            </div>
          </div>

          {/* 4. Blocked */}
          <div className="bg-brand-surface-low border border-brand-outline-variant/20 p-5 rounded hover:border-brand-error/35 transition-all duration-300 relative group overflow-hidden">
            <span className="text-[10px] uppercase tracking-widest text-brand-on-surface-variant font-mono font-medium block mb-4">BLOCKED</span>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-bold text-brand-error font-mono">{currentProject.metrics.blocked.toLocaleString()}</span>
              <span className="text-[10px] text-brand-on-surface-variant font-mono">
                {((currentProject.metrics.blocked / currentProject.metrics.total) * 100).toFixed(1)}%
              </span>
            </div>
            
            <div className="mt-4 h-1.5 w-full bg-brand-surface-highest rounded overflow-hidden">
              <div 
                className="bg-brand-error h-full rounded-full transition-all duration-500" 
                style={{ width: `${(currentProject.metrics.blocked / currentProject.metrics.total) * 100}%` }}
              />
            </div>
          </div>

          {/* 5. Avg Risk Score */}
          <div className="bg-brand-surface-low border border-brand-outline-variant/20 p-5 rounded hover:border-brand-secondary/35 transition-all duration-300 relative group overflow-hidden">
            <span className="text-[10px] uppercase tracking-widest text-brand-on-surface-variant font-mono font-medium block mb-4">AVG RISK SCORE</span>
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-bold text-white font-mono">{currentProject.metrics.avgRisk}</span>
              <span className="text-sm text-brand-on-surface-variant font-mono">/100</span>
            </div>
            <div className="mt-1">
              <span className="text-[9px] font-mono font-semibold uppercase px-2 py-0.5 rounded-full bg-brand-secondary/10 text-brand-secondary">
                LOW RISK
              </span>
            </div>
            
            <div className="mt-4 h-1.5 w-full bg-brand-surface-highest rounded overflow-hidden">
              <div className="bg-brand-secondary h-full w-[24%]" />
            </div>
          </div>

          {/* 6. Avg Confidence */}
          <div className="bg-brand-surface-low border border-brand-outline-variant/20 p-5 rounded hover:border-brand-primary/35 transition-all duration-300 relative group overflow-hidden">
            <span className="text-[10px] uppercase tracking-widest text-brand-on-surface-variant font-mono font-medium block mb-4">AVG CONFIDENCE</span>
            <div className="flex items-baseline gap-1">
              <span className="text-3xl font-bold text-white font-mono">{currentProject.metrics.avgConfidence}%</span>
            </div>
            <p className="text-[10px] text-brand-on-surface-variant mt-1">High precision</p>
            
            <div className="mt-4 h-1.5 w-full bg-brand-surface-highest rounded overflow-hidden">
              <div className="bg-brand-primary h-full w-[94.2%]" />
            </div>
          </div>

        </div>

        {/* ==================== RECENT DEPLOYMENTS SECTION ==================== */}
        <section className="bg-brand-surface-low border border-brand-outline-variant/20 rounded shadow-md overflow-hidden">
          
          {/* Search, Filter panels inside table */}
          <div className="px-6 py-5 border-b border-brand-outline-variant/15 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <h3 className="text-lg font-bold text-white">Recent Deployments</h3>
            
            <div className="flex flex-wrap items-center gap-3">
              {/* Search Field */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-brand-on-surface-variant absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={tableSearchQuery}
                  onChange={(e) => {
                    setTableSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  placeholder="Filter by ID or Repo..."
                  className="bg-brand-background border border-brand-outline-variant/25 rounded pl-9 pr-4 py-1.5 text-xs font-mono w-64 placeholder:text-brand-on-surface-variant focus:border-brand-primary/50 focus:outline-none transition-colors"
                />
              </div>

              {/* Branch Filter dropdown */}
              <div className="flex items-center gap-1.5 bg-brand-background border border-brand-outline-variant/25 px-2.5 py-1.5 rounded">
                <Filter className="w-3 h-3 text-brand-on-surface-variant" />
                <select
                  value={branchFilter}
                  onChange={(e) => {
                    setBranchFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="bg-transparent text-xs font-mono text-brand-on-surface-variant hover:text-white cursor-pointer focus:outline-none border-none p-0 pr-6"
                >
                  <option value="all" className="bg-brand-surface-high">Branch: All</option>
                  {uniqueBranches.map((branch) => (
                    <option key={branch} value={branch} className="bg-brand-surface-high">
                      {branch}
                    </option>
                  ))}
                </select>
              </div>

              {/* Decision Filter dropdown */}
              <div className="flex items-center gap-1.5 bg-brand-background border border-brand-outline-variant/25 px-2.5 py-1.5 rounded">
                <Sliders className="w-3 h-3 text-brand-on-surface-variant" />
                <select
                  value={decisionFilter}
                  onChange={(e) => {
                    setDecisionFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="bg-transparent text-xs font-mono text-brand-on-surface-variant hover:text-white cursor-pointer focus:outline-none border-none p-0 pr-6"
                >
                  <option value="all" className="bg-brand-surface-high">Decision: All</option>
                  <option value="SAFE" className="bg-brand-surface-high text-brand-secondary">SAFE</option>
                  <option value="REVIEW" className="bg-brand-surface-high text-brand-tertiary">REVIEW</option>
                  <option value="BLOCK" className="bg-brand-surface-high text-brand-error">BLOCK</option>
                </select>
              </div>
            </div>
          </div>

          {/* Table Data list */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-brand-surface-lowest border-b border-brand-outline-variant/15 text-[10px] uppercase font-mono font-semibold tracking-wider text-brand-on-surface-variant">
                  <th className="px-6 py-4 cursor-pointer hover:text-white transition-colors" onClick={() => {
                    setSortField("id");
                    setSortDirection(prev => prev === "asc" ? "desc" : "asc");
                  }}>
                    <div className="flex items-center gap-1">
                      <span>Deployment ID</span>
                      <ArrowUpDown className="w-3 h-3 text-brand-on-surface-variant/40" />
                    </div>
                  </th>
                  <th className="px-6 py-4 cursor-pointer hover:text-white transition-colors" onClick={() => {
                    setSortField("repository");
                    setSortDirection(prev => prev === "asc" ? "desc" : "asc");
                  }}>
                    <div className="flex items-center gap-1">
                      <span>Repository</span>
                      <ArrowUpDown className="w-3 h-3 text-brand-on-surface-variant/40" />
                    </div>
                  </th>
                  <th className="px-6 py-4">Branch</th>
                  <th className="px-6 py-4 cursor-pointer hover:text-white transition-colors" onClick={() => {
                    setSortField("timestamp");
                    setSortDirection(prev => prev === "asc" ? "desc" : "asc");
                  }}>
                    <div className="flex items-center gap-1">
                      <span>Time</span>
                      <ArrowUpDown className="w-3 h-3 text-brand-on-surface-variant/40" />
                    </div>
                  </th>
                  <th className="px-6 py-4">Decision</th>
                  <th className="px-6 py-4 cursor-pointer hover:text-white transition-colors" onClick={() => {
                    setSortField("risk");
                    setSortDirection(prev => prev === "asc" ? "desc" : "asc");
                  }}>
                    <div className="flex items-center gap-1">
                      <span>Risk</span>
                      <ArrowUpDown className="w-3 h-3 text-brand-on-surface-variant/40" />
                    </div>
                  </th>
                  <th className="px-6 py-4 text-right cursor-pointer hover:text-white transition-colors" onClick={() => {
                    setSortField("confidence");
                    setSortDirection(prev => prev === "asc" ? "desc" : "asc");
                  }}>
                    <div className="flex items-center gap-1 justify-end">
                      <span>Confidence</span>
                      <ArrowUpDown className="w-3 h-3 text-brand-on-surface-variant/40" />
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-outline-variant/10 text-xs font-mono">
                {paginatedDeployments.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-brand-on-surface-variant">
                      No deployments match current filter criteria.
                    </td>
                  </tr>
                ) : (
                  paginatedDeployments.map((dep) => (
                    <tr key={dep.id} className="hover:bg-brand-surface-high/50 transition-colors group">
                      <td className="px-6 py-4 text-brand-primary font-semibold">{dep.id}</td>
                      <td className="px-6 py-4 text-white font-medium">{dep.repository}</td>
                      <td className="px-6 py-4">
                      <span className="px-2 py-0.5 rounded bg-brand-surface-highest text-brand-on-surface-variant font-mono text-[10px]">
                        {dep.branch}
                      </span>
                      </td>
                      <td className="px-6 py-4 text-brand-on-surface-variant">{dep.time}</td>
                      <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold border ${
                        dep.decision === 'SAFE'
                          ? 'bg-brand-secondary/10 text-brand-secondary border-brand-secondary/20'
                          : dep.decision === 'REVIEW'
                            ? 'bg-brand-tertiary/10 text-brand-tertiary border-brand-tertiary/20'
                            : 'bg-brand-error/10 text-brand-error border-brand-error/20'
                      }`}>
                        {dep.decision}
                      </span>
                      </td>
                      <td className="px-6 py-4 font-semibold text-white">{dep.risk}</td>
                      <td className="px-6 py-4 text-right text-white">{dep.confidence}%</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Table pagination */}
          <div className="px-6 py-4 border-t border-brand-outline-variant/15 flex items-center justify-between bg-brand-surface-low">
            <p className="text-brand-on-surface-variant text-xs">
              Showing <span className="text-white font-semibold">{(currentPage - 1) * itemsPerPage + 1}-{Math.min(currentPage * itemsPerPage, filteredDeployments.length)}</span> of <span className="text-white font-semibold">{filteredDeployments.length.toLocaleString()}</span> deployments
            </p>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="w-8 h-8 flex items-center justify-center rounded hover:bg-brand-surface-highest text-brand-on-surface-variant disabled:opacity-30 transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: totalPages }).map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentPage(i + 1)}
                  className={`w-8 h-8 flex items-center justify-center rounded font-mono text-xs transition-colors ${
                    currentPage === i + 1
                      ? 'bg-brand-surface-highest text-white font-bold'
                      : 'text-brand-on-surface-variant hover:bg-brand-surface-high'
                  }`}
                >
                  {i + 1}
                </button>
              ))}
              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="w-8 h-8 flex items-center justify-center rounded hover:bg-brand-surface-highest text-brand-on-surface-variant disabled:opacity-30 transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>

        </section>

        {/* ==================== POLICY & AGENT HEALTH BENTOS ==================== */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pb-10">
          
          {/* Policy Health Card */}
          <div className="bg-brand-surface-low border border-brand-outline-variant/20 rounded p-6 flex flex-col justify-between overflow-hidden relative group">
            <div className="relative z-10">
              <h4 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                <Shield className="w-5 h-5 text-brand-primary" />
                <span>Policy Health</span>
              </h4>
              <p className="text-brand-on-surface-variant text-sm max-w-sm mt-3">
                {policyHealthScore}% of your active deployment security policies are fully compiled and passing vulnerability gates.
              </p>
              <button
                onClick={() => setIsPolicyModalOpen(true)}
                className="mt-6 flex items-center gap-2 text-brand-primary hover:text-white transition-colors font-mono text-xs font-semibold"
              >
                <span>Configure Security Policies</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>

            {/* Watermark Logo */}
            <div className="absolute -right-6 -bottom-6 opacity-[0.03] group-hover:opacity-[0.06] transition-all duration-300 pointer-events-none">
              <Shield className="w-40 h-40 text-white fill-white" />
            </div>
          </div>

          {/* Agent Status Monitor */}
          <div className="bg-brand-surface-low border border-brand-outline-variant/20 rounded p-6 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-bold text-white flex items-center gap-2">
                <Activity className="w-5 h-5 text-brand-secondary" />
                <span>Agent Status</span>
              </h4>
              <span className="flex items-center gap-1.5 text-brand-secondary font-mono text-[10px] uppercase font-bold bg-brand-secondary/10 px-2 py-0.5 rounded-full">
                <span className="w-2 h-2 rounded-full bg-brand-secondary animate-pulse" />
                <span>12 Online</span>
              </span>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-brand-outline-variant/10 pb-2.5">
                <span className="text-brand-on-surface-variant uppercase flex items-center gap-2">
                  <Globe className="w-3.5 h-3.5 text-brand-primary" />
                  <span>Region: US-East-1</span>
                </span>
                <span className="text-white font-semibold">{agentLatencies.usEast}ms latency</span>
              </div>
              <div className="flex items-center justify-between border-b border-brand-outline-variant/10 pb-2.5">
                <span className="text-brand-on-surface-variant uppercase flex items-center gap-2">
                  <Globe className="w-3.5 h-3.5 text-brand-primary" />
                  <span>Region: EU-West-1</span>
                </span>
                <span className="text-white font-semibold">{agentLatencies.euWest}ms latency</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-brand-on-surface-variant uppercase flex items-center gap-2">
                  <Globe className="w-3.5 h-3.5 text-brand-primary" />
                  <span>Region: AP-South-1</span>
                </span>
                <span className="text-white font-semibold">{agentLatencies.apSouth}ms latency</span>
              </div>
            </div>
          </div>

        </div>

      </div>

      {/* ==================== MODALS & POPUPS ==================== */}
      
      {/* 1. New Deployment modal */}
      <AnimatePresence>
        {isNewDeploymentOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-brand-surface-low border border-brand-outline-variant/30 rounded-lg max-w-lg w-full overflow-hidden shadow-2xl"
            >
              <div className="p-6 border-b border-brand-outline-variant/10 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Rocket className="w-5 h-5 text-brand-primary" />
                  <h3 className="text-base font-bold text-white">Trigger New Deployment Verification</h3>
                </div>
                <button
                  onClick={() => setIsNewDeploymentOpen(false)}
                  className="p-1 hover:bg-brand-surface-high rounded text-brand-on-surface-variant hover:text-white transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleCreateDeployment} className="p-6 space-y-4 font-mono text-xs">
                <div>
                  <label className="block text-brand-on-surface-variant mb-1">Target Repository</label>
                  <input
                    type="text"
                    required
                    value={newRepo}
                    onChange={(e) => setNewRepo(e.target.value)}
                    placeholder="e.g. auth-service"
                    className="w-full bg-brand-background border border-brand-outline-variant/25 rounded p-2 text-white focus:border-brand-primary/50 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-brand-on-surface-variant mb-1">Branch Name</label>
                  <input
                    type="text"
                    required
                    value={newBranch}
                    onChange={(e) => setNewBranch(e.target.value)}
                    className="w-full bg-brand-background border border-brand-outline-variant/25 rounded p-2 text-white focus:border-brand-primary/50 focus:outline-none"
                  />
                </div>

                <div className="p-4 bg-brand-surface-lowest rounded border border-brand-outline-variant/10">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] uppercase text-brand-on-surface-variant font-bold">Threat & Code Integrity Model</span>
                    <button
                      type="button"
                      onClick={handleAIEvaluation}
                      disabled={isAnalyzing}
                      className="text-brand-primary hover:underline flex items-center gap-1.5 disabled:opacity-50"
                    >
                      <RotateCw className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
                      <span>{isAnalyzing ? "Analyzing..." : "Auto evaluate risk"}</span>
                    </button>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="p-2 bg-brand-surface-high/40 rounded">
                      <p className="text-[9px] text-brand-on-surface-variant">DECISION</p>
                      <p className={`font-bold mt-1 ${
                        newDecision === 'SAFE' ? 'text-brand-secondary' : newDecision === 'REVIEW' ? 'text-brand-tertiary' : 'text-brand-error'
                      }`}>{newDecision}</p>
                    </div>
                    <div className="p-2 bg-brand-surface-high/40 rounded">
                      <p className="text-[9px] text-brand-on-surface-variant">RISK INDEX</p>
                      <p className="font-bold mt-1 text-white">{newRisk}/100</p>
                    </div>
                    <div className="p-2 bg-brand-surface-high/40 rounded">
                      <p className="text-[9px] text-brand-on-surface-variant">CONFIDENCE</p>
                      <p className="font-bold mt-1 text-white">{newConfidence}%</p>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-brand-outline-variant/10 flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setIsNewDeploymentOpen(false)}
                    className="bg-brand-surface-high border border-brand-outline-variant/30 px-4 py-2 rounded text-brand-on-surface hover:text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="bg-brand-primary hover:bg-white text-brand-background font-bold px-4 py-2 rounded transition-colors"
                  >
                    Authorize Release
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* 2. Security Policies configurations modal */}
      <AnimatePresence>
        {isPolicyModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-brand-surface-low border border-brand-outline-variant/30 rounded-lg max-w-2xl w-full overflow-hidden shadow-2xl"
            >
              <div className="p-6 border-b border-brand-outline-variant/10 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Shield className="w-5 h-5 text-brand-primary" />
                  <h3 className="text-base font-bold text-white">Deployment Security Policies</h3>
                </div>
                <button
                  onClick={() => setIsPolicyModalOpen(false)}
                  className="p-1 hover:bg-brand-surface-high rounded text-brand-on-surface-variant hover:text-white transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
                <p className="text-xs text-brand-on-surface-variant font-mono">
                  Toggle compile gates to automatically run AST and configuration analysis routines upon deployment authorization.
                </p>

                <div className="space-y-2.5">
                  {currentProject.policyRules.map((rule) => (
                    <div
                      key={rule.id}
                      className="p-3 bg-brand-surface-high/50 rounded border border-brand-outline-variant/10 flex items-start justify-between gap-4"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold text-white">{rule.name}</span>
                          <span className="text-[9px] font-mono uppercase bg-brand-surface-highest px-1.5 py-0.5 rounded text-brand-on-surface-variant">
                            {rule.category}
                          </span>
                        </div>
                        <p className="text-[11px] text-brand-on-surface-variant">{rule.description}</p>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleTogglePolicyRule(rule.id)}
                        className={`px-3 py-1 rounded font-mono text-[10px] font-bold transition-all ${
                          rule.active
                            ? 'bg-brand-secondary/15 text-brand-secondary border border-brand-secondary/30'
                            : 'bg-brand-surface-highest text-brand-on-surface-variant border border-brand-outline-variant/10'
                        }`}
                      >
                        {rule.active ? "ACTIVE" : "DISABLED"}
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-6 border-t border-brand-outline-variant/10 bg-brand-surface-lowest flex justify-end">
                <button
                  onClick={() => setIsPolicyModalOpen(false)}
                  className="bg-brand-primary text-brand-background font-mono text-xs font-bold px-4 py-2 rounded hover:bg-white transition-colors"
                >
                  Save Policy Configuration
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
