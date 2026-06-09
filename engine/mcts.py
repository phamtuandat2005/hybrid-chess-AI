import math
import torch
import chess
from .board_utils import board_to_tensor, move_to_index

class Node:
    def __init__(self, state: chess.Board, parent=None, prior_p=1.0):
        self.state = state
        self.parent = parent
        self.children = {} # move -> Node
        self.visits = 0
        self.value_sum = 0
        self.prior_p = prior_p
        
    @property
    def q(self):
        if self.visits == 0:
            return 0
        return self.value_sum / self.visits

def puct_score(parent: Node, child: Node, c_puct=1.0):
    pb_c = math.log((parent.visits + 19652 + 1) / 19652) + c_puct
    pb_c *= math.sqrt(parent.visits) / (child.visits + 1)
    return child.q + pb_c * child.prior_p

class MCTS:
    def __init__(self, model, num_simulations=50, device='cpu'):
        self.model = model
        self.num_simulations = num_simulations
        self.device = device
        
    def search(self, initial_state: chess.Board):
        root = Node(initial_state.copy())
        
        # Evaluate root
        tensor = torch.tensor(board_to_tensor(root.state)).unsqueeze(0).to(self.device)
        with torch.no_grad():
            policy_logits, _ = self.model(tensor)
            
        policy = torch.softmax(policy_logits, dim=1).squeeze(0).cpu().numpy()
        
        # Expand root
        legal_moves = list(root.state.legal_moves)
        for move in legal_moves:
            idx = move_to_index(move)
            root.children[move] = Node(root.state.copy(), parent=root, prior_p=policy[idx])
            
        for _ in range(self.num_simulations):
            node = root
            # 1. Select
            search_path = [node]
            while len(node.children) > 0:
                best_score = -float('inf')
                best_move = None
                best_child = None
                for move, child in node.children.items():
                    score = puct_score(node, child)
                    if score > best_score:
                        best_score = score
                        best_move = move
                        best_child = child
                
                node = best_child
                node.state.push(best_move)
                search_path.append(node)
                
            # 2. Expand & Evaluate
            if not node.state.is_game_over():
                tensor = torch.tensor(board_to_tensor(node.state)).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    policy_logits, value = self.model(tensor)
                    
                policy = torch.softmax(policy_logits, dim=1).squeeze(0).cpu().numpy()
                value = value.item()
                
                legal_moves = list(node.state.legal_moves)
                for move in legal_moves:
                    idx = move_to_index(move)
                    node.children[move] = Node(node.state.copy(), parent=node, prior_p=policy[idx])
            else:
                # Terminal state
                res = node.state.result()
                if res == '1-0': value = 1.0 if node.state.turn == chess.BLACK else -1.0
                elif res == '0-1': value = -1.0 if node.state.turn == chess.BLACK else 1.0
                else: value = 0.0
                
            # 3. Backpropagate
            for n in reversed(search_path):
                n.visits += 1
                n.value_sum += value
                value = -value # Flip value for the opponent
                
            # restore state for the nodes in the search path
            for n in reversed(search_path[1:]):
                n.state.pop()
                    
        # Return move probabilities based on visit counts
        move_probs = {}
        for move, child in root.children.items():
            move_probs[move] = child.visits / (root.visits - 1) if root.visits > 1 else 0
            
        return move_probs
