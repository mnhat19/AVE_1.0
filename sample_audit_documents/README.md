# Sample Audit Documents

This folder contains a realistic audit document set for the AI Audit Tool MVP.

## Structure
- `INTERIM/`: Procurement and internal-control evidence for the interim audit stage
- `FIELDWORK/`: Ledger, reconciliation, and confirmation evidence for fieldwork
- `edge_cases/`: Invalid or incomplete files for error-handling checks

## Supported Formats Included
- `PDF`: walkthrough notes, bank statement extracts, professional cover pages, KPI summary
- `DOCX`: SOP, internal policy, contract notes
- `XLSX`: risk matrix, test of controls, control questionnaire, trial balance, lead schedule, reconciliation, dashboards
- `CSV`: journal entries, ageing data, and GL export
- `TXT`: supporting narrative samples and fallback content
- `IMAGE`: inventory count photo sample for OCR
- `EML`: confirmation email samples
- `PST`: placeholder compatibility sample for parser-failure testing

## Recommended Test Flow
1. Upload the minimum complete interim bundle: `sop_procurement.docx`, `walkthrough_notes.pdf`, `risk_matrix.xlsx`.
2. Upload the minimum complete fieldwork bundle: `journal_entries.csv`, `trial_balance.xlsx`, `lead_schedule.xlsx`, `ageing.csv`, `reconciliation.xlsx`, `confirmation_letter.eml`.
3. Upload the full mixed bundle to run `BOTH` and verify cross-stage validation.
4. Upload `edge_cases/` files to confirm corrupted, incomplete, and unsupported-file handling.

## Notes
- The included PST sample is a compatibility placeholder because the repository does not ship PST authoring tooling.
- `Oversize_Attachment.txt` is a 5MB file; lower `MAX_FILE_SIZE_MB` to 1 to verify size-limit handling.
- The sample set is designed to satisfy the use cases, test cases, and edge cases described in the PRD and MVP todo list.