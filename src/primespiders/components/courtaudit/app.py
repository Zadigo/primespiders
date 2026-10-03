from primespiders.base import BaseSpider


class CourtAuditSpider(BaseSpider):
    start_url = 'https://www.ccomptes.fr/fr/publications?f%5B0%5D=institution%3A98'

    async def run(self):
        await super().run()

    async def on_page_actions(self, current_url, *, tg = None, **kwargs):
        pass
