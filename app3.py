from flask import Flask, request, render_template_string, redirect, url_for, session
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure secret key

# Core Data Classes
class User:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.task_events: List['TaskSwitchEvent'] = []
        self.accomplished_quests: List['Quest'] = []
        self.notifications: List['Event'] = []
        self.accomplishment_notifications: List['QuestAccomplishmentEvent'] = []
        self.archived_quests: Set[str] = set()  # Store quest IDs of archived quests

    @property
    def gratitude(self) -> timedelta:
        return sum((quest.total_attention_time for quest in self.accomplished_quests), timedelta())

class Quest:
    def __init__(self, quest_id: str, creator: Optional[User] = None):
        self.quest_id = quest_id
        self.creator = creator
        self.total_attention_time = timedelta()
        self.task_events: List['TaskSwitchEvent'] = []
        self.accomplished_by: Optional[User] = None

class Event:
    def __init__(self, timestamp: datetime):
        self.timestamp = timestamp

class TaskSwitchEvent(Event):
    def __init__(self, user: User, quest: Quest, previous_event: Optional['TaskSwitchEvent'] = None):
        super().__init__(datetime.now())
        self.event_id = None
        self.user = user
        self.quest = quest
        self.previous_event = previous_event
        self.duration_on_previous_quest = None

        if previous_event:
            self.duration_on_previous_quest = self.timestamp - previous_event.timestamp
            previous_event.quest.total_attention_time += self.duration_on_previous_quest

        self.user.task_events.append(self)
        self.quest.task_events.append(self)

class QuestAccomplishmentEvent(Event):
    def __init__(self, user: User, quest: Quest):
        super().__init__(datetime.now())
        self.user = user
        self.quest = quest

class CentralizedDatabase:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.quests: Dict[str, Quest] = {}
        self.events: List[Event] = []
        self.accomplishment_events: List[QuestAccomplishmentEvent] = []
        self.event_counter = 0

        user1 = User("user_earth")
        user2 = User("user_sky")
        user3 = User("user_ocean")
        self.users[user1.user_id] = user1
        self.users[user2.user_id] = user2
        self.users[user3.user_id] = user3

        quest1 = Quest("quest_reforest")
        quest2 = Quest("quest_clean_water")
        quest3 = Quest("quest_solar_energy")
        self.quests[quest1.quest_id] = quest1
        self.quests[quest2.quest_id] = quest2
        self.quests[quest3.quest_id] = quest3

    def add_task_switch_event(self, user_id: str, quest_id: str):
        user = self.users.get(user_id)
        quest = self.quests.get(quest_id)

        if not user or not quest:
            return

        previous_event = user.task_events[-1] if user.task_events else None
        event = TaskSwitchEvent(user, quest, previous_event)

        event.event_id = f"event_{self.event_counter}"
        self.event_counter += 1
        self.events.append(event)
        user.notifications.append(event)

    def accomplish_quest(self, quest_id: str, user_id: str):
        quest = self.quests.get(quest_id)
        user = self.users.get(user_id)
        if quest and user:
            quest.accomplished_by = user
            if quest not in user.accomplished_quests:
                user.accomplished_quests.append(quest)

            accomplishment_event = QuestAccomplishmentEvent(user, quest)
            self.events.append(accomplishment_event)
            self.accomplishment_events.append(accomplishment_event)

            contributing_users: Set[User] = set(event.user for event in quest.task_events)
            contributing_users.add(user)

            for contributing_user in contributing_users:
                contributing_user.accomplishment_notifications.append(accomplishment_event)

    def assign_quest(self, quest_id: str, assign_user_id: str, assigning_user_id: str):
        quest = self.quests.get(quest_id)
        assign_user = self.users.get(assign_user_id)
        assigning_user = self.users.get(assigning_user_id)
        if quest and assign_user and assigning_user:
            if quest.accomplished_by == assigning_user:
                if quest in assigning_user.accomplished_quests:
                    assigning_user.accomplished_quests.remove(quest)
                quest.accomplished_by = assign_user
                assign_user.accomplished_quests.append(quest)
                accomplishment_event = QuestAccomplishmentEvent(assign_user, quest)
                self.events.append(accomplishment_event)
                self.accomplishment_events.append(accomplishment_event)
                assign_user.accomplishment_notifications.append(accomplishment_event)

    def create_quest(self, quest_id: str, creator_id: str):
        if not quest_id.startswith('quest_'):
            quest_id = 'quest_' + quest_id
        if quest_id in self.quests:
            return
        creator = self.users.get(creator_id)
        if not creator:
            return
        new_quest = Quest(quest_id, creator)
        self.quests[quest_id] = new_quest

    def archive_quest(self, user_id: str, quest_id: str):
        user = self.users.get(user_id)
        if user and quest_id in self.quests:
            user.archived_quests.add(quest_id)

    def unarchive_quest(self, user_id: str, quest_id: str):
        user = self.users.get(user_id)
        if user and quest_id in user.archived_quests:
            user.archived_quests.remove(quest_id)

    def get_dashboard_data(self, selected_user_id: str):
        selected_user = self.users.get(selected_user_id)
        sorted_quests = sorted(self.quests.values(), key=lambda q: q.total_attention_time, reverse=True)
        archived_quests = [quest for quest in sorted_quests if quest.quest_id in selected_user.archived_quests]
        active_quests = [quest for quest in sorted_quests if quest.quest_id not in selected_user.archived_quests]
        return {
            "selected_user": selected_user,
            "users": list(self.users.values()),
            "active_quests": active_quests,
            "archived_quests": archived_quests,
            "events": self.events,
            "accomplishment_events": self.accomplishment_events,
        }

