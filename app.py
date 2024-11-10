from flask import Flask, request, render_template_string, redirect, url_for
from datetime import datetime, timedelta
from typing import Optional, List, Dict

app = Flask(__name__)

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
        if quest and user:
            # Remove old steward's reference if there is one
            if quest.steward:
                quest.steward.stewarded_quests.remove(quest)
            # Set new steward and add quest to their stewarded_quests list
            quest.steward = user
            user.stewarded_quests.append(quest)

    def get_dashboard_data(self):
        data = {
            "quests": [(quest_id, quest.total_attention_time, quest.steward) for quest_id, quest in self.quests.items()],
            "users": {
                user_id: (
                    user.task_events,
                    user.stewarded_quests,
                    user.gratitude,
                    user.task_events[-1].quest.quest_id if user.task_events else "None"
                ) for user_id, user in self.users.items()
            },
            "events": self.events,
            "user_ids": list(self.users.keys())
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
        <div class="header">Quests</div>
        <table>
            <tr>
                <th>Quest ID</th>
                <th>Total Attention Time</th>
                <th>Steward</th>
                <th>Claim Stewardship</th>
                <td>
                    {% if events %}
                        {% for event in events %}
                            {{ event.quest.quest_id }} at {{ event.timestamp }}<br>
                        {% endfor %}
                    {% else %}
                        None
                    {% endif %}
                <td>
                    {% if stewarded_quests %}
                        {% for quest in stewarded_quests %}
                            {{ quest.quest_id }}<br>
                        {% endfor %}
                    {% else %}
                        None
                    {% endif %}
                </td>
                <td>
                    {% if stewarded_quests %}
                        {% for quest in stewarded_quests %}
                            {{ quest.quest_id }}<br>
                        {% endfor %}
                    {% else %}
                        None
                    {% endif %}
                </td>
            </tr>
            {% for quest_id, total_attention_time, steward in dashboard_data['quests'] %}
            <tr>
                <td>{{ quest_id }}</td>
                <td>{{ total_attention_time }}</td>
                <td>{{ steward.user_id if steward else "None" }}</td>
                <td>
                    <form action="/claim-steward" method="post" style="display:inline;">
                        <select name="user_id">
                            {% for user_id in dashboard_data['user_ids'] %}
                            <option value="{{ user_id }}">{{ user_id }}</option>
                            {% endfor %}
                        </select>
                        <input type="hidden" name="quest_id" value="{{ quest_id }}">
                        <button type="submit">Claim</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="section">
        <div class="header">Users</div>
        <table>
            <tr>
                <th>User ID</th>
                <th>Gratitude</th>
                <th>Current Quest</th>
            </tr>
            {% for user_id, (_, stewarded_quests, gratitude, current_quest) in dashboard_data['users'].items() %}
            <tr>
                <td>{{ user_id }}</td>
                <td>{{ gratitude }}</td>
                <td>
                    <form action="/" method="post" style="display:inline;">
                        <select name="quest_id">
                            {% for quest_id, _, _ in dashboard_data['quests'] %}
                            <option value="{{ quest_id }}" {% if quest_id == current_quest %}selected{% endif %}>
                                {{ quest_id }}
                            </option>
                            {% endfor %}
                        </select>
                        <input type="hidden" name="user_id" value="{{ user_id }}">
                        <button type="submit">Switch</button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>

    <div class="section">
        <div class="header">Task-Switch Events</div>
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

@app.route("/claim-steward", methods=["POST"])
def claim_steward():
    user_id = request.form["user_id"]
    quest_id = request.form["quest_id"]
    db.claim_stewardship(quest_id, user_id)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
