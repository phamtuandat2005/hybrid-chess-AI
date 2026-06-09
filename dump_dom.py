from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
try:
    driver = webdriver.Chrome(options=options)
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if "chess.com" in driver.current_url:
            html = driver.page_source
            with open("dom_dump.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Dumped DOM to dom_dump.html")
            break
    driver.quit()
except Exception as e:
    print("Error:", e)
