export type DutyStatus = 'draft' | 'assigned' | 'accepted' | 'en_route' | 'started' | 'paused' | 'completed';

export type Duty = {
  id: string;
  status: DutyStatus;
  reporting_at?: string | null;
  customer?: string;
  passenger?: string;
  pickup?: string;
  dropoff?: string;
  vehicle?: string;
  driver?: string;
  booking_id?: string;
  driver_id?: string | null;
  vehicle_id?: string | null;
  calculation_snapshot?: { total_paise?: number };
};

export type QueueOperation = {
  entity_type: string;
  entity_id: string;
  operation: string;
  payload: Record<string, unknown>;
  idempotency_key: string;
  created_at: string;
};

export type SessionUser = {
  id: string;
  email: string;
  role: string;
  full_name: string;
  phone?: string;
  profile?: { city?: string; license_number?: string };
};

export type ApiResponse<T> = {
  ok: boolean;
  items?: T[];
  user?: SessionUser;
  access_token?: string;
  [key: string]: unknown;
};
