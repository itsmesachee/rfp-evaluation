"""
Generate 4 synthetic supplier RFP PDFs with intentionally different strengths/weaknesses.
Each PDF is 2-4 pages. All data is fictional.
"""
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

OUT_DIR = Path(__file__).parent / "data" / "sample_pdfs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

styles = getSampleStyleSheet()
title_style = ParagraphStyle("Title2", parent=styles["Title"], fontSize=20, spaceAfter=12)
h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=14, spaceBefore=12, spaceAfter=6)
h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=4)
body = ParagraphStyle("Body2", parent=styles["BodyText"], fontSize=10, leading=14, spaceAfter=6)
small = ParagraphStyle("Small", parent=styles["BodyText"], fontSize=9, leading=12, spaceAfter=4)
bullet = ParagraphStyle("Bullet", parent=body, leftIndent=18, bulletIndent=8)

def build_pdf(filename, supplier, sections):
    path = OUT_DIR / filename
    doc = SimpleDocTemplate(str(path), pagesize=LETTER,
                            topMargin=0.7*inch, bottomMargin=0.7*inch,
                            leftMargin=0.8*inch, rightMargin=0.8*inch,
                            title=f"RFP Response - {supplier}")
    story = [Paragraph(f"RFP Response: {supplier}", title_style),
             Paragraph("Procurement Request: Enterprise Workflow Automation Platform", small),
             Paragraph("All information in this proposal is fictional and created for evaluation purposes.", small),
             Spacer(1, 0.1*inch)]
    for heading, paras in sections:
        story.append(Paragraph(heading, h1))
        for p in paras:
            if isinstance(p, str):
                if p.startswith("• "):
                    story.append(Paragraph(p[2:], bullet, bulletText="•"))
                else:
                    story.append(Paragraph(p, body))
            else:  # table data
                t = Table(p)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eef2f7")),
                    ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                    ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                    ("FONTSIZE", (0,0), (-1,-1), 9),
                    ("TOPPADDING", (0,0), (-1,-1), 6),
                    ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ]))
                story.append(t)
                story.append(Spacer(1, 0.08*inch))
    doc.build(story)
    print(f"Wrote {path} ({path.stat().st_size} bytes)")

# --- Apex Systems: strong technical + security, higher price, moderate schedule ---
apex = [
    ("1. Executive Summary", [
        "Apex Systems proposes a cloud-native workflow automation platform built on a microservices architecture with Kubernetes orchestration, event-driven messaging via Apache Kafka, and a React-based user portal.",
        "We have carefully reviewed the requirement for 5,000 concurrent users, 99.9% uptime, and integration with SAP, Salesforce, and Okta SSO. Our solution directly addresses each with proven patterns from 12 prior enterprise deployments.",
        "• Proposed approach: phased delivery with architecture runway in Sprint 0, ensuring scalability from day one.",
        "• Key differentiator: reference architecture validated at 3x required throughput in load testing (15,000 concurrent users).",
    ]),
    ("2. Proposed Solution & Technical Architecture", [
        "Architecture: Microservices (12 services) on Amazon EKS, PostgreSQL with read replicas, Redis cache, Kafka for async workflows. API gateway with rate limiting and OpenAPI 3.1 specs.",
        "Integrations: Pre-built connectors for SAP S/4HANA (IDoc/BAPI), Salesforce (Bulk API 2.0), Okta (SAML/OIDC). Integration layer includes retry with exponential backoff, dead-letter queues, and idempotency keys.",
        "Scalability: Horizontal pod autoscaling (HPA) on CPU and custom Kafka-lag metrics. Load test evidence: p95 latency 320ms at 15k concurrent users (report attached as Appendix A in full proposal).",
        "• Technology fit: aligns with client's AWS-first policy; Infrastructure as Code with Terraform modules provided.",
        "• Data migration: ETL pipeline with validation checksums; rollback runbook included.",
    ]),
    ("3. Implementation Plan & Timeline", [
        "Moderate 24-week delivery across 4 phases: Foundation (6 wks), Core Workflows (8 wks), Integrations (6 wks), UAT & Hypercare (4 wks).",
        [[ "Phase", "Duration", "Key Milestones"],
         ["Foundation", "Wks 1-6", "EKS cluster, CI/CD, auth integration"],
         ["Core Workflows", "Wks 7-14", "8 priority workflows live in staging"],
         ["Integrations", "Wks 15-20", "SAP/Salesforce/Okta certified"],
         ["UAT & Hypercare", "Wks 21-24", "Cutover, 30-day hypercare"]],
        "Team: 1 delivery lead, 2 architects, 4 backend, 2 frontend, 1 QA automation, 1 DevOps. RACI matrix provided.",
        "Risk plan: integration dependency on client SAP team mitigated by mock services and 2-week buffer; risk register with 14 items and owners.",
    ]),
    ("4. Commercials & Price Table", [
        [[ "Item", "Cost (USD)"],
         ["Implementation (fixed fee)", "$485,000"],
         ["Licenses Year 1 (5,000 users)", "$120,000"],
         ["Managed hosting Year 1", "$60,000"],
         ["Total Year 1", "$665,000"]],
        "Assumptions: client provides AWS accounts and SAP sandbox by Week 2; change requests billed at $185/hr; price valid 90 days.",
        "Pricing is at the higher end, reflecting senior staffing and extended hypercare. Volume discount of 8% available for 3-year commitment.",
        "Total cost of ownership (3 years): $1.45M including support.",
    ]),
    ("5. Security, Compliance & Risk Controls", [
        "Certifications: ISO 27001:2022, SOC 2 Type II (report available under NDA). Data encrypted AES-256 at rest, TLS 1.3 in transit.",
        "Privacy: GDPR and CCPA compliant; data residency in us-east-1; DPA provided. PII tokenization in logs.",
        "Auditability: immutable audit trail (WORM storage), SIEM forwarding to Splunk, quarterly pen tests by independent firm.",
        "• Controls: least-privilege IAM, MFA enforced, secrets in AWS Secrets Manager with rotation.",
        "• Business continuity: RPO 15 min, RTO 2 hrs, multi-AZ with tested failover.",
    ]),
    ("6. Support Model, Experience & References", [
        "Support: 24/7 follow-the-sun, 99.9% SLA, 15-min P1 response. Dedicated TAM and quarterly business reviews.",
        "Experience: 12 enterprise workflow deployments (2019-2025), including 2 Fortune 500 manufacturers. Average CSAT 4.6/5.",
        "References: (1) Global logistics firm – 8,000 users, on-time delivery; (2) Financial services – SAP integration, contact available upon request.",
        "Team certifications: 6x AWS Solutions Architect Pro, 3x CKA.",
    ]),
]

