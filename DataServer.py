from flask import Flask, request

# Setup flask API
api = Flask(__name__)

# Data variables
current_checkpoint = 0


# Request methods
@api.route('/checkpoint', methods=['GET'])
def get_checkpoint():
    global current_checkpoint
    return str(current_checkpoint)


@api.route('/checkpoint', methods=['POST'])
def post_checkpoint():
    global current_checkpoint
    current_checkpoint += 1
    print(f"Checkpoint incremented to {current_checkpoint}")
    return str(current_checkpoint)


@api.route('/reset', methods=['POST'])
def post_reset():
    global current_checkpoint
    current_checkpoint = 0
    print(f"Checkpoint has been reset to {current_checkpoint}")
    return str(current_checkpoint)


@api.route('/set', methods=['POST'])
def post_set():
    global current_checkpoint
    current_checkpoint = int(request.args.get("index"))
    print(f"Checkpoint set to {current_checkpoint}")
    return str(current_checkpoint)


if __name__ == '__main__':
    api.run()
