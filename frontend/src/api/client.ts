export interface DeploymentEvent {
  correlation_id: string;
  repository: string;
  commit_message: string;
  author: string;
  pull_request_title: string;
  pull_request_body: string;
  status: 'pending' | 'complete' | 'failed';
  decision?: 'SAFE' | 'REVIEW' | 'BLOCK';
  overall_score?: number;
  overall_confidence?: number;
  severity?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  summary?: string;
  reasons?: string[];
  recommendations?: string[];
  generated_at?: string;
  agents?: Record<string, any>;
}

// Seeded local mock data for high-fidelity initial display
const MOCK_DEPLOYMENTS: DeploymentEvent[] = [
  {
    correlation_id: "cf6691cc-b711-4b61-9e7f-2806952df01d",
    repository: "myorg/payments-api",
    commit_message: "fix: database connection pool exhaustion under high load",
    author: "developer",
    pull_request_title: "Optimize postgres connection pooling",
    pull_request_body: "Adjusts pool settings and adds connection timeouts for Payments DB.",
    status: "complete",
    decision: "SAFE",
    overall_score: 22,
    overall_confidence: 0.88,
    severity: "LOW",
    summary: "The deployment is safe to proceed. Code risk detected routine db pool config updates with zero security vulnerabilities. Infrastructure metrics are optimal.",
    reasons: [
      "No critical files or dependencies modified.",
      "Database pool configuration is safe and non-blocking."
    ],
    recommendations: [
      "Deploy during off-peak hours as a standard best practice."
    ],
    generated_at: new Date(Date.now() - 3600000 * 2).toISOString(),
    agents: {
      "code-risk": { score: 15, severity: "low", confidence: 0.90, reasons: [], recommendations: [] },
      "infra-risk": { score: 25, severity: "low", confidence: 0.85, reasons: [], recommendations: [] },
      "incident-history": { score: 10, severity: "low", confidence: 0.90, reasons: [], recommendations: [] }
    }
  },
  {
    correlation_id: "a3f5a2b8-932f-4101-b842-bc2459588b23",
    repository: "myorg/auth-service",
    commit_message: "feat: Add database migrations and disable oauth validation temporarily",
    author: "sre-lead",
    pull_request_title: "Privileged container update and RDS database migration for OAuth",
    pull_request_body: "Updating the security configuration to include database schema changes and authentication changes.",
    status: "complete",
    decision: "BLOCK",
    overall_score: 74,
    overall_confidence: 0.89,
    severity: "HIGH",
    summary: "The deployment is blocked due to high-risk database migrations combined with disabled OAuth validation and privileged containers in infrastructure.",
    reasons: [
      "Disabled OAuth validation creates immediate security vulnerability.",
      "Infrastructure analysis detected privileged container configs.",
      "Database migrations modifying tables holding credentials."
    ],
    recommendations: [
      "Do NOT merge without disabling privileged security context.",
      "Restore OAuth verification checks before shipping.",
      "Validate Postgres rollback plan."
    ],
    generated_at: new Date(Date.now() - 3600000 * 6).toISOString(),
    agents: {
      "code-risk": { score: 72, severity: "high", confidence: 0.91, reasons: ["Disabled OAuth verification"], recommendations: ["Restore authentication guards"] },
      "infra-risk": { score: 65, severity: "high", confidence: 0.88, reasons: ["Privileged container configuration"], recommendations: ["Remove privileged tag"] },
      "incident-history": { score: 55, severity: "medium", confidence: 0.85, reasons: ["Similar auth incident resolved in past"], recommendations: ["Audit access keys"] }
    }
  },
  {
    correlation_id: "e386a9d5-4bf5-11e2-9b3b-0800200c9a66",
    repository: "myorg/frontend-dashboard",
    commit_message: "style: Update landing page UI and navigation link highlights",
    author: "designer",
    pull_request_title: "Refactor global header styles for premium branding",
    pull_request_body: "Update CSS layouts, add Outfit font import, improve responsive margins.",
    status: "complete",
    decision: "SAFE",
    overall_score: 5,
    overall_confidence: 0.95,
    severity: "LOW",
    summary: "The deployment is safe. Clean markup changes and CSS revisions only. No operational or infrastructure impact detected.",
    reasons: [
      "Only style and presentation files affected."
    ],
    recommendations: [
      "Perform visual regression tests on staging before shipping."
    ],
    generated_at: new Date(Date.now() - 3600000 * 12).toISOString(),
    agents: {
      "code-risk": { score: 5, severity: "low", confidence: 0.98, reasons: [], recommendations: [] },
      "infra-risk": { score: 5, severity: "low", confidence: 0.95, reasons: [], recommendations: [] },
      "incident-history": { score: 5, severity: "low", confidence: 0.92, reasons: [], recommendations: [] }
    }
  }
];

