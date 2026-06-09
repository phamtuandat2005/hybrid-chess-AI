from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import chess
from bot import get_best_move
import sys

# Đảm bảo in được Tiếng Việt ra console trên Windows
sys.stdout.reconfigure(encoding='utf-8')

def get_game_state(driver):
    board = chess.Board()
    try:
        move_elements = driver.find_elements(By.CSS_SELECTOR, "wc-move-list div.move .node, div[data-ply]")
        for el in move_elements:
            san_move = el.text.strip().split('\n')[0].split()[0] # Dọn dẹp text thừa
            if san_move and not san_move.endswith("..."):
                try:
                    board.push_san(san_move)
                except ValueError:
                    pass
    except Exception as e:
        pass
    return board

def run_assistant(url=None):
    print("Khởi động Trợ lý Cờ vua...")
    options = Options()
    
    if url:
        print(f"Đang mở trực tiếp link: {url}")
        # Mở một trình duyệt Chrome mới
        driver = webdriver.Chrome(options=options)
        driver.get(url)
    else:
        # Chế độ Debug (Cách 3)
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        try:
            driver = webdriver.Chrome(options=options)
            print("Đã kết nối với Chrome hiện tại đang mở qua port 9222!")
        except Exception:
            print("Lỗi kết nối! Bạn chưa mở Chrome ở chế độ debug.")
            print("Vui lòng làm theo các bước sau:")
            print("1. Tắt HOÀN TOÀN trình duyệt Chrome hiện tại.")
            print("2. Mở cmd hoặc PowerShell (Windows) và chạy lệnh sau:")
            print(r'   "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222')
            print("3. Sau khi Chrome mở lên, vào trang chess.com")
            print("4. Chạy lại script này.")
            return
            
    last_fen = ""
    print("Đang theo dõi bàn cờ (Nhấn Ctrl+C để thoát)...")
    
    try:
        while True:
            board = get_game_state(driver)
            current_fen = board.fen()
            
            if current_fen != last_fen:
                print("\n" + "="*30)
                print(f"Trạng thái FEN: {current_fen}")
                print("Đang suy nghĩ...")
                
                best_move = get_best_move(current_fen)
                if best_move:
                    print(f"=> GỢI Ý NƯỚC ĐI TỐT NHẤT: {best_move.uci()} (hoặc {board.san(best_move)})")
                else:
                    print("=> VÁN CỜ ĐÃ KẾT THÚC.")
                    
                last_fen = current_fen
                
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("Đã đóng trợ lý.")
    finally:
        if url: # Chỉ tắt trình duyệt nếu là bot tự mở
            driver.quit()

if __name__ == "__main__":
    import sys
    # Mặc định gọi None để kết nối với Chrome đang mở (Cách 3)
    target_url = sys.argv[1] if len(sys.argv) > 1 else None
    run_assistant(target_url)
