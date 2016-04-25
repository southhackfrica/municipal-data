from django.contrib.sites.shortcuts import get_current_site

from utils import jsonify


class ApiErrorHandler(object):
    """ Return API 500-level errors as JSON. """
    def process_exception(self, request, exception):
        if request.path.startswith('/api/'):
            return jsonify({
                'status': 'error',
                'message': exception.message,
            }, status=500)


class SiteMiddleware(object):
    """ Toggle urls based on site.
    """
    def process_request(self, request):
        site = get_current_site(request)
        if site.name == 'Scorecard':
            request.urlconf = 'scorecard.urls'
        else:
            request.urlconf = 'municipal_finance.urls'