// Seeded local mock data for Incident History Page
export interface MockIncident {
  incident_id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  outcome: string;
  service: string;
  environment: string;
  similarity?: number;
}

export const MOCK_INCIDENTS: MockIncident[] = [
  {
    incident_id: "INC-101",
    title: "Authentication middleware removed",
    description: "Production deployment accidentally removed API authentication.",
    severity: "critical",
    outcome: "Rollback",
    service: "Authentication API",
    environment: "production"
  },
  {
    incident_id: "INC-160",
    title: "Rolling deployment failure",
    description: "New pods failed readiness while old pods drained.",
    severity: "medium",
    outcome: "Production Outage",
    service: "Release Engineering",
    environment: "production"
  },
  {
    incident_id: "INC-172",
    title: "Failed deployment",
    description: "Release job promoted artifact with failing smoke tests.",
    severity: "low",
    outcome: "Security Incident",
    service: "CI Pipeline",
    environment: "staging"
  },
  {
    incident_id: "INC-161",
    title: "Blue-Green deployment failure",
    description: "Traffic switched to unhealthy green pool.",
    severity: "medium",
    outcome: "Manual Intervention",
    service: "Release Engineering",
    environment: "staging"
  }
];

class ApiClient {
  private localDeployments: DeploymentEvent[] = [...MOCK_DEPLOYMENTS];

  async getDeployments(): Promise<DeploymentEvent[]> {
    // Return combined mock and real deployments
    return [...this.localDeployments].sort(
      (a, b) => new Date(b.generated_at || 0).getTime() - new Date(a.generated_at || 0).getTime()
    );
  }

  async triggerDeployment(repository: string, prTitle: string, prBody: string, commitMsg: string): Promise<string> {
    const correlation_id = Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    
    const payload = {
      repository: { name: repository.split("/")[1] || repository, full_name: repository },
      pull_request: { title: prTitle, body: prBody, user: { login: "deployguard-gui" } },
      head_commit: { message: commitMsg, author: { name: "developer" }, id: correlation_id.substring(0, 8) }
    };

    // Add as pending in local cache
    const newDep: DeploymentEvent = {
      correlation_id,
      repository,
      commit_message: commitMsg,
      author: "deployguard-gui",
      pull_request_title: prTitle,
      pull_request_body: prBody,
      status: "pending",
      generated_at: new Date().toISOString()
    };
    this.localDeployments.push(newDep);

    try {
      // Trigger gateway
      const res = await fetch("/api/gateway/webhook/github", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const data = await res.json();
        // Update local item with real correlation_id if returned
        if (data.correlation_id) {
          newDep.correlation_id = data.correlation_id;
          return data.correlation_id;
        }
      }
    } catch (e) {
      console.warn("Failed to trigger webhook on real gateway. Falling back to local simulation.", e);
      
      // Simulate real agent processing asynchronously
      setTimeout(() => {
        this.simulateAgentResponses(newDep.correlation_id);
      }, 5000);
    }

    return newDep.correlation_id;
  }

