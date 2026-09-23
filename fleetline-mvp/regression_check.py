from pathlib import Path
import gzip
import re, struct, sys, json, urllib.request
from bs4 import BeautifulSoup

ROOT = Path('/home/user/fleetline-mvp')
HTML_PATH = ROOT / 'index.html'
html = HTML_PATH.read_text()
soup = BeautifulSoup(html, 'html.parser')
checks = []
def check(name, ok, detail=''):
    checks.append((name, bool(ok), detail))

# HTTP / delivery checks
for url, expected_type in [
    ('http://127.0.0.1:4173/', 'text/html'),
    ('http://127.0.0.1:4173/axiom-fleet-logo.png', 'image/png'),
    ('http://127.0.0.1:4173/api/health', 'application/json'),
]:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            body = r.read()
            ctype = r.headers.get_content_type()
            check(f'HTTP {url}', r.status == 200 and ctype == expected_type,
                  f'status={r.status}, type={ctype}, bytes={len(body)}')
    except Exception as e:
        check(f'HTTP {url}', False, repr(e))

# Optimized delivery checks
try:
    request = urllib.request.Request('http://127.0.0.1:4173/', headers={'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(request, timeout=5) as response:
        compressed = response.read()
        decoded = gzip.decompress(compressed)
        check('gzip delivery for HTML', response.headers.get('Content-Encoding') == 'gzip' and decoded == html.encode(),
              f'encoding={response.headers.get("Content-Encoding")}, compressed={len(compressed)}, raw={len(decoded)}')
except Exception as e:
    check('gzip delivery for HTML', False, repr(e))

# Document structure
check('HTML doctype', html.lstrip().lower().startswith('<!doctype html>'))
check('document language', soup.html and soup.html.get('lang') == 'en')
check('viewport meta', bool(soup.find('meta', attrs={'name':'viewport'})))
check('single title', len(soup.find_all('title')) == 1 and 'AXIOM FLEET' in soup.title.get_text())
ids = [x.get('id') for x in soup.find_all(attrs={'id': True})]
dups = sorted({i for i in ids if ids.count(i) > 1})
check('unique static IDs', not dups, ', '.join(dups))

# Required application surfaces
required_ids = ['public-site','public-pages','public-page-content','auth-screen','app-shell','login-form','login-email','login-password','toggle-password','forgot-password','signup-form','signup-role','signup-name','signup-email','signup-phone','signup-city','signup-organization','signup-gstin','signup-size','signup-license','signup-password','impact-range','demo-form','demo-form-note','drawerBackdrop','modalBackdrop','mobileMenu','notificationsBtn','helpBtn','profileBtn','logoutBtn','globalSearch']
missing = [i for i in required_ids if soup.find(id=i) is None]
check('required static IDs present', not missing, ', '.join(missing))

# Logo integration and local assets
logo_imgs = soup.find_all('img', src='axiom-fleet-logo.png')
check('official logo used in six surfaces', len(logo_imgs) == 6, f'found={len(logo_imgs)}')
check('logo images have alt text', all(i.get('alt','').strip() for i in logo_imgs))
logo_path = ROOT / 'axiom-fleet-logo.png'
check('logo asset exists', logo_path.is_file(), '')
check('logo asset non-trivial', logo_path.stat().st_size > 10000, str(logo_path.stat().st_size))
if logo_path.is_file():
    png_header = logo_path.read_bytes()[:24]
    png_width, png_height = struct.unpack('>II', png_header[16:24])
    check('optimized logo dimensions', (png_width, png_height) == (640, 184), f'{png_width}x{png_height}')
    check('optimized logo under 100KB', logo_path.stat().st_size < 100000, str(logo_path.stat().st_size))

# Route model
required_routes = ['about-us','blogs','newsroom','careers','contact-us','success-stories','terms','privacy','disclaimer','refund']
template_keys = re.findall(r"^\s*'([^']+)': `", html, re.M)
check('all requested public templates declared', all(r in template_keys for r in required_routes), f'missing={[r for r in required_routes if r not in template_keys]}')
check('template count is 10', len(template_keys) == 10, f'count={len(template_keys)}')
# Main nav/footer references should expose every route.
public_refs = set(re.findall(r'data-public-page="([^"]+)"', html))
check('all requested routes linked from public UI', set(required_routes).issubset(public_refs), f'missing={sorted(set(required_routes)-public_refs)}')

# Routing / auth guards present in source
check('backend API health route is wired', 'route == "/api/health"' in Path(ROOT / 'server.py').read_text())
check('app route is protected by backend session', "if (!currentUser && !(await restoreSession())) { showLogin(updateHash); return; }" in html)
check('hashchange route handling', "window.addEventListener('hashchange'" in html and "else if (publicPageTemplates[route]) showPublicPage(route, false);" in html)
check('all three signup roles are available', all(role in html for role in ('value=\"vendor\"','value=\"driver\"','value=\"corporate\"')))
check('prototype credentials remain available', 'admin@blueorbit.in' in html and 'motion2026' in html)
check('httpOnly session cookie is implemented', 'HttpOnly' in Path(ROOT / 'server.py').read_text())

# Interaction bindings / key source contracts
source_contracts = {
    'login submit binding': "document.getElementById('login-form').addEventListener('submit'",
    'signup submit binding': "document.getElementById('signup-form').addEventListener('submit'",
    'backend request helper': "async function apiRequest(path, options = {})",
    'password visibility toggle': "document.getElementById('toggle-password').addEventListener('click'",
    'forgot password feedback': "document.getElementById('forgot-password').addEventListener('click'",
    'calculator input update': "impactRange.addEventListener('input', updateImpact)",
    'demo form submission': "document.getElementById('demo-form').addEventListener('submit'",
    'public page interaction binding': 'function bindPublicPageInteractions(scope = document)',
    'logout clears backend session': "apiRequest('/api/auth/logout', { method: 'POST' })",
    'dashboard render path': 'function render()'
}
for name, needle in source_contracts.items():
    check(name, needle in html)

# Static images and anchors
all_local_img_src = []
for img in soup.find_all('img'):
    src = img.get('src','')
    if src and not src.startswith(('data:', 'http:', 'https:')):
        all_local_img_src.append(src)
missing_img = [src for src in all_local_img_src if not (ROOT/src).is_file()]
check('all local image sources resolve', not missing_img, ', '.join(missing_img))
local_script_srcs = [script.get('src') for script in soup.find_all('script', src=True) if script.get('src') and not script.get('src').startswith(('http:', 'https:'))]
missing_scripts = [src for src in local_script_srcs if not (ROOT / src).is_file()]
check('all local scripts resolve', not missing_scripts, ', '.join(missing_scripts))
migration_path = ROOT / 'supabase/migrations/20260919000000_axiom_fleet_foundation.sql'
check('Supabase migration is present', migration_path.is_file())
openapi_path = ROOT / 'openapi.yaml'
check('OpenAPI contract is present', openapi_path.is_file() and 'openapi: 3.1.0' in openapi_path.read_text() and '/api/bookings/recurring:' in openapi_path.read_text() and '/api/security/2fa/setup:' in openapi_path.read_text())
mobile_contract_path = ROOT / 'mobile_driver_contract_test.py'
check('Driver mobile vertical slice is present', mobile_contract_path.is_file() and (ROOT / 'driver-app' / 'index.html').is_file() and (ROOT / 'mobile-driver' / 'App.tsx').is_file())
if migration_path.is_file():
    migration = migration_path.read_text()
    required_domain_contracts = ('create policy customers_member_select', 'create policy sync_operations_user_access', 'create or replace function public.transition_duty', 'create or replace function public.issue_invoice', 'create or replace function public.record_payment', 'create or replace function public.record_expense', 'create or replace function public.enqueue_sync_operation', 'create or replace function public.create_invitation', 'create or replace function public.accept_invitation', 'create table if not exists public.employees', 'create table if not exists public.support_tickets', 'create table if not exists public.einvoice_records', 'create table if not exists public.collection_actions', 'create table if not exists public.onboarding_states', 'create table if not exists public.supplier_bills', 'create table if not exists public.cost_entries', 'create table if not exists public.approval_steps', 'create table if not exists public.network_edges', 'create table if not exists public.report_exports', 'create table if not exists public.retention_locks', 'create policy einvoice_records_billing_write', 'create policy collection_actions_billing_write')
    check('Supabase domain/RLS/RPC contracts are present', all(contract in migration for contract in required_domain_contracts))
network_migration_path = ROOT / 'supabase/migrations/20260922000000_axiom_network_mvp.sql'
check('Axiom Network migration is present', network_migration_path.is_file())
if network_migration_path.is_file():
    network_migration = network_migration_path.read_text()
    network_contracts = (
        'create table if not exists public.network_programs',
        'create table if not exists public.network_requirements',
        'create table if not exists public.network_requirement_versions',
        'create table if not exists public.network_vendor_profiles',
        'create table if not exists public.network_match_runs',
        'create table if not exists public.network_quote_versions',
        'create table if not exists public.network_comparisons',
        'create table if not exists public.network_awards',
        'create table if not exists public.network_activation_checks',
        'create table if not exists public.network_service_orders',
        'create table if not exists public.network_scorecards',
        'create table if not exists public.network_settlements',
        'create or replace function public.network_activate_award',
        'network_quote_versions_tenant_access',
        'network_requirements_tenant_access'
    )
    check('Axiom Network Supabase/RLS/RPC contracts are present', all(contract in network_migration for contract in network_contracts))
network_backend_path = ROOT / 'backend_network.py'
check('local Axiom Network handler is present', network_backend_path.is_file() and 'def handle_network' in network_backend_path.read_text())
check('Network smoke contract test is present', (ROOT / 'network_mvp_smoke_test.py').is_file())
check('Supabase adapter exposes Network v1 boundary', 'supabaseNetworkRequest' in (ROOT / 'supabase/client.js').read_text() and "path.startsWith('/api/network/v1')" in (ROOT / 'supabase/client.js').read_text())
p0_backend_path = ROOT / 'backend_p0.py'
p0_migration_path = ROOT / 'supabase/migrations/20260923000000_axiom_p0_foundations.sql'
p0_client = (ROOT / 'supabase/client.js').read_text()
check('P0 local handler is wired', p0_backend_path.is_file() and 'def handle_p0' in p0_backend_path.read_text() and 'handle_p0(conn' in (ROOT / 'server.py').read_text())
check('P0 Supabase migration is present', p0_migration_path.is_file() and 'create table if not exists public.p0_route_plans' in p0_migration_path.read_text() and 'p0_audit_row' in p0_migration_path.read_text())
check('P0 Supabase adapter mappings are present', 'supabaseP0Request' in p0_client and 'p0-orchestrator' in p0_client and '/api/permissions' in p0_client)
check('P0 Planning/Safety UI wiring is present', 'handlePlanningAction' in html and 'handleSafetyAction' in html and 'data-planning-action' in html and 'data-safety-action' in html)
check('P0 smoke coverage is present', (ROOT / 'p0_smoke_test.py').is_file())
check('focused uncovered smoke coverage is present', (ROOT / 'uncovered_smoke_test.py').is_file())
phase12_backend = ROOT / 'backend_phase12.py'
phase12_migration = ROOT / 'supabase/migrations/20260924000000_axiom_phase12_foundations.sql'
phase12_client = (ROOT / 'supabase/client.js').read_text()
check('Phase 1/2 local handler is wired', phase12_backend.is_file() and 'def handle_phase12' in phase12_backend.read_text() and 'handle_phase12(conn' in (ROOT / 'server.py').read_text())
phase12_sql = phase12_migration.read_text() if phase12_migration.is_file() else ''
check('Phase 1/2 migration is present', phase12_migration.is_file() and 'create table if not exists public.phase12_master_records' in phase12_sql and 'phase12_master_records' in phase12_sql and 'organization_id is not null' in phase12_sql and 'is_platform_user()' in phase12_sql)
phase12_function = ROOT / 'supabase/functions/phase12-orchestrator/index.ts'
check('Phase 1/2 Supabase boundary mappings are present', 'phase12-orchestrator' in phase12_client and '/api/mobile/home' in phase12_client and '/api/operations/live-board' in phase12_client and phase12_function.is_file() and 'RLS' in phase12_function.read_text() and 'idempotency_key' in phase12_function.read_text())
check('Phase 1/2 UI state and workflows are present', 'state.phase12Data' in html and 'renderLoadingState' in html and 'openSavedViewModal' in html and 'Mobile operations home' in html)
check('Phase 1/2 smoke coverage is present', (ROOT / 'phase12_smoke_test.py').is_file())
phase3_backend = ROOT / 'backend_phase3.py'
phase3_migration = ROOT / 'supabase/migrations/20260925000000_axiom_phase3_moat.sql'
phase3_function = ROOT / 'supabase/functions/phase3-orchestrator/index.ts'
phase3_client = (ROOT / 'supabase/client.js').read_text()
phase3_sql = phase3_migration.read_text() if phase3_migration.is_file() else ''
phase3_contracts = ('phase3_predictive_alerts', 'phase3_vendor_quality_snapshots', 'phase3_simulations', 'phase3_variance_findings', 'phase3_sustainability_trips', 'phase3_regions', 'phase3_exchange_rates')
phase3_routes = ('/api/phase3/predictive-alerts', '/api/phase3/vendor-quality/graph', '/api/phase3/simulations', '/api/phase3/variance/findings', '/api/phase3/sustainability/summary', '/api/phase3/regions')
check('Phase 3 local handler is wired', phase3_backend.is_file() and 'def handle_phase3' in phase3_backend.read_text() and 'handle_phase3(conn' in (ROOT / 'server.py').read_text())
check('Phase 3 migration and tenant RLS are present', phase3_migration.is_file() and all(f'public.{name}' in phase3_sql for name in phase3_contracts) and 'has_permission' in phase3_sql and 'p0_audit_row' in phase3_sql)
check('Phase 3 authenticated Edge/browser boundary is present', phase3_function.is_file() and 'phase3-orchestrator' in phase3_client and 'supabasePhase3Request' in phase3_client and 'getUser' in phase3_function.read_text() and all(route in phase3_function.read_text() for route in phase3_routes))
check('Phase 3 UI intelligence surface is present', 'data-page="phase3"' in html and 'function renderPhase3()' in html and 'state.phase3Data' in html and 'handlePhase3Action' in html)
check('Phase 3 OpenAPI routes are declared', openapi_path.is_file() and all(route in openapi_path.read_text() for route in phase3_routes))
check('Phase 3 smoke coverage is present', (ROOT / 'phase3_smoke_test.py').is_file() and 'RESULT Phase 3 smoke test passed' in (ROOT / 'phase3_smoke_test.py').read_text())
check('Phase 3 documentation and production gates are present', (ROOT / 'docs/phase3-moat.md').is_file() and 'Supabase production boundary' in (ROOT / 'docs/phase3-moat.md').read_text() and 'physical Android' in (ROOT / 'docs/phase3-moat.md').read_text())
# Product acceptance criteria contracts: these are intentionally source-level guards
# in addition to browser/WCAG testing at the release gate.
acceptance_contracts = {
    'loading skeleton and recovery': 'function renderLoadingState()' in html and 'data-action="retry-hydration"' in html,
    'empty states explain next action': 'class="table-empty"' in html and 'Add the first' in html,
    'sticky long-form save actions': '.modal-footer { position: sticky' in html and 'settings-save-bar' in html and 'master-form-section' in html,
    'field-level accessible validation': 'function validateFields' in html and 'aria-invalid' in html and 'inline-error' in html,
    'search result count and selection': 'result${list.length' in html and 'selected' in html and 'result_count' in (ROOT / 'backend_phase3.py').read_text(),
    'mobile table card equivalents': 'mobile-card-table' in html and 'decorateResponsiveTables' in html,
    'bulk edit assign archive workflows': 'bulk-duty-edit' in html and 'bulk-duty-archive' in html and 'bulk_assign' in (ROOT / 'backend_phase12.py').read_text(),
    'saved views persist and reapply': '/api/views' in html and 'data-saved-view' in html and 'Saved view applied' in html,
    'keyboard shortcuts and command palette': 'ctrlKey' in html and 'openCommandPalette' in html and 'commandPaletteInput' in html,
    'mutation audit references': 'audit_reference' in html and 'toastAudit' in html,
    'error recovery action': 'toastRecovery' in html and 'recoveryAction' in html,
    'regionalized labels and formatting': 'regionalSettings' in html and 'formatDateTime' in html and 'regionalTaxLabel' in html and 'formatAmount' in html,
    'sustainability intelligence surface': all(token in html for token in ('ev-eligibility','charging-stations','total_avoided_emissions_kg','emissions_per_passenger_km_g','sustainability-report-v2')),
}
for name, ok in acceptance_contracts.items():
    check(f'Acceptance · {name}', ok)
check('domain calculation engine is present', (ROOT / 'domain_engine.py').is_file())
check('driver offline shell manifest is present', (ROOT / 'driver-manifest.json').is_file() and (ROOT / 'driver-sw.js').is_file())
check('service worker registration is wired', "navigator.serviceWorker.register('/driver-sw.js')" in html)
# Any local href should point to an in-file route, page anchor, or existing asset.
local_hrefs = [a.get('href') for a in soup.find_all('a') if a.get('href') and not a.get('href').startswith(('http:', 'https:', 'mailto:', 'tel:', 'javascript:'))]
allowed_hashes = {'#', '#home', '#login', '#app'} | {f'#{r}' for r in required_routes}
unknown_hashes = sorted({h for h in local_hrefs if h.startswith('#') and h not in allowed_hashes and not re.match(r'^#[A-Za-z][\w-]*$', h)})
check('local anchor syntax', not unknown_hashes, ', '.join(unknown_hashes))

# Form accessibility baseline
forms = soup.find_all('form')
inputs_without_label = []
for el in soup.find_all(['input','select','textarea']):
    if el.get('type') == 'hidden':
        continue
    eid = el.get('id')
    has_label = bool(el.get('aria-label','').strip()) or bool(eid and soup.find('label', attrs={'for': eid})) or bool(el.find_parent('label'))
    if not has_label:
        inputs_without_label.append(eid or el.name)
check('static form controls have labels', not inputs_without_label, ', '.join(inputs_without_label))

# CSS / logo sizing contract after requested reduction
size_contracts = ['width:140px', 'width:130px', 'width:150px', 'width:160px', 'width:112px']
check('reduced logo sizing rules present', all(x in html for x in size_contracts))

# Print results
passed = sum(ok for _,ok,_ in checks)
failed = len(checks) - passed
for name, ok, detail in checks:
    print(('PASS' if ok else 'FAIL').ljust(4), name, ('— ' + detail) if detail else '')
print(f'RESULT {passed}/{len(checks)} passed; {failed} failed')
sys.exit(1 if failed else 0)
