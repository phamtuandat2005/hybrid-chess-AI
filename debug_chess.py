from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sys

print("Connecting...")
options = Options()
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
driver = webdriver.Chrome(options=options)

print("Title:", driver.title)
print("URL:", driver.current_url)

js = """
let selectors = [
    'wc-move-list',
    '.move-list-component',
    '.move', 
    '.node', 
    '[data-ply]'
];
let res = {};
for (let s of selectors) {
    res[s] = document.querySelectorAll(s).length;
}
return res;
"""
counts = driver.execute_script(js)
print("Elements found:", counts)

js_moves = """
return Array.from(document.querySelectorAll('div.node, div[data-ply]')).map(e => e.innerText.trim()).filter(t => t.length > 0).slice(-15);
"""
moves = driver.execute_script(js_moves)
print("Moves list:", moves)

driver.quit()