  async getDecision(correlationId: string): Promise<any> {
    try {
      const res = await fetch(`/api/aggregator/decision/${correlationId}`);
      if (res.ok) {
        const decisionData = await res.json();
        
        // Sync to local client state
        const index = this.localDeployments.findIndex(d => d.correlation_id === correlationId);
        if (index !== -1) {
          const updated: DeploymentEvent = {
            ...this.localDeployments[index],
            status: (decisionData.status === "pending" ? "pending" : "complete") as "pending" | "complete" | "failed",
            decision: decisionData.decision,
            overall_score: decisionData.overall_score,
            overall_confidence: decisionData.overall_confidence,
            severity: decisionData.severity,
            summary: decisionData.summary,
            reasons: decisionData.reasons,
            recommendations: decisionData.recommendations,
            agents: decisionData.agents,
            generated_at: decisionData.generated_at || new Date().toISOString()
          };
          this.localDeployments[index] = updated;
        }
        return decisionData;
      }
    } catch (e) {
      console.warn("Failed to fetch decision from real aggregator. Reading local cache.", e);
    }

    // Fallback: Read from local state
    const dep = this.localDeployments.find(d => d.correlation_id === correlationId);
    if (dep) {
      if (dep.status === "pending") {
        return { status: "pending", correlation_id: correlationId, message: "Aggregating results..." };
      }
      return dep;
    }
    return null;
  }

  private simulateAgentResponses(correlationId: string) {
    const index = this.localDeployments.findIndex(d => d.correlation_id === correlationId);
    if (index === -1) return;

    const dep = this.localDeployments[index];
    const text = (dep.commit_message + " " + dep.pull_request_title + " " + dep.pull_request_body).toLowerCase();
    
    let codeScore = 10;
    let infraScore = 10;
    let histScore = 10;
    let reasons: string[] = [];
    let recommendations: string[] = [];

    if (text.includes("auth") || text.includes("oauth") || text.includes("login")) {
      codeScore += 40;
      reasons.push("Authentication / OAuth logic changes found in PR context.");
      recommendations.push("Ensure standard OAuth config variables are verified.");
    }
    if (text.includes("database") || text.includes("migration") || text.includes("rds")) {
      codeScore += 30;
      reasons.push("SQL schema modifications or DDL migrations detected.");
      recommendations.push("Verify DB migration rollback script handles data preservation.");
    }
    if (text.includes("privileged") || text.includes("root") || text.includes("capabilities")) {
      infraScore += 65;
      reasons.push("Infrastructure heuristics flagged container running as root / privileged.");
      recommendations.push("Configure standard security context parameters in k8s configs.");
    }

    const overallScore = Math.min(100, Math.round(codeScore * 0.4 + infraScore * 0.35 + histScore * 0.25));
    const decision = overallScore >= 60 ? 'BLOCK' : (overallScore >= 30 ? 'REVIEW' : 'SAFE');
    const severity = overallScore >= 85 ? 'CRITICAL' : (overallScore >= 60 ? 'HIGH' : (overallScore >= 30 ? 'MEDIUM' : 'LOW'));

    this.localDeployments[index] = {
      ...dep,
      status: "complete",
      decision,
      overall_score: overallScore,
      overall_confidence: 0.90,
      severity,
      summary: `The deployment resulted in a ${decision} verdict. Heuristic analysis detected score ${overallScore} based on changes: ${reasons.join(" ")}`,
      reasons,
      recommendations,
      agents: {
        "code-risk": { score: codeScore, severity: codeScore >= 60 ? "high" : "low", confidence: 0.92, reasons, recommendations },
        "infra-risk": { score: infraScore, severity: infraScore >= 60 ? "high" : "low", confidence: 0.88, reasons, recommendations },
        "incident-history": { score: histScore, severity: "low", confidence: 0.90, reasons: [], recommendations: [] }
      },
      generated_at: new Date().toISOString()
    };
  }

  async calculateSimilarity(text: string): Promise<MockIncident[]> {
    const query = text.toLowerCase();
    const results = MOCK_INCIDENTS.map(inc => {
      let score = 0.1 + Math.random() * 0.2;
      if (query.includes("auth") && inc.title.toLowerCase().includes("auth")) {
        score = 0.85 + Math.random() * 0.1;
      } else if (query.includes("deployment") && inc.title.toLowerCase().includes("deployment")) {
        score = 0.75 + Math.random() * 0.1;
      } else if (query.includes("pods") && inc.description.toLowerCase().includes("pods")) {
        score = 0.65 + Math.random() * 0.15;
      }
      return { ...inc, similarity: round(score, 3) };
    }).sort((a, b) => (b.similarity || 0) - (a.similarity || 0));

    return results;
  }
}

function round(value: number, decimals: number): number {
  return Number(Math.round(Number(value + 'e' + decimals)) + 'e-' + decimals);
}

export const api = new ApiClient();
