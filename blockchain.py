from flask import Flask, jsonify, request
import hashlib
import time
import json

app = Flask(__name__)

# Block class
class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp  # Timestamp set when the block is created
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        # Include all relevant fields in the hash calculation
        block_string = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        # Mine the block by finding a hash with the required leading zeros
        while self.hash[:difficulty] != "0" * difficulty:
            self.nonce += 1
            self.hash = self.calculate_hash()  # Recalculate hash with updated nonce
        print(f"Block mined: {self.hash}")

# Blockchain class
class Blockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.difficulty = 4
        self.pending_tasks = []
        self.groups = {}  # Groups with participants and tasks
        self.reputation_threshold = 50  # Minimum reputation to approve tasks
        self.approval_threshold = 0.66  # Percentage of approvals required
        self.reputation = {}  # Track reputation points for each participant
        self.rewards = {}  # Track rewards (coins/points) for each participant

    def create_genesis_block(self):
        # Create the genesis block with hardcoded values
        return Block(0, time.time(), "Genesis Block", "0")

    def get_latest_block(self):
        return self.chain[-1]

    def create_group(self, group_name):
        if group_name not in self.groups:
            self.groups[group_name] = {"participants": [], "tasks": []}
            print(f"Group {group_name} created.")
            return True
        return False

    def enroll_in_group(self, group_name, participant):
        if group_name in self.groups:
            if participant not in self.groups[group_name]["participants"]:
                self.groups[group_name]["participants"].append(participant)
                # Initialize reputation and rewards for new participants
                if participant not in self.reputation:
                    self.reputation[participant] = 0
                if participant not in self.rewards:
                    self.rewards[participant] = 0
                print(f"{participant} enrolled in {group_name}.")
                return True
        return False

    def create_task(self, group_name, task):
        if group_name in self.groups:
            # Check if the task creator is enrolled in the group
            if task["creator"] not in self.groups[group_name]["participants"]:
                print(f"User {task['creator']} is not enrolled in {group_name}.")
                return False
            # Add a creation timestamp to the task
            task["created_at"] = time.time()
            task["approved_by"] = []
            self.groups[group_name]["tasks"].append(task)
            print(f"Task created in {group_name}: {task['description']}")
            # Reward the task creator with reputation points
            self.reputation[task["creator"]] += 20
            print(f"User {task['creator']} gained 10 reputation points for creating a task.")
            return True
        return False

    def approve_task(self, group_name, task_id, participant):
        if group_name in self.groups:
            # Check if the participant has enough reputation to approve tasks
            if self.reputation.get(participant, 0) < self.reputation_threshold:
                print(f"{participant} does not have enough reputation to approve tasks.")
                return False
            task = next((t for t in self.groups[group_name]["tasks"] if t["id"] == task_id), None)
            if task:
                # Prevent the task creator from approving their own task
                if participant == task["creator"]:
                    print(f"User {participant} cannot approve their own task.")
                    return False
                if participant not in task["approved_by"]:
                    task["approved_by"].append(participant)
                    print(f"Task {task_id} approved by {participant} in {group_name}.")
                    # Reward the approver with reputation points
                    self.reputation[participant] += 5
                    print(f"User {participant} gained 5 reputation points for approving a task.")
                    # Check if the approval threshold is reached
                    required_approvals = self.approval_threshold * len(self.groups[group_name]["participants"])
                    if len(task["approved_by"]) >= required_approvals:
                        self.mine_pending_task(group_name, task)
                    return True
        return False

    def mine_pending_task(self, group_name, task):
        # Create a new block with the task data
        new_block = Block(
            len(self.chain),
            time.time(),  # Timestamp when the block is created
            task,
            self.get_latest_block().hash
        )
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        self.groups[group_name]["tasks"] = [t for t in self.groups[group_name]["tasks"] if t["id"] != task["id"]]
        print(f"Task {task['id']} mined and added to the blockchain in {group_name}.")
        self.reward_users(group_name, task)
        return True

    def reward_users(self, group_name, task):
        # Reward the task creator with coins/points
        creator = task["creator"]
        self.rewards[creator] += 50  # Reward 50 coins for creating a task
        print(f"User {creator} rewarded with 50 coins.")

        # Reward the validators (approvers) with coins/points
        for approver in task["approved_by"]:
            self.rewards[approver] += 20  # Reward 20 coins for approving a task
            print(f"User {approver} rewarded with 20 coins for validating the task.")
        return True

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Debugging: Print block details
            print(f"Validating Block {current_block.index}:")
            print(f"Current Block Hash: {current_block.hash}")
            print(f"Calculated Hash: {current_block.calculate_hash()}")
            print(f"Previous Block Hash: {current_block.previous_hash}")
            print(f"Expected Previous Hash: {previous_block.hash}")

            if current_block.hash != current_block.calculate_hash():
                print(f"Block {current_block.index} has an invalid hash.")
                return False
            if current_block.previous_hash != previous_block.hash:
                print(f"Block {current_block.index} has an invalid previous hash.")
                return False
        return True

