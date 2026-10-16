# Prepare branch purchase/sale drafts and valued inventory dispatches

Sucursal submissions can now create one draft purchase in their actual company
and one draft sale in the configured Industria company, atomically. Industry's
existing salesperson reviews the sale; standard Inventory validation records
actual partial/full dispatches and separate buyer receipts. The A4 valued PDF
shows demand, preparation, net delivered quantity, pending balances and standard
commercial taxes/prices. No automatic confirmations or invoices.

This is a **draft integration**, not approved for production. Enterprise's native
`account_inter_company_rules` source was unavailable: activation/confirmation
with that module installed fails closed until an audited adapter exists.
Same-company branches also fail closed pending approval and mapping of their
internal-transfer variant; no self intercompany documents or fictitious companies
are created. Known private `alvinha_mrp` BOM side effects require an adapter.

Security retains existing company memberships/roles and adds assignment limits
to linked documents. Submission input cannot choose commercial links/companies.
Document identity, shipping/invoice contacts and buyer receipt are protected.
Original demand cannot silently be reduced; closing an unserved balance requires
an immutable reasoned record after open Inventory operations are canceled.

Consolidation keeps the Purchase submenus and credits this demand's own physical
reservations once, while other orders' reservations remain unavailable. Historical
served quantities survive migration without retrospective commercial documents.
The separately published `central-supply-multicompany` alternative is untouched;
its different keeper-assignment schema requires a specific migration, enforced
by a guard rather than silently dropping assignments.

Validation and reproducible commands are in TESTING.md. Configuration and explicit
limits are in INTERCOMPANY_FLOW.md and NATIVE_INTERCOMPANY.md. No production or
shared operational repository has been modified.

Verified locally: 117 Odoo cases with no failures/errors/skips, 6 Python cases,
5 DOM cases, real Chromium, binary A4 PDF, concurrent HTTP idempotence, manual
20/15/5 stock delivery/backorder and historical 1.2→2.0 upgrade. A clean initial
installation passed 116 cases before the final alternative-schema guard case was
added; the final 117-case run included that guard. Enterprise is untested.

Proposed base: `feature/multi-company-supply` (`d59eea3`).
Head: `feature/intercompany-purchase-sales-flow`.
Do not merge or deploy until the documented integrations are accepted in staging.
