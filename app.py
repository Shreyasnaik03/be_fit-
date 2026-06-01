from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import argparse
import html
import json
import mimetypes
import time


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "befit_data.json"
TODAY = time.strftime("%Y-%m-%d")

DISHES = [
    {"name": "poha", "calories": 250, "protein": 6, "unit": "g", "quantity": 200},
    {"name": "upma", "calories": 270, "protein": 7, "unit": "g", "quantity": 220},
    {"name": "idli sambar", "calories": 310, "protein": 11, "unit": "plate", "quantity": 1},
    {"name": "masala dosa", "calories": 420, "protein": 10, "unit": "piece", "quantity": 1},
    {"name": "plain dosa", "calories": 300, "protein": 8, "unit": "piece", "quantity": 1},
    {"name": "dosa", "calories": 300, "protein": 8, "unit": "piece", "quantity": 1},
    {"name": "rice", "calories": 260, "protein": 5, "unit": "g", "quantity": 200},
    {"name": "dal rice", "calories": 420, "protein": 14, "unit": "g", "quantity": 300},
    {"name": "chapati", "calories": 110, "protein": 3, "unit": "piece", "quantity": 1},
    {"name": "dal", "calories": 180, "protein": 11, "unit": "g", "quantity": 200},
    {"name": "paneer tikka", "calories": 360, "protein": 22, "unit": "g", "quantity": 180},
    {"name": "chicken biryani", "calories": 650, "protein": 32, "unit": "g", "quantity": 350},
    {"name": "protein shake", "calories": 180, "protein": 25, "unit": "ml", "quantity": 300},
    {"name": "tea", "calories": 80, "protein": 2, "unit": "ml", "quantity": 150},
    {"name": "coffee", "calories": 90, "protein": 3, "unit": "ml", "quantity": 150},
    {"name": "milk", "calories": 122, "protein": 6, "unit": "ml", "quantity": 200},
    {"name": "samosa", "calories": 260, "protein": 5, "unit": "piece", "quantity": 1},
    {"name": "burger", "calories": 540, "protein": 22, "unit": "piece", "quantity": 1},
    {"name": "pizza", "calories": 700, "protein": 28, "unit": "piece", "quantity": 2},
]

MEAL_TYPES = ["Breakfast", "Lunch", "Snack", "Dinner", "Cheat Meal"]
UNITS = ["piece", "plate", "g", "kg", "ml", "L"]
THEMES = {"fresh": "Fresh Green", "dark": "Dark Focus", "sunrise": "Sunrise"}
ACTIVITY = {
    "sedentary": ("No regular workout", 1.2),
    "light": ("Light: 1-3 days/week", 1.375),
    "moderate": ("Moderate: 3-5 days/week", 1.55),
    "active": ("Active: 6-7 days/week", 1.725),
    "athlete": ("Athlete: intense routine", 1.9),
}


def default_data():
    return {
        "goal": "loss",
        "theme": "fresh",
        "selected_date": TODAY,
        "profile": {
            "weight": 70,
            "height": 170,
            "age": 25,
            "gender": "male",
            "routine": "sedentary",
        },
        "meals": [],
    }


def load_data():
    if not DATA_FILE.exists():
        return default_data()
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default_data()
    merged = default_data()
    merged.update(data)
    merged["profile"].update(data.get("profile", {}))
    return merged


def save_data(data):
    DATA_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def esc(value):
    return html.escape(str(value), quote=True)


def number(form, key, fallback):
    try:
        return float(form.get(key, [fallback])[0])
    except (TypeError, ValueError):
        return fallback


def text(form, key, fallback=""):
    return form.get(key, [fallback])[0]


def title_case(value):
    return " ".join(word.capitalize() for word in value.split())


def find_dish(name):
    normalized = name.strip().lower()
    for dish in DISHES:
        if dish["name"] == normalized:
            return {**dish, "source": "Database match"}
    for dish in DISHES:
        if len(normalized) > 2 and (normalized in dish["name"] or dish["name"] in normalized):
            return {**dish, "source": "Similar dish match"}
    return None


