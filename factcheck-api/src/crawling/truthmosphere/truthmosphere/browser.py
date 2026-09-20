import scrapy
from scrapy.http import HtmlResponse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

CHROME_ARGUMENTS = [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-extensions",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-features=TranslateUI",
    "--disable-ipc-flooding-protection",
    "--memory-pressure-off",
    "--max_old_space_size=4096",
    # tables are laid out by javascript, which needs a viewport wide enough to render them
    "--window-size=1920,1080",
]


def build_chrome_driver() -> webdriver.Chrome:
    options = Options()

    for argument in CHROME_ARGUMENTS:
        options.add_argument(argument)

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def render(
    driver: webdriver.Chrome,
    url: str,
    ready_script: str,
    timeout: int = 30,
) -> scrapy.Selector:
    # Load the URL in the Chrome driver and wait until the ready_script returns true
    driver.get(url)

    WebDriverWait(driver, timeout).until(lambda d: d.execute_script(ready_script))

    return scrapy.Selector(
        HtmlResponse(
            url=url,
            body=driver.page_source.encode(),
            encoding="utf-8",
        )
    )
