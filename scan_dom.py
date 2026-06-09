from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_experimental_option('debuggerAddress', '127.0.0.1:9222')

try:
    driver = webdriver.Chrome(options=options)
    for handle in driver.window_handles:
        driver.switch_to.window(handle)
        if 'chess.com' in driver.current_url:
            print('URL:', driver.current_url)
            js = """
            return Array.from(new Set(
                Array.from(document.querySelectorAll('[class]'))
                    .flatMap(el => Array.from(el.classList))
            )).sort();
            """
            classes = driver.execute_script(js)
            print(f'Total classes: {len(classes)}')
            # Loc ra nhung class lien quan
            keywords = ['game', 'result', 'end', 'modal', 'win', 'lose', 'over', 'resign', 'draw', 'abort', 'flag']
            for c in classes:
                cl = c.lower()
                if any(k in cl for k in keywords):
                    print('  MATCH:', c)
            print('---ALL---')
            for c in classes:
                print(' ', c)
            break
    driver.quit()
except Exception as e:
    print('Error:', e)
