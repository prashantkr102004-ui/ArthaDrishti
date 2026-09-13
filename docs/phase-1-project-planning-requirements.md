# ArthaDrishti: Smart Financial Assistant

## Phase 1: Project Planning & Requirements

ArthaDrishti is a personal financial analysis and planning assistant that helps an individual upload bank and credit-card statements, extract transaction data, organize it into a reliable financial dataset, analyze spending and cash-flow patterns, and later ask natural-language questions over verified financial records.

The project should be treated as a serious financial data system first and an AI assistant second. The assistant experience is valuable only if the underlying financial data is extracted, normalized, validated, and calculated deterministically.

## 1. Project Overview

ArthaDrishti will provide a structured way for users to convert personal financial documents into usable financial insight.

The initial MVP should focus on:

- Uploading PDF bank statements and PDF credit-card statements.
- Extracting transaction-level data from those documents.
- Reviewing, correcting, and confirming extracted transactions.
- Storing normalized transactions across one or more accounts.
- Producing deterministic financial analytics such as income, expenses, savings, category-wise spending, and monthly trends.
- Preparing the architecture for future natural-language querying, RAG, anomaly detection, recurring-payment detection, and planning features.

The system must not use an LLM as the source of truth for numbers. LLMs may assist with document understanding, merchant/category classification, query interpretation, and explanations, but all financial calculations must be performed by deterministic backend logic, SQL, Python, or appropriate statistical/ML methods.

## 2. Clear Problem Statement

Individuals often receive financial data in scattered formats across bank statements, credit-card statements, PDFs, emails, and account portals. These records are difficult to search, compare, analyze, and use for planning without manual spreadsheet work.

Most personal finance tools either require account-linking integrations, provide limited statement import support, or behave like generic chatbots without reliable financial data grounding. Users need a system that can transform their own documents into an auditable financial dataset and then provide trustworthy analysis over that dataset.

## 3. Real-World Problem Being Solved

The project solves the practical problem of personal financial visibility.

Many users want to answer questions such as:

- How much did I spend last month?
- Where is my money going?
- Which subscriptions or merchants are costing me the most?
- Is my spending increasing month over month?
- How much am I saving?
- Are there unusual transactions I should review?

Without structured transaction data, answering these questions requires manually reading statements, copying values into spreadsheets, cleaning descriptions, and performing calculations. This is time-consuming, error-prone, and hard to repeat every month.

## 4. Proposed Solution

ArthaDrishti will ingest supported financial PDFs, extract transaction rows, normalize them into a consistent internal schema, allow user review and correction, and generate financial analytics from the verified dataset.

The proposed system should follow this principle:

- Documents are evidence.
- Extracted transactions are structured records.
- User review resolves uncertainty.
- Deterministic logic calculates financial results.
- AI explains, classifies, and helps users interact with verified data.

For the MVP, the solution should prioritize reliable ingestion and analytics over conversational sophistication.

## 5. Primary Target User

The initial target user is one individual managing personal financial data across one or more bank accounts and credit-card accounts.

This user is likely:

- A student, early professional, freelancer, or financially curious individual.
- Comfortable uploading statements manually.
- Interested in understanding spending, income, savings, and trends.
- Not necessarily an accounting expert.
- Using the system for personal analysis and planning, not regulated financial advice.

The MVP should not target businesses, family offices, accountants, loan underwriting, tax filing, or autonomous investment decision-making.

## 6. Core User Journey

1. The user creates or opens their personal workspace.
2. The user uploads a PDF bank statement or credit-card statement.
3. The system identifies basic document metadata such as statement type, likely institution, statement period, and account reference if available.
4. The system extracts transaction rows from the PDF.
5. The system maps extracted rows into normalized transaction fields.
6. The system marks uncertain fields with confidence indicators.
7. The user reviews extracted transactions, fixes errors, and confirms import.
8. The confirmed transactions are stored against the relevant source account and source document.
9. The system calculates financial summaries and visual analytics.
10. The user reviews spending, income, savings, cash flow, category trends, and top merchants.
11. In later phases, the user asks natural-language questions over the verified data.

## 7. Main Use Cases

- Upload a PDF bank statement.
- Upload a PDF credit-card statement.
- Extract transactions from a statement.
- Detect and review low-confidence extraction results.
- Assign or edit transaction categories.
- Identify merchant names from transaction descriptions.
- Import confirmed transactions into the user's financial dataset.
- Track multiple accounts for one user.
- View monthly income, expenses, and savings.
- View category-wise spending.
- View month-over-month spending changes.
- View top merchants by amount or frequency.
- Trace each transaction back to its source document.
- Prepare verified outputs that can later be explained through natural language.

