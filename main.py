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
        num_canvas = 0
        num_flash = 0
        num_text = 0
        num_image_single = 0
        num_image_multiple = 0
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

                context.log.info(f"\t-> Selecting category {category['text']}")
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

                question_links = await page.query_selector_all("a.otazka")
                question_urls = [f"http://demo.ibobor.sk/sutaz_demo/sutaz.php?id=1"]

                for link in question_links:
                    href = await link.get_attribute("href")
                    if href:
                        question_urls.append(f"http://demo.ibobor.sk/sutaz_demo/{href}")

                serial_number = 1
                for qurl in question_urls:
                    context.log.info(f"\t\tVisiting {qurl}")
                    await page.goto(qurl)

                    form = await page.query_selector("form[name='otazka']")
                    form_html = await page.inner_html("form[name='otazka']")

                    title = await page.inner_text("h3")
                    context.log.info(f"\t\t-> {title}")

                    canvas = await form.query_selector_all("canvas")
                    images = await form.query_selector_all("img")

                    qtype = None
                    question_text = ""
                    choices = []

                    if 'aplikácia Flash' in form_html:
                        qtype = "Flash"
                        num_flash += 1
                        context.log.info(f"\t\t-> FLASH")
                    elif len(canvas) > 0:
                        qtype = "canvas"
                        num_canvas += 1
                        context.log.info(f"\t\t-> CANVAS")
                    elif len(images) == 0:
                        qtype = "text"
                        num_text += 1
                        context.log.info(f"\t\t-> TEXT")

                        question_text = await form.inner_text()
                        question_text = " ".join(question_text.split())

                        option_divs = await form.query_selector_all("div.moznosti")

                        for div in option_divs:
                            input_el = await div.query_selector("input")
                            label_el = await div.query_selector("label")

                            value = await input_el.get_attribute("value") if input_el else None
                            label_text = (await label_el.inner_text()).strip() if label_el else None
                            # raw_html = await div.inner_html()

                            choices.append({
                                "value": value,
                                "label": label_text,
                                # "html": raw_html,
                            })

                    elif len(images) == 1:
                        qtype = "image_single"
                        num_image_single += 1
                        context.log.info(f"\t\t-> SINGLE IMAGE")
                    elif len(images) > 1:
                        qtype = "image_multiple"
                        num_image_multiple += 1
                        context.log.info(f"\t\t-> MULTIPLE IMAGES")

                    # TODO: https://huggingface.co/datasets/CohereLabs/kaleidoscope#data-schema
                    data = {
                        "serial_number": serial_number,
                        "title": title,
                        "question": question_text,
                        "choices": choices,
                        "year": year['text'],
                        "category": category['text'],
                        "type": qtype,
                    }

                    await context.push_data(data)
                    serial_number += 1

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

                await page.wait_for_selector('a[href="/sutaz_demo/?action=logout"]')
                try:
                    async with page.expect_navigation(timeout=5000):
                        await page.click('a[href="/sutaz_demo/?action=logout"]')
                except Exception:
                    context.log.error("!!! Unable to click 'Odhlásiť sa' selector!!!")

                await page.wait_for_timeout(GENERAL_TIMEOUT)

        context.log.info(f"FLASH = {num_flash}")
        context.log.info(f"CANVAS = {num_canvas}")
        context.log.info(f"TEXT = {num_text}")
        context.log.info(f"SINGLE IMAGE = {num_image_single}")
        context.log.info(f"MULTIPLE IMAGES = {num_image_multiple}")

    # run crawler on the single start URL
    await crawler.run(["http://demo.ibobor.sk/sutaz_demo/index.php"])


if __name__ == "__main__":
    asyncio.run(main())
