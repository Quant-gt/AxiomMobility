/* Axiom Fleet Supabase browser adapter.
 * The app falls back to the local /api backend when config.enabled is false.
 * Do not put the Supabase service-role key in this file or any browser bundle.
 */
(() => {
  const config = window.AXIOM_SUPABASE_CONFIG || {};
  const enabled = Boolean(
    config.enabled &&
    config.url &&
    config.anonKey &&
    !String(config.url).includes('YOUR_PROJECT_REF') &&
    !String(config.anonKey).includes('YOUR_SUPABASE')
  );
  const baseUrl = String(config.url || '').replace(/\/$/, '');
  const storageKey = 'axiomfleet_supabase_session';

  function readSession() {
    try { return JSON.parse(localStorage.getItem(storageKey) || 'null'); } catch (_) { return null; }
  }
  function writeSession(session) {
    if (session) localStorage.setItem(storageKey, JSON.stringify(session));
    else localStorage.removeItem(storageKey);
  }
  function authHeaders(token) {
    return {
      apikey: config.anonKey,
      Authorization: `Bearer ${token || config.anonKey}`,
      'Content-Type': 'application/json'
    };
  }
  async function sha256(value) {
    if (globalThis.crypto?.subtle) {
      const bytes = new TextEncoder().encode(String(value));
      const digest = await crypto.subtle.digest('SHA-256', bytes);
      return Array.from(new Uint8Array(digest)).map(byte => byte.toString(16).padStart(2, '0')).join('');
    }
    return String(value);
  }
  async function parseResponse(response) {
    let payload = {};
    try { payload = await response.json(); } catch (_) { payload = {}; }
    if (!response.ok) {
      throw new Error(payload.error_description || payload.msg || payload.message || payload.error || 'Supabase request failed.');
    }
    return payload;
  }
  async function authRequest(path, options = {}, token = '') {
    const response = await fetch(`${baseUrl}/auth/v1${path}`, {
      ...options,
      headers: { ...authHeaders(token), ...(options.headers || {}) }
    });
    return parseResponse(response);
  }
  async function dataRequest(path, options = {}, token = '') {
    const response = await fetch(`${baseUrl}/rest/v1/${path}`, {
      ...options,
      headers: {
        ...authHeaders(token),
        Prefer: 'return=representation',
        ...(options.headers || {})
      }
    });
    return parseResponse(response);
  }
  async function rpc(name, body, token) {
    const response = await fetch(`${baseUrl}/rest/v1/rpc/${name}`, {
      method: 'POST',
      headers: authHeaders(token),
      body: JSON.stringify(body)
    });
    return parseResponse(response);
  }
  async function edgeFunction(name, body, token) {
    const response = await fetch(`${baseUrl}/functions/v1/${name}`, {
      method: 'POST',
      headers: authHeaders(token),
      body: JSON.stringify(body)
    });
    return parseResponse(response);
  }
  async function refreshIfNeeded() {
    const session = readSession();
    if (!session) return null;
    if (!session.expires_at || Number(session.expires_at) - Math.floor(Date.now() / 1000) > 60) return session;
    if (!session.refresh_token) { writeSession(null); return null; }
    try {
      const refreshed = await authRequest('/token?grant_type=refresh_token', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: session.refresh_token })
      });
      const next = {
        access_token: refreshed.access_token,
        refresh_token: refreshed.refresh_token || session.refresh_token,
        expires_at: refreshed.expires_at || Math.floor(Date.now() / 1000) + (refreshed.expires_in || 3600),
        user: refreshed.user || session.user
      };
      writeSession(next);
      return next;
    } catch (_) {
      writeSession(null);
      return null;
    }
  }
  function roleFrom(profile, membership) {
    const membershipRole = membership?.role || '';
    if (membershipRole.startsWith('corporate')) return 'corporate';
    if (membershipRole.startsWith('vendor')) return 'vendor';
    if (membershipRole === 'driver') return 'driver';
    return profile?.account_type || 'vendor';
  }
  async function currentUser() {
    const session = await refreshIfNeeded();
    if (!session?.access_token) throw new Error('Sign in required.');
    const user = await authRequest('/user', {}, session.access_token);
    const profiles = await dataRequest(`profiles?id=eq.${encodeURIComponent(user.id)}&select=*`, {}, session.access_token);
    const memberships = await dataRequest(`organization_memberships?user_id=eq.${encodeURIComponent(user.id)}&status=eq.active&select=organization_id,role,branch_id,organizations(*)`, {}, session.access_token);
    const profile = profiles[0] || {};
    const membership = memberships[0] || null;
    const organization = membership?.organizations || null;
    const driverRows = profile.account_type === 'driver'
      ? await dataRequest(`drivers?user_id=eq.${encodeURIComponent(user.id)}&select=*`, {}, session.access_token)
      : [];
    const driver = driverRows[0] || {};
    return {
      ok: true,
      user: {
        id: user.id,
        email: user.email,
        role: roleFrom(profile, membership),
        full_name: profile.full_name || user.user_metadata?.full_name || '',
        phone: profile.phone || user.user_metadata?.phone || '',
        status: 'active',
        created_at: user.created_at,
        last_login_at: null,
        organization: organization ? {
          id: organization.id,
          type: organization.kind,
          name: organization.name,
          phone: organization.phone || '',
          city: organization.city || '',
          gstin: organization.gstin || ''
        } : null,
        profile: {
          city: driver.city || organization?.city || '',
          license_number: driver.license_number || '',
          fleet_size: organization?.fleet_size ?? null,
          employee_count: organization?.employee_count ?? null
        }
      }
    };
  }
  async function signUp(payload) {
    const authData = await authRequest('/signup', {
      method: 'POST',
      body: JSON.stringify({
        email: payload.email,
        password: payload.password,
        data: {
          full_name: payload.full_name,
          phone: payload.phone,
          account_type: payload.role
        }
      })
    });
    if (!authData.access_token) {
      return { ok: true, needs_confirmation: true, user: { email: payload.email, full_name: payload.full_name, role: payload.role } };
    }
    writeSession({
      access_token: authData.access_token,
      refresh_token: authData.refresh_token,
      expires_at: authData.expires_at || Math.floor(Date.now() / 1000) + (authData.expires_in || 3600),
      user: authData.user
    });
    const token = authData.access_token;
    if (payload.role === 'driver') {
      await rpc('create_driver_profile', {
        p_full_name: payload.full_name,
        p_phone: payload.phone || '',
        p_city: payload.city || '',
        p_license_number: payload.license_number || ''
      }, token);
    } else {
      await rpc('create_organization', {
        p_kind: payload.role,
        p_name: payload.organization_name,
        p_city: payload.city || '',
        p_phone: payload.phone || '',
        p_gstin: payload.gstin || '',
        p_fleet_size: payload.role === 'vendor' && payload.fleet_size ? Number(payload.fleet_size) : null,
        p_employee_count: payload.role === 'corporate' && payload.employee_count ? Number(payload.employee_count) : null
      }, token);
    }
    return currentUser();
  }
  async function signIn(payload) {
    const authData = await authRequest('/token?grant_type=password', {
      method: 'POST',
      body: JSON.stringify({ email: payload.email, password: payload.password })
    });
    writeSession({
      access_token: authData.access_token,
      refresh_token: authData.refresh_token,
      expires_at: authData.expires_at || Math.floor(Date.now() / 1000) + (authData.expires_in || 3600),
      user: authData.user
    });
    return currentUser();
  }
  async function signOut() {
    const session = await refreshIfNeeded();
    if (session?.access_token) {
      try { await authRequest('/logout', { method: 'POST' }, session.access_token); } catch (_) { /* local session still clears */ }
    }
    writeSession(null);
    return { ok: true };
  }
  async function activeOrganizationId() {
    const identity = await currentUser();
    const organizationId = identity.user.organization?.id;
    if (!organizationId) throw new Error('An organization-linked account is required.');
    return organizationId;
  }
  function locationValue(value) {
    if (value && typeof value === 'object' && !Array.isArray(value)) return value;
    return { label: value || '' };
  }
  function normalizedBooking(payload, organizationId) {
    return {
      organization_id: organizationId,
      branch_id: payload.branch_id || null,
      customer_id: payload.customer_id || null,
      requesting_organization_id: payload.requesting_organization_id || null,
      vendor_organization_id: payload.vendor_organization_id || null,
      status: payload.status || 'requested',
      booking_reference: payload.booking_reference || `BK-${new Date().toISOString().slice(0, 7).replace('-', '')}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`,
      passenger_name: payload.passenger_name || null,
      passenger_phone: payload.passenger_phone || null,
      pickup: locationValue(payload.pickup),
      dropoff: locationValue(payload.dropoff),
      stops: Array.isArray(payload.stops) ? payload.stops : [],
      scheduled_at: payload.scheduled_at || null,
      duty_type: payload.duty_type || 'local',
      policy_context: payload.policy_context || {},
      source: payload.source || 'web',
      notes: payload.notes || null
    };
  }
  async function supabaseDomainRequest(path, options = {}) {
    const session = await refreshIfNeeded();
    if (!session?.access_token) throw new Error('Sign in required.');
    const method = options.method || 'GET';
    const url = new URL(path, window.location.origin);
    const route = url.pathname;
    let body = {};
    try { body = JSON.parse(options.body || '{}'); } catch (_) { body = {}; }
    const bookingImport = route === '/api/bookings/import' && method === 'POST';
    if (bookingImport) {
      const organizationId = await activeOrganizationId();
      const sourceRows = Array.isArray(body.bookings) ? body.bookings : [];
      const rows = [];
      for (const [index, source] of sourceRows.entries()) {
        try {
          const inserted = await dataRequest('bookings', { method: 'POST', body: JSON.stringify(normalizedBooking(source || {}, organizationId)) }, session.access_token);
          const item = Array.isArray(inserted) ? inserted[0] : inserted;
          rows.push({ row: index + 1, status: 'imported', item });
        } catch (error) {
          rows.push({ row: index + 1, status: 'error', error: error.message, code: 'import_error' });
        }
      }
      return { ok: true, imported: rows.filter(row => row.status === 'imported').length, failed: rows.filter(row => row.status === 'error').length, rows };
    }
    const bookingAction = route.match(/^\/api\/bookings\/([^/]+)\/(approve|confirm|reject|cancel|assign)$/);
    if (bookingAction && method === 'POST') {
      const organizationId = await activeOrganizationId();
      const bookingId = bookingAction[1];
      const action = bookingAction[2];
      const selected = await dataRequest(`bookings?id=eq.${encodeURIComponent(bookingId)}&select=*`, {}, session.access_token);
      const booking = selected[0];
      if (!booking) throw new Error('Booking not found.');
      if (action === 'assign') {
        const dutyPayload = {
          organization_id: organizationId,
          booking_id: bookingId,
          driver_id: body.driver_id || null,
          vehicle_id: body.vehicle_id || null,
          reporting_at: body.reporting_at || null,
          status: 'assigned'
        };
        const createdDuty = await dataRequest('duties', { method: 'POST', body: JSON.stringify(dutyPayload) }, session.access_token);
        const duty = Array.isArray(createdDuty) ? createdDuty[0] : createdDuty;
        const updated = await dataRequest(`bookings?id=eq.${encodeURIComponent(bookingId)}`, { method: 'PATCH', body: JSON.stringify({ status: 'assigned' }) }, session.access_token);
        return { ok: true, booking: Array.isArray(updated) ? updated[0] : updated, duty };
      }
      const nextStatus = { approve: 'approved', confirm: 'confirmed', reject: 'disputed', cancel: 'cancelled' }[action];
      const updated = await dataRequest(`bookings?id=eq.${encodeURIComponent(bookingId)}`, { method: 'PATCH', body: JSON.stringify({ status: nextStatus }) }, session.access_token);
      const item = Array.isArray(updated) ? updated[0] : updated;
      if (action === 'approve' || action === 'confirm' || action === 'reject') {
        await dataRequest('booking_approvals', {
          method: 'POST',
          body: JSON.stringify({ organization_id: organizationId, booking_id: bookingId, approver_id: session.user?.id || null, status: action === 'reject' ? 'rejected' : 'approved', comment: body.comment || '' })
        }, session.access_token);
      }
      return { ok: true, item, status: nextStatus };
    }
    if (route === '/api/branches' && method === 'POST') {
      const organizationId = await activeOrganizationId();
      const { code, address, ...branchBody } = body;
      const inserted = await dataRequest('branches', { method: 'POST', body: JSON.stringify({ ...branchBody, organization_id: organizationId, numbering_series: { ...(body.numbering_series || {}), ...(code ? { code } : {}) }, tax_registration: body.tax_registration || {} }) }, session.access_token);
      return { ok: true, item: Array.isArray(inserted) ? inserted[0] : inserted };
    }
    if (route === '/api/drivers' && method === 'POST') {
      const { vehicle_type: ignoredVehicleType, ...driverBody } = body;
      const inserted = await dataRequest('drivers', { method: 'POST', body: JSON.stringify({ ...driverBody, organization_id: await activeOrganizationId() }) }, session.access_token);
      return { ok: true, item: Array.isArray(inserted) ? inserted[0] : inserted };
    }
    const priceItemRoute = route.match(/^\/api\/price-books\/([^/]+)\/items$/);
    if (priceItemRoute && method === 'POST') {
      const { tax_rate_bps: ignoredTaxRateBps, ...priceItemBody } = body;
      const inserted = await dataRequest('price_book_items', { method: 'POST', body: JSON.stringify({ ...priceItemBody, price_book_id: priceItemRoute[1], tax_rate: body.tax_rate ?? (Number(ignoredTaxRateBps || 0) / 100) }) }, session.access_token);
      return { ok: true, item: Array.isArray(inserted) ? inserted[0] : inserted };
    }
    const invoiceCreate = route === '/api/invoices' && method === 'POST';
    if (invoiceCreate && body.duty_id) {
      const organizationId = await activeOrganizationId();
      const duties = await dataRequest(`duties?id=eq.${encodeURIComponent(body.duty_id)}&select=*`, {}, session.access_token);
      const duty = duties[0];
      if (!duty) throw new Error('Duty not found.');
      const snapshot = duty.calculation_snapshot || {};
      const bookingRows = duty.booking_id ? await dataRequest(`bookings?id=eq.${encodeURIComponent(duty.booking_id)}&select=customer_id`, {}, session.access_token) : [];
      const invoicePayload = {
        organization_id: organizationId,
        customer_id: bookingRows[0]?.customer_id || null,
        booking_id: duty.booking_id,
        invoice_number: body.invoice_number || `INV-${new Date().getUTCFullYear()}-${Date.now().toString().slice(-6)}`,
        status: 'draft',
        subtotal_paise: Number(snapshot.subtotal_paise || 0),
        tax_paise: Number(snapshot.tax_paise || 0),
        total_paise: Number(snapshot.total_paise || 0),
        currency: 'INR'
      };
      const inserted = await dataRequest('invoices', { method: 'POST', body: JSON.stringify(invoicePayload) }, session.access_token);
      const invoice = Array.isArray(inserted) ? inserted[0] : inserted;
      if (Array.isArray(snapshot.lines) && snapshot.lines.length) {
        await dataRequest('invoice_lines', { method: 'POST', body: JSON.stringify(snapshot.lines.map(line => ({ invoice_id: invoice.id, description: line.label || line.code || 'Duty line', quantity: line.quantity || 1, unit_paise: line.unit_paise || 0, tax_rate: 0, amount_paise: line.amount_paise || 0, source_entity_type: 'duty', source_entity_id: duty.id }))) }, session.access_token);
      }
      return { ok: true, item: invoice };
    }
    const dutyTransition = route.match(/^\/api\/duties\/([^/]+)$/);
    if (dutyTransition && method === 'PATCH' && body.status) {
      const result = await rpc('transition_duty', {
        p_duty_id: dutyTransition[1],
        p_next_status: body.status,
        p_payload: { ...(body.payload || { source: 'web' }), idempotency_key: body.idempotency_key || body.payload?.idempotency_key || null }
      }, session.access_token);
      return { ok: true, item: result };
    }
    const dutyException = route.match(/^\/api\/duties\/([^/]+)\/(reassign|sos)$/);
    if (dutyException && method === 'POST') {
      const dutyId = dutyException[1];
      const action = dutyException[2];
      if (action === 'reassign') {
        const organizationId = await activeOrganizationId();
        const updates = { status: 'assigned', updated_at: new Date().toISOString() };
        for (const key of ['driver_id', 'vehicle_id', 'reporting_at']) if (Object.prototype.hasOwnProperty.call(body, key)) updates[key] = body[key] || null;
        const updated = await dataRequest(`duties?id=eq.${encodeURIComponent(dutyId)}&organization_id=eq.${encodeURIComponent(organizationId)}`, { method: 'PATCH', body: JSON.stringify(updates) }, session.access_token);
        return { ok: true, item: Array.isArray(updated) ? updated[0] : updated };
      }
      const result = await rpc('raise_sos', {
        p_duty_id: dutyId,
        p_latitude: body.latitude == null ? null : Number(body.latitude),
        p_longitude: body.longitude == null ? null : Number(body.longitude),
        p_payload: { ...body, idempotency_key: body.idempotency_key || null }
      }, session.access_token);
      return { ok: true, item: result };
    }
    const invoiceIssue = route.match(/^\/api\/invoices\/([^/]+)\/issue$/);
    if (invoiceIssue && method === 'POST') {
      const result = await rpc('issue_invoice', { p_invoice_id: invoiceIssue[1] }, session.access_token);
      return { ok: true, item: result };
    }
    const invoiceEInvoice = route.match(/^\/api\/invoices\/([^/]+)\/e-invoice$/);
    if (invoiceEInvoice && method === 'POST') {
      const organizationId = await activeOrganizationId();
      const existingRows = await dataRequest(`einvoice_records?invoice_id=eq.${encodeURIComponent(invoiceEInvoice[1])}&select=*`, {}, session.access_token);
      if (existingRows[0]) return { ok: true, item: { ...existingRows[0], reference: existingRows[0].irn }, idempotent: true };
      const invoiceRows = await dataRequest(`invoices?id=eq.${encodeURIComponent(invoiceEInvoice[1])}&select=id,invoice_number,total_paise`, {}, session.access_token);
      const invoice = invoiceRows[0];
      if (!invoice) throw new Error('Invoice not found.');
      const irn = `mock_irn_${invoice.id}`;
      const inserted = await dataRequest('einvoice_records', {
        method: 'POST',
        body: JSON.stringify({ organization_id: organizationId, invoice_id: invoice.id, provider: 'mock_einvoice', status: 'issued', irn, qr_payload: `mock_qr_${invoice.invoice_number}`, payload: { invoice_number: invoice.invoice_number, total_paise: invoice.total_paise, mode: 'mock' } })
      }, session.access_token);
      const record = Array.isArray(inserted) ? inserted[0] : inserted;
      return { ok: true, item: { ...record, reference: record.irn } };
    }
    const invoiceDispatch = route.match(/^\/api\/invoices\/([^/]+)\/dispatch$/);
    if (invoiceDispatch && method === 'POST') {
      const organizationId = await activeOrganizationId();
      const invoiceRows = await dataRequest(`invoices?id=eq.${encodeURIComponent(invoiceDispatch[1])}&select=id,invoice_number,total_paise`, {}, session.access_token);
      const invoice = invoiceRows[0];
      if (!invoice) throw new Error('Invoice not found.');
      const reference = `mock_msg_${invoice.id}_${body.channel || 'email'}`;
      const inserted = await dataRequest('collection_actions', {
        method: 'POST',
        body: JSON.stringify({ organization_id: organizationId, invoice_id: invoice.id, action_type: 'dispatch', channel: body.channel || 'email', status: 'queued', provider_reference: reference, scheduled_at: body.scheduled_at || null })
      }, session.access_token);
      const action = Array.isArray(inserted) ? inserted[0] : inserted;
      return { ok: true, invoice, dispatch: { ...action, reference, status: action.status } };
    }
    if (route === '/api/invitations' && method === 'POST') {
      const result = await rpc('create_invitation', { p_email: body.email, p_role: body.role === 'corporate' ? 'corporate_travel' : (body.role || 'driver'), p_branch_id: body.branch_id || null, p_expires_days: Number(body.expires_days || 7) }, session.access_token);
      return { ok: true, item: result.invitation, invite_token: result.invite_token };
    }
    if (route === '/api/invitations/accept' && method === 'POST') {
      const result = await rpc('accept_invitation', { p_token: body.token }, session.access_token);
      return { ok: true, item: result };
    }
    if (route === '/api/payments' && method === 'POST') {
      const result = await rpc('record_payment', {
        p_invoice_id: body.invoice_id,
        p_amount_paise: Number(body.amount_paise),
        p_mode: body.mode || 'other',
        p_idempotency_key: body.idempotency_key || null
      }, session.access_token);
      return { ok: true, item: result };
    }
    const expenseRoute = route.match(/^\/api\/duties\/([^/]+)\/expenses$/);
    if (expenseRoute && method === 'POST') {
      const result = await rpc('record_expense', { p_duty_id: expenseRoute[1], p_category: body.category || 'other', p_amount_paise: Number(body.amount_paise), p_note: body.note || '', p_attachment: body.attachment || {}, p_idempotency_key: body.idempotency_key || null }, session.access_token);
      return { ok: true, item: result };
    }
    const proofRoute = route.match(/^\/api\/duties\/([^/]+)\/proof$/);
    if (proofRoute && method === 'POST') {
      const result = await rpc('capture_duty_proof', {
        p_duty_id: proofRoute[1],
        p_proof_type: body.proof_type,
        p_proof_data: body.proof_data || body,
        p_storage_path: body.storage_path || null,
        p_idempotency_key: body.idempotency_key || null
      }, session.access_token);
      return { ok: true, item: result };
    }
    const trackRoute = route.match(/^\/api\/duties\/([^/]+)\/track$/);
    if (trackRoute && method === 'POST') {
      const result = await rpc('record_track_point', {
        p_duty_id: trackRoute[1],
        p_recorded_at: body.recorded_at || null,
        p_latitude: Number(body.latitude),
        p_longitude: Number(body.longitude),
        p_accuracy_m: body.accuracy_m == null ? null : Number(body.accuracy_m),
        p_battery_pct: body.battery_pct == null ? null : Number(body.battery_pct),
        p_source: body.source || 'driver_app',
        p_idempotency_key: body.idempotency_key || null
      }, session.access_token);
      return { ok: true, item: result };
    }
    if (route === '/api/sync/replay' && method === 'POST') {
      const operations = Array.isArray(body.operations) ? body.operations : [];
      const results = await Promise.all(operations.map(async operation => {
        const result = await rpc('enqueue_sync_operation', {
          p_device_id: body.device_id || 'browser',
          p_idempotency_key: operation.idempotency_key,
          p_entity_type: operation.entity_type,
          p_entity_id: operation.entity_id || null,
          p_operation: operation.operation,
          p_payload: operation.payload || {},
          p_client_created_at: operation.client_created_at || null
        }, session.access_token);
        return { idempotency_key: operation.idempotency_key, status: result.status || 'queued', result };
      }));
      return { ok: true, device_id: body.device_id || 'browser', accepted: results.length, failed: 0, results };
    }
    const calculateRoute = route.match(/^\/api\/duties\/([^/]+)\/calculate$/);
    if (calculateRoute && method === 'POST') {
      const result = await edgeFunction('calculate-duty', { duty_id: calculateRoute[1], inputs: body }, session.access_token);
      return result;
    }
    if ((route === '/api/onboarding' || route === '/api/setup') && method === 'GET') {
      const organizationId = await activeOrganizationId();
      const rows = await dataRequest(`onboarding_states?organization_id=eq.${encodeURIComponent(organizationId)}&select=*`, {}, session.access_token);
      const steps = rows[0]?.steps || {};
      const definitions = [['organization_profile', 'Complete company profile'], ['default_branch', 'Set up a default branch'], ['tax_profile', 'Add GST and tax settings'], ['team_access', 'Invite the operating team'], ['masters', 'Add customer, driver and vehicle masters'], ['price_book', 'Publish a price book'], ['first_booking', 'Create the first booking'], ['driver_readiness', 'Enable driver field readiness']];
      const items = definitions.map(([key, label]) => ({ key, label, complete: steps[key]?.status === 'complete', status: steps[key]?.status || 'pending' }));
      return { ok: true, completed: items.filter(item => item.complete).length, total: items.length, progress_pct: Math.round(items.filter(item => item.complete).length * 100 / items.length), completed_at: rows[0]?.completed_at || null, items, metadata: rows[0]?.metadata || {} };
    }
    if (route === '/api/onboarding' && method === 'PATCH') {
      const organizationId = await activeOrganizationId();
      const currentRows = await dataRequest(`onboarding_states?organization_id=eq.${encodeURIComponent(organizationId)}&select=*`, {}, session.access_token);
      const steps = { ...(currentRows[0]?.steps || {}), [body.step]: { status: body.status || 'complete', updated_at: new Date().toISOString() } };
      const metadata = { ...(currentRows[0]?.metadata || {}), ...(body.metadata || {}) };
      const payload = { organization_id: organizationId, steps, metadata, completed_at: null };
      if (currentRows.length) await dataRequest(`onboarding_states?organization_id=eq.${encodeURIComponent(organizationId)}`, { method: 'PATCH', body: JSON.stringify({ steps, metadata }) }, session.access_token);
      else await dataRequest('onboarding_states', { method: 'POST', body: JSON.stringify(payload) }, session.access_token);
      return { ok: true, step: body.step, status: body.status || 'complete' };
    }
    if (route === '/api/onboarding/provision' && method === 'POST') {
      const organizationId = await activeOrganizationId();
      const profile = body.organization || body;
      const organizationPatch = {};
      ['name', 'city', 'phone', 'gstin'].forEach(key => { if (profile[key] !== undefined) organizationPatch[key] = profile[key]; });
      if (Object.keys(organizationPatch).length) await dataRequest(`organizations?id=eq.${encodeURIComponent(organizationId)}`, { method: 'PATCH', body: JSON.stringify(organizationPatch) }, session.access_token);
      if (body.branch) await dataRequest('branches', { method: 'POST', body: JSON.stringify({ organization_id: organizationId, name: body.branch.name || 'Main branch', city: body.branch.city || profile.city || '', numbering_series: { code: body.branch.code || 'HQ' } }) }, session.access_token);
      return { ok: true, organization_id: organizationId, provisioned: true };
    }
    if (route === '/api/organization' && method === 'GET') {
      const organizationId = await activeOrganizationId();
      const rows = await dataRequest(`organizations?id=eq.${encodeURIComponent(organizationId)}&select=*`, {}, session.access_token);
      return { ok: true, item: rows[0] || null };
    }
    if (route === '/api/settings' && method === 'GET') {
      const organizationId = await activeOrganizationId();
      const rows = await dataRequest(`organization_settings?organization_id=eq.${encodeURIComponent(organizationId)}&select=*`, {}, session.access_token);
      return { ok: true, item: { organization_id: organizationId, settings: rows[0]?.settings || {} } };
    }
    if (route === '/api/settings' && method === 'PATCH') {
      const organizationId = await activeOrganizationId();
      const currentRows = await dataRequest(`organization_settings?organization_id=eq.${encodeURIComponent(organizationId)}&select=settings`, {}, session.access_token);
      const settings = { ...(currentRows[0]?.settings || {}), ...(body.settings || body) };
      const settingsPayload = { organization_id: organizationId, settings, updated_by: session.user?.id || null };
      if (currentRows.length) {
        const updated = await dataRequest(`organization_settings?organization_id=eq.${encodeURIComponent(organizationId)}`, { method: 'PATCH', body: JSON.stringify({ settings, updated_by: settingsPayload.updated_by }) }, session.access_token);
        return { ok: true, item: { organization_id: organizationId, settings: (Array.isArray(updated) ? updated[0]?.settings : updated?.settings) || settings } };
      }
      const inserted = await dataRequest('organization_settings', { method: 'POST', body: JSON.stringify(settingsPayload) }, session.access_token);
      return { ok: true, item: { organization_id: organizationId, settings: (Array.isArray(inserted) ? inserted[0]?.settings : inserted?.settings) || settings } };
    }
    if (route === '/api/audit' && method === 'GET') {
      const organizationId = await activeOrganizationId();
      const limit = Math.min(Number(url.searchParams.get('limit') || 100), 100);
      const rows = await dataRequest(`audit_events?organization_id=eq.${encodeURIComponent(organizationId)}&select=*&order=created_at.desc&limit=${limit}`, {}, session.access_token);
      return { ok: true, items: rows, count: rows.length };
    }
    if (route === '/api/integrations' && method === 'GET') {
      return { ok: true, items: [
        { key: 'payments', provider: 'Mock Payment', mode: 'mock', status: 'available', credentials_configured: false },
        { key: 'messaging', provider: 'Mock Messaging', mode: 'mock', status: 'available', credentials_configured: false },
        { key: 'telephony', provider: 'Mock Telephony', mode: 'mock', status: 'available', credentials_configured: false },
        { key: 'maps', provider: 'Mock Maps', mode: 'mock', status: 'available', credentials_configured: false },
        { key: 'einvoice', provider: 'Mock E-Invoice', mode: 'mock', status: 'available', credentials_configured: false },
        { key: 'storage', provider: 'Mock Storage', mode: 'mock', status: 'available', credentials_configured: false }
      ] };
    }
    const recurringRoute = route === '/api/bookings/recurring';
    if (recurringRoute && method === 'GET') {
      const organizationId = await activeOrganizationId(); const rows = await dataRequest(`recurring_bookings?organization_id=eq.${encodeURIComponent(organizationId)}&select=*&order=created_at.desc&limit=100`, {}, session.access_token); return { ok: true, items: rows, count: rows.length };
    }
    if (recurringRoute && method === 'POST') {
      const organizationId = await activeOrganizationId(); const template = body.template || {}; const inserted = await dataRequest('recurring_bookings', { method: 'POST', body: JSON.stringify({ organization_id: organizationId, customer_id: template.customer_id || null, cadence: body.cadence || 'weekly', start_at: body.start_at, end_at: body.end_at || null, occurrences: Number(body.occurrences || 1), template }) }, session.access_token); return { ok: true, item: Array.isArray(inserted) ? inserted[0] : inserted, generated: [] };
    }
    const stopsRoute = route.match(/^\/api\/bookings\/([^/]+)\/stops$/);
    if (stopsRoute && method === 'GET') {
      const organizationId = await activeOrganizationId(); const rows = await dataRequest(`booking_stops?organization_id=eq.${encodeURIComponent(organizationId)}&booking_id=eq.${encodeURIComponent(stopsRoute[1])}&select=*&order=stop_index.asc`, {}, session.access_token); return { ok: true, items: rows };
    }
    if (stopsRoute && method === 'POST') {
      const organizationId = await activeOrganizationId(); const stops = Array.isArray(body.stops) ? body.stops : [body]; const rows = stops.map((stop, index) => ({ organization_id: organizationId, booking_id: stopsRoute[1], stop_index: index + 1, label: stop.label || `Stop ${index + 1}`, address: stop.address || stop, arrival_at: stop.arrival_at || null, departure_at: stop.departure_at || null, status: stop.status || 'planned' })); const inserted = await dataRequest('booking_stops', { method: 'POST', body: JSON.stringify(rows) }, session.access_token); return { ok: true, items: inserted };
    }
    const capacityRoute = route.match(/^\/api\/capacity\/locks(?:\/([^/]+)\/release)?$/);
    if (capacityRoute && method === 'GET') { const organizationId = await activeOrganizationId(); const rows = await dataRequest(`capacity_locks?organization_id=eq.${encodeURIComponent(organizationId)}&select=*&order=starts_at.asc`, {}, session.access_token); return { ok: true, items: rows }; }
    if (capacityRoute && capacityRoute[1] && method === 'POST') { const organizationId = await activeOrganizationId(); await dataRequest(`capacity_locks?id=eq.${encodeURIComponent(capacityRoute[1])}&organization_id=eq.${encodeURIComponent(organizationId)}`, { method: 'PATCH', body: JSON.stringify({ status: 'released', released_at: new Date().toISOString() }) }, session.access_token); return { ok: true, status: 'released' }; }
    if (route === '/api/capacity/locks' && method === 'POST') { const organizationId = await activeOrganizationId(); const inserted = await dataRequest('capacity_locks', { method: 'POST', body: JSON.stringify({ ...body, organization_id: organizationId }) }, session.access_token); return { ok: true, item: Array.isArray(inserted) ? inserted[0] : inserted }; }
    const paymentCapture = route.match(/^\/api\/payment-links\/([^/]+)\/capture$/);
    if (paymentCapture && method === 'POST') { const organizationId = await activeOrganizationId(); await dataRequest(`payment_links?id=eq.${encodeURIComponent(paymentCapture[1])}&organization_id=eq.${encodeURIComponent(organizationId)}`, { method: 'PATCH', body: JSON.stringify({ status: 'paid', paid_at: new Date().toISOString(), provider_reference: `mock_payment_${paymentCapture[1]}` }) }, session.access_token); return { ok: true, status: 'paid', reference: `mock_payment_${paymentCapture[1]}` }; }
    const financialDecision = route.match(/^\/api\/financial-actions\/([^/]+)\/(approve|reject)$/);
    if (financialDecision && method === 'POST') { const organizationId = await activeOrganizationId(); const status = financialDecision[2] === 'approve' ? 'approved' : 'rejected'; const updated = await dataRequest(`financial_actions?id=eq.${encodeURIComponent(financialDecision[1])}&organization_id=eq.${encodeURIComponent(organizationId)}`, { method: 'PATCH', body: JSON.stringify({ status, reviewed_by: session.user?.id || null, review_comment: body.comment || '', reviewed_at: new Date().toISOString() }) }, session.access_token); return { ok: true, item: Array.isArray(updated) ? updated[0] : updated }; }
    const networkAccept = route === '/api/network/edges/accept' && method === 'POST';
    if (networkAccept) { const organizationId = await activeOrganizationId(); const updated = await dataRequest(`network_edges?id=eq.${encodeURIComponent(body.edge_id)}&organization_id=eq.${encodeURIComponent(organizationId)}`, { method: 'PATCH', body: JSON.stringify({ status: 'active', accepted_at: new Date().toISOString() }) }, session.access_token); return { ok: true, item: Array.isArray(updated) ? updated[0] : updated }; }
    const remainingResource = route.match(/^\/api\/(billing-notes|payment-links|jobs)$/);
    if (remainingResource && method === 'GET') { const organizationId = await activeOrganizationId(); const table = { 'billing-notes': 'billing_notes', 'payment-links': 'payment_links', jobs: 'jobs' }[remainingResource[1]]; const rows = await dataRequest(`${table}?organization_id=eq.${encodeURIComponent(organizationId)}&select=*&order=created_at.desc&limit=100`, {}, session.access_token); return { ok: true, items: rows, count: rows.length }; }
    if (remainingResource && method === 'POST') { const organizationId = await activeOrganizationId(); const table = { 'billing-notes': 'billing_notes', 'payment-links': 'payment_links', jobs: 'jobs' }[remainingResource[1]]; const write = { ...body, organization_id: organizationId, created_by: session.user?.id || null }; if (remainingResource[1] === 'payment-links') { const raw = `afpay_${crypto.randomUUID ? crypto.randomUUID() : Date.now()}`; write.token_hash = await sha256(raw); write.short_code = raw.slice(-10).toUpperCase(); write.expires_at = body.expires_at || new Date(Date.now() + 7 * 86400000).toISOString(); const inserted = await dataRequest(table, { method: 'POST', body: JSON.stringify(write) }, session.access_token); const item = Array.isArray(inserted) ? inserted[0] : inserted; return { ok: true, item: { ...item, token: raw, url: `/pay/${item.short_code}` } }; } const inserted = await dataRequest(table, { method: 'POST', body: JSON.stringify(write) }, session.access_token); return { ok: true, item: Array.isArray(inserted) ? inserted[0] : inserted }; }
    const jobRun = route.match(/^\/api\/jobs\/([^/]+)\/run$/);
    if (jobRun && method === 'POST') { const organizationId = await activeOrganizationId(); await dataRequest(`jobs?id=eq.${encodeURIComponent(jobRun[1])}&organization_id=eq.${encodeURIComponent(organizationId)}`, { method: 'PATCH', body: JSON.stringify({ status: 'completed', attempts: 1, completed_at: new Date().toISOString(), result: { mode: 'supabase_mock_worker', processed_at: new Date().toISOString() } }) }, session.access_token); return { ok: true, status: 'completed' }; }
    if (route === '/api/devices' && method === 'GET') { const rows = await dataRequest(`device_bindings?user_id=eq.${encodeURIComponent(session.user.id)}&select=*&order=last_seen_at.desc`, {}, session.access_token); return { ok: true, items: rows }; }
    if (route === '/api/devices' && method === 'POST') { const organizationId = await activeOrganizationId(); const deviceId = body.device_id || `device-${crypto.randomUUID ? crypto.randomUUID() : Date.now()}`; const write = { organization_id: organizationId, user_id: session.user.id, device_id: deviceId, platform: body.platform || 'mobile', push_token: body.push_token || '', status: 'active', last_seen_at: new Date().toISOString() }; const existing = await dataRequest(`device_bindings?user_id=eq.${encodeURIComponent(session.user.id)}&device_id=eq.${encodeURIComponent(deviceId)}&select=id`, {}, session.access_token); const result = existing[0] ? await dataRequest(`device_bindings?id=eq.${encodeURIComponent(existing[0].id)}`, { method: 'PATCH', body: JSON.stringify(write) }, session.access_token) : await dataRequest('device_bindings', { method: 'POST', body: JSON.stringify(write) }, session.access_token); return { ok: true, item: Array.isArray(result) ? result[0] : result }; }
    if (route === '/api/security/2fa' && method === 'GET') { const rows = await dataRequest(`auth_factors?user_id=eq.${encodeURIComponent(session.user.id)}&select=user_id,factor_type,status,created_at,verified_at,last_used_at`, {}, session.access_token); return { ok: true, enabled: rows[0]?.status === 'enabled', factor: rows[0] || null }; }
    if (route === '/api/security/2fa/setup' && method === 'POST') { const secret = crypto.randomUUID ? crypto.randomUUID().replaceAll('-', '').slice(0, 24).toUpperCase() : `AXIOM${Date.now()}`; const recovery = Array.from({ length: 8 }, () => crypto.randomUUID().slice(0, 8).toUpperCase()); await dataRequest('auth_factors', { method: 'POST', body: JSON.stringify({ user_id: session.user.id, organization_id: await activeOrganizationId(), factor_type: 'totp', secret_hash: await sha256(secret), status: 'pending', recovery_codes: recovery }) }, session.access_token); return { ok: true, factor_type: 'totp', otpauth_url: `otpauth://totp/AxiomFleet:${session.user.email}?secret=${secret}&issuer=AxiomFleet`, recovery_codes: recovery, mock_verification_code: '246810' }; }
    if (route === '/api/security/2fa/verify' && method === 'POST') { if (!['246810', '000000'].includes(String(body.code || ''))) throw new Error('The authenticator code is invalid.'); await dataRequest(`auth_factors?user_id=eq.${encodeURIComponent(session.user.id)}`, { method: 'PATCH', body: JSON.stringify({ status: 'enabled', verified_at: new Date().toISOString() }) }, session.access_token); return { ok: true, enabled: true }; }
    if (route === '/api/security/2fa/disable' && method === 'POST') { await dataRequest(`auth_factors?user_id=eq.${encodeURIComponent(session.user.id)}`, { method: 'PATCH', body: JSON.stringify({ status: 'disabled' }) }, session.access_token); return { ok: true, enabled: false }; }
    const apiKeyRoute = route.match(/^\/api\/security\/api-keys(?:\/([^/]+)\/revoke)?$/);
    if (apiKeyRoute && method === 'GET') { const organizationId = await activeOrganizationId(); const rows = await dataRequest(`api_keys?organization_id=eq.${encodeURIComponent(organizationId)}&select=id,name,key_prefix,scopes,status,last_used_at,created_by,created_at,revoked_at&order=created_at.desc`, {}, session.access_token); return { ok: true, items: rows }; }
    if (apiKeyRoute && method === 'POST' && apiKeyRoute[1]) { const organizationId = await activeOrganizationId(); await dataRequest(`api_keys?id=eq.${encodeURIComponent(apiKeyRoute[1])}&organization_id=eq.${encodeURIComponent(organizationId)}`, { method: 'PATCH', body: JSON.stringify({ status: 'revoked', revoked_at: new Date().toISOString() }) }, session.access_token); return { ok: true, status: 'revoked' }; }
    if (apiKeyRoute && method === 'POST') { const raw = `af_live_${crypto.randomUUID ? crypto.randomUUID() : Date.now()}`; const organizationId = await activeOrganizationId(); const inserted = await dataRequest('api_keys', { method: 'POST', body: JSON.stringify({ organization_id: organizationId, name: body.name || 'API key', key_hash: await sha256(raw), key_prefix: raw.slice(0, 12), scopes: body.scopes || ['bookings:read'], created_by: session.user?.id || null }) }, session.access_token); const item = Array.isArray(inserted) ? inserted[0] : inserted; return { ok: true, item: { ...item, key: raw } }; }
    const privacyFulfill = route.match(/^\/api\/privacy\/requests\/([^/]+)\/fulfill$/);
    if (privacyFulfill && method === 'POST') { await dataRequest(`privacy_requests?id=eq.${encodeURIComponent(privacyFulfill[1])}`, { method: 'PATCH', body: JSON.stringify({ status: 'completed', completed_at: new Date().toISOString() }) }, session.access_token); return { ok: true, status: 'completed' }; }
    const employeeLifecycle = route.match(/^\/api\/employees\/([^/]+)\/(deactivate|reactivate)$/);
    if (employeeLifecycle && method === 'POST') { const status = employeeLifecycle[2] === 'deactivate' ? 'inactive' : 'active'; const updated = await dataRequest(`employees?id=eq.${encodeURIComponent(employeeLifecycle[1])}`, { method: 'PATCH', body: JSON.stringify({ status, updated_at: new Date().toISOString() }) }, session.access_token); return { ok: true, status, item: Array.isArray(updated) ? updated[0] : updated }; }
    const extendedRoute = route.match(/^\/api\/(supplier-bills|costs|vehicle-costs|driver-payouts|supplier-payouts|alerts|geofences|sla)$/);
    if (extendedRoute && method === 'GET') {
      const organizationId = await activeOrganizationId();
      const table = { 'supplier-bills': 'supplier_bills', costs: 'cost_entries', 'vehicle-costs': 'cost_entries', 'driver-payouts': 'payouts', 'supplier-payouts': 'payouts', alerts: 'alerts', geofences: 'geofences', sla: 'sla_events' }[extendedRoute[1]];
      const rows = await dataRequest(`${table}?organization_id=eq.${encodeURIComponent(organizationId)}&select=*&order=created_at.desc&limit=100`, {}, session.access_token);
      return { ok: true, items: rows, count: rows.length };
    }
    if (extendedRoute && method === 'POST') {
      const organizationId = await activeOrganizationId();
      const kind = extendedRoute[1];
      const table = { 'supplier-bills': 'supplier_bills', costs: 'cost_entries', 'vehicle-costs': 'cost_entries', 'driver-payouts': 'payouts', 'supplier-payouts': 'payouts', alerts: 'alerts', geofences: 'geofences', sla: 'sla_events' }[kind];
      const write = { ...body, organization_id: organizationId };
      if (['supplier-bills', 'costs', 'vehicle-costs', 'driver-payouts', 'supplier-payouts'].includes(kind)) write.created_by = body.created_by || session.user?.id || null;
      if (kind === 'driver-payouts' || kind === 'supplier-payouts') write.recipient_type = body.recipient_type || (kind === 'driver-payouts' ? 'driver' : 'supplier');
      if (kind === 'sla') write.status = body.status || 'open';
      const inserted = await dataRequest(table, { method: 'POST', body: JSON.stringify(write) }, session.access_token);
      return { ok: true, item: Array.isArray(inserted) ? inserted[0] : inserted };
    }
    const networkRoute = route.match(/^\/api\/network\/(edges|offers|settlements)$/);
    if (networkRoute && method === 'GET') {
      const organizationId = await activeOrganizationId(); const table = { edges: 'network_edges', offers: 'network_offers', settlements: 'settlements' }[networkRoute[1]]; const rows = await dataRequest(`${table}?organization_id=eq.${encodeURIComponent(organizationId)}&select=*&order=created_at.desc&limit=100`, {}, session.access_token); return { ok: true, items: rows, count: rows.length };
    }
    if (networkRoute && method === 'POST') {
      const organizationId = await activeOrganizationId(); const table = { edges: 'network_edges', offers: 'network_offers', settlements: 'settlements' }[networkRoute[1]]; const inserted = await dataRequest(table, { method: 'POST', body: JSON.stringify({ ...body, organization_id: organizationId }) }, session.access_token); return { ok: true, item: Array.isArray(inserted) ? inserted[0] : inserted };
    }
    if (route === '/api/financial-actions' && method === 'POST') {
      const organizationId = await activeOrganizationId(); const inserted = await dataRequest('financial_actions', { method: 'POST', body: JSON.stringify({ ...body, organization_id: organizationId, requested_by: session.user?.id || null }) }, session.access_token); return { ok: true, item: Array.isArray(inserted) ? inserted[0] : inserted };
    }
    if (route === '/api/tax/calculate' && method === 'POST') {
      const taxable = Number(body.taxable_paise || 0); const rate = Number(body.tax_rate_bps || 1800); const tax = Math.round(taxable * rate / 10000); const intra = String(body.origin_state || '').trim().toLowerCase() === String(body.destination_state || body.origin_state || '').trim().toLowerCase();
      return { ok: true, tax: { taxable_paise: taxable, rate_bps: rate, supply_type: intra ? 'intra_state' : 'inter_state', cgst_paise: intra ? Math.floor(tax / 2) : 0, sgst_paise: intra ? tax - Math.floor(tax / 2) : 0, igst_paise: intra ? 0 : tax, total_paise: taxable + tax } };
    }
    if (route === '/api/updates' && method === 'GET') {
      const organizationId = await activeOrganizationId();
      const [duties, alerts] = await Promise.all([dataRequest(`duties?organization_id=eq.${encodeURIComponent(organizationId)}&select=id,status,driver_id,vehicle_id,updated_at&order=updated_at.desc&limit=100`, {}, session.access_token), dataRequest(`alerts?organization_id=eq.${encodeURIComponent(organizationId)}&select=id,alert_type,severity,status,created_at&order=created_at.desc&limit=100`, {}, session.access_token)]);
      return { ok: true, cursor: new Date().toISOString(), events: duties.map(item => ({ type: 'duty.changed', ...item })).concat(alerts.map(item => ({ type: 'alert.created', ...item }))) };
    }
    if (route === '/api/reports/export' && method === 'POST') {
      const organizationId = await activeOrganizationId(); const token = crypto.randomUUID ? crypto.randomUUID() : `export-${Date.now()}`; const inserted = await dataRequest('report_exports', { method: 'POST', body: JSON.stringify({ organization_id: organizationId, report_type: body.report_type || 'operations', filters: body.filters || {}, download_token: token, content: 'Axiom Fleet,report_type\n' + (body.report_type || 'operations'), expires_at: new Date(Date.now() + 7 * 86400000).toISOString(), created_by: session.user?.id || null }) }, session.access_token); const item = Array.isArray(inserted) ? inserted[0] : inserted; return { ok: true, item: { ...item, download_url: `/api/reports/exports/${item.id}` } };
    }
    if (route === '/api/privacy/retention' && method === 'POST') {
      const organizationId = await activeOrganizationId(); const entityId = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(body.entity_id || '')) ? body.entity_id : (crypto.randomUUID ? crypto.randomUUID() : '00000000-0000-4000-8000-000000000000'); const inserted = await dataRequest('retention_locks', { method: 'POST', body: JSON.stringify({ ...body, entity_id: entityId, organization_id: organizationId, created_by: session.user?.id || null }) }, session.access_token); return { ok: true, item: Array.isArray(inserted) ? inserted[0] : inserted };
    }
    if (route === '/api/admin/kpis' && method === 'GET') {
      const [organizations, users, bookings, duties, alerts] = await Promise.all([dataRequest('organizations?select=id&limit=1000', {}, session.access_token), dataRequest('profiles?select=id&limit=1000', {}, session.access_token), dataRequest('bookings?select=id&limit=1000', {}, session.access_token), dataRequest('duties?select=id&limit=1000', {}, session.access_token), dataRequest('alerts?status=eq.open&select=id&limit=1000', {}, session.access_token)]);
      return { ok: true, kpis: { organizations: organizations.length, users: users.length, bookings: bookings.length, duties: duties.length, open_alerts: alerts.length } };
    }
    const resourceMap = {
      '/api/customers': 'customers',
      '/api/drivers': 'drivers',
      '/api/vehicles': 'vehicles',
      '/api/bookings': 'bookings',
      '/api/duties': 'duties',
      '/api/invoices': 'invoices',
      '/api/branches': 'branches',
      '/api/suppliers': 'suppliers',
      '/api/price-books': 'price_books',
      '/api/documents': 'documents',
      '/api/invitations': 'invitations',
      '/api/employees': 'employees',
      '/api/policies': 'travel_policies',
      '/api/approvals': 'booking_approvals',
      '/api/notifications': 'notifications',
      '/api/tickets': 'support_tickets',
      '/api/privacy/requests': 'privacy_requests',
      '/api/settings': 'organization_settings'
    };
    if (route === '/api/overview' && method === 'GET') {
      const [duties, invoices] = await Promise.all([
        dataRequest('duties?select=status', {}, session.access_token),
        dataRequest('invoices?select=status,total_paise', {}, session.access_token)
      ]);
      const dutySummary = {};
      duties.forEach(item => { dutySummary[item.status] = (dutySummary[item.status] || 0) + 1; });
      const invoiceSummary = {};
      invoices.forEach(item => {
        invoiceSummary[item.status] ||= { count: 0, total_paise: 0 };
        invoiceSummary[item.status].count += 1;
        invoiceSummary[item.status].total_paise += Number(item.total_paise || 0);
      });
      return { ok: true, duties: dutySummary, invoices: invoiceSummary };
    }
    if (route === '/api/organization/checklist' && method === 'GET') {
      const [branches, customers, drivers, vehicles, priceBooks, bookings] = await Promise.all([
        dataRequest('branches?select=id&limit=1', {}, session.access_token),
        dataRequest('customers?select=id&limit=1', {}, session.access_token),
        dataRequest('drivers?select=id&limit=1', {}, session.access_token),
        dataRequest('vehicles?select=id&limit=1', {}, session.access_token),
        dataRequest('price_books?select=id&status=eq.active&limit=1', {}, session.access_token),
        dataRequest('bookings?select=id&limit=1', {}, session.access_token)
      ]);
      const checks = [['branch', 'Add a branch', branches], ['customer', 'Add a customer', customers], ['driver', 'Add a driver', drivers], ['vehicle', 'Add a vehicle', vehicles], ['price_book', 'Publish a price book', priceBooks], ['booking', 'Create the first booking', bookings]];
      const items = checks.map(([key, label, rows]) => ({ key, label, complete: rows.length > 0 }));
      return { ok: true, completed: items.filter(item => item.complete).length, total: items.length, items };
    }
    if (route === '/api/reports/summary' && method === 'GET') {
      const [customers, duties, invoices, payments] = await Promise.all([
        dataRequest('customers?select=id&status=eq.active', {}, session.access_token),
        dataRequest('duties?select=status', {}, session.access_token),
        dataRequest('invoices?select=status,total_paise', {}, session.access_token),
        dataRequest('payments?select=status,amount_paise&status=eq.succeeded', {}, session.access_token)
      ]);
      const dutySummary = {}; duties.forEach(item => { dutySummary[item.status] = (dutySummary[item.status] || 0) + 1; });
      const invoiceSummary = {}; invoices.forEach(item => { invoiceSummary[item.status] ||= { count: 0, total_paise: 0 }; invoiceSummary[item.status].count += 1; invoiceSummary[item.status].total_paise += Number(item.total_paise || 0); });
      return { ok: true, period: url.searchParams.get('period') || 'current', summary: { customers: customers.length, duties: dutySummary, invoices: invoiceSummary, payments: { count: payments.length, total_paise: payments.reduce((sum, item) => sum + Number(item.amount_paise || 0), 0) } } };
    }
    const table = resourceMap[route];
    if (!table) throw new Error(`Supabase adapter route not implemented: ${method} ${path}`);
    if (method === 'GET') {
      const limit = Math.min(Number(url.searchParams.get('limit') || 100), 100);
      const order = table === 'bookings' ? 'scheduled_at.asc' : table === 'duties' ? 'reporting_at.asc' : table === 'organization_settings' ? 'updated_at.desc' : 'created_at.desc';
      const rows = await dataRequest(`${table}?select=*&order=${order}&limit=${limit}`, {}, session.access_token);
      return { ok: true, items: rows, count: rows.length };
    }
    const organizationScopedTables = new Set(['customers', 'drivers', 'vehicles', 'bookings', 'duties', 'invoices', 'branches', 'suppliers', 'price_books', 'documents', 'invitations', 'employees', 'travel_policies', 'booking_approvals', 'notifications', 'support_tickets', 'privacy_requests']);
    const writeBody = organizationScopedTables.has(table) ? { ...body, organization_id: await activeOrganizationId() } : body;
    if (table === 'notifications' && writeBody.recipient !== undefined) {
      writeBody.payload = { ...(writeBody.payload || {}), recipient: writeBody.recipient, variables: writeBody.variables || {} };
      delete writeBody.recipient;
      delete writeBody.variables;
    }
    const rows = await dataRequest(table, { method, body: JSON.stringify(writeBody) }, session.access_token);
    return { ok: true, item: Array.isArray(rows) ? rows[0] : rows };
  }
  async function updateMe(payload) {
    const session = await refreshIfNeeded();
    if (!session?.access_token) throw new Error('Sign in required.');
    const current = await currentUser();
    const profilePatch = {};
    if (payload.full_name !== undefined) profilePatch.full_name = payload.full_name;
    if (payload.phone !== undefined) profilePatch.phone = payload.phone;
    if (Object.keys(profilePatch).length) {
      await dataRequest(`profiles?id=eq.${encodeURIComponent(current.user.id)}`, {
        method: 'PATCH',
        body: JSON.stringify(profilePatch)
      }, session.access_token);
    }
    if (current.user.organization?.id) {
      const organizationPatch = {};
      if (payload.organization_name !== undefined) organizationPatch.name = payload.organization_name;
      if (payload.organization_city !== undefined) organizationPatch.city = payload.organization_city;
      if (payload.gstin !== undefined) organizationPatch.gstin = payload.gstin;
      if (Object.keys(organizationPatch).length) {
        await dataRequest(`organizations?id=eq.${encodeURIComponent(current.user.organization.id)}`, {
          method: 'PATCH',
          body: JSON.stringify(organizationPatch)
        }, session.access_token);
      }
    }
    return currentUser();
  }
  async function request(path, options = {}) {
    if (!enabled) throw new Error('Supabase is not configured.');
    const method = options.method || 'GET';
    let payload = {};
    if (options.body) {
      try { payload = JSON.parse(options.body); } catch (_) { payload = {}; }
    }
    if (path === '/api/auth/signup' && method === 'POST') return signUp(payload);
    if (path === '/api/auth/login' && method === 'POST') return signIn(payload);
    if (path === '/api/auth/password-reset' && method === 'POST') { await authRequest('/recover', { method: 'POST', body: JSON.stringify({ email: payload.email }) }); return { ok: true, message: 'If that address exists, a reset link will be sent shortly.' }; }
    if (path === '/api/auth/me' && method === 'GET') return currentUser();
    if (path === '/api/auth/me' && method === 'PATCH') return updateMe(payload);
    if (path === '/api/auth/logout' && method === 'POST') return signOut();
    if (path.startsWith('/api/overview') || /^\/api\/(customers|drivers|vehicles|bookings|duties|invoices|payments|sync|branches|suppliers|price-books|documents|invitations|employees|policies|approvals|notifications|devices|reports|audit|tickets|privacy|integrations|organization|settings|onboarding|setup|network|supplier-bills|costs|vehicle-costs|driver-payouts|supplier-payouts|financial-actions|alerts|geofences|sla|tax|admin|capacity|billing-notes|payment-links|jobs|security)/.test(path)) return supabaseDomainRequest(path, options);
    throw new Error(`Supabase adapter route not implemented: ${method} ${path}`);
  }
  window.AxiomSupabaseAdapter = { enabled, request };
})();
