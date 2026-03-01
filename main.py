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
        num_canvas, num_flash, num_text, num_image = 0, 0, 0, 0
        question_id = 0
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
                questions = []

                for link in question_links:
                    href = await link.get_attribute("href")
                    if href:
                        question_urls.append(f"http://demo.ibobor.sk/sutaz_demo/{href}")

                serial_number = 1
                for qurl in question_urls:
                    context.log.info(f"\t\tVisiting {qurl}")
                    await page.goto(qurl)

                    screenshot = await page.query_selector("div#columnA_pozadie")
                    await screenshot.screenshot(
                        path=f"questions/{question_id}.png"
                    )

                    form = await page.query_selector("form[name='otazka']")
                    form_html = await form.inner_html()

                    import re
                    title = await page.inner_text("h3")
                    # Remove leading number, dot, and spaces
                    question_name = re.sub(r"^\d+\.\s*", "", title)
                    context.log.info(f"\t\t-> {question_name}")

                    canvas = await form.query_selector_all("canvas")
                    images = await form.query_selector_all("img")

                    qtype, question_text = "", ""
                    choices, images_arr = [], []

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

                        # question_text = await form.inner_text()
                        question_html = form_html.split('<div class="moznosti">', 1)[0]
                        question_text = " ".join(question_html.split()).replace("&nbsp;", " ")
                        option_divs = await form.query_selector_all("div.moznosti")

                        for div in option_divs:
                            import html, re
                            from bs4 import BeautifulSoup
                            input_el = await div.query_selector("input")
                            label_el = await div.query_selector("label")

                            value = await input_el.get_attribute("value") if input_el else None
                            # label_text = (await label_el.inner_text()).strip() if label_el else None
                            raw_label_html = await label_el.inner_html() if label_el else ""
                            soup_l = BeautifulSoup(raw_label_html, "html.parser")
                            label_html = html.unescape(" ".join(str(soup_l).split()))

                            # raw_html = await div.inner_html()

                            choices.append({
                                "value": value,
                                "label": label_html,
                                # "html": raw_html,
                            })

                    elif len(images) > 0:
                        qtype = "image"
                        num_image += 1
                        context.log.info("\t\t-> WITH IMAGE(S)")

                        import html, re
                        from bs4 import BeautifulSoup

                        images_arr = []
                        img_counter = 1

                        for img in images:
                            src = await img.get_attribute("src")
                            if src:
                                if src.startswith("http"):
                                    images_arr.append(src)
                                else:
                                    images_arr.append(f"http://demo.ibobor.sk{src}")

                        # ---- QUESTION ----
                        question_html = re.split(r'<div class="moznosti(?:_vedla_seba)?">', form_html, maxsplit=1)[0]
                        soup_q = BeautifulSoup(question_html, "html.parser")

                        for img in soup_q.find_all("img"):
                            img.replace_with(f"<image_{img_counter}>")
                            img_counter += 1

                        question_text = html.unescape(
                            " ".join(str(soup_q).split())
                        )

                        # ---- OPTIONS ----
                        option_divs = await form.query_selector_all(
                            "div.moznosti, div.moznosti_vedla_seba"
                        )

                        for option_div in option_divs:
                            input_el = await option_div.query_selector("input")
                            label_el = await option_div.query_selector("label")

                            value = await input_el.get_attribute("value") if input_el else None
                            label_html = ""

                            if label_el:
                                raw_label_html = await label_el.inner_html()
                                soup_l = BeautifulSoup(raw_label_html, "html.parser")

                                for img in soup_l.find_all("img"):
                                    img.replace_with(f"<image_{img_counter}>")
                                    img_counter += 1

                                label_html = html.unescape(
                                    " ".join(str(soup_l).split())
                                )

                            choices.append({
                                "value": value,
                                "label": label_html
                            })

                    data = {
                        "id": question_id,
                        "serial_number": serial_number,
                        "title": question_name,
                        "question": question_text,
                        "choices": choices,
                        "images": images_arr,
                        "year": year['text'],
                        "category": category['text'],
                        "type": qtype,
                        "correct_index": None,
                        "correct_answer": None
                    }
                    questions.append(data)

                    serial_number += 1
                    question_id += 1

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

                from bs4 import BeautifulSoup
                import re, html, os

                page_html = await page.content()
                soup = BeautifulSoup(page_html, "html.parser")

                h3_blocks = soup.find_all(
                    lambda tag: tag.name == "h3" and tag.find("a", attrs={"name": re.compile(r"^otazka\d+$")})
                )

                for h3 in h3_blocks:
                    title = h3.get_text(strip=True)
                    question_name = re.sub(r"^\d+\.\s*", "", title)

                    matching_question = next((q for q in questions if q["title"] == question_name), None)
                    if not matching_question:
                        continue

                    q_type = matching_question["type"]
                    question_id = matching_question["id"]
                    if q_type in ["Flash", "canvas"]:
                        if os.path.exists(f"questions/{question_id}.png"):
                            os.remove(f"questions/{question_id}.png")
                        continue
                    else:
                        node = h3.next_sibling
                        correct_answer = None

                        while node and getattr(node, "name", None) != "h3":
                            # CASE 1: multiple-choice (text or image)
                            if getattr(node, "name", None) == "ol":
                                for li in node.find_all("li"):
                                    img_marker = li.find("img", src=lambda x: x and "spravna" in x)
                                    if img_marker:
                                        for img in li.find_all("img", src=lambda x: x and "spravna" in x):
                                            img.decompose()

                                        answer_img = li.find("img", src=lambda x: x and "sutaz/images" in x)
                                        if answer_img:
                                            if os.path.exists(f"questions/{question_id}.png"):
                                                os.remove(f"questions/{question_id}.png")
                                            src = answer_img.get("src")
                                            if src:
                                                if src.startswith("http"):
                                                    correct_answer = src
                                                else:
                                                    correct_answer = f"http://demo.ibobor.sk{src[2:]}"
                                        else:
                                            correct_answer = html.unescape("".join(str(c) for c in li.contents))
                                        break

                            # CASE 2: text answer
                            if getattr(node, "name", None) == "p":
                                img = node.find("img", src=lambda x: x and "spravna" in x)
                                if img:
                                    next_p = node.find_next_sibling("p")
                                    if next_p:
                                        for img in next_p.find_all("img", src=lambda x: x and "spravna" in x):
                                            img.decompose()
                                        correct_answer = html.unescape("".join(str(c) for c in next_p.contents))
                                        break
                            node = node.next_sibling

                        if correct_answer:
                            correct_index = None
                            has_image_choices = any(
                                "<image_" in choice.get("label", "") for choice in matching_question["choices"])
                            if has_image_choices:
                                # Image choices: map URL → <image_N> → index
                                try:
                                    img_idx = matching_question["images"].index(correct_answer)
                                    target_label = f"<image_{img_idx + 1}>"
                                    for idx, choice in enumerate(matching_question["choices"]):
                                        if choice.get("label") == target_label:
                                            correct_index = idx
                                            break
                                except ValueError:
                                    correct_index = None
                            else:
                                # Text choices: normalize text and match
                                def norm(s):
                                    return " ".join(s.split()).strip()

                                for idx, choice in enumerate(matching_question["choices"]):
                                    if norm(choice.get("label", "")) == norm(correct_answer):
                                        correct_index = idx
                                        break
                        else:
                            correct_index = None

                        matching_question["correct_index"] = correct_index
                        matching_question["correct_answer"] = correct_answer


                for question in questions:
                    await context.push_data(question)

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
        context.log.info(f"WITH IMAGE(S) = {num_image}")
        context.log.info(f"ALL = {num_flash + num_canvas + num_text + num_image}")

    # run crawler on the single start URL
    await crawler.run(["http://demo.ibobor.sk/sutaz_demo/index.php"])


if __name__ == "__main__":
    asyncio.run(main())
