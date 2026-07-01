import logging
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ReportListView(TemplateView):
    """Browse latest reports from Codal.ir (live search)."""
    template_name = 'reports/report_list.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        q = self.request.GET.get('q', '').strip()
        page = int(self.request.GET.get('page', 1))
        force = self.request.GET.get('refresh', '') == '1'
        ctx['q'] = q
        ctx['page'] = page

        if q:
            try:
                from crawler.codal_service import get_codal_service
                service = get_codal_service()
                result = service.search(q, page=page, per_page=50, force_refresh=force)
                ctx['codal_result'] = result
                ctx['error'] = result.get('error')
            except Exception as exc:
                logger.exception('Report search failed: %s', exc)
                ctx['codal_result'] = None
                ctx['error'] = str(exc)
        else:
            ctx['codal_result'] = None
            ctx['error'] = None

        return ctx