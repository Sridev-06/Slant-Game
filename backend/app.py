from flask import Flask, jsonify, request
from flask_cors import CORS
from game_logic import SlantGame
from cpu_ai import GreedyAI

app = Flask(__name__)
CORS(app) # Enable CORS for frontend

game = SlantGame(size=5)
selected_strategy = 1  # Default to strategy 1

@app.route('/api/state', methods=['GET'])
def get_state():
    return jsonify(game.to_dict())

@app.route('/api/new_game', methods=['POST'])
def new_game():
    global game
    data = request.json or {}
    size = data.get('size', 5)
    game = SlantGame(size=size)
    return jsonify(game.to_dict())

@app.route('/api/move', methods=['POST'])
def make_move():
    # Human move
    data = request.json
    r = data.get('row')
    c = data.get('col')
    move_type = data.get('type') # 'L', 'R', or None/CLEAR
    
    if r is None or c is None:
        return jsonify({"error": "Invalid params"}), 400
    
    # Handle "CLEAR" string from frontend if used
    if move_type == "CLEAR":
        move_type = None

    # REMOVED Turn Check to allow free clicking in single-player mode
    # The frontend will manage multiplayer mode and only call CPU moves when needed
    # In single-player mode, the human can make as many moves as they want

    # Relaxed Rule: Allow Human to make invalid moves (check_validity=False)
    # The frontend will show visual errors (red markers).
    success = game.apply_move(r, c, move_type, check_validity=False, player='HUMAN')
    if not success:
        return jsonify({"error": "Invalid move", "state": game.to_dict()}), 400
        
    # Wait, we need to ensure corrections invoke apply_move in a way that checks self?
    # Yes, apply_move now handles is_correction internally to Undo first.
    
    return jsonify({
        "success": True,
        "state": game.to_dict()
    })

@app.route('/api/cpu_move', methods=['POST'])
def cpu_move():
    global selected_strategy
    if game.turn != 'CPU':
        return jsonify({"success": False, "message": "Not CPU turn", "state": game.to_dict()})

    ai = GreedyAI(game, strategy=selected_strategy)  # Use selected strategy
    move = ai.get_best_move()
    
    if move:
        cr, cc, ctype = move
        game.apply_move(cr, cc, ctype, player='CPU')
        return jsonify({
            "success": True, 
            "cpu_move": {"row": cr, "col": cc, "type": ctype},
            "state": game.to_dict()
        })
    else:
        # CPU Pass
        game.turn = 'HUMAN' # Toggle back
        return jsonify({"success": True, "message": "CPU Passed (No Moves)", "state": game.to_dict()})

@app.route('/api/undo', methods=['POST'])
def undo_move():
    if game.undo():
        return jsonify({"success": True, "state": game.to_dict()})
    else:
        return jsonify({"error": "Nothing to undo", "state": game.to_dict()}), 400

@app.route('/api/set_strategy', methods=['POST'])
def set_strategy():
    global selected_strategy
    data = request.json or {}
    strategy = data.get('strategy', 1)
    
    # Validate strategy number
    if strategy not in [1, 2, 3]:
        return jsonify({"error": "Invalid strategy. Must be 1, 2, or 3"}), 400
    
    selected_strategy = strategy
    return jsonify({"success": True, "strategy": selected_strategy})

@app.route('/api/solve', methods=['POST'])
def solve_game():
    # Attempt to solve the game from current state
    if game.solve_game(randomize=True, strategy=selected_strategy):
        return jsonify({"success": True, "state": game.to_dict(), "message": "Solved!"})
    else:

        msg = "No more valid greedy moves" if selected_strategy else "No solution found"
        return jsonify({"success": False, "state": game.to_dict(), "message": msg}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
