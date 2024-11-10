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

        # Prepopulate with users
        user1 = User("user_earth")
        user2 = User("user_sky")
        self.users[user1.user_id] = user1
        self.users[user2.user_id] = user2

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
    <title>The Synchronicity Engine</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; }
    </style>
</head>
<body>
    <h1>The Synchronicity Engine</h1>
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

@app.route("/canvas")
def canvas():
    return """
    <!doctype html>
    <html lang="en">
    <head>
        <title>Canvas</title>
        <style>
            body { font-family: Arial, sans-serif; }
            canvas { border: 1px solid black; }
        </style>
    </head>
    <body>
        <h1>Canvas</h1>
        <canvas id="myCanvas" width="500" height="500"></canvas>
        <script>
            var canvas = document.getElementById('myCanvas');
            var context = canvas.getContext('2d');
            // Add drawing logic here
        </script>
        <a href="{{ url_for('index') }}">Back to Dashboard</a>
    </body>
    </html>
    """
if __name__ == "__main__":
    app.run(debug=True)