bright = [
    ("1. Executive Summary", [
        "BrightPath Tech offers the fastest, most affordable path to workflow automation: a low-code platform that can go live in 12 weeks at the lowest price in this evaluation.",
        "We understand you need core workflow digitization quickly. Our streamlined approach prioritizes speed and cost-efficiency over extensive customization.",
        "• Go-live in 12 weeks – 50% faster than typical enterprise timelines.",
        "• Total Year 1 cost of $295,000 – significantly below market average.",
    ]),
    ("2. Proposed Solution & Technical Approach", [
        "Platform: Our BrightFlow low-code suite (SaaS) with drag-and-drop workflow builder, hosted in our multi-tenant cloud.",
        "Integrations: REST API connectors for Salesforce and Okta available. SAP integration via CSV import and scheduled sync (real-time BAPI integration listed as roadmap item, not in Phase 1).",
        "Scalability: Vendor states support for up to 10,000 users; however no independent load-test report is included in this proposal.",
        "• Customization limits: complex branching logic requires professional services add-on.",
        "Note: architecture diagram is high-level; detailed integration sequence diagrams are not provided.",
    ]),
    ("3. Implementation Plan & Timeline", [
        "Aggressive 12-week plan: Design (3 wks), Build (5 wks), UAT (2 wks), Go-live (2 wks).",
        [[ "Phase", "Duration", "Milestones"],
         ["Design", "Wks 1-3", "Requirements sign-off"],
         ["Build", "Wks 4-8", "6 core workflows configured"],
         ["UAT & Go-live", "Wks 9-12", "Production cutover"]],
        "Team: 1 project manager, 2 low-code configurators, 1 QA (part-time). Client is expected to provide a full-time product owner.",
        "Risk plan: brief – identifies timeline dependency on client availability; no detailed mitigation for integration delays.",
    ]),
    ("4. Commercials & Price Table", [
        [[ "Item", "Cost (USD)"],
         ["Implementation (fixed)", "$145,000"],
         ["SaaS Year 1 (5,000 users)", "$110,000"],
         ["Support Year 1", "$40,000"],
         ["Total Year 1", "$295,000"]],
        "Assumptions: standard SaaS terms; data migration limited to 50k records; additional records at $2k per 10k.",
        "Lowest total cost among bidders. Price lock for 60 days. Renewal uplift capped at 5%.",
        "3-year TCO: $780k – the most economical option.",
    ]),
    ("5. Security, Compliance & Risk Controls", [
        "Security overview: BrightFlow is hosted in a SOC 2-aligned facility. Encryption at rest and in transit is stated.",
        "Compliance detail is limited in this proposal: no ISO 27001 certificate number provided, no pen-test summary, no DPA attached.",
        "Audit logs are available in the admin console (30-day retention on standard plan).",
        "Privacy: vendor states GDPR readiness; specific data residency options are not documented.",
    ]),
    ("6. Support Model, Experience & References", [
        "Support: business-hours support (9-5 ET), email + portal; 4-hour P1 response. 24/7 available as $35k/yr add-on.",
        "Experience: 8 small-to-mid deployments (largest 1,200 users). No prior SAP S/4HANA integration reference provided.",
        "References: one mid-market retail client (600 users) – contact details included; second reference listed as 'available on request' without detail.",
        "Team is lean; resumes not included.",
    ]),
]

