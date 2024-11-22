from flask import Flask, request, render_template_string, redirect, url_for, session
from datetime import datetime, timedelta
from typing import Optional, List, Dict

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure secret key

# Core Data Classes
class User:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.task_events: List['TaskSwitchEvent'] = []
        self.stewarded_quests: List['Quest'] = []  # List of Quest objects for which this user is the steward

    @property
    def gratitude(self) -> timedelta:
        """Calculates the Gratitude stat as the sum of attention times across all stewarded quests."""
        return sum((quest.total_attention_time for quest in self.stewarded_quests), timedelta())

class Quest:
    def __init__(self, quest_id: str):
        self.quest_id = quest_id
        self.total_attention_time = timedelta()  # Sum of time spent on this quest
        self.task_events: List['TaskSwitchEvent'] = []
        self.steward: Optional[User] = None  # The steward of the quest

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
            self.duration_on_previous_quest = self.timestamp - previous_event.timestamp
            previous_event.quest.total_attention_time += self.duration_on_previous_quest

        self.user.task_events.append(self)
        self.quest.task_events.append(self)

# Centralized Database to simulate Holochain DHT
class CentralizedDatabase:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.quests: Dict[str, Quest] = {}
        self.events: List[TaskSwitchEvent] = []
        self.event_counter = 0  # Counter for generating unique event IDs

        # Prepopulate with users
        user1 = User("user_earth")
        user2 = User("user_sky")
        user3 = User("user_ocean")
        self.users[user1.user_id] = user1
        self.users[user2.user_id] = user2
        self.users[user3.user_id] = user3

        # Prepopulate with quests
        quest1 = Quest("quest_reforest")
        quest2 = Quest("quest_clean_water")
        quest3 = Quest("quest_solar_energy")
        self.quests[quest1.quest_id] = quest1
        self.quests[quest2.quest_id] = quest2
        self.quests[quest3.quest_id] = quest3

        # Assign initial stewardship
        self.claim_stewardship(quest1.quest_id, user1.user_id)
        self.claim_stewardship(quest2.quest_id, user2.user_id)
        self.claim_stewardship(quest3.quest_id, user1.user_id)

    def add_task_switch_event(self, user_id: str, quest_id: str):
        user = self.users.get(user_id, User(user_id))
        if user_id not in self.users:
            self.users[user_id] = user

        quest = self.quests.get(quest_id, Quest(quest_id))
        if quest_id not in self.quests:
            self.quests[quest_id] = quest

        previous_event = user.task_events[-1] if user.task_events else None
        event = TaskSwitchEvent(user, quest, previous_event)

        event.event_id = f"event_{self.event_counter}"
        self.event_counter += 1
        self.events.append(event)

    def claim_stewardship(self, quest_id: str, user_id: str):
        quest = self.quests.get(quest_id)
        user = self.users.get(user_id)
        if quest and user and (quest.steward is None or quest.steward.user_id == user_id):
            # Remove old steward's reference if there is one
            if quest.steward:
                quest.steward.stewarded_quests.remove(quest)
            # Set new steward and add quest to their stewarded_quests list
            quest.steward = user
            user.stewarded_quests.append(quest)

    def get_dashboard_data(self, selected_user_id: str):
        selected_user = self.users.get(selected_user_id)
        data = {
            "selected_user": selected_user,
            "users": list(self.users.values()),
            "quests": list(self.quests.values()),
            "events": self.events,
        }
        return data

# Initialize Centralized Database
db = CentralizedDatabase()