## 8. Functional Requirements

### Document Upload

- The system must allow the user to upload PDF bank statements.
- The system must allow the user to upload PDF credit-card statements.
- The system must store document metadata such as upload time, file name, detected document type, statement period if available, and extraction status.
- The system must associate extracted transactions with the source document.

### Document Processing

- The system must attempt to extract tabular transaction data from supported PDFs.
- The system must support text-based PDFs in the MVP.
- The system should detect when a PDF appears scanned or image-based and report that extraction may not be supported in the MVP.
- The system must preserve enough extraction evidence to debug mistakes, such as source page number, raw row text, or raw parsed values.

### Transaction Normalization

- The system must normalize transactions into a consistent schema.
- The system must identify transaction date.
- The system should identify value date when available.
- The system must preserve original description text.
- The system should infer merchant when feasible.
- The system must determine debit/credit direction.
- The system must parse amount.
- The system should parse balance when available.
- The system must associate each transaction with a source account.
- The system must associate each transaction with a source document.
- The system should store confidence for fields that may be uncertain.

### Review And Correction

- The system must allow users to review extracted transactions before final import.
- The system must highlight missing, invalid, or low-confidence fields.
- The system must allow users to correct transaction fields.
- The system must avoid silently importing clearly invalid rows.

### Categorization

- The system should assign initial transaction categories.
- The system must allow users to override categories.
- The system should preserve the distinction between deterministic rules and AI-assisted classifications.
- The system should store classification confidence when category or merchant extraction is uncertain.

### Analytics

- The system must calculate total income for a selected period.
- The system must calculate total expenses for a selected period.
- The system must calculate savings as income minus expenses.
- The system must calculate savings rate where income is greater than zero.
- The system must calculate monthly cash flow.
- The system must calculate category-wise spending.
- The system must calculate monthly trends.
- The system must calculate month-over-month comparisons.
- The system must identify top merchants.

### Traceability

- The system must allow analytics to be traced back to underlying transactions.
- Each transaction must be traceable to its source document.
- Financial summaries must be reproducible from stored transaction records.

### Natural-Language Preparation

- The MVP does not need a full natural-language assistant.
- The data model and analytics layer should be designed so a later assistant can query verified transactions and deterministic summaries.
- Natural-language answers in later phases must cite or reference computed results rather than inventing calculations.

## 9. Non-Functional Requirements

### Accuracy

- Financial calculations must be deterministic and reproducible.
- Extracted values must be reviewable before import.
- The system must avoid using LLM-generated numbers as authoritative financial records.

### Security

- Personal financial documents and transaction data must be treated as sensitive.
- The system must minimize unnecessary data exposure to third-party services.
- Secrets, API keys, and uploaded documents must not be committed to source control.

### Privacy

- Users should understand what data is stored and what is sent to any external model or service.
- Future cloud deployment must include strong access control and data isolation.
- The architecture should support deletion of uploaded documents and extracted records.

### Reliability

- Failed extraction must produce a clear status and actionable error.
- The system should be resilient to different bank statement layouts within the initially supported scope.
- Analytics should handle missing categories, missing balances, duplicate imports, and incomplete months gracefully.

### Auditability

- Imported transactions should retain raw source context where possible.
- User edits should be distinguishable from machine extraction.
- The system should support debugging why a transaction was categorized or classified a certain way.

### Usability

- The MVP should make review and correction efficient.
- Analytics should be understandable without requiring accounting knowledge.
- Errors should be written in user-facing language, not only developer logs.

### Maintainability

- Extraction, normalization, storage, analytics, and AI-assisted explanation should be separated conceptually.
- The architecture should allow new document templates and institutions to be added incrementally.
- The analytics logic should be testable independently of the UI and LLM layer.

### Performance

- MVP processing can be asynchronous but should provide clear status.
- Typical personal statements should process within an acceptable interactive time window.
- Analytics over one user's personal transaction history should load quickly.

## 10. MVP Scope

The MVP should include only the minimum feature set needed to prove the core product loop:

