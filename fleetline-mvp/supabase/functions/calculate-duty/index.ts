import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const ENGINE_VERSION = "2026.09.1";
const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...cors, "Content-Type": "application/json" },
  });
}

function integer(value: unknown, name: string): number {
  if (value === null || value === undefined || value === "") return 0;
  const number = Number(value);
  if (!Number.isSafeInteger(number) || number < 0 || number > 1_000_000_000) {
    throw new Error(`${name} must be a non-negative integer under 1,000,000,000`);
  }
  return number;
}

function roundHalfUp(numerator: number, denominator: number): number {
  if (!Number.isSafeInteger(numerator) || !Number.isSafeInteger(denominator) || denominator <= 0) throw new Error("Invalid rounding input");
  return Math.floor((numerator + Math.floor(denominator / 2)) / denominator);
}

function calculate(input: Record<string, unknown>) {
  const fields = ["base_paise", "distance_km", "per_km_paise", "duration_minutes", "per_hour_paise", "waiting_minutes", "waiting_paise", "toll_paise", "parking_paise", "expense_paise", "tax_rate_bps"];
  const values = Object.fromEntries(fields.map((field) => [field, integer(input[field], field)])) as Record<string, number>;
  if (values.tax_rate_bps > 10_000) throw new Error("tax_rate_bps cannot exceed 10000");
  const lines: Array<Record<string, unknown>> = [];
  const add = (code: string, label: string, quantity: number, unit: number, amount: number, source: string) => {
    if (amount) lines.push({ code, label, quantity, unit_paise: unit, amount_paise: amount, source });
  };
  add("base", "Base duty", 1, values.base_paise, values.base_paise, "price_book");
  add("distance", "Distance", values.distance_km, values.per_km_paise, values.distance_km * values.per_km_paise, "odometer");
  add("time", "Time", values.duration_minutes, values.per_hour_paise, roundHalfUp(values.duration_minutes * values.per_hour_paise, 60), "duty_clock");
  add("waiting", "Waiting", values.waiting_minutes, values.waiting_paise, roundHalfUp(values.waiting_minutes * values.waiting_paise, 60), "duty_clock");
  add("toll", "Toll", 1, values.toll_paise, values.toll_paise, "expense");
  add("parking", "Parking", 1, values.parking_paise, values.parking_paise, "expense");
  add("expense", "Other expense", 1, values.expense_paise, values.expense_paise, "expense");
  const subtotal_paise = lines.reduce((sum, line) => sum + Number(line.amount_paise), 0);
  const tax_paise = roundHalfUp(subtotal_paise * values.tax_rate_bps, 10_000);
  return {
    engine_version: ENGINE_VERSION,
    inputs: values,
    lines,
    subtotal_paise,
    tax_rate_bps: values.tax_rate_bps,
    tax_paise,
    total_paise: subtotal_paise + tax_paise,
  };
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (request.method !== "POST") return response({ error: "POST required" }, 405);
  const authorization = request.headers.get("Authorization");
  const url = Deno.env.get("SUPABASE_URL");
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY");
  if (!authorization || !url || !anonKey) return response({ error: "Authenticated Supabase configuration is required" }, 401);
  const token = authorization.replace(/^Bearer\s+/i, "");
  const supabase = createClient(url, anonKey, { global: { headers: { Authorization: `Bearer ${token}` } } });
  try {
    const payload = await request.json();
    if (!payload?.duty_id || typeof payload.duty_id !== "string") return response({ error: "duty_id is required" }, 400);
    const snapshot = calculate(payload.inputs || payload);
    const { data, error } = await supabase.rpc("save_duty_calculation", { p_duty_id: payload.duty_id, p_snapshot: snapshot });
    if (error) return response({ error: error.message }, 400);
    return response({ ok: true, item: data, calculation: snapshot });
  } catch (error) {
    return response({ error: error instanceof Error ? error.message : "Calculation failed" }, 400);
  }
});