def estimate_dish(name):
    dish = find_dish(name)
    if dish:
        return dish

    words = name.lower().split()
    calories = 300
    protein = 9
    if any(word in words for word in ["chicken", "fish", "egg", "eggs"]):
        calories += 90
        protein += 22
    if any(word in words for word in ["paneer", "tofu", "dal", "sprouts", "chana", "rajma"]):
        calories += 70
        protein += 12
    if any(word in words for word in ["rice", "biryani", "pulao", "paratha", "noodles", "pasta"]):
        calories += 150
        protein += 4
    if any(word in words for word in ["fried", "butter", "pizza", "burger", "samosa", "vada"]):
        calories += 180
        protein += 5
    if any(word in words for word in ["salad", "soup", "fruit"]):
        calories -= 110
        protein -= 2
    return {
        "name": name.strip().lower() or "custom dish",
        "calories": max(120, calories),
        "protein": max(3, protein),
        "unit": "piece",
        "quantity": 1,
        "source": "Smart estimate",
    }


def converted_quantity(quantity, selected_unit, base_unit):
    metric = quantity * 1000 if selected_unit in ["kg", "L"] else quantity
    if base_unit in ["g", "ml"] and selected_unit in ["g", "kg", "ml", "L"]:
        return metric
    if base_unit in ["piece", "plate"] and selected_unit in ["g", "kg", "ml", "L"]:
        return metric / 100
    return quantity


def meal_estimate(name, quantity, unit):
    dish = estimate_dish(name)
    base_quantity = dish.get("quantity") or 1
    base_unit = dish.get("unit") or "piece"
    multiplier = converted_quantity(quantity, unit, base_unit) / base_quantity
    return {
        "name": title_case(name.strip() or dish["name"]),
        "calories": round(dish["calories"] * multiplier),
        "protein": round(dish["protein"] * multiplier),
        "quantity": quantity,
        "unit": unit,
        "source": dish["source"],
    }


def calculate_plan(data):
    profile = data["profile"]
    weight = float(profile.get("weight", 70))
    height = float(profile.get("height", 170))
    age = float(profile.get("age", 25))
    gender = profile.get("gender", "male")
    routine = profile.get("routine", "sedentary")
    height_m = height / 100
    bmi = weight / (height_m * height_m)
    healthy_low = 18.5 * height_m * height_m
    healthy_high = 24.9 * height_m * height_m
    height_inches = height / 2.54
    inches_over_five = max(0, height_inches - 60)
    devine_base = 45.5 if gender == "female" else 50 if gender == "male" else 47.75
    ideal_weight = devine_base + 2.3 * inches_over_five
    bmr_offset = -161 if gender == "female" else 5 if gender == "male" else -78
    bmr = 10 * weight + 6.25 * height - 5 * age + bmr_offset
    activity_label, activity_factor = ACTIVITY.get(routine, ACTIVITY["sedentary"])
    maintenance = bmr * activity_factor
    calorie_target = maintenance - 450 if data["goal"] == "loss" else maintenance + 350
    protein_target = weight * (1.7 if data["goal"] == "loss" else 1.8)
    if routine in ["active", "athlete"]:
        protein_target += weight * 0.2
    return {
        "bmi": bmi,
        "healthy_low": healthy_low,
        "healthy_high": healthy_high,
        "ideal_weight": ideal_weight,
        "maintenance": maintenance,
        "calorie_target": round(max(1200, min(4200, calorie_target)) / 50) * 50,
        "protein_target": round(max(45, min(240, protein_target)) / 5) * 5,
        "activity_label": activity_label,
    }


def selected_meals(data):
    selected_date = data.get("selected_date", TODAY)
    return [meal for meal in data["meals"] if meal.get("date", TODAY) == selected_date]


def totals(data):
    meals = selected_meals(data)
    return {
        "calories": sum(meal.get("calories", 0) for meal in meals),
        "protein": sum(meal.get("protein", 0) for meal in meals),
        "count": len(meals),
    }