nexa = [
    ("1. Executive Summary", [
        "NexaWorks proposes a balanced, low-risk delivery combining a proven integration framework with the strongest implementation discipline in this set.",
        "We deeply understand the need for predictable delivery: our proposal emphasizes milestones, staffing clarity, and a support model that has earned 4.8/5 CSAT across 20 projects.",
        "• Standout: the most detailed implementation plan with resource-loaded schedule and contingency.",
        "• Balanced commercial and technical offer with transparent assumptions.",
    ]),
    ("2. Proposed Solution & Technical Architecture", [
        "Architecture: modular monolith-to-microservices path on Azure AKS, .NET 8 services, Azure SQL, Service Bus. Sensible and maintainable.",
        "Integrations: Nexa Integration Hub with certified adapters for SAP (RFC/BAPI), Salesforce, Okta. Includes canonical data model and error-handling framework with retries and alerting.",
        "Scalability: designed for 8,000 concurrent users with autoscaling; load test summary shows p95 410ms at 8k users (adequate headroom).",
        "• Technical fit: good – aligns with client's Microsoft Entra ID roadmap; Terraform + Bicep IaC.",
        "• Migration: phased cutover with parallel run of 2 weeks; data validation dashboards.",
    ]),
    ("3. Implementation Plan & Timeline (Strongest)", [
        "18-week plan with the clearest work breakdown: 5 phases, 32 milestones, resource-loaded Gantt, and 10% schedule contingency.",
        [[ "Phase", "Duration", "Milestones & Deliverables"],
         ["Mobilize", "Wks 1-2", "Charter, RACI, environments"],
         ["Design", "Wks 3-6", "Signed-off FDD, API contracts"],
         ["Build", "Wks 7-13", "10 workflows, integration sprints"],
         ["Validate", "Wks 14-16", "SIT, pen test, UAT"],
         ["Deploy", "Wks 17-18", "Cutover + 45-day hypercare"]],
        "Staffing: 1 program manager (PMP), 1 solution architect, 5 engineers, 2 QA, 1 change manager. Named CVs attached; backfill plan included.",
        "Risk plan: exemplary – 22 risks with probability/impact, owners, triggers, and mitigations; e.g., SAP access delay mitigated by sandbox + stubbed APIs from Week 3.",
        "Governance: weekly steering, burn-down tracking, definition-of-done checklists.",
    ]),
    ("4. Commercials & Price Table", [
        [[ "Item", "Cost (USD)"],
         ["Implementation", "$340,000"],
         ["Licenses Year 1", "$105,000"],
         ["Hosting & Support Y1", "$55,000"],
         ["Total Year 1", "$500,000"]],
        "Assumptions: detailed – 8 pages of assumptions covering roles, data volumes (up to 200k records), environments, and out-of-scope items.",
        "Pricing clarity is excellent: fixed-fee with unit rates for changes ($175/hr), no hidden uplift.",
        "3-year TCO: $1.12M.",
    ]),
    ("5. Security, Compliance & Risk Controls", [
        "Certifications: ISO 27001:2022 certified, SOC 2 Type II. Pen test summary (2025) included with 2 medium findings remediated.",
        "Controls: Azure Private Link, Key Vault with rotation, MFA/Conditional Access, WAF + DDoS protection.",
        "Privacy: GDPR/CCPA compliant, EU/US data residency options, DPA attached. Retention policies configurable.",
        "Auditability: centralized logging to Sentinel, 1-year audit retention, quarterly access reviews.",
    ]),
    ("6. Support Model, Experience & References (Strongest)", [
        "Support: 24/7 with 99.95% SLA, 10-min P1 response, named TAM, monthly service reviews, and included admin training (3 cohorts).",
        "Experience: 20 enterprise projects, 6 with SAP + Salesforce + SSO together. CSAT 4.8/5 (2024-2025).",
        "References: (1) Healthcare network – 6,500 users, delivered 2 weeks early; (2) Manufacturing – SAP S/4HANA integration, both contacts provided with quotes.",
        "Knowledge transfer: runbooks, recorded training, and 60-day shadowing.",
    ]),
]