- Single-user local or authenticated workspace.
- Upload PDF bank statements.
- Upload PDF credit-card statements.
- Support text-based PDFs first.
- Extract transaction rows from a limited set of statement layouts.
- Normalize transaction data into a consistent schema.
- Review and correct extracted transactions before import.
- Store transactions with source account and source document references.
- Basic category assignment with user correction.
- Deterministic financial analytics:
  - total income
  - total expenses
  - savings
  - savings rate
  - monthly cash flow
  - category-wise spending
  - monthly trends
  - month-over-month comparisons
  - top merchants
- Basic dashboard or reporting interface.
- Clear separation between verified financial data and AI-generated explanations.

Critical scope judgment: the MVP should prove that the system can produce trustworthy structured financial data from real statements. A polished chatbot over unreliable extracted data would be impressive-looking but weak as an engineering project.

## 11. Explicitly Excluded MVP Features

The following should not be included in the first MVP:

- Live bank account linking.
- Support for every bank, card issuer, country, currency, or statement format.
- Scanned PDF OCR unless it becomes necessary for the selected test documents.
- Full RAG-based document chat.
- Autonomous investment recommendations.
- Trading or portfolio execution.
- Tax filing.
- Loan eligibility advice.
- Multi-user household collaboration.
- Business accounting workflows.
- Voice assistant features.
- Multi-agent systems.
- Forecasting and long-term planning.
- Complex anomaly detection.
- Recurring-payment detection.
- Budget automation.
- Mobile app.
- Email inbox ingestion.
- Real-time notifications.

Some of these are good future features, but including them in the MVP would dilute the core proof: accurate extraction, normalization, review, and analytics.

## 12. Future/Advanced Features

Once the MVP foundation is stable, later phases may add:

- Natural-language financial Q&A over verified transactions.
- RAG over source documents and transaction records.
- Institution-specific extraction adapters.
- OCR for scanned statements.
- Recurring-payment and subscription detection.
- Anomaly and unusual spending detection.
- Cash-flow forecasting.
- Budget recommendations.
- Financial goal planning.
- What-if analysis.
- Multi-account reconciliation.
- Duplicate transaction detection across accounts.
- Merchant normalization learning from user corrections.
- Personalized category rules.
- Export to CSV, Excel, or accounting tools.
- Voice interface.
- Multi-agent financial workflow orchestration.
- Privacy-preserving local model options.
- Secure cloud sync.

## 13. Key Assumptions

- The initial user manually uploads documents.
- The initial user is an individual, not an organization.
- The first supported files are PDF bank statements and PDF credit-card statements.
- The MVP can begin with text-based PDFs rather than scanned image PDFs.
- One user may have multiple accounts.
- Not every statement provides value date or balance.
- Bank and card statement formats vary significantly.
- User review is necessary because extraction will not be perfect.
- Categories and merchants may require user correction.
- Analytics are only as trustworthy as the confirmed transaction dataset.
- The project is a financial analysis assistant, not a regulated adviser or autonomous investment product.

## 14. System Constraints

- LLMs must not be treated as the source of truth for transaction amounts, balances, totals, or financial metrics.
- Financial calculations must be deterministic.
- The MVP must avoid overbroad document support.
- The system must preserve source traceability for transactions.
- The system must handle sensitive financial data securely from the beginning.
- Extraction confidence and uncertainty must be represented explicitly.
- The architecture must support multiple accounts per user eventually, even if the first demo uses one account.
- The project must remain feasible for a final-year/portfolio timeline.

## 15. Data The System Will Handle

The system will handle:

- Uploaded PDF financial statements.
- Document metadata.
- Raw extracted text or table fragments.
- Parsed transaction rows.
- Normalized transactions.
- User-corrected transaction fields.
- Account metadata.
- Categories.
- Merchant names.
- Analytics summaries.
- Extraction and classification confidence scores.
- Processing statuses and error messages.

Sensitive data may include:

- Names.
- Account numbers or masked account numbers.
- Card numbers or masked card numbers.
- Bank names.
- Transaction descriptions.
- Merchant names.
- Dates.
- Income information.
- Spending behavior.
- Balances.
- Personally identifying financial patterns.

## 16. Initial Supported Document Types

The MVP should initially support:

- PDF bank statements.
- PDF credit-card statements.

The MVP should preferably start with a small number of known statement layouts. For example, two or three representative banks/card issuers are enough to validate the design.

The MVP should not initially support:

- Brokerage statements.
- Loan statements.
- Insurance documents.
- Tax forms.
- Salary slips.
- Receipts.
- Invoices.
- UPI app exports unless explicitly selected later.
- CSV imports unless chosen as a deliberate simplification.
- Email-based documents.