def totals_for_date(data, date_key):
    meals = [meal for meal in data["meals"] if meal.get("date", TODAY) == date_key]
    return {
        "calories": sum(meal.get("calories", 0) for meal in meals),
        "protein": sum(meal.get("protein", 0) for meal in meals),
        "count": len(meals),
    }


def date_title(date_key):
    return f"Today, {date_key}" if date_key == TODAY else date_key


def option(value, label, selected):
    return f'<option value="{esc(value)}" {"selected" if value == selected else ""}>{esc(label)}</option>'


def shell(data, active, body):
    theme = data.get("theme", "fresh")
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>BE FIT</title>
    <link rel="stylesheet" href="/styles.css" />
  </head>
  <body data-theme="{esc(theme)}">
    <div class="app-shell">
      <aside class="sidebar">
        <div class="brand">
          <div class="brand-mark">BF</div>
          <div>
            <h1>BE FIT</h1>
            <p>Python powered tracker.</p>
          </div>
        </div>
        <nav class="nav-list" aria-label="Primary">
          <a href="/" class="nav-link {'active' if active == 'tracker' else ''}">Tracker</a>
          <a href="/#diet" class="nav-link">Diet Sheet</a>
          <a href="/#progress" class="nav-link">Progress</a>
        </nav>
        {profile_form(data)}
      </aside>
      <main>{body}</main>
    </div>
  </body>
