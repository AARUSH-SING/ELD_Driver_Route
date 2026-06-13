from django.views.generic import TemplateView
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

# Serve React frontend for non-API routes
@method_decorator(never_cache, name='dispatch')
class FrontendView(TemplateView):
    template_name = 'index.html'
    content_type = 'text/html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
