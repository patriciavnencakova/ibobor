import asyncio
from datetime import timedelta

from crawlee import ConcurrencySettings
from crawlee.crawlers import PlaywrightCrawler, PlaywrightCrawlingContext

GENERAL_TIMEOUT = 500


async def main() -> None:
    crawler = PlaywrightCrawler(
        request_handler_timeout=timedelta(minutes=30),
        concurrency_settings=ConcurrencySettings(
            desired_concurrency=1,
            max_concurrency=1,
        ),
        headless=False,
        browser_new_context_options={"viewport": {"width": 1280, "height": 720}},
    )

    @crawler.router.default_handler
    async def request_handler(context: PlaywrightCrawlingContext) -> None:
        page = context.page
        url = context.request.url
        context.log.info(f"Processing {url}")
        await page.goto(url)

        year_options = await page.query_selector_all('select[name="rok"] option')
        all_years = [{"value": await year.get_attribute("value"), "text": (await year.inner_text()).strip()} for year in
                     year_options]
        for year in all_years:
            if year['value'] is None or year['value'] == "":
                continue

            context.log.info(f"-> Selecting year {year['text']}")
            await page.select_option('select[name="rok"]', year['value'])

            category_options = await page.query_selector_all(
                'select[name="kat"] option'
            )
            all_categories = [
                {"value": await category.get_attribute("value"), "text": (await category.inner_text()).strip()} for
                category in category_options]
            for category in all_categories:
                if category['value'] is None or category['value'] == "":
                    continue

                # after log out, we need to select year again
                await page.select_option('select[name="rok"]', year['value'])

                context.log.info(f"-> Selecting category {category['text']}")
                await page.select_option('select[name="kat"]', category['value'])

                submit_selector = 'input[type="submit"][value="Prihlás sa!"]'
                await page.wait_for_selector(submit_selector)
                try:
                    async with page.expect_navigation(timeout=5000):
                        await page.click(submit_selector)
                except Exception:
                    context.log.error("!!! Unable to click 'Prihlás sa' selector!!!")

                await page.wait_for_timeout(GENERAL_TIMEOUT)

                submit_selector = 'input[type="submit"][value="Začať súťaž!"]'
                await page.wait_for_selector(submit_selector)
                try:
                    async with page.expect_navigation(timeout=5000):
                        await page.click(submit_selector)
                except Exception:
                    context.log.error("!!! Unable to click 'Začať súťaž' selector!!!")

                await page.wait_for_timeout(GENERAL_TIMEOUT)

                await page.wait_for_selector('a[href="sutaz.php?ukonci=1"]')
                try:
                    async with page.expect_navigation(timeout=5000):
                        await page.click('a[href="sutaz.php?ukonci=1"]')
                except Exception:
                    context.log.error("!!! Unable to click 'Ukončiť súťaž' selector!!!")

                await page.wait_for_timeout(GENERAL_TIMEOUT)

                await page.wait_for_selector('a[href="vysledky.php"]')
                try:
                    async with page.expect_navigation(timeout=5000):
                        await page.click('a[href="vysledky.php"]')
                except Exception:
                    context.log.error("!!! Unable to click 'Vyhodnotenie môjho riešenia' selector!!!")

                await page.wait_for_timeout(GENERAL_TIMEOUT)

                try:
                    title = await page.title()
                    current_url = page.url
                    context.log.info(
                        f"\tAfter submit  — title: {title}, url: {current_url}"
                    )
                except Exception:
                    context.log.info("!!! Unable to read title/url after submit!!!")

                question_titles = []
                h3s = await page.query_selector_all('h3:has(a[name^="otazka"])')

                for h3 in h3s:
                    full_text = (await h3.inner_text()).strip()
                    question_number = int(full_text.split(".")[0])
                    question_title = full_text.split(".")[1]

                    question_titles.append({"question": full_text})

                    first_p = await h3.query_selector('xpath=following-sibling::p[1]')
                    first_p_text = await first_p.inner_text() if first_p else None

                    # TODO: https://huggingface.co/datasets/CohereLabs/kaleidoscope#data-schema
                    data = {
                        "serial_number": question_number,
                        "title": question_title.strip(),
                        "preview": first_p_text,
                        "year": year['text'],
                        "category": category['text'],
                    }

                    await context.push_data(data)

                context.log.info(f"\tExtracted {len(question_titles)} questions")
                for q in question_titles:
                    context.log.info(f"\t{q['question']}")

                await page.wait_for_selector('a[href="/sutaz_demo/?action=logout"]')
                try:
                    async with page.expect_navigation(timeout=5000):
                        await page.click('a[href="/sutaz_demo/?action=logout"]')
                except Exception:
                    context.log.error("!!! Unable to click 'Odhlásiť sa' selector!!!")

                await page.wait_for_timeout(GENERAL_TIMEOUT)

    # run crawler on the single start URL
    await crawler.run(["http://demo.ibobor.sk/sutaz_demo/index.php"])


if __name__ == "__main__":
    asyncio.run(main())
