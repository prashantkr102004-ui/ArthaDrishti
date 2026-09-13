# Project Summary

## Abstract

ArthaDrishti is a smart personal financial assistant that converts uploaded bank and credit-card PDFs into structured transactions, deterministic analytics, document search, and explainable insights. It uses LLMs only for language interpretation and grounded explanations, never as the source of financial numbers.

## Objectives

- Ingest financial PDFs securely.
- Extract and normalize transactions.
- Store canonical financial records.
- Categorize merchants and spending.
- Calculate financial analytics deterministically.
- Answer natural-language questions through approved backend tools.
- Search unstructured document text with RAG.
- Provide explainable advanced features such as recurring payments, budgets, forecasts, and anomalies.

## Problem

Individuals often have financial data scattered across statements and accounts. Basic chatbots can summarize text, but they are unsafe as financial calculators because they may hallucinate or mishandle exact numbers.

## Proposed Solution

ArthaDrishti uses a modular FastAPI backend, PostgreSQL, deterministic financial services, and a Next.js frontend. LLMs are bounded behind approved tools and receive only verified outputs or retrieved document chunks.

## Methodology

The system was built phase by phase:

1. Planning and requirements
2. Architecture/database design
3. Development setup
4. Authentication
5. Document upload
6. PDF parsing
7. Transaction persistence
8. Categorization
9. Analytics
10. Dashboard visualization
11. Natural-language Q&A
12. RAG document search
13. Advanced insights
14. Security/testing hardening
15. Deployment/documentation/demo readiness

## Results

The final portfolio scope includes authenticated financial document upload, transaction extraction, storage, categorization, analytics, dashboard visualizations, grounded assistant answers, RAG document search, budgets/goals, forecasts, and explainable anomaly/recurrence insights.

## Limitations

- Parser support is limited to a synthetic statement layout.
- Scanned PDFs require future OCR.
- Categorization is rule-based.
- Forecasting is an estimate based on history.
- Anomaly detection is not fraud detection.
- No live bank integration.
- Not an investment adviser.

## Future Scope

More bank parsers, OCR, Open Banking integrations, richer merchant intelligence, learned categorization, notifications, encrypted object storage, email ingestion, mobile app, multilingual support, and richer reporting.

## Conclusion

ArthaDrishti demonstrates a serious AI-assisted financial system where exact numbers are controlled by deterministic backend logic and AI is used safely for interpretation, retrieval, and explanation.
