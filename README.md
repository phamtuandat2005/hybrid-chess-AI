# AI Play Chess ♟️

Dự án AI chơi cờ vua kết hợp giữa các phương pháp lập trình cờ vua truyền thống (Minimax, Alpha-Beta Pruning, Bảng giá trị vị trí - PST) và các kỹ thuật Học sâu hiện đại (Neural Network, Monte Carlo Tree Search - MCTS). Đặc biệt, Bot có khả năng đọc trực tiếp trạng thái bàn cờ từ trang chess.com để hỗ trợ hoặc tự động chơi.

## 🌟 Tính năng nổi bật

- **Hybrid AI Engine:** Kết hợp Mạng Nơ-ron và MCTS để đánh giá chiến lược dài hạn, đồng thời dùng Minimax (Negamax) với Alpha-Beta Pruning để tính toán chính xác các chiến thuật (tactics) trong ngắn hạn.
- **Tối ưu hóa vị trí:** Sử dụng Bảng giá trị vị trí (Piece-Square Tables - PST) để thưởng/phạt cách bố trí quân cờ, giúp AI biết chiếm quyền kiểm soát trung tâm.
- **Học hỏi liên tục (Online Learning):** Có khả năng tự động học lại từ các ván đấu vừa kết thúc để cải thiện Trọng số (Weights) của Mạng Nơ-ron.
- **Tích hợp Chess.com:** Có thể phân tích DOM để trích xuất vị trí bàn cờ hiện tại từ web chess.com.
- **Giao diện thân thiện:** Tích hợp GUI trực quan bằng Python.

## 📁 Cấu trúc Dự án

```text
ai_play_chess/
├── bot.py                # Bộ não của AI: Kết hợp MCTS, Minimax, PST, Opening Book.
├── gui.py                # File khởi chạy chính (Entry point), giao diện người dùng.
├── train.py              # Script để huấn luyện model Neural Network độc lập.
├── chess_com_reader.py   # Script quét và đọc bàn cờ từ giao diện của chess.com.
├── engine/               # Chứa kiến trúc Deep Learning:
│   ├── model.py          # Định nghĩa Mạng Nơ-ron (ChessNet).
│   ├── mcts.py           # Thuật toán Monte Carlo Tree Search.
│   └── board_utils.py    # Các hàm hỗ trợ xử lý bàn cờ (Tensor conversion).
├── models/               # Nơi lưu trữ các file weights của model (VD: chess_model_it4.pth).
├── run_bot.bat           # Script khởi chạy nhanh Bot cùng GUI trên Windows.
└── training.bat          # Script khởi chạy quá trình huấn luyện mô hình.
```

## 🚀 Hướng dẫn Cài đặt & Sử dụng

### Yêu cầu hệ thống
- Python 3.8+
- Môi trường ảo (Virtual Environment) đã được thiết lập sẵn trong thư mục `venv`.

### Các thư viện chính (Dependencies)
Dự án yêu cầu cài đặt các thư viện sau:
- `torch` (PyTorch - Có hỗ trợ CUDA nếu có GPU sẽ tối ưu tốc độ)
- `chess` (python-chess)
- `numpy`

### Khởi chạy dự án

**1. Khởi chạy Bot qua Giao diện (GUI):**
Cách đơn giản nhất trên Windows là click đúp vào file `run_bot.bat`. Script này sẽ kích hoạt môi trường ảo và chạy `gui.py`.
Hoặc chạy trực tiếp qua Command Line:
```bash
venv\Scripts\activate
python gui.py
```

**2. Huấn luyện lại Model:**
Chạy file `training.bat` hoặc lệnh:
```bash
venv\Scripts\activate
python train.py
```

## 🧠 Logic Hoạt động của AI (`bot.py`)

Khi yêu cầu AI tìm nước đi (`get_best_move`), Bot sẽ xử lý theo trình tự:
1. **Khai cuộc (Opening Book):** Kiểm tra xem thế cờ hiện tại có nằm trong Khai cuộc Ý (Italian Game) đã định nghĩa sẵn không.
2. **Chiến thuật (Tactics):** Tính toán sâu (nhìn trước nhiều nước đi) bằng thuật toán Minimax kết hợp Alpha-Beta Pruning nhằm phát hiện và đi các nước đi ăn quân, chiếu tướng hoặc thoát khỏi nguy hiểm khẩn cấp.
3. **Chiến lược (Strategy):** Dùng Neural Network để đánh giá thế cờ, MCTS để mở rộng nhánh tìm kiếm các nước đi khả thi, sau đó kết hợp với điểm số PST để chọn ra nước đi mang lại lợi thế cao nhất.
4. **Tránh đi lặp/đi lùi:** Tự động áp dụng các hình phạt với các nước đi lùi (undo) hoặc đi luẩn quẩn vô nghĩa.

---
*Dự án đang trong quá trình phát triển và hoàn thiện. Cảm ơn bạn đã quan tâm!*