orbit = [
    ("1. Executive Summary", [
        "Orbit Digital brings the deepest relevant experience: 25 enterprise automation programs, including 5 in your industry, with strong client references.",
        "Our approach leans on proven playbooks and senior talent. We propose a pragmatic platform on Google Cloud with a focus on user adoption.",
        "• Most experienced bidder with verifiable references and senior team.",
        "• Medium pricing with flexible commercial terms.",
    ]),
    ("2. Proposed Solution & Technical Approach", [
        "Platform: Google Cloud Run + Workflows, Cloud SQL, Pub/Sub, Angular portal. Sound managed-service choices.",
        "Integrations: description is vague – states 'seamless integration with SAP, Salesforce, and Okta via APIs' but provides no connector details, no sequence diagrams, no error-handling description.",
        "Scalability: mentions autoscaling; no load-test evidence included. Statement: 'expected to handle required load.'",
        "• Gap: integration plan lacks specificity – adapter maturity, data mapping, and cutover approach are not documented.",
        "• Strength: UX approach is well described with design system and usability testing plan.",
    ]),
    ("3. Implementation Plan & Timeline", [
        "20-week plan: Discover (4 wks), Build (10 wks), Test (4 wks), Launch (2 wks).",
        [[ "Phase", "Duration", "Milestones"],
         ["Discover", "Wks 1-4", "Blueprint sign-off"],
         ["Build", "Wks 5-14", "Workflows iteratively released"],
         ["Test & Launch", "Wks 15-20", "UAT, cutover, hypercare (30 days)"]],
        "Team: senior-heavy – 1 partner sponsor, 1 architect (15 yrs), 4 engineers, 1 UX lead. Bios included.",
        "Risk plan: moderate – 8 risks listed; integration risk acknowledged but mitigation is generic ('close collaboration').",
    ]),
    ("4. Commercials & Price Table", [
        [[ "Item", "Cost (USD)"],
         ["Implementation", "$375,000"],
         ["Licenses Year 1", "$95,000"],
         ["Support Year 1", "$50,000"],
         ["Total Year 1", "$520,000"]],
        "Assumptions: reasonable; 90-day price validity; T&M for out-of-scope at $190/hr.",
        "Medium pricing. 3-year TCO ~$1.18M. Flexible payment milestones tied to acceptance.",
        "Discount: 5% for upfront annual payment.",
    ]),
    ("5. Security, Compliance & Risk Controls", [
        "Certifications: ISO 27001:2022, SOC 2 Type II. Cloud Security Alliance STAR listed.",
        "Controls: VPC-SC, Cloud KMS, Binary Authorization, MFA enforced. Annual pen tests; latest summary available on request.",
        "Privacy: GDPR compliant; DPA available. Data residency in us-central1.",
        "Auditability: Cloud Audit Logs with 400-day retention; SIEM export supported.",
        "Overall solid, though integration-specific security (e.g., SAP credential vaulting) is not detailed.",
    ]),
    ("6. Support Model, Experience & References (Strongest Experience)", [
        "Support: 24/7, 99.9% SLA, 20-min P1 response, dedicated success manager, adoption playbooks.",
        "Experience: 25 enterprise programs; 5 in manufacturing/logistics; 3 with 10k+ users. Industry awards listed.",
        "References: three detailed references with named contacts, project sizes, and outcome metrics – the most convincing in this set.",
        "• Reference 1: National distributor – 11,000 users, 98% adoption.",
        "• Reference 2: Industrial firm – SAP + Okta integration (note: Salesforce was not in scope there).",
        "Team tenure averages 7 years; low attrition cited.",
    ]),
]

build_pdf("Apex_Systems_RFP.pdf", "Apex Systems", apex)
build_pdf("BrightPath_Tech_RFP.pdf", "BrightPath Tech", bright)
build_pdf("NexaWorks_RFP.pdf", "NexaWorks", nexa)
build_pdf("Orbit_Digital_RFP.pdf", "Orbit Digital", orbit)
print("Done.")
