/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { Incident } from '../types';

export const INITIAL_INCIDENTS: Incident[] = [
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
