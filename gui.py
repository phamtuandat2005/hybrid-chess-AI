import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import time
import chess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from bot import get_best_move, learn_from_final_board
import sys
import subprocess
import os
import traceback

# --- Helper dịch nước cờ sang Tiếng Việt ---
def translate_move(board, move):
    piece = board.piece_at(move.from_square)
    piece_names = {
        chess.PAWN:   "Tốt (Pawn)",
        chess.KNIGHT: "Mã (Knight)",
        chess.BISHOP: "Tượng (Bishop)",
        chess.ROOK:   "Xe (Rook)",
        chess.QUEEN:  "Hậu (Queen)",
        chess.KING:   "Vua (King)"
    }
    p_name = piece_names.get(piece.piece_type, "Quân") if piece else "Quân"
    from_sq = chess.square_name(move.from_square)
    to_sq   = chess.square_name(move.to_square)
    if board.is_castling(move):
        return "Nhập thành (Castling)"
    return f"{p_name} từ ô {from_sq} -> đến ô {to_sq}"

sys.stdout.reconfigure(encoding='utf-8')

# ────────────────────────────────────────────────────────────────
# Redirect print -> Tkinter Text widget
# ────────────────────────────────────────────────────────────────
class RedirectText:
    def __init__(self, text_ctrl):
        self.output = text_ctrl
        self.output.tag_config("error", foreground="#ff4d4d")
        self.output.tag_config("warning", foreground="#f0a500")
        self.output.tag_config("info", foreground="#00ff88")

    def write(self, string):
        s = string.lower()
        tag = "info"
        if "lỗi" in s or "error" in s or "exception" in s:
            tag = "error"
        elif "cảnh báo" in s or "đối thủ" in s:
            tag = "warning"
        self.output.insert(tk.END, string, tag)
        self.output.see(tk.END)

    def flush(self):
        pass


