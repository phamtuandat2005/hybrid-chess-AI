import torch
import torch.optim as optim
import torch.nn.functional as F
import chess
import random
import numpy as np
from engine.model import ChessNet
from engine.mcts import MCTS
from engine.board_utils import board_to_tensor, move_to_index
from tqdm import tqdm
from colorama import init, Fore, Style
import sys

# Đảm bảo in được Tiếng Việt ra console trên Windows
sys.stdout.reconfigure(encoding='utf-8')

# Khởi tạo colorama cho Windows
init(autoreset=True)

class ReplayBuffer:
    def __init__(self, capacity=10000):
        self.capacity = capacity
        self.buffer = []
        
    def add(self, state, policy, value):
        if len(self.buffer) >= self.capacity:
            self.buffer.pop(0)
        self.buffer.append((state, policy, value))
        
    def sample(self, batch_size):
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))
        
    def __len__(self):
        return len(self.buffer)

def self_play(model, mcts, num_games=50):
    model.eval()
    buffer = []
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}>> AI đang tự phân thân chơi cờ để rút kinh nghiệm...{Style.RESET_ALL}")
    
    for game in tqdm(range(num_games), desc=f"{Fore.GREEN}Tiến trình ván đấu{Style.RESET_ALL}", unit="ván", leave=True):
        board = chess.Board()
        states, policies, players = [], [], []
        
        while not board.is_game_over() and board.fullmove_number < 100:
            move_probs = mcts.search(board)
            
            # Create policy array
            policy = np.zeros(4096, dtype=np.float32)
            for move, prob in move_probs.items():
                policy[move_to_index(move)] = prob
                
            states.append(board_to_tensor(board))
            policies.append(policy)
            players.append(board.turn)
            
            # Select move
            moves = list(move_probs.keys())
            probs = list(move_probs.values())
            
            # Add some temperature/randomness in the first few moves
            if board.fullmove_number < 15:
                # Normalize probabilities to avoid floating point errors
                probs = np.array(probs, dtype=np.float64)
                if np.sum(probs) > 0:
                    probs /= np.sum(probs)
                else:
                    probs = np.ones(len(probs)) / len(probs)
                move = np.random.choice(moves, p=probs)
            else:
                move = moves[np.argmax(probs)]
                
            board.push(move)
            
        # Determine value
        res = board.result()
        if res == '1-0': winner = chess.WHITE
        elif res == '0-1': winner = chess.BLACK
        else: winner = None
        
        for state, policy, player in zip(states, policies, players):
            if winner is None:
                value = 0.0
            else:
                value = 1.0 if player == winner else -1.0
            buffer.append((state, policy, value))
            
    return buffer

def train(model, optimizer, buffer, batch_size=64, epochs=1, device='cpu'):
    model.train()
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}>> AI đang cập nhật lại bộ não từ các ván vừa chơi...{Style.RESET_ALL}")
    
    total_loss = 0
    for epoch in tqdm(range(epochs), desc=f"{Fore.YELLOW}Tiến trình học tập{Style.RESET_ALL}", unit="epoch", leave=True):
        batch = buffer.sample(batch_size)
        
        states = torch.tensor(np.array([x[0] for x in batch])).to(device)
        policies = torch.tensor(np.array([x[1] for x in batch])).to(device)
        values = torch.tensor(np.array([x[2] for x in batch]), dtype=torch.float32).unsqueeze(1).to(device)
        
        optimizer.zero_grad()
        
        pred_policies, pred_values = model(states)
        
        policy_loss = -torch.sum(policies * F.log_softmax(pred_policies, dim=1)) / states.size(0)
        value_loss = F.mse_loss(pred_values, values)
        
        loss = policy_loss + value_loss
        loss.backward()
        optimizer.step()
        
        total_loss = loss.item()
        
    print(f"{Fore.GREEN}Hoàn tất! Mức độ lỗi (Loss) hiện tại: {total_loss:.4f}{Style.RESET_ALL}")

if __name__ == '__main__':
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"{Fore.MAGENTA}Khởi động hệ thống AI trên: {device}{Style.RESET_ALL}")
    
    model = ChessNet().to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    replay_buffer = ReplayBuffer(capacity=50000)
    
    iterations = 5
    for it in range(iterations):
        print(f"\n{Fore.WHITE}{Style.BRIGHT}{'='*120}")
        print(" "*40 +f"BẮT ĐẦU VÒNG HUẤN LUYỆN {it+1}/{iterations}")
        print(f"{'='*120}{Style.RESET_ALL}")
        
        mcts = MCTS(model, num_simulations=100, device=device) # Low simulations for speed
        
        # 1. Self Play
        new_data = self_play(model, mcts, num_games=50)
        for d in new_data:
            replay_buffer.add(*d)
            
        # 2. Train
        if len(replay_buffer) >= 64:
            train(model, optimizer, replay_buffer, batch_size=64, epochs=5, device=device)
            
        # Save model
        torch.save(model.state_dict(), f'models/chess_model_it{it}.pth')
        print(f"{Fore.BLUE}>>> Đã lưu trữ kiến thức vào file models/chess_model_it{it}.pth{Style.RESET_ALL}")
