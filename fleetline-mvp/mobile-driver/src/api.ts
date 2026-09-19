import * as SecureStore from 'expo-secure-store';
import type { ApiResponse, Duty, QueueOperation, SessionUser } from './types';

const API_BASE = (process.env.EXPO_PUBLIC_API_URL || 'http://localhost:4173').replace(/\/$/, '');
const TOKEN_KEY = 'axiom_driver_access_token';

async function token(): Promise<string | null> {
  return SecureStore.getItemAsync(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
  const accessToken = await token();
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');
  if (options.body) headers.set('Content-Type', 'application/json');
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  let body: ApiResponse<T> = { ok: response.ok };
  try { body = await response.json(); } catch (_) { /* response may be empty */ }
  if (!response.ok) throw new Error(String(body.error || 'The driver service could not complete that request.'));
  return body;
}

export async function signIn(email: string, password: string): Promise<SessionUser> {
  const response = await request<never>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
  if (!response.user || !response.access_token) throw new Error('The sign-in response did not include a mobile session.');
  await SecureStore.setItemAsync(TOKEN_KEY, response.access_token);
  return response.user;
}

export async function signOut(): Promise<void> {
  try { await request<never>('/api/auth/logout', { method: 'POST' }); } finally { await SecureStore.deleteItemAsync(TOKEN_KEY); }
}

export async function currentUser(): Promise<SessionUser> {
  const response = await request<never>('/api/auth/me');
  if (!response.user) throw new Error('No active driver session.');
  return response.user;
}

export async function assignedDuty(): Promise<Duty | null> {
  const duties = await request<Duty>('/api/duties?limit=20');
  const row = (duties.items || []).find(item => ['assigned', 'accepted', 'en_route', 'started', 'paused'].includes(item.status)) || duties.items?.[0];
  if (!row) return null;
  const bookings = await request<Record<string, unknown>>('/api/bookings?limit=50');
  const booking = (bookings.items || []).find(item => item.id === row.booking_id) as Record<string, any> | undefined;
  return {
    ...row,
    customer: booking?.customer_name || 'Assigned customer',
    passenger: booking?.passenger_name || 'Passenger',
    pickup: booking?.pickup?.label || 'Pickup',
    dropoff: booking?.dropoff?.label || 'Drop-off',
    vehicle: row.vehicle_id || 'Vehicle assigned',
  };
}

export async function transitionDuty(dutyId: string, status: string, idempotencyKey: string): Promise<void> {
  await request(`/api/duties/${encodeURIComponent(dutyId)}`, { method: 'PATCH', body: JSON.stringify({ status, idempotency_key: idempotencyKey }) });
}

export async function recordProof(dutyId: string, code: string, note: string, idempotencyKey: string, attachments: Record<string, unknown> = {}): Promise<void> {
  await request(`/api/duties/${encodeURIComponent(dutyId)}/proof`, { method: 'POST', body: JSON.stringify({ proof_type: 'otp', proof_data: { code, note, ...attachments }, idempotency_key: idempotencyKey }) });
}

export async function recordExpense(dutyId: string, payload: Record<string, unknown>, idempotencyKey: string): Promise<void> {
  await request(`/api/duties/${encodeURIComponent(dutyId)}/expenses`, { method: 'POST', body: JSON.stringify({ ...payload, idempotency_key: idempotencyKey }) });
}

export async function recordLocation(dutyId: string, latitude: number, longitude: number, recordedAt: string, idempotencyKey?: string, accuracyM?: number, batteryPct?: number): Promise<void> {
  await request(`/api/duties/${encodeURIComponent(dutyId)}/track`, { method: 'POST', body: JSON.stringify({ latitude, longitude, recorded_at: recordedAt, idempotency_key: idempotencyKey, accuracy_m: accuracyM, battery_pct: batteryPct, source: 'driver_app' }) });
}

export async function sendSos(dutyId: string, idempotencyKey?: string): Promise<void> {
  await request(`/api/duties/${encodeURIComponent(dutyId)}/sos`, { method: 'POST', body: JSON.stringify({ alert_type: 'sos', severity: 'critical', entity_type: 'duty', entity_id: dutyId, idempotency_key: idempotencyKey }) });
}

export async function replay(operations: QueueOperation[], deviceId = 'axiom-driver-native'): Promise<{ failed: Set<string>; count: number }> {
  const response = await request<{ idempotency_key: string; status: string }>('/api/sync/replay', { method: 'POST', body: JSON.stringify({ device_id: deviceId, operations }) });
  const results = (response.results as Array<{ idempotency_key: string; status: string }> | undefined) || [];
  return { failed: new Set(results.filter(item => item.status === 'failed').map(item => item.idempotency_key)), count: results.length };
}

export async function testMaskedCall(): Promise<string> {
  const response = await request('/api/integrations/test', { method: 'POST', body: JSON.stringify({ provider: 'telephony' }) });
  return String((response.result as { reference?: string } | undefined)?.reference || 'provider-reference');
}

export async function registerDevice(deviceId: string, platform: string, pushToken: string): Promise<void> {
  await request('/api/devices', { method: 'POST', body: JSON.stringify({ device_id: deviceId, platform, push_token: pushToken }) });
}

export { API_BASE };