db = CentralizedDatabase()

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
        .quest-card.accomplished-by-user {
            background-color: #d1e7dd;
            border-color: #0f5132;
            color: #0f5132;
        }
        .quest-card.current { border: 2px solid #ff9800; }
        .quest-card.archived {
            background-color: #f0f0f0;
        }
        .quest-header { display: flex; justify-content: space-between; align-items: center; }
        .quest-actions { margin-top: 10px; }
        .btn { padding: 5px 10px; border: none; border-radius: 3px; cursor: pointer; }
        .btn-switch { background-color: #2196F3; color: white; }
        .btn-accomplish { background-color: #4CAF50; color: white; }
        .btn-assign { background-color: #FFC107; color: white; }
        .btn-create { background-color: #9C27B0; color: white; }
        .btn-archive { background-color: #607D8B; color: white; }
        .btn-unarchive { background-color: #795548; color: white; }
        .stats { margin-top: 20px; }
        .event-feed { margin-top: 20px; }
        .event { border-bottom: 1px solid #ccc; padding: 10px 0; }
        .event:last-child { border-bottom: none; }
        .accomplishment-feed { margin-top: 20px; background-color: #fff3cd; padding: 10px; border-radius: 5px; }
        .accomplishment-feed h2 { margin-top: 0; }
        .create-quest-form { margin-top: 20px; }
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
    <section class="create-quest-form">
        <h2>Create New Quest</h2>
        <form method="post" action="{{ url_for('create_quest') }}">
            <input type="hidden" name="creator_id" value="{{ dashboard_data['selected_user'].user_id }}">
            <label for="quest_id">Quest Name:</label>
            <input type="text" name="quest_id" id="quest_id" required placeholder="Enter quest name (e.g., 'reforest')">
            <p>Note: 'quest_' will be automatically prepended to the quest ID.</p>
            <button type="submit" class="btn btn-create">Create Quest</button>
        </form>
    </section>
    <section>
        <h2>Active Quests for {{ dashboard_data['selected_user'].user_id }}</h2>
        {% for quest in dashboard_data['active_quests'] %}
            <div class="quest-card 
                {% if quest.accomplished_by == dashboard_data['selected_user'] %}accomplished-by-user{% endif %}
                {% if dashboard_data['selected_user'].task_events and dashboard_data['selected_user'].task_events[-1].quest == quest %}current{% endif %}">
                <div class="quest-header">
                    <h3>{{ quest.quest_id }}</h3>
                    <p>Total Attention: {{ quest.total_attention_time }}</p>
                </div>
                <p>Created By: {{ quest.creator.user_id if quest.creator else 'System' }}</p>
                <p>Accomplished By: {{ quest.accomplished_by.user_id if quest.accomplished_by else 'None' }}</p>
                <div class="quest-actions">
                    <form method="post" action="{{ url_for('switch_task') }}" style="display: inline;">
                        <input type="hidden" name="user_id" value="{{ dashboard_data['selected_user'].user_id }}">
                        <input type="hidden" name="quest_id" value="{{ quest.quest_id }}">
                        <button type="submit" class="btn btn-switch">Switch to this Quest</button>
                    </form>
                    {% if quest.accomplished_by == dashboard_data['selected_user'] %}
                        <form method="post" action="{{ url_for('assign_quest') }}" style="display: inline;">
                            <input type="hidden" name="assigning_user_id" value="{{ dashboard_data['selected_user'].user_id }}">
                            <input type="hidden" name="quest_id" value="{{ quest.quest_id }}">
                            <label for="assign_user_id">Assign to:</label>
                            <select name="assign_user_id">
                                {% for user in dashboard_data['users'] %}
                                    {% if user != dashboard_data['selected_user'] %}
                                        <option value="{{ user.user_id }}">{{ user.user_id }}</option>
                                    {% endif %}
                                {% endfor %}
                            </select>
                            <button type="submit" class="btn btn-assign">Assign Quest</button>
                        </form>
                    {% endif %}
                    {% if quest.accomplished_by is none %}
                        <form method="post" action="{{ url_for('accomplish_quest') }}" style="display: inline;">
                            <input type="hidden" name="user_id" value="{{ dashboard_data['selected_user'].user_id }}">
                            <input type="hidden" name="quest_id" value="{{ quest.quest_id }}">
                            <button type="submit" class="btn btn-accomplish">Accomplish Quest</button>
                        </form>
                    {% endif %}
                    <!-- Archive Button -->
                    <form method="post" action="{{ url_for('archive_quest') }}" style="display: inline;">
                        <input type="hidden" name="user_id" value="{{ dashboard_data['selected_user'].user_id }}">
                        <input type="hidden" name="quest_id" value="{{ quest.quest_id }}">
                        <button type="submit" class="btn btn-archive">Archive Quest</button>
                    </form>
                </div>
            </div>
        {% endfor %}
    </section>
    <!-- Archived Quests Section -->
    <section>
        <h2>Archived Quests for {{ dashboard_data['selected_user'].user_id }}</h2>
        {% for quest in dashboard_data['archived_quests'] %}
            <div class="quest-card archived
                {% if quest.accomplished_by == dashboard_data['selected_user'] %}accomplished-by-user{% endif %}
                {% if dashboard_data['selected_user'].task_events and dashboard_data['selected_user'].task_events[-1].quest == quest %}current{% endif %}">
                <div class="quest-header">
                    <h3>{{ quest.quest_id }}</h3>
                    <p>Total Attention: {{ quest.total_attention_time }}</p>
                </div>
                <p>Created By: {{ quest.creator.user_id if quest.creator else 'System' }}</p>
                <p>Accomplished By: {{ quest.accomplished_by.user_id if quest.accomplished_by else 'None' }}</p>
                <div class="quest-actions">
                    <form method="post" action="{{ url_for('switch_task') }}" style="display: inline;">
                        <input type="hidden" name="user_id" value="{{ dashboard_data['selected_user'].user_id }}">
                        <input type="hidden" name="quest_id" value="{{ quest.quest_id }}">
                        <button type="submit" class="btn btn-switch">Switch to this Quest</button>
                    </form>
                    {% if quest.accomplished_by == dashboard_data['selected_user'] %}
                        <form method="post" action="{{ url_for('assign_quest') }}" style="display: inline;">
                            <input type="hidden" name="assigning_user_id" value="{{ dashboard_data['selected_user'].user_id }}">
                            <input type="hidden" name="quest_id" value="{{ quest.quest_id }}">
                            <label for="assign_user_id">Assign to:</label>
                            <select name="assign_user_id">
                                {% for user in dashboard_data['users'] %}
                                    {% if user != dashboard_data['selected_user'] %}
                                        <option value="{{ user.user_id }}">{{ user.user_id }}</option>
                                    {% endif %}
                                {% endfor %}
                            </select>
                            <button type="submit" class="btn btn-assign">Assign Quest</button>
                        </form>
                    {% endif %}
                    {% if quest.accomplished_by is none %}
                        <form method="post" action="{{ url_for('accomplish_quest') }}" style="display: inline;">
                            <input type="hidden" name="user_id" value="{{ dashboard_data['selected_user'].user_id }}">
                            <input type="hidden" name="quest_id" value="{{ quest.quest_id }}">
                            <button type="submit" class="btn btn-accomplish">Accomplish Quest</button>
                        </form>
                    {% endif %}
                    <!-- Unarchive Button -->
                    <form method="post" action="{{ url_for('unarchive_quest') }}" style="display: inline;">
                        <input type="hidden" name="user_id" value="{{ dashboard_data['selected_user'].user_id }}">
                        <input type="hidden" name="quest_id" value="{{ quest.quest_id }}">
                        <button type="submit" class="btn btn-unarchive">Unarchive Quest</button>
                    </form>
                </div>
            </div>
        {% endfor %}
    </section>
    <!-- Rest of the template remains the same -->
    <section class="stats">
        <h2>Statistics for {{ dashboard_data['selected_user'].user_id }}</h2>
        <p>Total Gratitude: {{ dashboard_data['selected_user'].gratitude }}</p>
        <h3>Accomplished Quests</h3>
        <ul>
            {% for quest in dashboard_data['selected_user'].accomplished_quests %}
                <li>{{ quest.quest_id }} (Total Attention: {{ quest.total_attention_time }})</li>
            {% endfor %}
        </ul>
    </section>
    <section class="event-feed">
        <h2>Event Feed</h2>
        {% for event in dashboard_data['selected_user'].notifications | sort(attribute='timestamp', reverse=True) %}
            <div class="event">
                {% if event.__class__.__name__ == 'TaskSwitchEvent' %}
                    <p><strong>{{ event.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</strong>: You switched to quest <em>{{ event.quest.quest_id }}</em>.</p>
                {% endif %}
            </div>
        {% endfor %}
    </section>
    <section class="accomplishment-feed">
        <h2>Quest Accomplishments</h2>
        {% for event in dashboard_data['selected_user'].accomplishment_notifications | sort(attribute='timestamp', reverse=True) %}
            <div class="event">
                {% if event.user == dashboard_data['selected_user'] %}
                    <p><strong>{{ event.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</strong>: You have accomplished the quest <em>{{ event.quest.quest_id }}</em>.</p>
                {% else %}
                    <p><strong>{{ event.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</strong>: User {{ event.user.user_id }} has accomplished the quest <em>{{ event.quest.quest_id }}</em>.</p>
                {% endif %}
            </div>
        {% endfor %}
    </section>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
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
    session['selected_user_id'] = user_id
    return redirect(url_for("index"))

@app.route("/accomplish-quest", methods=["POST"])
def accomplish_quest():
    user_id = request.form["user_id"]
    quest_id = request.form["quest_id"]
    db.accomplish_quest(quest_id, user_id)
    session['selected_user_id'] = user_id
    return redirect(url_for("index"))

@app.route("/assign-quest", methods=["POST"])
def assign_quest():
    quest_id = request.form["quest_id"]
    assign_user_id = request.form["assign_user_id"]
    assigning_user_id = request.form["assigning_user_id"]
    db.assign_quest(quest_id, assign_user_id, assigning_user_id)
    session['selected_user_id'] = assigning_user_id
    return redirect(url_for("index"))

@app.route("/create-quest", methods=["POST"])
def create_quest():
    quest_id = request.form["quest_id"]
    creator_id = request.form["creator_id"]
    db.create_quest(quest_id, creator_id)
    session['selected_user_id'] = creator_id
    return redirect(url_for("index"))

@app.route("/archive-quest", methods=["POST"])
def archive_quest():
    user_id = request.form["user_id"]
    quest_id = request.form["quest_id"]
    db.archive_quest(user_id, quest_id)
    session['selected_user_id'] = user_id
    return redirect(url_for("index"))

@app.route("/unarchive-quest", methods=["POST"])
def unarchive_quest():
    user_id = request.form["user_id"]
    quest_id = request.form["quest_id"]
    db.unarchive_quest(user_id, quest_id)
    session['selected_user_id'] = user_id
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)