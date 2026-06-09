import time
import chess
from engine.model import ChessNet
from engine.mcts import MCTS
from engine.board_utils import board_to_tensor, move_to_index
import torch
import torch.optim as optim
import torch.nn.functional as F
import numpy as np

# --- KHAI CUỘC (Italian Game) ---
ITALIAN_OPENING = {
    # Nước 1: e4
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1": "e2e4",
    # Trắng e4, Đen e5 -> Trắng Nf3
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2": "g1f3",
    # Trắng Nf3, Đen Nc6 -> Trắng Bc4 (Italian Game)
    "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3": "f1c4",
    # Trắng Bc4, Đen Bc5 (Giuoco Piano) -> Trắng c3 (Chuẩn bị d4)
    "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4": "c2c3",
    # Trắng Bc4, Đen Nf6 (Two Knights Defense) -> Trắng Ng5 (Fried Liver Attack)
    "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4": "f3g5",
}

PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100
}

# --- BẢNG GIÁ TRỊ VỊ TRÍ (Piece-Square Tables - PST) ---
# Điểm số được thiết kế cho quân Trắng, Mảng 1 chiều 64 phần tử (từ A1 đến H8).
# Mục đích: Thưởng điểm khi quân cờ đứng ở trung tâm hoặc vị trí đắc địa, phạt điểm khi ở rìa.
PST = {
    chess.PAWN: [
        0,  0,  0,  0,  0,  0,  0,  0,
        5, 10, 10,-20,-20, 10, 10,  5,
        5, -5,-10,  0,  0,-10, -5,  5,
        0,  0,  0, 20, 20,  0,  0,  0,
        5,  5, 10, 25, 25, 10,  5,  5,
       10, 10, 20, 30, 30, 20, 10, 10,
       50, 50, 50, 50, 50, 50, 50, 50,
        0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.KNIGHT: [
       -50,-40,-30,-30,-30,-30,-40,-50,
       -40,-20,  0,  5,  5,  0,-20,-40,
       -30,  5, 10, 15, 15, 10,  5,-30,
       -30,  0, 15, 20, 20, 15,  0,-30,
       -30,  5, 15, 20, 20, 15,  5,-30,
       -30,  0, 10, 15, 15, 10,  0,-30,
       -40,-20,  0,  0,  0,  0,-20,-40,
       -50,-40,-30,-30,-30,-30,-40,-50
    ],
    chess.BISHOP: [
       -20,-10,-10,-10,-10,-10,-10,-20,
       -10,  5,  0,  0,  0,  0,  5,-10,
       -10, 10, 10, 10, 10, 10, 10,-10,
       -10,  0, 10, 10, 10, 10,  0,-10,
       -10,  5,  5, 10, 10,  5,  5,-10,
       -10,  0,  5, 10, 10,  5,  0,-10,
       -10,  0,  0,  0,  0,  0,  0,-10,
       -20,-10,-10,-10,-10,-10,-10,-20
    ],
    chess.ROOK: [
         0,  0,  0,  5,  5,  0,  0,  0,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
        -5,  0,  0,  0,  0,  0,  0, -5,
         5, 10, 10, 10, 10, 10, 10,  5,
         0,  0,  0,  0,  0,  0,  0,  0
    ],
    chess.QUEEN: [
       -20,-10,-10, -5, -5,-10,-10,-20,
       -10,  0,  0,  0,  0,  0,  0,-10,
       -10,  0,  5,  5,  5,  5,  0,-10,
        -5,  0,  5,  5,  5,  5,  0, -5,
         0,  0,  5,  5,  5,  5,  0, -5,
       -10,  5,  5,  5,  5,  5,  0,-10,
       -10,  0,  5,  0,  0,  0,  0,-10,
       -20,-10,-10, -5, -5,-10,-10,-20
    ],
    chess.KING: [
        20, 30, 10,  0,  0, 10, 30, 20,
        20, 20,  0,  0,  0,  0, 20, 20,
       -10,-20,-20,-20,-20,-20,-20,-10,
       -20,-30,-30,-40,-40,-30,-30,-20,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30,
       -30,-40,-40,-50,-50,-40,-40,-30
    ]
}

def evaluate_pst(board):
    """Tính tổng điểm lợi thế vị trí của bàn cờ hiện tại dựa theo bảng PST"""
    score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            # Lật bảng cho quân Đen
            idx = square if piece.color == chess.WHITE else chess.square_mirror(square)
            val = PST[piece.piece_type][idx]
            if piece.color == board.turn:
                score += val
            else:
                score -= val
    return score

def evaluate_board_abs(board):
    if board.is_checkmate():
        return -99999
    if board.is_stalemate() or board.is_insufficient_material() or board.is_repetition():
        return 0
    score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            val = PIECE_VALUES.get(piece.piece_type, 0) * 100
            idx = square if piece.color == chess.WHITE else chess.square_mirror(square)
            pst_val = PST[piece.piece_type][idx]
            piece_score = val + pst_val
            if piece.color == board.turn:
                score += piece_score
            else:
                score -= piece_score
    return score

def negamax(board, depth, alpha, beta):
    if depth == 0 or board.is_game_over():
        return evaluate_board_abs(board), None
        
    best_move = None
    max_eval = -float('inf')
    
    moves = list(board.legal_moves)
    # Sắp xếp nước đi: ưu tiên nước ăn quân hoặc chiếu tướng để cắt tỉa (Alpha-Beta pruning) tốt hơn
    moves.sort(key=lambda m: board.is_capture(m) or board.gives_check(m), reverse=True)
    
    for move in moves:
        board.push(move)
        ev, _ = negamax(board, depth - 1, -beta, -alpha)
        ev = -ev
        board.pop()
        
        if ev > max_eval:
            max_eval = ev
            best_move = move
            
        alpha = max(alpha, ev)
        if alpha >= beta:
            break
            
    return max_eval, best_move

def analyze_tactics(board, depth=3):
    """
    Phân tích chiến thuật sâu bằng Minimax với Alpha-Beta pruning:
    Tính toán trước các nước đi của đối thủ để tìm ra nước đi tối ưu nhất.
    """
    # Lấy điểm số hiện tại của bàn cờ
    current_score = evaluate_board_abs(board)
    
    # Tính toán trước 3 nước đi (độ sâu = 3)
    score, best_move = negamax(board, depth, -float('inf'), float('inf'))
    
    # Nếu nước đi tìm được mang lại lợi thế lớn hơn một ngưỡng nhất định (ví dụ: > 100 điểm, tương đương ăn 1 Tốt)
    # Hoặc nếu đang bị đe dọa nặng (score hiện tại âm nhiều) mà nước đi này giúp cải thiện
    if best_move and score > current_score + 50:
        return best_move, f"Tính toán đa bước: Nhìn trước {depth} nước, cải thiện lợi thế ({(score - current_score)/100:.1f} điểm)"
    
    # Nếu bị đe dọa (phòng thủ)
    if best_move and score > -90000 and current_score < -50 and score > current_score:
         return best_move, f"Phòng thủ đa bước: Nhìn trước {depth} nước để thoát hiểm"

    return None, None

def get_best_move(board_input, model_path='models/chess_model_it4.pth'):
    if isinstance(board_input, str):
        board = chess.Board(board_input)
    else:
        board = board_input.copy()
        
    if board.is_game_over():
        return None, "Ván cờ đã kết thúc."
        
    # 1. Kiểm tra Khai Cuộc (Italian Game)
    # Loại bỏ phần đếm số nước đi (halfmove, fullmove) ra khỏi FEN để so sánh cấu trúc
    board_fen = board.fen()
    fen_without_clock = " ".join(board_fen.split(" ")[:4])
    for book_fen, book_move_uci in ITALIAN_OPENING.items():
        book_fen_base = " ".join(book_fen.split(" ")[:4])
        if fen_without_clock == book_fen_base:
            move = chess.Move.from_uci(book_move_uci)
            if move in board.legal_moves:
                return move, "Khai cuộc: Triển khai bài Italian Game (Ván cờ Ý)"
                
    # 2. Phân tích Chiến thuật (Tấn công / Phòng thủ)
    tactical_move, reason = analyze_tactics(board)
    if tactical_move:
        return tactical_move, reason

    # 3. Chống đi lùi (Undo) & Đi quẩn
    # MCTS chưa train kỹ dễ có xu hướng "đi quẩn" (move qua move lại 1 quân).
    # Ta sẽ phạt nặng nước đi lùi trực tiếp (A->B rồi B->A).
    last_my_move = None
    if len(board.move_stack) >= 2:
        last_my_move = board.move_stack[-2]

    # 4. Sử dụng MCTS + Neural Network (Mặc định)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = ChessNet().to(device)
    try:
        model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    except FileNotFoundError:
        pass
    
    model.eval()
    mcts = MCTS(model, num_simulations=1500, device=device)
    
    move_probs = mcts.search(board)
    
    # 5. Phối hợp kết quả MCTS và Bảng giá trị vị trí (PST)
    best_move = None
    best_prob = -float('inf')
    
    current_pst_score = evaluate_pst(board)
    
    for move, prob in move_probs.items():
        # Đánh giá sự cải thiện vị trí (PST) của nước đi này
        board.push(move)
        # Điểm PST lật ngược vì đến lượt đối thủ
        move_pst_score = -evaluate_pst(board)
        board.pop()
        
        # Điểm thưởng = Lợi thế vị trí mới so với vị trí cũ
        pst_bonus = (move_pst_score - current_pst_score) / 500.0
        prob += pst_bonus
        # Phạt nước đi "lùi" (Undo)
        if last_my_move:
            if move.from_square == last_my_move.to_square and move.to_square == last_my_move.from_square:
                prob -= 20.0 # Phạt cực nặng nước đi lùi hệt như cũ
            elif move.from_square == last_my_move.to_square and not board.is_capture(move):
                prob -= 2.0  # Phạt nhẹ nếu cứ di chuyển mãi 1 quân mà không có mục đích
            
        if prob > best_prob:
            best_prob = prob
            best_move = move
            
    return best_move, "Tính toán Chiến lược: Kết hợp PST & MCTS"

def learn_from_final_board(board, model_path='models/chess_model_it4.pth', override_result=None):
    """
    Học hỏi (Online Learning) từ ván cờ vừa kết thúc.
    Tái tạo lại các bước đi, đánh giá kết quả thắng/thua để cập nhật lại weights của Neural Network.
    """
    if not board.is_game_over() and not board.move_stack and not override_result:
        return
        
    print("\n[AI] Bắt đầu học và rút kinh nghiệm từ ván đấu vừa xong...")
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = ChessNet().to(device)
    try:
        model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    except FileNotFoundError:
        print("[AI] Không tìm thấy mô hình để học.")
        return
        
    # Xác định người chiến thắng
    res = override_result if override_result else board.result()
    if res == '1-0': winner = chess.WHITE
    elif res == '0-1': winner = chess.BLACK
    else: winner = None
    
    # Tái tạo lại game từ đầu
    temp_board = chess.Board()
    states, policies, values = [], [], []
    
    for move in board.move_stack:
        state_tensor = board_to_tensor(temp_board)
        
        # Mô phỏng policy: ưu tiên tuyệt đối nước đi thực tế (để bắt chước)
        policy = np.zeros(4096, dtype=np.float32)
        policy[move_to_index(move)] = 1.0
        
        player = temp_board.turn
        if winner is None:
            value = 0.0
        else:
            value = 1.0 if player == winner else -1.0
            
        states.append(state_tensor)
        policies.append(policy)
        values.append(value)
        
        temp_board.push(move)
        
    if not states:
        return
        
    states_t = torch.tensor(np.array(states)).to(device)
    policies_t = torch.tensor(np.array(policies)).to(device)
    values_t = torch.tensor(np.array(values), dtype=torch.float32).unsqueeze(1).to(device)
    
    optimizer = optim.Adam(model.parameters(), lr=0.0005)
    model.train()
    
    # Học nhanh 2 epochs
    for epoch in range(2):
        optimizer.zero_grad()
        pred_policies, pred_values = model(states_t)
        
        policy_loss = -torch.sum(policies_t * F.log_softmax(pred_policies, dim=1)) / states_t.size(0)
        value_loss = F.mse_loss(pred_values, values_t)
        
        loss = policy_loss + value_loss
        loss.backward()
        optimizer.step()
        
    torch.save(model.state_dict(), model_path)
    print(f"[AI] Đã cập nhật xong bộ não! (Lưu tại {model_path})")

if __name__ == "__main__":
    # Example usage with starting position FEN
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    
    print(f"Current position (FEN): {fen}")
    print("AI is thinking...")
    
    start_time = time.time()
    best_move, reason = get_best_move(fen)
    
    if best_move:
        print(f"Best move predicted: {best_move.uci()} - {reason}")
    else:
        print("Game is over or no moves available.")
        
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
