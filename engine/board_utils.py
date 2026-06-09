import chess
import numpy as np

def board_to_tensor(board: chess.Board):
    """
    Converts a chess.Board into a 3D numpy array (18, 8, 8)
    - 12 planes for pieces (P, N, B, R, Q, K for White and Black)
    - 1 plane for turn (1 if White, 0 if Black)
    - 4 planes for castling rights (WK, WQ, BK, BQ)
    - 1 plane for en passant
    """
    state = np.zeros((18, 8, 8), dtype=np.float32)
    
    # 0-5: White pieces, 6-11: Black pieces
    piece_map = {
        chess.PAWN: 0, chess.KNIGHT: 1, chess.BISHOP: 2,
        chess.ROOK: 3, chess.QUEEN: 4, chess.KING: 5
    }
    
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            idx = piece_map[piece.piece_type]
            if not piece.color: # Black
                idx += 6
            row, col = divmod(square, 8)
            state[idx, row, col] = 1.0
            
    # Turn (12)
    if board.turn == chess.WHITE:
        state[12, :, :] = 1.0
        
    # Castling rights (13-16)
    if board.has_kingside_castling_rights(chess.WHITE): state[13, :, :] = 1.0
    if board.has_queenside_castling_rights(chess.WHITE): state[14, :, :] = 1.0
    if board.has_kingside_castling_rights(chess.BLACK): state[15, :, :] = 1.0
    if board.has_queenside_castling_rights(chess.BLACK): state[16, :, :] = 1.0
    
    # En passant (17)
    if board.ep_square is not None:
        row, col = divmod(board.ep_square, 8)
        state[17, row, col] = 1.0
        
    return state

def move_to_index(move: chess.Move):
    """
    Map a move to an index in [0, 4095].
    Index = from_square * 64 + to_square
    Note: This ignores underpromotions (knight/bishop/rook) for simplicity in a basic model.
    """
    return move.from_square * 64 + move.to_square

def index_to_move(index: int, board: chess.Board):
    """
    Convert an index back to a chess.Move.
    """
    from_square = index // 64
    to_square = index % 64
    move = chess.Move(from_square, to_square)
    
    # Auto-queen promotion if applicable
    if board.piece_at(from_square) and board.piece_at(from_square).piece_type == chess.PAWN:
        if chess.square_rank(to_square) == 0 or chess.square_rank(to_square) == 7:
            move.promotion = chess.QUEEN
            
    return move
