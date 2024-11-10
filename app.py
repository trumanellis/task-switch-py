from flask import Flask, request, render_template_string, redirect, url_for
from datetime import datetime, timedelta
from typing import Optional, List, Dict

app = Flask(__name__)

# Core Data Classes
class User:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.task_events: List['TaskSwitchEvent'] = []

class Quest:
    def __init__(self, quest_id: str):
        self.quest_id = quest_id
        self.total_attention_time = timedelta()  # Sum of time spent on this quest
        self.task_events: List['TaskSwitchEvent'] = []

class TaskSwitchEvent:
    def __init__(self, user: User, quest: Quest, previous_event: Optional['TaskSwitchEvent'] = None):
        self.event_id = None  # ID will be assigned by CentralizedDatabase
        self.user = user
        self.quest = quest
        self.timestamp = datetime.now()  # Automatically set to the current time
        self.previous_event = previous_event
        self.duration_on_previous_quest = None

        # Update quest attention time based on previous event
        if previous_event:
            # Calculate time difference between events
            self.duration_on_previous_quest = self.timestamp - previous_event.timestamp
            # Update the total attention time of the previous quest
            previous_event.quest.total_attention_time += self.duration_on_previous_quest

        # Add references to user and quest
        self.user.task_events.append(self)
        self.quest.task_events.append(self)

# Centralized Database to simulate Holochain DHT
class CentralizedDatabase:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.quests: Dict[str, Quest] = {}
        self.events: List[TaskSwitchEvent] = []
        self.event_counter = 0  # Counter for generating unique event IDs

    def add_task_switch_event(self, user_id: str, quest_id: str):
        # Retrieve or create user and quest
        user = self.users.get(user_id, User(user_id))
        if user_id not in self.users:
            self.users[user_id] = user
            
        quest = self.quests.get(quest_id, Quest(quest_id))
        if quest_id not in self.quests:
            self.quests[quest_id] = quest

        # Get the user's last event for linking
        previous_event = user.task_events[-1] if user.task_events else None

        # Create new task-switch event with current timestamp
        event = TaskSwitchEvent(user, quest, previous_event)
        
        # Generate and assign a unique event ID
        event.event_id = f"event_{self.event_counter}"
        self.event_counter += 1
        
        # Store the event
        self.events.append(event)

    def get_dashboard_data(self):
        # Collects dashboard data for rendering
        data = {
            "quests": [(quest_id, quest.total_attention_time) for quest_id, quest in self.quests.items()],
            "users": {user_id: [event for event in user.task_events] for user_id, user in self.users.items()},
            "events": self.events
        }
        return data

# Initialize Centralized Database
db = CentralizedDatabase()

# HTML Template for the Dashboard
TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <title>Task-Switch Event Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; }
        .section { margin: 20px 0; }
        .header { font-size: 24px; font-weight: bold; margin-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        table, th, td { border: 1px solid black; padding: 8px; text-align: left; }
    </style>
</head>
<body>
    <h1>Task-Switch Event Dashboard</h1>
    
    <div class="section">
        <div class="header">Add Task-Switch Event</div>
        <form action="/" method="post">
            <label for="user_id">User ID:</label>
            <input type="text" id="user_id" name="user_id" required>
            <label for="quest_id">Quest ID:</label>
            <input type="text" id="quest_id" name="quest_id" required>
            <button type="submit">Add Event</button>
        </form>
    </div>

    <div class="section">
        <div class="header">Quest Attention Summary</div>
        <table>
            <tr>
                <th>Quest ID</th>
                <th>Total Attention Time</th>
            </tr>
            {% for quest_id, total_attention_time in dashboard_data['quests'] %}
            <tr>
                <td>{{ quest_id }}</td>
                <td>{{ total_attention_time }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="section">
        <div class="header">Users and Task Events</div>
        <table>
            <tr>
                <th>User ID</th>
                <th>Task Events</th>
            </tr>
            {% for user_id, events in dashboard_data['users'].items() %}
            <tr>
                <td>{{ user_id }}</td>
                <td>
                    {% for event in events %}
                        Event '{{ event.event_id }}' -> Quest '{{ event.quest.quest_id }}' at {{ event.timestamp }}<br>
                    {% endfor %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="section">
        <div class="header">All Task-Switch Events</div>
        <table>
            <tr>
                <th>Event ID</th>
                <th>User ID</th>
                <th>Quest ID</th>
                <th>Timestamp</th>
                <th>Duration on Previous Quest</th>
            </tr>
            {% for event in dashboard_data['events'] %}
            <tr>
                <td>{{ event.event_id }}</td>
                <td>{{ event.user.user_id }}</td>
                <td>{{ event.quest.quest_id }}</td>
                <td>{{ event.timestamp }}</td>
                <td>{{ event.duration_on_previous_quest or "N/A" }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_id = request.form["user_id"]
        quest_id = request.form["quest_id"]
        db.add_task_switch_event(user_id, quest_id)
        return redirect(url_for("index"))

    dashboard_data = db.get_dashboard_data()
    return render_template_string(TEMPLATE, dashboard_data=dashboard_data)

if __name__ == "__main__":
    app.run(debug=True)