# HTML Template for the New Dashboard
TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <title>The Synchronicity Engine Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        header { display: flex; justify-content: space-between; align-items: center; }
        .user-toggle { margin-bottom: 20px; }
        .quest-card { border: 1px solid #ccc; padding: 15px; margin-bottom: 10px; border-radius: 5px; }
        .quest-card.steward { background-color: #e0ffe0; }
        .quest-card.current { border: 2px solid #ff9800; }
        .quest-header { display: flex; justify-content: space-between; align-items: center; }
        .quest-actions { margin-top: 10px; }
        .btn { padding: 5px 10px; border: none; border-radius: 3px; cursor: pointer; }
        .btn-switch { background-color: #2196F3; color: white; }
        .btn-steward { background-color: #4CAF50; color: white; }
        .btn-claim { background-color: #FF5722; color: white; }
        .stats { margin-top: 20px; }
    </style>
</head>
<body>
    <header>
        <h1>The Synchronicity Engine Dashboard</h1>
        <div class="user-toggle">
            <form method="post" action="{{ url_for('select_user') }}">
                <label for="user_id">Select User:</label>
                <select name="user_id" id="user_id" onchange="this.form.submit()">
                    {% for user in dashboard_data['users'] %}
                        <option value="{{ user.user_id }}" {% if dashboard_data['selected_user'].user_id == user.user_id %}selected{% endif %}>
                            {{ user.user_id }}
                        </option>
                    {% endfor %}
                </select>
            </form>
        </div>
    </header>
    <section>
        <h2>Quests for {{ dashboard_data['selected_user'].user_id }}</h2>
        {% for quest in dashboard_data['quests'] %}
            <div class="quest-card 
                {% if quest.steward == dashboard_data['selected_user'] %}steward{% endif %}
                {% if dashboard_data['selected_user'].task_events and dashboard_data['selected_user'].task_events[-1].quest == quest %}current{% endif %}">
                <div class="quest-header">
                    <h3>{{ quest.quest_id }}</h3>
                    <p>Total Attention: {{ quest.total_attention_time }}</p>
                </div>
                <p>Steward: {{ quest.steward.user_id if quest.steward else 'None' }}</p>
                <div class="quest-actions">
                    <form method="post" action="{{ url_for('switch_task') }}" style="display: inline;">
                        <input type="hidden" name="user_id" value="{{ dashboard_data['selected_user'].user_id }}">
                        <input type="hidden" name="quest_id" value="{{ quest.quest_id }}">
                        <button type="submit" class="btn btn-switch">Switch to this Quest</button>
                    </form>
                    {% if quest.steward != dashboard_data['selected_user'] %}
                        <form method="post" action="{{ url_for('claim_steward') }}" style="display: inline;">
                            <input type="hidden" name="user_id" value="{{ dashboard_data['selected_user'].user_id }}">
                            <input type="hidden" name="quest_id" value="{{ quest.quest_id }}">
                            <button type="submit" class="btn btn-steward">Claim Stewardship</button>
                        </form>
                    {% endif %}
                </div>
            </div>
        {% endfor %}
    </section>
    <section class="stats">
        <h2>Statistics for {{ dashboard_data['selected_user'].user_id }}</h2>
        <p>Total Gratitude: {{ dashboard_data['selected_user'].gratitude }}</p>
        <h3>Stewarded Quests</h3>
        <ul>
            {% for quest in dashboard_data['selected_user'].stewarded_quests %}
                <li>{{ quest.quest_id }} (Total Attention: {{ quest.total_attention_time }})</li>
            {% endfor %}
        </ul>
        <h3>Recent Task Switch Events</h3>
        <ul>
            {% for event in dashboard_data['events'] %}
                {% if event.user == dashboard_data['selected_user'] %}
                    <li>
                        Switched to {{ event.quest.quest_id }} at {{ event.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}
                        {% if event.duration_on_previous_quest %}
                            (Spent {{ event.duration_on_previous_quest }} on previous quest)
                        {% endif %}
                    </li>
                {% endif %}
            {% endfor %}
        </ul>
    </section>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    # Default to the first user if no user is selected
    selected_user_id = session.get('selected_user_id', list(db.users.keys())[0])
    dashboard_data = db.get_dashboard_data(selected_user_id)
    return render_template_string(TEMPLATE, dashboard_data=dashboard_data)

@app.route("/select-user", methods=["POST"])
def select_user():
    user_id = request.form["user_id"]
    session['selected_user_id'] = user_id
    return redirect(url_for("index"))

@app.route("/switch-task", methods=["POST"])
def switch_task():
    user_id = request.form["user_id"]
    quest_id = request.form["quest_id"]
    db.add_task_switch_event(user_id, quest_id)
    session['selected_user_id'] = user_id  # Ensure the selected user remains the same
    return redirect(url_for("index"))

@app.route("/claim-steward", methods=["POST"])
def claim_steward():
    user_id = request.form["user_id"]
    quest_id = request.form["quest_id"]
    db.claim_stewardship(quest_id, user_id)
    session['selected_user_id'] = user_id  # Ensure the selected user remains the same
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)