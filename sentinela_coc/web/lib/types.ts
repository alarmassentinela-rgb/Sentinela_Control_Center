// DTOs del contrato OpenAPI v1 (docs/api/openapi_coc_v1.yaml). Única fuente de integración.

export type ServiceStatus = "active" | "suspended" | "pending_signature" | "inactive" | string;

export interface Service {
  id: number;
  reference: string;
  service_type: string;
  service_type_label: string;
  plan: string | null;
  status: ServiceStatus;
  state: string;
  technical_state: string;
  monthly_total: number;
  currency: string;
  billing_interval: string;
  billing_interval_label: string;
  next_billing_date: string | null;
  service_address: string | null;
}

export interface Invoice {
  id: number;
  number: string | null;
  date: string | null;
  due_date: string | null;
  amount_total: number;
  amount_due: number;
  currency: string;
  payment_state: string;
  doc_type: "factura" | "remision" | string;
  cfdi_status: string | null;
  cfdi_uuid: string | null;
  has_pdf: boolean;
  has_xml: boolean;
  cfdi_timestamp?: string | null;
  lines?: { name: string; quantity: number; price_subtotal: number }[];
}

export interface Payment {
  id: number;
  date: string | null;
  amount: number;
  currency: string;
  reference: string | null;
}

export interface BillingSummary {
  currency: string;
  total_due: number;
  overdue_amount: number;
  open_count: number;
  upcoming: Invoice[];
}

// Estado de Cuenta servido por el Ledger (GET /v1/ledger/statement).
export interface AccountStatement {
  currency: string;
  balance: number;   // saldo por pagar
  overdue: number;   // vencido
  upcoming: number;  // por vencer
}

export type ActionType =
  | "payment_overdue"
  | "invoice_due"
  | "contract_pending_signature"
  | "service_suspended";

export interface NextAction {
  key: string;
  type: ActionType;
  severity: "high" | "medium" | "low";
  title: string;
  detail: string;
  amount?: number | null;
  target: string;
}

export interface Dashboard {
  peace_of_mind: { status: "tranquilo" | "atencion" | string; label: string };
  services: { total: number; active: number; suspended: number; items: Partial<Service>[] };
  billing: { total_due: number; overdue_amount: number; currency: string; upcoming: Invoice[] };
  next_actions: NextAction[];
}

export interface Meta {
  server_time: string;
  request_id: string;
  last_refresh?: string;
  cache_ttl_sec?: number;
}

export interface Paged<T> {
  count: number;
  page: number;
  limit: number;
  items: T[];
}

export interface Theme {
  app_name: string;
  logo_url: string;
  primary_color: string;
  support_phone: string;
  support_whatsapp: string;
}
