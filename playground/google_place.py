import asyncio

from playwright.async_api import async_playwright

URL = 'https://www.google.com/maps/place/Grande+Pharmacie+de+Lille/@50.61921,3.0031802,14z/data=!4m10!1m2!2m1!1spharmacie+lille!3m6!1s0x47c2d573496fa237:0x2dd485f0ab4a9155!8m2!3d50.61921!4d3.041289!15sCg9waGFybWFjaWUgbGlsbGVaESIPcGhhcm1hY2llIGxpbGxlkgEIcGhhcm1hY3ngAQA!16s%2Fg%2F1v16pg3_?entry=ttu&g_ep=EgoyMDI2MDkyOS4wIKXMDSoASAFQAw%3D%3D'

if __name__ == "__main__":
    async def main():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()

            await page.goto(URL)
            
            await page.wait_for_selector('body')
            while True:
                pass

            await browser.close()

    asyncio.run(main())