## 17. Expected Transaction Fields

Each transaction should eventually support:

- Transaction date.
- Value date if available.
- Description.
- Merchant.
- Debit/credit direction.
- Amount.
- Balance if available.
- Category.
- Source account.
- Source document.
- Extraction confidence.
- Classification confidence.
- Original/raw text where useful.
- Page number or source location where available.
- User-edited flag or edit history.

Recommended MVP field set:

- Transaction date.
- Description.
- Debit/credit direction.
- Amount.
- Category.
- Source account.
- Source document.
- Extraction confidence.
- Raw row text or source reference.

Fields such as value date, balance, merchant, and detailed edit history are valuable but should be optional in the MVP because not all statement formats expose them cleanly.

## 18. High-Level Financial Analytics Required In The MVP

The MVP analytics should include:

- Total income over a selected period.
- Total expenses over a selected period.
- Savings as income minus expenses.
- Savings rate as savings divided by income.
- Monthly cash flow.
- Category-wise spending.
- Monthly income and expense trends.
- Month-over-month comparisons.
- Top merchants by total spend.
- Top merchants by transaction count.

Analytics should be calculated from confirmed transactions only, or clearly separate confirmed and unreviewed transactions.

The MVP should avoid complex financial forecasting until the transaction dataset is accurate and sufficiently historical.

## 19. Natural-Language Questions The MVP Should Eventually Support

The MVP architecture should eventually support questions such as:

- How much did I spend last month?
- What was my total income in August?
- What was my savings rate this quarter?
- Which category increased the most compared with last month?
- What are my top five merchants this year?
- How much did I spend on food delivery?
- Show my monthly cash flow for the last six months.
- Did my expenses increase month over month?
- Which transactions make up my travel spending?
- Which account had the most outgoing money last month?
- Why is my savings lower this month?
- Are there transactions that need review?

These questions should be answered by translating user intent into deterministic queries and analytics, then using an LLM only to explain the verified results.

## 20. Security/Privacy Requirements That Must Influence The Architecture From The Beginning

- Uploaded financial documents must be stored securely.
- Sensitive files must never be committed to source control.
- The system should support deleting uploaded documents and derived transaction data.
- Access control must be designed before cloud deployment.
- User data must be isolated from other users if multi-user support is added.
- Logs must avoid storing raw sensitive financial data unless explicitly required and protected.
- External LLM usage must be intentional, minimal, and documented.
- If data is sent to an external model, the system should send the smallest necessary context.
- The system should distinguish between local deterministic processing and external AI processing.
- Secrets must be stored in environment variables or a secure secret manager.
- The architecture should support encryption at rest for uploaded documents and sensitive records in future deployment.
- The system should provide traceability for AI-assisted classifications.
- The product must clearly state that it provides analysis and planning support, not professional financial, legal, tax, or investment advice.

## 21. Major Technical Risks

### PDF Extraction Variability

Bank and credit-card statements vary widely in layout, tables, date formats, merged columns, page headers, footers, and balance representations. This is the biggest MVP risk.

Better MVP approach: support a small, explicit set of statement layouts and design the parser system so new layouts can be added incrementally.

### Scanned Documents And OCR

Scanned PDFs require OCR and introduce more extraction errors.

Better MVP approach: treat scanned PDFs as unsupported or experimental unless the selected sample documents require OCR.

### Incorrect Financial Numbers

Wrong amounts, dates, or debit/credit direction would damage user trust.

Better MVP approach: require review before import and calculate analytics only from confirmed records.

### Overusing LLMs

LLMs may hallucinate numbers, categories, or explanations.

Better MVP approach: use LLMs only around verified data and store confidence or provenance for AI-assisted fields.

### Ambiguous Credit-Card Semantics

Credit-card statements may represent purchases, payments, credits, interest, and fees differently from bank statements.

Better MVP approach: model transaction direction carefully and avoid forcing credit-card records into simplistic income/expense assumptions without rules.

### Duplicate Imports

Users may upload overlapping statements or the same document twice.

Better MVP approach: design deduplication and document fingerprinting early, even if the first implementation is simple.

### Category Quality

Merchant descriptions are messy, abbreviated, and institution-specific.

Better MVP approach: use a combination of rules, user overrides, and later learned preferences rather than expecting perfect automatic categorization.

