import logging
import traceback
from django.shortcuts import render
from django.views.generic import ListView, DetailView, TemplateView
from django.db.models import Q, Count
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from companies.models import Company, Sector
from companies.forms import SearchForm

logger = logging.getLogger(__name__)


def _json(data, status=200):
    r = JsonResponse(data, status=status, json_dumps_params={'ensure_ascii': False})
    r['Access-Control-Allow-Origin'] = '*'
    return r


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sectors'] = Sector.objects.annotate(
            cc=Count('companies', filter=Q(companies__is_active=True))
        ).order_by('-cc', 'name')[:20]
        ctx['total_companies'] = Company.objects.filter(is_active=True).count()
        ctx['total_reports'] = 'زنده از کدال'
        ctx['total_sectors'] = Sector.objects.count()
        ctx['top_companies'] = Company.objects.filter(
            is_active=True
        ).select_related('sector').order_by('symbol')[:12]
        return ctx


class SearchView(TemplateView):
    """LIVE SEARCH — goes directly to Codal.ir"""
    template_name = 'search_results.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()
        page = int(self.request.GET.get('page', 1))
        per_page = int(self.request.GET.get('per_page', 25))
        force = self.request.GET.get('refresh', '') == '1'
        ctx['q'] = q
        ctx['page'] = page
        ctx['per_page'] = per_page
        ctx['force_refresh'] = force
        ctx['codal_url'] = f"https://codal.ir/ReportList.aspx?search&Symbol={q}" if q else ''

        if not q:
            ctx['codal_result'] = None
            ctx['error'] = None
            return ctx

        # Try DB enrichment
        try:
            ctx['company'] = Company.objects.select_related('sector').get(symbol=q)
        except Company.DoesNotExist:
            ctx['company'] = None

        # FETCH FROM CODAL
        try:
            from crawler.codal_service import get_codal_service
            service = get_codal_service()
            result = service.search(q, page=page, per_page=per_page, force_refresh=force)
            ctx['codal_result'] = result
            ctx['error'] = result.get('error')
        except Exception as exc:
            logger.exception('Codal search failed for %s: %s', q, exc)
            ctx['codal_result'] = None
            ctx['error'] = f"خطا در اتصال به Codal.ir: {str(exc)}"
        return ctx


class CompanyListView(ListView):
    model = Company
    template_name = 'companies/company_list.html'
    paginate_by = 24
    context_object_name = 'companies'

    def get_queryset(self):
        qs = Company.objects.filter(is_active=True).select_related('sector').order_by('symbol')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(symbol__icontains=q) | Q(name__icontains=q))
        s = self.request.GET.get('sector', '').strip()
        if s:
            qs = qs.filter(Q(sector__code__iexact=s) | Q(sector__name__icontains=s))
        ct = self.request.GET.get('company_type', '').strip()
        if ct and ct in dict(Company.COMPANY_TYPE_CHOICES):
            qs = qs.filter(company_type=ct)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['q'] = self.request.GET.get('q', '')
        ctx['sector'] = self.request.GET.get('sector', '')
        ctx['company_type'] = self.request.GET.get('company_type', '')
        ctx['sectors'] = Sector.objects.order_by('name')
        ctx['company_types'] = Company.COMPANY_TYPE_CHOICES
        return ctx


class CompanyDetailView(DetailView):
    model = Company
    template_name = 'companies/company_detail.html'
    slug_field = 'symbol'
    slug_url_kwarg = 'symbol'
    context_object_name = 'company'

    def get_queryset(self):
        return Company.objects.select_related('sector')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        c = self.object
        force = self.request.GET.get('refresh', '') == '1'
        page = int(self.request.GET.get('page', 1))
        from crawler.codal_service import get_codal_service
        service = get_codal_service()
        result = service.search_all(c.symbol, force_refresh=force, max_pages=50)
        letters = result.get('letters', [])
        total = result.get('total', 0)
        paginator = Paginator(letters, 20)
        try:
            rp = paginator.page(page)
        except Exception:
            rp = paginator.page(1)
        ctx['reports_page'] = rp
        ctx['reports'] = rp.object_list
        ctx['total_reports'] = total
        ctx['codal_result'] = result
        return ctx


class SectorDetailView(DetailView):
    model = Sector
    template_name = 'companies/sector_detail.html'
    slug_field = 'code'
    slug_url_kwarg = 'code'
    context_object_name = 'sector'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['companies'] = Company.objects.filter(
            sector=self.object, is_active=True
        ).order_by('symbol')
        ctx['company_count'] = ctx['companies'].count()
        return ctx