# Initialize blockchain
blockchain = Blockchain()

# Flask API Endpoints
@app.route("/chain", methods=["GET"])
def get_chain():
    chain_data = [block.__dict__ for block in blockchain.chain]
    return jsonify({"chain": chain_data, "length": len(chain_data)}), 200

@app.route("/groups", methods=["GET"])
def get_groups():
    return jsonify({"groups": blockchain.groups}), 200

@app.route("/reputation", methods=["GET"])
def get_reputation():
    return jsonify({"reputation": blockchain.reputation}), 200

@app.route("/rewards", methods=["GET"])
def get_rewards():
    return jsonify({"rewards": blockchain.rewards}), 200

@app.route("/create_group", methods=["POST"])
def create_group():
    data = request.get_json()
    group_name = data.get("group_name")
    if not group_name:
        return jsonify({"message": "Group name is required"}), 400
    if blockchain.create_group(group_name):
        return jsonify({"message": f"Group {group_name} created"}), 201
    return jsonify({"message": f"Group {group_name} already exists"}), 400

@app.route("/enroll_in_group", methods=["POST"])
def enroll_in_group():
    data = request.get_json()
    group_name = data.get("group_name")
    participant = data.get("participant")
    if not group_name or not participant:
        return jsonify({"message": "Group name and participant are required"}), 400
    if blockchain.enroll_in_group(group_name, participant):
        return jsonify({"message": f"{participant} enrolled in {group_name}"}), 201
    return jsonify({"message": "Failed to enroll participant"}), 400

@app.route("/create_task", methods=["POST"])
def create_task():
    data = request.get_json()
    group_name = data.get("group_name")
    task_id = data.get("id")
    description = data.get("description")
    creator = data.get("creator")
    if not group_name or not task_id or not description or not creator:
        return jsonify({"message": "Group name, task ID, description, and creator are required"}), 400
    task = {"id": task_id, "description": description, "creator": creator}
    if blockchain.create_task(group_name, task):
        return jsonify({"message": "Task created", "task": task}), 201
    return jsonify({"message": "Failed to create task. User is not enrolled in the group."}), 400

@app.route("/approve_task", methods=["POST"])
def approve_task():
    data = request.get_json()
    group_name = data.get("group_name")
    task_id = data.get("task_id")
    participant = data.get("participant")
    if not group_name or not task_id or not participant:
        return jsonify({"message": "Group name, task ID, and participant are required"}), 400
    if blockchain.approve_task(group_name, task_id, participant):
        return jsonify({"message": f"Task {task_id} approved by {participant} in {group_name}"}), 200
    return jsonify({"message": "Failed to approve task"}), 400

@app.route("/validate_chain", methods=["GET"])
def validate_chain():
    is_valid = blockchain.is_chain_valid()
    return jsonify({"is_valid": is_valid}), 200

# Run the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)