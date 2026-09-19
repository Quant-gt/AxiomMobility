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
check('focused uncovered smoke coverage is present', (ROOT / 'uncovered_smoke_test.py').is_file())
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