### Scope Creep

RAG, anomaly detection, forecasting, and multi-agent systems are attractive but premature.

Better MVP approach: keep these as future architecture considerations, not MVP deliverables.

## 22. Success Criteria For The MVP

The MVP is successful if:

- A user can upload at least one supported bank statement PDF.
- A user can upload at least one supported credit-card statement PDF.
- The system extracts transaction rows into a normalized structure.
- The user can review and correct extracted transactions.
- Confirmed transactions are stored with source document and account references.
- The system calculates income, expenses, savings, savings rate, monthly cash flow, category spending, trends, comparisons, and top merchants deterministically.
- Analytics can be traced back to underlying transactions.
- Low-confidence or failed extractions are visible to the user.
- The project clearly separates financial computation from AI-generated explanation.
- The implementation remains small enough to finish, demo, and explain in a final-year/portfolio review.

## 23. Definition Of Done For Phase 1

Phase 1 is done when:

- The problem statement is clear.
- The MVP user and use cases are defined.
- Supported MVP document types are fixed.
- MVP analytics are defined.
- Excluded features are explicitly documented.
- Key assumptions and risks are documented.
- Security and privacy requirements are documented.
- The team has agreed on architecture decisions needed before coding.
- There is enough clarity to begin Phase 2 without debating basic product scope.

## Architecture Decisions We Should Lock Before Coding

Before Phase 2 begins, the following decisions should be agreed upon:

- Backend language and framework.
- Frontend framework and UI approach.
- Database choice.
- Whether the MVP is local-first, cloud-hosted, or hybrid.
- Authentication approach, if any, for the MVP.
- File storage strategy for uploaded PDFs.
- Whether uploaded PDFs are retained after extraction or optionally deleted.
- Initial statement layouts or institutions to support.
- PDF extraction libraries and fallback strategy.
- Whether OCR is excluded, experimental, or required.
- Canonical transaction schema.
- Account model and how multiple accounts are represented.
- Category taxonomy for MVP analytics.
- Merchant normalization strategy.
- Confidence scoring approach for extraction and classification.
- Review workflow for uncertain fields.
- Duplicate document and duplicate transaction detection strategy.
- Currency handling strategy.
- Date and timezone handling strategy.
- Rules for credit-card purchases, payments, refunds, fees, and reversals.
- Analytics definitions for income, expenses, savings, and savings rate.
- Boundary between deterministic analytics and LLM-generated explanations.
- Whether any external LLM/API is used in the MVP.
- Privacy policy assumptions for local demo versus deployed demo.
- Logging policy for sensitive financial data.
- Test strategy and sample statement dataset.
- Demo success path for the final-year/portfolio presentation.

## Critical Scope Evaluation

The strongest version of this project is not a broad AI finance chatbot. It is a trustworthy financial data pipeline with an assistant layer on top.

The MVP should resist the temptation to include RAG, forecasting, anomaly detection, recurring-payment detection, or multi-agent orchestration immediately. Those features depend on clean, normalized, traceable transaction data. Building them too early would increase complexity without proving the core system.

The first technical milestone should be narrow and rigorous: extract transactions from a few real PDF statement formats, let the user review them, store them cleanly, and compute reliable analytics. That is already a meaningful and portfolio-worthy challenge.

## Phase 1 Completion Checklist

- [ ] Project overview is documented.
- [ ] Problem statement is documented.
- [ ] Real-world problem is documented.
- [ ] Proposed solution is documented.
- [ ] Primary target user is documented.
- [ ] Core user journey is documented.
- [ ] Main use cases are documented.
- [ ] Functional requirements are documented.
- [ ] Non-functional requirements are documented.
- [ ] MVP scope is documented.
- [ ] Explicitly excluded MVP features are documented.
- [ ] Future/advanced features are documented.
- [ ] Key assumptions are documented.
- [ ] System constraints are documented.
- [ ] Data handled by the system is documented.
- [ ] Initial supported document types are documented.
- [ ] Expected transaction fields are documented.
- [ ] MVP financial analytics are documented.
- [ ] Future natural-language questions are documented.
- [ ] Security and privacy requirements are documented.
- [ ] Major technical risks are documented.
- [ ] MVP success criteria are documented.
- [ ] Definition of Done for Phase 1 is documented.
- [ ] Architecture decisions to lock before coding are documented.
- [ ] MVP scope has been reviewed for overreach.
- [ ] Phase 2 has not started automatically.