# ── API ENDPOINTS ──────────────────────────────────────────────────

def api_search_companies(request):
    """Search companies in local DB."""
    try:
        qs = Company.objects.filter(is_active=True).select_related('sector')
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(symbol__icontains=q) | Q(name__icontains=q))
        data = [
            {'symbol': c.symbol, 'name': c.name, 'sector': c.sector.name if c.sector else ''}
            for c in qs[:50]
        ]
        return _json({'results': data})
    except Exception as e:
        return _json({'error': str(e)}, 500)


def api_search_codal(request):
    """MAIN API — search Codal.ir directly"""
    try:
        q = request.GET.get('q', '').strip()
        if not q:
            return _json({'error': 'نماد را وارد کنید', 'letters': [], 'total': 0})
        page = int(request.GET.get('page', 1))
        pp = int(request.GET.get('per_page', 50))
        force = request.GET.get('refresh', '') == '1'
        from crawler.codal_service import get_codal_service
        svc = get_codal_service()
        result = svc.search(q, page=page, per_page=pp, force_refresh=force)
        return _json(result)
    except Exception as e:
        logger.exception('api_search_codal error: %s', e)
        return _json({'error': str(e), 'letters': [], 'total': 0}, 500)


def api_search_codal_all(request, symbol):
    """Fetch ALL pages for a symbol from Codal.ir."""
    try:
        force = request.GET.get('refresh', '') == '1'
        from crawler.codal_service import get_codal_service
        svc = get_codal_service()
        result = svc.search_all(symbol, force_refresh=force, max_pages=50)
        return _json(result)
    except Exception as e:
        return _json({'error': str(e), 'letters': [], 'total': 0}, 500)


def api_company_reports(request, symbol):
    """API endpoint for company reports — paginated."""
    try:
        force = request.GET.get('refresh', '') == '1'
        page = int(request.GET.get('page', 1))
        pp = int(request.GET.get('per_page', 50))
        from crawler.codal_service import get_codal_service
        svc = get_codal_service()
        result = svc.search(symbol, page=page, per_page=pp, force_refresh=force)
        info = None
        try:
            c = Company.objects.select_related('sector').get(symbol=symbol)
            info = {
                'symbol': c.symbol,
                'name': c.name,
                'sector': c.sector.name if c.sector else '',
            }
        except Exception:
            pass
        data = dict(result)
        data['company_info'] = info
        return _json(data)
    except Exception as e:
        return _json({'error': str(e), 'letters': [], 'total': 0}, 500)


def api_autocomplete(request):
    """Autocomplete endpoint for search bar."""
    try:
        t = request.GET.get('term', '').strip()
        if not t or len(t) > 100:
            return _json({'results': []})
        cs = Company.objects.filter(is_active=True).filter(
            Q(symbol__icontains=t) | Q(name__icontains=t)
        ).select_related('sector').order_by('symbol')[:15]
        data = [
            {'symbol': c.symbol, 'name': c.name, 'sector': c.sector.name if c.sector else ''}
            for c in cs
        ]
        return _json({'results': data})
    except Exception:
        return _json({'results': []})


def api_sectors(request):
    """List all sectors with company counts."""
    try:
        ss = Sector.objects.annotate(
            cc=Count('companies', filter=Q(companies__is_active=True))
        ).order_by('-cc', 'name')
        return _json({
            'results': [
                {'code': s.code, 'name': s.name, 'count': s.cc}
                for s in ss
            ]
        })
    except Exception:
        return _json({'results': []}, 500)


def api_debug_codal(request):
    """DEBUG ENDPOINT — shows raw Codal response for troubleshooting"""
    try:
        q = request.GET.get('q', '').strip()
        if not q:
            return _json({'error': 'add ?q=SYMBOL'})
        from crawler.codal_scraper import (
            CodalScraper, codal_api_url, _http_get,
            extract_total_count, parse_codal_xml,
        )
        url = codal_api_url(q, page=1, length=5)
        http = _http_get(url, timeout=15)
        xml = http.get('text', '')
        parsed = parse_codal_xml(xml) if xml else []
        total = extract_total_count(xml) if xml else 0
        return _json({
            'url': url,
            'http_ok': http.get('ok'),
            'http_method': http.get('method'),
            'http_error': http.get('error'),
            'xml_length': len(xml) if xml else 0,
            'xml_preview': xml[:2000] if xml else '',
            'total_count': total,
            'parsed_letters': len(parsed),
            'first_letter': parsed[0] if parsed else None,
        })
    except Exception as e:
        return _json({
            'error': str(e),
            'traceback': traceback.format_exc(),
        }, 500)