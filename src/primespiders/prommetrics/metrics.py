from prometheus_client import Counter
from prometheus_client.validation import _validate_labelnames


class CustomCounter(Counter):
    def __call__(self, *labelnames: str):
        self._labelnames = _validate_labelnames(self, labelnames)
        return self


PROMETHEUS_URLS_TO_VISIT = CustomCounter(
    'urls_to_visit', 
    'Total HTTP requests received', 
    namespace='primespiders', 
    subsystem='crawl'
)

PROMETHEUS_SEEN_URLS = CustomCounter(
    'seen_urls', 
    'Total URLs seen', 
    namespace='primespiders', 
    subsystem='crawl'
)

PROMETHEUS_CRAWL_SCHEDULER_RUN = CustomCounter(
    'scheduler_runs', 
    'Total scheduler runs', 
    namespace='primespiders', 
    subsystem='crawl'
)

PROMETHEUS_AUTOMATION_SCHEDULER_RUN = CustomCounter(
    'scheduler_runs_automation', 
    'Total scheduler runs', 
    namespace='primespiders', 
    subsystem='automation'
)

PROMETHEUS_CRAWL_ON_PAGE_ACTIONS_FAILURES = CustomCounter(
    'on_page_actions_failures', 
    'Total on page actions failures', 
    namespace='primespiders', 
    subsystem='crawl'
)

PROMETHEUS_AUTOMATION_ON_PAGE_ACTIONS_FAILURES = CustomCounter(
    'on_page_actions_failures_automation', 
    'Total on page actions failures', 
    namespace='primespiders', 
    subsystem='automation'
)