</html>"""


def profile_form(data):
    profile = data["profile"]
    plan = calculate_plan(data)
    goal = data["goal"]
    theme = data["theme"]
    routine = profile.get("routine", "sedentary")
    gender = profile.get("gender", "male")
    return f"""
      <form class="profile-panel" method="post" action="/profile">
        <h2>Your Profile</h2>
        <div class="segmented" role="group" aria-label="Goal choice">
          <label><input type="radio" name="goal" value="loss" {'checked' if goal == 'loss' else ''} /> Weight Loss</label>
          <label><input type="radio" name="goal" value="gain" {'checked' if goal == 'gain' else ''} /> Weight Gain</label>
        </div>
        <div class="form-row compact">
          <label>Weight (kg)<input name="weight" type="number" min="25" max="250" step="0.1" value="{esc(profile.get('weight', 70))}" /></label>
          <label>Height (cm)<input name="height" type="number" min="120" max="230" step="1" value="{esc(profile.get('height', 170))}" /></label>
        </div>
        <div class="form-row compact">
          <label>Age<input name="age" type="number" min="12" max="90" step="1" value="{esc(profile.get('age', 25))}" /></label>
          <label>Gender<select name="gender">
            {option('male', 'Male', gender)}
            {option('female', 'Female', gender)}
            {option('other', 'Other', gender)}
          </select></label>
        </div>
        <label>Workout routine<select name="routine">
          {''.join(option(key, label, routine) for key, (label, _factor) in ACTIVITY.items())}
        </select></label>
        <label>Suggested calorie target<input name="calorie_target" type="number" value="{plan['calorie_target']}" /></label>
        <label>Suggested protein target (g)<input name="protein_target" type="number" value="{plan['protein_target']}" /></label>
        <label>Theme<select name="theme">
          {''.join(option(key, label, theme) for key, label in THEMES.items())}
        </select></label>
        <button class="primary-action" type="submit">Update Plan</button>
      </form>"""


def topbar(data, title):
    total = totals(data)
    return f"""
      <section class="topbar" aria-label="Daily summary">
        <div>
          <p class="eyebrow">{esc(date_title(data.get('selected_date', TODAY)))}</p>
          <h2>{esc(title)}</h2>
        </div>
        <div class="summary-strip">
          <div><span>{total['calories']}</span><small>calories</small></div>
          <div><span>{total['protein']}g</span><small>protein</small></div>
          <div><span>{total['count']}</span><small>meals</small></div>
        </div>
      </section>"""


def tracker_page(data):
    plan = calculate_plan(data)
    body = topbar(data, "Food Tracking Dashboard")
    body += f"""
      <section id="tracker" class="grid two-column">
        <div class="panel meal-entry">
          <div class="panel-heading">
            <div><p class="eyebrow">Meal Input</p><h2>Add a dish</h2></div>
            <span class="status-pill">{'Weight Loss' if data['goal'] == 'loss' else 'Weight Gain'}</span>
          </div>
          <form class="meal-form" method="post" action="/add-meal">
            <label>Dish name
              <input name="dish_name" type="text" list="dishSuggestions" placeholder="e.g. paneer tikka, dosa, dal rice" required />
              <datalist id="dishSuggestions">{''.join(f'<option value="{esc(title_case(dish["name"]))}"></option>' for dish in DISHES)}</datalist>
            </label>
            <div class="form-row">
              <label>Quantity<input name="quantity" type="number" min="1" max="5000" step="1" value="1" /></label>
              <label>Unit<select name="unit">{''.join(option(unit, unit, 'piece') for unit in UNITS)}</select></label>
              <label>Meal type<select name="meal_type">{''.join(option(item, item, 'Breakfast') for item in MEAL_TYPES)}</select></label>
            </div>
            <label>Date<input name="date" type="date" value="{esc(data.get('selected_date', TODAY))}" /></label>
            <div class="estimate-box">
              <strong>Python will calculate calories and protein after submit.</strong>
              <span>You can use any unit for any dish.</span>
            </div>
            <button class="primary-action" type="submit">Add Meal</button>
          </form>
        </div>
        <div class="panel">
          <div class="panel-heading"><div><p class="eyebrow">Personal Plan</p><h2>Targets & ideal range</h2></div></div>
          <div class="profile-summary">
            <div class="summary-card"><strong>{plan['bmi']:.1f}</strong><span>BMI</span></div>
            <div class="summary-card"><strong>{plan['ideal_weight']:.1f} kg</strong><span>Ideal body weight</span></div>
            <div class="summary-card"><strong>{plan['healthy_low']:.1f}-{plan['healthy_high']:.1f} kg</strong><span>Healthy BMI range</span></div>
            <div class="summary-card"><strong>{round(plan['maintenance'])}</strong><span>Maintenance calories</span></div>
          </div>
          <div class="insight-card">{suggestion(data, plan)}</div>
          {dashboard_calendar(data)}
        </div>
      </section>
      <section class="grid two-column">
        <div class="panel">
          <div class="panel-heading">
            <div><p class="eyebrow">Food Log</p><h2>Meals & cheat meals</h2></div>
            <form method="post" action="/clear-date"><button class="ghost-action" type="submit">Clear</button></form>
          </div>
          {meal_list(data)}
        </div>
        <div id="diet" class="panel">
          <div class="panel-heading"><div><p class="eyebrow">Routine</p><h2>Balanced diet sheet</h2></div></div>
          {diet_sheet(data, plan)}
        </div>
      </section>
      <section id="progress" class="panel progress-panel">
        <div class="panel-heading"><div><p class="eyebrow">Improvements</p><h2>Healthy lifestyle suggestions</h2></div></div>
        <div class="suggestion-grid">{suggestion_cards(data, plan)}</div>
      </section>"""
    return shell(data, "tracker", body)


def dashboard_calendar(data):
    selected = data.get("selected_date", TODAY)
    try:
        year, month, _day = [int(part) for part in selected.split("-")]
    except ValueError:
        year, month = [int(part) for part in TODAY.split("-")[:2]]
    import calendar as cal

    month_name = time.strftime("%B %Y", time.strptime(f"{year}-{month}-01", "%Y-%m-%d"))
    first_weekday, days_in_month = cal.monthrange(year, month)
    start_padding = (first_weekday + 1) % 7
    cells = ['<span class="calendar-day muted"></span>' for _ in range(start_padding)]

    for day in range(1, days_in_month + 1):
        key = f"{year}-{month:02d}-{day:02d}"
        total = totals_for_date(data, key)
        classes = "calendar-day selected" if key == selected else "calendar-day"
        calories = f"{total['calories']} cal" if total["count"] else ""
        cells.append(f"""
          <a class="{classes}" href="/details.html?date={esc(key)}">
            <strong>{day}</strong>
            <small>{esc(calories)}</small>
          </a>""")

    return f"""
      <section class="mini-calendar">
        <div class="panel-heading compact-heading">
          <div><p class="eyebrow">Calendar</p><h2>Calories by date</h2></div>
        </div>
        <div class="calendar-head compact-calendar-head">
          <span></span>
          <strong>{esc(month_name)}</strong>
          <span></span>
        </div>
        <div class="calendar-weekdays"><span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span></div>
        <div class="calendar-grid">{''.join(cells)}</div>
      </section>"""


def details_page(data, date_key):
    data["selected_date"] = date_key
    total = totals_for_date(data, date_key)
    body = f"""
      <section class="topbar" aria-label="Selected date summary">
        <div>
          <p class="eyebrow">{esc(date_title(date_key))}</p>
          <h2>Meal Details</h2>
        </div>
        <div class="summary-strip">
          <div><span>{total['calories']}</span><small>calories</small></div>
          <div><span>{total['protein']}g</span><small>protein</small></div>
          <div><span>{total['count']}</span><small>meals</small></div>
        </div>
      </section>
      <section class="panel">
        <div class="panel-heading">
          <div><p class="eyebrow">Selected Date</p><h2>Meals consumed</h2></div>
          <a class="ghost-link" href="/">Back to Dashboard</a>
        </div>
        {meal_list(data)}
      </section>"""
    return shell(data, "tracker", body)


def suggestion(data, plan):
    total = totals(data)
    if total["count"] == 0:
        return "Start logging meals for this date to get improvement suggestions."
    if data["goal"] == "loss" and total["calories"] > plan["calorie_target"] + 150:
        return "You are above your loss target. Keep the next meal lighter with protein and vegetables."
    if data["goal"] == "gain" and total["calories"] < plan["calorie_target"] - 400:
        return "You still have room for calories. Add milk, nuts, rice, roti, banana, or a smoothie."
    return "Your intake is close to the selected goal. Keep the next meal balanced."


def suggestion_cards(data, plan):
    total = totals(data)
    protein_gap = plan["protein_target"] - total["protein"]
    cards = [
        ("Daily pacing", suggestion(data, plan)),
        ("Protein gap", "Add paneer, tofu, dal, eggs, chicken, fish, sprouts, curd, or a protein shake." if protein_gap > 20 else "Protein is moving well today."),
        ("Consistency", "Plan cheat meals instead of reacting to cravings. That keeps the routine realistic."),
    ]
    return "".join(f'<article class="suggestion-card"><strong>{esc(title)}</strong><span>{esc(text)}</span></article>' for title, text in cards)


def diet_sheet(data, plan):
    goal_text = "fat loss" if data["goal"] == "loss" else "healthy weight gain"
    items = [
        ("Calories", f"Aim for about {plan['calorie_target']} calories daily for {goal_text}."),
        ("Protein", f"Target about {plan['protein_target']}g protein daily across 3-5 meals."),
        ("Workout", f"{plan['activity_label']}: keep meals timed around training."),
        ("Breakfast", "Choose eggs, sprouts, idli sambar, oats, poha, or paneer with vegetables."),
        ("Lunch", "Use rice or chapati with dal, sabzi, curd, salad, and a protein source."),
        ("Dinner", "Keep dinner balanced with vegetables plus paneer, tofu, dal, chicken, fish, or khichdi."),
    ]
    return '<div class="diet-sheet">' + "".join(f'<div class="diet-item"><strong>{esc(title)}</strong><span>{esc(text)}</span></div>' for title, text in items) + "</div>"


def meal_list(data):
    meals = selected_meals(data)
    if not meals:
        return f'<div class="meal-list empty-state">No meals added for {esc(date_title(data.get("selected_date", TODAY)))}.</div>'
    groups = []
    for meal_type in MEAL_TYPES:
        group_meals = [meal for meal in meals if meal.get("type") == meal_type]
        if group_meals:
            items = "".join(meal_item(meal) for meal in group_meals)
        else:
            items = f'<div class="empty-state">No {esc(meal_type.lower())} items yet.</div>'
        groups.append(f'<section class="meal-group"><h3>{esc(meal_type)}<span>{len(group_meals)} item{"s" if len(group_meals) != 1 else ""}</span></h3>{items}</section>')
    return '<div class="meal-list">' + "".join(groups) + "</div>"


def meal_item(meal):
    quantity = f'{meal.get("quantity", 1)} {meal.get("unit", "piece")}'
    return f"""
      <article class="meal-item {'cheat' if meal.get('type') == 'Cheat Meal' else ''}">
        <div class="meal-row">
          <div class="meal-title">
            <span>{esc(meal.get('name', 'Meal'))}</span>
            <small class="meal-meta">{esc(quantity)}</small>
          </div>
          <form method="post" action="/delete-meal"><input type="hidden" name="id" value="{esc(meal.get('id', ''))}" /><button class="delete-meal" type="submit">&times;</button></form>
        </div>
        <div class="meal-stats">
          <span class="stat-chip">{esc(meal.get('calories', 0))} cal</span>
          <span class="stat-chip">{esc(meal.get('protein', 0))}g protein</span>
        </div>
      </article>"""


class BeFitHandler(BaseHTTPRequestHandler):
    def read_form(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        return parse_qs(body)

    def redirect(self, path):
        self.send_response(303)
        self.send_header("Location", path)
        self.end_headers()

    def html_response(self, content):
        encoded = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def file_response(self, path):
        file_path = ROOT / path.lstrip("/")
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(str(file_path))[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        data = load_data()
        parsed = urlparse(self.path)
        if parsed.path in ["/", "/index.html"]:
            self.html_response(tracker_page(data))
        elif parsed.path in ["/details", "/details.html"]:
            query = parse_qs(parsed.query)
            date_key = query.get("date", [data.get("selected_date", TODAY)])[0]
            data["selected_date"] = date_key
            save_data(data)
            self.html_response(details_page(data, date_key))
        elif parsed.path in ["/history", "/history.html"]:
            self.redirect("/")
        elif parsed.path == "/styles.css":
            self.file_response("styles.css")
        else:
            self.send_error(404)

    def do_POST(self):
        data = load_data()
        form = self.read_form()
        path = urlparse(self.path).path

        if path == "/profile":
            data["goal"] = text(form, "goal", data["goal"])
            data["theme"] = text(form, "theme", data["theme"])
            data["profile"] = {
                "weight": number(form, "weight", 70),
                "height": number(form, "height", 170),
                "age": number(form, "age", 25),
                "gender": text(form, "gender", "male"),
                "routine": text(form, "routine", "sedentary"),
            }
            save_data(data)
            self.redirect("/")
        elif path == "/add-meal":
            date = text(form, "date", data.get("selected_date", TODAY))
            data["selected_date"] = date
            estimate = meal_estimate(text(form, "dish_name", ""), number(form, "quantity", 1), text(form, "unit", "piece"))
            data["meals"].insert(0, {
                "id": f"{int(time.time() * 1000)}",
                "name": estimate["name"],
                "calories": estimate["calories"],
                "protein": estimate["protein"],
                "quantity": estimate["quantity"],
                "unit": estimate["unit"],
                "type": text(form, "meal_type", "Breakfast"),
                "date": date,
            })
            save_data(data)
            self.redirect("/")
        elif path == "/delete-meal":
            meal_id = text(form, "id", "")
            data["meals"] = [meal for meal in data["meals"] if meal.get("id") != meal_id]
            save_data(data)
            self.redirect(self.headers.get("Referer", "/"))
        elif path == "/clear-date":
            selected = data.get("selected_date", TODAY)
            data["meals"] = [meal for meal in data["meals"] if meal.get("date", TODAY) != selected]
            save_data(data)
            self.redirect(self.headers.get("Referer", "/"))
        else:
            self.send_error(404)


def main():
    parser = argparse.ArgumentParser(description="Run the Python BE FIT tracker.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), BeFitHandler)
    print(f"BE FIT Python app: http://127.0.0.1:{args.port}/")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