# ────────────────────────────────────────────────────────────────
# Main App
# ────────────────────────────────────────────────────────────────
class ChessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Trợ lý AI Cờ Vua V2.2")
        self.root.geometry("1000x650")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        self.driver  = None
        self.running = False
        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        # HEADER
        hdr = tk.Frame(self.root, bg="#16213e", pady=10)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="\u265f  Trợ lý AI Cờ Vua", font=("Segoe UI", 16, "bold"),
                 bg="#16213e", fg="#e94560").pack(side=tk.LEFT, padx=20)
        tk.Label(hdr, text="RTX 3050 \u00b7 MCTS + CNN", font=("Segoe UI", 9),
                 bg="#16213e", fg="#555").pack(side=tk.RIGHT, padx=20)

        # MAIN CONTENT (Bỏ tab thủ công)
        main_frame = tk.Frame(self.root, bg="#1a1a2e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 0))
        self._build_auto_tab(main_frame)

    # ── TAB 1: AUTO ───────────────────────────────────────────────
    def _build_auto_tab(self, parent):
        ctrl = tk.Frame(parent, bg="#1a1a2e", pady=8)
        ctrl.pack(fill=tk.X)

        # BUOC 1
        row1 = tk.Frame(ctrl, bg="#1a1a2e")
        row1.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(row1, text="BƯỚC 1:", font=("Segoe UI", 10, "bold"),
                 bg="#1a1a2e", fg="#f0a500").pack(side=tk.LEFT)
        tk.Label(row1, text="  Tắt Chrome cũ & mở Chrome kết nối với AI",
                 font=("Segoe UI", 10), bg="#1a1a2e", fg="#aaa").pack(side=tk.LEFT)
        tk.Button(row1, text="\u26a1 Tắt Chrome cũ & Mở lại cho AI",
                  font=("Segoe UI", 10, "bold"), bg="#f0a500", fg="#1a1a2e",
                  relief=tk.FLAT, padx=12, pady=4,
                  command=lambda: threading.Thread(
                      target=self.kill_and_launch_chrome, daemon=True).start()
                  ).pack(side=tk.RIGHT)

        # BUOC 2
        row2 = tk.Frame(ctrl, bg="#1a1a2e")
        row2.pack(fill=tk.X, padx=12, pady=8)
        tk.Label(row2, text="BƯỚC 2:", font=("Segoe UI", 10, "bold"),
                 bg="#1a1a2e", fg="#f0a500").pack(side=tk.LEFT)
        tk.Label(row2, text="  Dán link trận đấu: ",
                 font=("Segoe UI", 10), bg="#1a1a2e", fg="#aaa").pack(side=tk.LEFT)
        
        # Tăng chiều cao thanh tìm kiếm
        self.url_entry = tk.Entry(row2, font=("Segoe UI", 12),
                                  bg="#0f3460", fg="#e0e0e0", relief=tk.FLAT,
                                  insertbackground="white")
        self.url_entry.insert(0, "https://www.chess.com")
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=5)
        
        self.start_btn = tk.Button(row2, text="\u25b6 Bắt đầu",
                                   font=("Segoe UI", 10, "bold"),
                                   bg="#00b74a", fg="white", relief=tk.FLAT,
                                   padx=12, pady=4, command=self.start_auto)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.stop_btn  = tk.Button(row2, text="\u25a0 Dừng",
                                   font=("Segoe UI", 10, "bold"),
                                   bg="#e94560", fg="white", relief=tk.FLAT,
                                   padx=12, pady=4, state=tk.DISABLED,
                                   command=self.stop_bot)
        self.stop_btn.pack(side=tk.LEFT)

        # CHỌN MÀU
        row_color = tk.Frame(ctrl, bg="#1a1a2e")
        row_color.pack(fill=tk.X, padx=12, pady=4)
        tk.Label(row_color, text="CÀI ĐẶT:", font=("Segoe UI", 10, "bold"),
                 bg="#1a1a2e", fg="#f0a500").pack(side=tk.LEFT)
        tk.Label(row_color, text="  Chỉ gợi ý cho: ",
                 font=("Segoe UI", 10), bg="#1a1a2e", fg="#aaa").pack(side=tk.LEFT)
        self.color_var = tk.StringVar()
        self.color_combo = ttk.Combobox(row_color, textvariable=self.color_var, state="readonly", width=15, font=("Segoe UI", 12))
        self.color_combo['values'] = ("Quân trắng", "Quân đen")
        self.color_combo.current(0)
        self.color_combo.pack(side=tk.LEFT, padx=(0, 8), ipady=2)

        # TỰ ĐỘNG ĐI NƯỚC
        self.auto_play_var = tk.BooleanVar(value=False)
        auto_play_cb = tk.Checkbutton(
            row_color, text="🤖 Tự động đi nước",
            variable=self.auto_play_var,
            font=("Segoe UI", 10, "bold"),
            bg="#1a1a2e", fg="#00ff88",
            activebackground="#1a1a2e", activeforeground="#00ff88",
            selectcolor="#0f3460", relief=tk.FLAT, cursor="hand2"
        )
        auto_play_cb.pack(side=tk.LEFT, padx=(20, 0))

        # Bottom: log + move panel
        bottom = tk.Frame(parent, bg="#1a1a2e")
        bottom.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self._build_log_and_move(bottom)

    # ── Log + Move Widget (shared) ─────────────────────────────────
    def _build_log_and_move(self, parent):
        log_frame = tk.Frame(parent, bg="#1a1a2e")
        log_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(log_frame, text="Nhật ký", font=("Segoe UI", 9, "italic"),
                 bg="#1a1a2e", fg="#555").pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(log_frame, bg="#0d0d1a", fg="#00ff88",
                                                   font=("Consolas", 10), bd=0)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        move_frame = tk.Frame(parent, bg="#16213e", width=220)
        move_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(12, 0))
        move_frame.pack_propagate(False)
        tk.Label(move_frame, text="GỢI Ý\nNƯỚC ĐI", font=("Segoe UI", 12, "bold"),
                 bg="#16213e", fg="#888").pack(pady=(20, 0))
        self.move_label = tk.Label(move_frame, text="--", font=("Segoe UI", 48, "bold"),
                                    fg="#e94560", bg="#16213e")
        self.move_label.pack(expand=True)
        self.desc_label = tk.Label(move_frame, text="", font=("Segoe UI", 11, "bold"),
                                   bg="#16213e", fg="#00ff88", wraplength=210)
        self.desc_label.pack(pady=(0, 8))
        self.status_label = tk.Label(move_frame, text="Đang chờ...",
                                      font=("Segoe UI", 10), bg="#16213e", fg="#555")
        self.status_label.pack(pady=(0, 20))

        sys.stdout = RedirectText(self.log_area)

    # ── CHROME ────────────────────────────────────────────────────
    def kill_and_launch_chrome(self):
        print("Đang tắt tất cả Chrome đang chạy...")
        subprocess.call("taskkill /F /IM chrome.exe /T", shell=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        print("Đã tắt Chrome cũ. Đang mở Chrome mới với cổng AI (9222)...")

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)
        if not chrome_exe:
            print("LỖI: Không tìm thấy Chrome! Bạn hãy chắc chắn Chrome đã được cài đặt ở thư mục mặc định.")
            return

        subprocess.Popen([chrome_exe, "--remote-debugging-port=9222",
                          "--user-data-dir=C:\\ChessAI_Chrome"])
        time.sleep(2)
        print("Chrome đã mở!")
        print("-> Vào chess.com, vào trận đấu, dán link vào ô BƯỚC 2 rồi nhấn [Bắt đầu].")

    # ── GET GAME STATE (selector da xac nhan hoat dong) ───────────
    def get_game_state(self):
        board = chess.Board()
        try:
            js_code = """
            let nodes = document.querySelectorAll('.node.white-move, .node.black-move');
            return Array.from(nodes).map(n => {
                let hl = n.querySelector('.node-highlight-content');
                let text = hl ? hl.innerText.trim() : n.innerText.trim();
                let fig = n.querySelector('.icon-font-chess, [data-figurine], .node-figurine');
                let prefix = fig ? (fig.getAttribute('data-figurine') || fig.innerText.trim()) : '';
                if (prefix && !text.startsWith(prefix)) {
                    return prefix + text;
                }
                return text;
            }).filter(t => t.length > 0 && !t.includes('...'));
            """
            moves = self.driver.execute_script(js_code)
            if moves:
                for san in moves:
                    try:
                        board.push_san(san)
                    except ValueError:
                        pass
        except Exception:
            pass
        return board

    # ── DETECT GAME OVER FROM chess.com PAGE ─────────────────────
    def get_game_over_result(self):
        """
        Phát hiện ván cờ kết thúc từ trang chess.com:
        - Modal kết thúc (timeout, resign, draw, checkmate)
        - Tiêu đề trang thay đổi
        - Đồng hồ dừng hẳn
        Trả về: (is_over: bool, result: str '1-0'/'0-1'/'1/2-1/2'/None)
        """
        try:
            js_code = """
            // 1. Tìm modal kết thúc ván
            let modalSelectors = [
                '.game-over-modal-content',
                '.modal-game-over-header',
                '[class*="game-over"]',
                '[class*="gameOver"]',
                '[class*="endgame"]',
                '.result-message',
                '[class*="result-"]',
                '.board-modal-container'
            ];
            for (let sel of modalSelectors) {
                let el = document.querySelector(sel);
                if (el && el.offsetParent !== null) {
                    let txt = el.innerText.toLowerCase();
                    if (txt.includes('win') || txt.includes('thắng')) return 'white_win';
                    if (txt.includes('lose') || txt.includes('thua') || txt.includes('lost')) return 'black_win';
                    if (txt.includes('draw') || txt.includes('hòa') || txt.includes('stale')) return 'draw';
                    if (txt.length > 0) return 'over_unknown';
                }
            }
            
            // 2. Kiểm tra nút 'New Game' / 'Rematch' hiện ra (dấu hiệu ván đã xong)
            let btns = document.querySelectorAll('button, a');
            for (let btn of btns) {
                let txt = (btn.innerText || '').toLowerCase();
                let cls = (btn.className || '').toLowerCase();
                if (txt.includes('new game') || txt.includes('rematch') || txt.includes('ván mới')
                    || cls.includes('new-game') || cls.includes('rematch')) {
                    if (btn.offsetParent !== null) return 'over_unknown';
                }
            }
            
            // 3. Kiểm tra title trang
            let title = document.title.toLowerCase();
            if (title.includes('won') || title.includes('lost') || title.includes('draw')) {
                return 'over_by_title';
            }
            
            return null;
            """
            raw = self.driver.execute_script(js_code)
            if raw:
                # Suy ra result từ raw + màu mình chơi
                mode = self.color_var.get()
                my_color = chess.WHITE if mode == "Quân trắng" else chess.BLACK
                if raw == 'white_win':
                    return True, '1-0' if my_color == chess.WHITE else '0-1'
                elif raw == 'black_win':
                    return True, '0-1' if my_color == chess.WHITE else '1-0'
                elif raw == 'draw':
                    return True, '1/2-1/2'
                else:
                    return True, None
        except Exception:
            pass
        return False, None

    # ── AUTO BOT LOOP ─────────────────────────────────────────────
    def make_move_on_board(self, move):
        """
        Tự động di chuyển quân cờ trên chess.com bằng ActionChains (tọa độ pixel).
        Cách này mô phỏng click chuột vật lý, tránh lỗi React synthetic events và SVG overlay.
        """
        from selenium.common.exceptions import StaleElementReferenceException
        
        for attempt in range(3):
            try:
                # 1. Dùng JS để tìm và scroll bàn cờ, tránh lỗi stale element do DOM refresh
                self.driver.execute_script("""
                    let b = document.querySelector('.board');
                    if (b) b.scrollIntoView({block: 'center', inline: 'center'});
                """)
                time.sleep(0.3) # Chờ cuộn trang và DOM ổn định

                # 2. Lấy thông tin bàn cờ mới nhất trực tiếp bằng JS
                board_info = self.driver.execute_script("""
                    let b = document.querySelector('.board');
                    if (!b) return null;
                    let r = b.getBoundingClientRect();
                    return { w: r.width, h: r.height, flipped: b.classList.contains('flipped') };
                """)
                if not board_info:
                    print("  [AUTO] Không tìm thấy bàn cờ trên trang!")
                    return False

                bw, bh = board_info['w'], board_info['h']
                sq_w, sq_h = bw / 8, bh / 8
                is_flipped = board_info['flipped']

                def get_offset(square):
                    f = chess.square_file(square)
                    r = chess.square_rank(square)
                    col = (7 - f) if is_flipped else f
                    row = r if is_flipped else (7 - r)
                    # Tính offset từ tâm của board (Selenium yêu cầu offset từ tâm element)
                    ox = col * sq_w + sq_w / 2 - bw / 2
                    oy = row * sq_h + sq_h / 2 - bh / 2
                    return ox, oy

                fox, foy = get_offset(move.from_square)
                tox, toy = get_offset(move.to_square)

                if attempt == 0:
                    print(f"  [AUTO] Click tọa độ: {chess.square_name(move.from_square)} -> {chess.square_name(move.to_square)}")

                # 3. Tìm lại board_el ngay trước khi click để giảm thiểu stale
                board_el = self.driver.find_element(By.CSS_SELECTOR, '.board')
                actions = ActionChains(self.driver)
                
                # Click ô xuất phát
                actions.move_to_element(board_el)
                actions.move_by_offset(fox, foy)
                actions.click()
                actions.pause(0.2)
                
                # Click ô đích
                actions.move_to_element(board_el)
                actions.move_by_offset(tox, toy)
                actions.click()
                actions.perform()

                # 4. Xử lý phong cấp Tốt
                if move.promotion:
                    time.sleep(0.5)
                    for promo_sel in [
                        ".promotion-piece.wq", ".promotion-piece.bq",
                        "[class*='promotion-piece'][class*='q']",
                        "[data-piece='q']", "[data-piece='Q']",
                    ]:
                        try:
                            promo_el = self.driver.find_element(By.CSS_SELECTOR, promo_sel)
                            promo_el.click()
                            break
                        except Exception:
                            continue

                print(f"  [AUTO] ✓ Đã đi: {move.uci()}")
                return True

            except StaleElementReferenceException:
                print(f"  [AUTO] Bàn cờ đang tải lại (StaleElement), thử lại lần {attempt+1}...")
                time.sleep(1)
            except Exception as e:
                print(f"  [AUTO] Lỗi khi đi nước: {e}")
                return False
                
        return False
    def bot_loop(self, url):
        self.running = True
        print("Đang kết nối vào Chrome (port 9222)...")
        options = Options()
        options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        try:
            self.driver = webdriver.Chrome(options=options)
            print("Kết nối thành công! Đang tìm tab chess.com...")

            found_chess = False
            for handle in self.driver.window_handles:
                self.driver.switch_to.window(handle)
                if "chess.com" in self.driver.current_url:
                    found_chess = True
                    break

            if not found_chess:
                self.driver.execute_script("window.open('');")
                self.driver.switch_to.window(self.driver.window_handles[-1])

            if url and "chess.com" in url:
                print(f"Đang mở: {url}")
                self.driver.get(url)
                time.sleep(2)
        except Exception as e:
            print("\n== LỖI KẾT NỐI ==")
            print("Chi tiết lỗi:", str(e))
            print("\n-> Có thể Chrome chưa được bật đúng cách với port 9222.")
            print("-> Hãy nhấn nút [Tắt Chrome cũ & Mở lại cho AI] trước, đợi Chrome mở lên rồi nhấn [Bắt đầu]!")
            self.running = False
            self.root.after(0, self.reset_buttons)
            return

        last_fen = ""
        print("Đang theo dõi bàn cờ... (Nhấn [Dừng] để thoát)\n")
        while self.running:
            try:
                board = self.get_game_state()
                fen = board.fen()

                # ── Kiểm tra kết thúc ván từ trang chess.com (resign, timeout, draw...) ──
                page_over, page_result = self.get_game_over_result()
                if page_over or board.is_game_over():
                    result_str = page_result if page_result else (board.result() if board.is_game_over() else None)
                    label_map = {'1-0': '♔ Trắng Thắng!', '0-1': '♚ Đen Thắng!', '1/2-1/2': '🤝 Hòa!'}
                    label_text = label_map.get(result_str, 'KẾT THÚC')
                    print(f"\n{'='*30}")
                    print(f"VÁN CỜ KẾT THÚC! Kết quả: {result_str or 'Không rõ'}")
                    print(f"{'='*30}")
                    self.root.after(0, lambda t=label_text: self.move_label.config(text="END", fg="#e94560"))
                    self.root.after(0, lambda t=label_text: self.desc_label.config(text=t))
                    self.root.after(0, lambda: self.status_label.config(text="Đang rút kinh nghiệm..."))

                    # Online Learning: rút kinh nghiệm từ ván vừa xong
                    try:
                        learn_from_final_board(board, override_result=result_str)
                        print("[AI] Học xong!")
                        self.root.after(0, lambda: self.status_label.config(text="AI đã học xong ✓"))
                    except Exception as e:
                        print(f"[Lỗi học tập] {e}")

                    self.running = False
                    break

                if fen != last_fen:
                    print("-" * 30)
                    print("Nước mới! Đang phân tích...")
                    
                    mode = self.color_var.get()
                    current_turn = board.turn # True = White, False = Black
                    
                    if (mode == "Quân trắng" and not current_turn) or \
                       (mode == "Quân đen" and current_turn):
                        print("Lượt đối thủ, đang chờ...")
                        self.root.after(0, lambda: self.move_label.config(text="--", fg="#555"))
                        self.root.after(0, lambda: self.desc_label.config(text="Lượt đối thủ..."))
                        self.root.after(0, lambda: self.status_label.config(text=""))
                    else:
                        self.root.after(0, lambda: self.move_label.config(text="...", fg="#f0a500"))
                        self.root.after(0, lambda: self.desc_label.config(text=""))
                        self.root.after(0, lambda: self.status_label.config(text="Đang suy nghĩ..."))
                        best, reason = get_best_move(board)
                        if best:
                            san  = board.san(best)
                            uci  = best.uci()
                            desc = translate_move(board, best)
                            print(f"  Gợi ý: {desc} ({san})")
                            self.root.after(0, lambda m=san:  self.move_label.config(text=m, fg="#00ff88"))
                            self.root.after(0, lambda d=desc: self.desc_label.config(text=f"{d}"))
                            self.root.after(0, lambda u=uci:  self.status_label.config(text=f"UCI: {u}"))

                            # Nếu bật chế độ tự động đi nước
                            if self.auto_play_var.get():
                                time.sleep(0.3)  # Dừng nhỏ để tự nhiên hơn
                                self.make_move_on_board(best)
                    last_fen = fen
                time.sleep(1)
            except Exception:
                time.sleep(1)

        try:
            self.driver.quit()
        except Exception:
            pass
        print("Đã dừng theo dõi.")
        self.root.after(0, self.reset_buttons)

    def start_auto(self):
        url = self.url_entry.get().strip()
        print(f"\n=== BẮT ĐẦU THEO DÕI ===")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.move_label.config(text="--", fg="#e94560")
        self.status_label.config(text="Đang kết nối...")
        threading.Thread(target=self.bot_loop, args=(url,), daemon=True).start()

    def stop_bot(self):
        self.running = False
        self.stop_btn.config(state=tk.DISABLED)
        print("Đang dừng...")

    def reset_buttons(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Đã dừng.")

if __name__ == "__main__":
    root = tk.Tk()
    app  = ChessApp(root)
    root.mainloop()
