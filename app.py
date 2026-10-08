from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import argparse
import hashlib
import hmac
import html
import json
import mimetypes
import os
import secrets
import smtplib
import time
from email.message import EmailMessage


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "befit_data.json"
USERS_FILE = ROOT / "befit_users.json"
TODAY = time.strftime("%Y-%m-%d")
SESSIONS = {}
RESET_CODES = {}

SMTP_HOST = os.getenv("BEFIT_SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.getenv("BEFIT_SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("BEFIT_SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("BEFIT_SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("BEFIT_SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
EMAIL_FROM = os.getenv("BEFIT_EMAIL_FROM", "no-reply@example.com")

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
        "activity": {},
    }


def ensure_daily_activity(data):
    if not isinstance(data.get("activity"), dict):
        data["activity"] = {}
    return data


def get_day_activity(data, date_key):
    ensure_daily_activity(data)
    entry = data["activity"].get(date_key, {})
    if not isinstance(entry, dict):
        entry = {}
    return {
        "steps": int(entry.get("steps", 0) or 0),
        "calories_burned": int(entry.get("calories_burned", 0) or 0),
        "updated_at": entry.get("updated_at") or "",
        "source": entry.get("source") or "web",
    }


def sync_device_activity(data, payload):
    ensure_daily_activity(data)
    if not payload:
        return data

    date_key = str(payload.get("date") or TODAY)
    existing = data["activity"].get(date_key, {})
    if not isinstance(existing, dict):
        existing = {}

    steps = int(float(payload.get("steps", existing.get("steps", 0) or 0)))
    calories = int(float(payload.get("calories_burned", existing.get("calories_burned", 0) or 0)))

    data["activity"][date_key] = {
        "steps": steps,
        "calories_burned": calories,
        "updated_at": payload.get("updated_at") or time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": payload.get("source") or "phone",
    }
    return data


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


def load_users():
    if not USERS_FILE.exists():
        return []
    try:
        return json.loads(USERS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def save_users(users):
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def normalize_email(value):
    return value.strip().lower()


def normalize_phone(value):
    digits = ''.join(ch for ch in str(value or '') if ch.isdigit())
    return digits if digits else ''


def hash_password(password, salt=None):
    salt_bytes = bytes.fromhex(salt) if salt else os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 210000)
    return salt_bytes.hex(), digest.hex()


def password_matches(password, user):
    _salt, candidate = hash_password(password, user["salt"])
    return hmac.compare_digest(candidate, user["password_hash"])


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


def shell(data, active, body, user=None):
    theme = data.get("theme", "fresh")
    account = ""
    if user:
        account = f"""
        <div class="account-panel">
          <div class="account-avatar">{esc(user.get('name', 'U')[:1].upper())}</div>
          <div class="account-copy">
            <strong>{esc(user.get('name', 'User'))}</strong>
            <span>{esc(user.get('email', ''))}</span>
          </div>
          <form method="post" action="/logout">
            <button class="logout-button" type="submit" title="Log out" aria-label="Log out">&#x2192;</button>
          </form>
        </div>"""
    theme_options = "".join(f'<button class="theme-option" type="submit" name="theme" value="{esc(key)}" {'data-selected' if key == theme else ''}>{esc(label)}</button>' for key, label in THEMES.items())
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="theme-color" content="#2f8a54" />
    <meta name="description" content="BE FIT calorie tracker with step and activity syncing across devices." />
    <title>BE FIT</title>
    <link rel="manifest" href="/manifest.webmanifest" />
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
        <div class="top-app-actions">
          <details class="theme-menu">
            <summary class="theme-toggle" aria-label="Choose a theme">☼</summary>
            <form class="theme-menu-panel" method="post" action="/profile">
              {theme_options}
            </form>
          </details>
        </div>
        <nav class="nav-list" aria-label="Primary">
          <a href="/" class="nav-link {'active' if active == 'tracker' else ''}">Tracker</a>
          <a href="/#diet" class="nav-link">Diet Sheet</a>
          <a href="/#progress" class="nav-link">Progress</a>
        </nav>
        {account}
        {profile_form(data)}
      </aside>
      <main>{body}</main>
    </div>
    <script>
      if ('serviceWorker' in navigator) {{
        window.addEventListener('load', function () {{
          navigator.serviceWorker.register('/service-worker.js').catch(function () {{}});
        }});
      }}
    </script>
  </body>
</html>"""


def auth_page(mode="login", error="", values=None):
    values = values or {}
    is_signup = mode == "signup"
    title = "Create your account" if is_signup else "Welcome back"
    subtitle = "Start building a healthier routine." if is_signup else "Sign in to continue to your tracker."
    alternate = (
        'Already have an account? <a href="/login">Sign in</a>'
        if is_signup
        else 'New to BE FIT? <a href="/signup">Create an account</a>'
    )
    name_field = ""
    if is_signup:
        name_field = f"""
              <label>Full name
                <input name="name" type="text" autocomplete="name" value="{esc(values.get('name', ''))}" placeholder="Your name" required />
              </label>"""

    phone_field = ""
    if is_signup:
        phone_field = f"""
              <label>Phone number
                <input name="phone" type="tel" autocomplete="tel" value="{esc(values.get('phone', ''))}" placeholder="1234567890" />
              </label>"""

    error_box = f'<div class="auth-error" role="alert">{esc(error)}</div>' if error else ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{esc(title)} | BE FIT</title>
    <link rel="stylesheet" href="/styles.css" />
  </head>
  <body class="auth-body" data-theme="fresh">
    <main class="auth-layout">
      <section class="auth-intro">
        <div class="brand auth-brand">
          <div class="brand-mark">BF</div>
          <div><h1>BE FIT</h1><p>Fitness, made measurable.</p></div>
        </div>
        <div class="auth-message">
          <p class="eyebrow">Your daily momentum</p>
          <h2>Plan meals. Track progress. Feel stronger.</h2>
          <p>Keep your nutrition, goals, and everyday wins together in one focused dashboard.</p>
        </div>
        <div class="auth-stats" aria-label="Tracker features">
          <div><strong>Calories</strong><span>Daily targets</span></div>
          <div><strong>Protein</strong><span>Simple tracking</span></div>
          <div><strong>Progress</strong><span>Built around you</span></div>
        </div>
      </section>
      <section class="auth-form-section">
        <div class="auth-card">
          <div class="auth-heading">
            <p class="eyebrow">{'Join BE FIT' if is_signup else 'Member access'}</p>
            <h1>{esc(title)}</h1>
            <p>{esc(subtitle)}</p>
          </div>
          {error_box}
          <form class="auth-form" method="post" action="/{'signup' if is_signup else 'login'}">
            {name_field}
            <label>Email address
              <input name="email" type="email" autocomplete="email" value="{esc(values.get('email', ''))}" placeholder="you@example.com" required />
            </label>
            {phone_field}
            <label>Password
              <input name="password" type="password" autocomplete="{'new-password' if is_signup else 'current-password'}" placeholder="At least 8 characters" minlength="8" required />
            </label>
            <button class="primary-action auth-submit" type="submit">{'Create account' if is_signup else 'Sign in'}</button>
          </form>
          {'' if is_signup else '<p class="auth-helper"><a href="/forgot">Forgot password?</a></p>'}
          <p class="auth-switch">{alternate}</p>
        </div>
      </section>
    </main>
  </body>
</html>"""


def mask_contact(contact, method):
    if method == "email":
        local, sep, domain = contact.partition("@")
        if not sep:
            return contact
        if len(local) <= 2:
            return local[0] + "***@" + domain
        return local[0] + "***" + local[-1] + "@" + domain
    if len(contact) <= 4:
        return "*" * len(contact)
    return "*" * (len(contact) - 4) + contact[-4:]


def send_reset_email(to_email, otp):
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_HOST:
        raise RuntimeError("SMTP configuration is not set. Please set BEFIT_SMTP_HOST, BEFIT_SMTP_USERNAME, and BEFIT_SMTP_PASSWORD.")
    message = EmailMessage()
    message["Subject"] = "BE FIT password reset code"
    message["From"] = EMAIL_FROM
    message["To"] = to_email
    message.set_content(f"Your BE FIT password reset code is: {otp}\n\nIf you did not request this, please ignore this message.")

    server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
    try:
        if SMTP_USE_TLS:
            server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(message)
    finally:
        server.quit()


def get_reset_record(token):
    record = RESET_CODES.get(token)
    if not record:
        return None
    if record["expires"] < time.time():
        RESET_CODES.pop(token, None)
        return None
    return record


def forgot_page(error="", values=None):
    values = values or {}
    reset_method = values.get("reset_method", "email")
    error_box = f'<div class="auth-error" role="alert">{esc(error)}</div>' if error else ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Reset password | BE FIT</title>
    <link rel="stylesheet" href="/styles.css" />
  </head>
  <body class="auth-body" data-theme="fresh">
    <main class="auth-layout">
      <section class="auth-intro">
        <div class="brand auth-brand">
          <div class="brand-mark">BF</div>
          <div><h1>BE FIT</h1><p>Verify your account before resetting your password.</p></div>
        </div>
        <div class="auth-message">
          <p class="eyebrow">Secure reset</p>
          <h2>Confirm your identity with email or phone.</h2>
          <p>Choose the contact method you used during signup, then enter the verification code you receive.</p>
        </div>
      </section>
      <section class="auth-form-section">
        <div class="auth-card">
          <div class="auth-heading">
            <p class="eyebrow">Password recovery</p>
            <h1>Reset password</h1>
            <p>First verify your account, then choose a new password.</p>
          </div>
          {error_box}
          <form class="auth-form" method="post" action="/forgot">
            <label>Reset via
              <select name="reset_method">
                <option value="email" {'selected' if reset_method != 'phone' else ''}>Email</option>
                <option value="phone" {'selected' if reset_method == 'phone' else ''}>Phone</option>
              </select>
            </label>
            <label>Email address
              <input name="email" type="email" autocomplete="email" value="{esc(values.get('email', ''))}" placeholder="you@example.com" />
            </label>
            <label>Phone number
              <input name="phone" type="tel" autocomplete="tel" value="{esc(values.get('phone', ''))}" placeholder="1234567890" />
            </label>
            <button class="primary-action auth-submit" type="submit">Send verification code</button>
          </form>
          <p class="auth-switch"><a href="/login">Back to sign in</a></p>
        </div>
      </section>
    </main>
  </body>
</html>"""


def verify_reset_page(token, error="", values=None):
    values = values or {}
    record = get_reset_record(token)
    if not record:
        return forgot_page("Verification session expired. Please start again.")
    contact = mask_contact(record["contact"], record["method"])
    delivery = "email" if record["method"] == "email" else "phone"
    error_box = f'<div class="auth-error" role="alert">{esc(error)}</div>' if error else ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Verify code | BE FIT</title>
    <link rel="stylesheet" href="/styles.css" />
  </head>
  <body class="auth-body" data-theme="fresh">
    <main class="auth-layout">
      <section class="auth-intro">
        <div class="brand auth-brand">
          <div class="brand-mark">BF</div>
          <div><h1>BE FIT</h1><p>Two-step verification for password reset.</p></div>
        </div>
        <div class="auth-message">
          <p class="eyebrow">Verify your identity</p>
          <h2>Enter the code sent to {esc(delivery)}</h2>
          <p>We sent a one-time passcode to {esc(contact)}.</p>
        </div>
      </section>
      <section class="auth-form-section">
        <div class="auth-card">
          <div class="auth-heading">
            <p class="eyebrow">Verification required</p>
            <h1>Enter your code</h1>
          </div>
          {error_box}
          <form class="auth-form" method="post" action="/verify-reset">
            <input type="hidden" name="token" value="{esc(token)}" />
            <label>Verification code
              <input name="otp" type="text" autocomplete="one-time-code" value="{esc(values.get('otp', ''))}" placeholder="000000" minlength="4" maxlength="6" required />
            </label>
            <button class="primary-action auth-submit" type="submit">Verify code</button>
          </form>
          {'' if record['method'] == 'email' else f'<p class="auth-note">For local demo, your code is: {esc(record["otp"])}</p>'}
          <p class="auth-switch"><a href="/forgot">Start over</a></p>
        </div>
      </section>
    </main>
  </body>
</html>"""


def reset_password_page(token, error="", values=None):
    values = values or {}
    record = get_reset_record(token)
    if not record or not record.get("verified"):
        return forgot_page("Verification required. Please start over.")
    error_box = f'<div class="auth-error" role="alert">{esc(error)}</div>' if error else ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Choose new password | BE FIT</title>
    <link rel="stylesheet" href="/styles.css" />
  </head>
  <body class="auth-body" data-theme="fresh">
    <main class="auth-layout">
      <section class="auth-intro">
        <div class="brand auth-brand">
          <div class="brand-mark">BF</div>
          <div><h1>BE FIT</h1><p>Secure password update.</p></div>
        </div>
        <div class="auth-message">
          <p class="eyebrow">Reset password</p>
          <h2>Choose a new password.</h2>
          <p>Your account is verified. Enter a new password and confirm it to continue.</p>
        </div>
      </section>
      <section class="auth-form-section">
        <div class="auth-card">
          <div class="auth-heading">
            <p class="eyebrow">New password</p>
            <h1>Set a secure password</h1>
          </div>
          {error_box}
          <form class="auth-form" method="post" action="/reset-password">
            <input type="hidden" name="token" value="{esc(token)}" />
            <label>New password
              <input name="password" type="password" autocomplete="new-password" placeholder="At least 8 characters" minlength="8" required />
            </label>
            <label>Confirm password
              <input name="confirm_password" type="password" autocomplete="new-password" placeholder="Enter it again" required />
            </label>
            <button class="primary-action auth-submit" type="submit">Update password</button>
          </form>
          <p class="auth-switch"><a href="/login">Back to sign in</a></p>
        </div>
      </section>
    </main>
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
        <button class="primary-action" type="submit">Update Plan</button>
      </form>"""


def topbar(data, title):
    total = totals(data)
    activity = get_day_activity(data, data.get("selected_date", TODAY))
    return f"""
      <section class="topbar" aria-label="Daily summary">
        <div>
          <p class="eyebrow">{esc(date_title(data.get('selected_date', TODAY)))}</p>
          <h2>{esc(title)}</h2>
        </div>
        <div class="summary-strip">
          <div><span>{total['calories']}</span><small>calories</small></div>
          <div><span>{total['protein']}g</span><small>protein</small></div>
          <div><span>{activity['steps']}</span><small>steps</small></div>
          <div><span>{activity['calories_burned']} cal</span><small>burned</small></div>
          <div><span>{total['count']}</span><small>meals</small></div>
        </div>
      </section>"""


def tracker_page(data, user=None):
    plan = calculate_plan(data)
    selected_activity = get_day_activity(data, data.get("selected_date", TODAY))
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
        <div class="panel movement-panel">
          <div class="panel-heading">
            <div><p class="eyebrow">Movement</p><h2>Daily activity sync</h2></div>
            <span class="status-pill">Phone + Web</span>
          </div>
          <div class="movement-grid">
            <div class="movement-card">
              <span>Steps</span>
              <strong>{selected_activity['steps']}</strong>
              <small>Synced across devices</small>
            </div>
            <div class="movement-card accent">
              <span>Calories burned</span>
              <strong>{selected_activity['calories_burned']} cal</strong>
              <small>Updated from phone</small>
            </div>
          </div>
          <div class="sync-note">Phone data is written to the same backend, so web and mobile stay aligned.</div>
        </div>
        <div class="panel">
          <div class="panel-heading">
            <div><p class="eyebrow">Food Log</p><h2>Meals & cheat meals</h2></div>
            <form method="post" action="/clear-date"><button class="ghost-action" type="submit">Clear</button></form>
          </div>
          {meal_list(data)}
        </div>
      </section>
      <section class="grid two-column">
        <div id="diet" class="panel">
          <div class="panel-heading"><div><p class="eyebrow">Routine</p><h2>Balanced diet sheet</h2></div></div>
          {diet_sheet(data, plan)}
        </div>
        <div id="progress" class="panel progress-panel">
          <div class="panel-heading"><div><p class="eyebrow">Improvements</p><h2>Healthy lifestyle suggestions</h2></div></div>
          <div class="suggestion-grid">{suggestion_cards(data, plan)}</div>
        </div>
      </section>"""
    return shell(data, "tracker", body, user)


def dashboard_calendar(data):
    selected = data.get("selected_date", TODAY)
    try:
        year, month, _day = [int(part) for part in selected.split("-")]
    except ValueError:
        year, month = [int(part) for part in TODAY.split("-")[:2]]

    day_totals = {}
    for meal in data.get("meals", []):
        key = meal.get("date", TODAY)
        if key:
            day_totals[key] = day_totals.get(key, 0) + int(meal.get("calories", 0) or 0)

    year_panel = "".join(
        f'<button type="button" class="calendar-year-option" data-year="{year_value}">{year_value}</button>'
        for year_value in range(year - 5, year + 6)
    )

    return f"""
      <section class="mini-calendar" data-selected-date="{esc(selected)}" data-view-year="{year}" data-view-month="{month}" data-day-totals='{esc(json.dumps(day_totals))}'>
        <div class="panel-heading compact-heading">
          <div><p class="eyebrow">Calendar</p><h2>Calories by date</h2></div>
        </div>
        <div class="calendar-head compact-calendar-head">
          <button type="button" class="calendar-nav" data-step="-1" aria-label="Previous month">&#8249;</button>
          <button type="button" class="calendar-year-trigger" aria-label="Choose year">{esc(time.strftime('%B %Y', time.strptime(f'{year}-{month:02d}-01', '%Y-%m-%d')))}</button>
          <button type="button" class="calendar-nav" data-step="1" aria-label="Next month">&#8250;</button>
        </div>
        <div class="calendar-year-panel hidden" aria-live="polite">{year_panel}</div>
        <div class="calendar-weekdays"><span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span></div>
        <div class="calendar-grid"></div>
      </section>
      <script>
        (function () {{
          const calendarSections = document.querySelectorAll('.mini-calendar');
          if (!calendarSections.length) return;

          const calendarSection = calendarSections[calendarSections.length - 1];
          const grid = calendarSection.querySelector('.calendar-grid');
          const yearPanel = calendarSection.querySelector('.calendar-year-panel');
          const yearTrigger = calendarSection.querySelector('.calendar-year-trigger');
          const navButtons = calendarSection.querySelectorAll('.calendar-nav');
          const selectedDate = calendarSection.dataset.selectedDate || '';
          const dayTotals = JSON.parse(calendarSection.dataset.dayTotals || '{{}}');
          const state = {{
            year: Number(calendarSection.dataset.viewYear || new Date().getFullYear()),
            month: Number(calendarSection.dataset.viewMonth || new Date().getMonth() + 1),
          }};

          function pad(value) {{
            return String(value).padStart(2, '0');
          }}

          function monthLabel(year, month) {{
            return new Date(year, month - 1, 1).toLocaleString('en-US', {{ month: 'long', year: 'numeric' }});
          }}

          function renderYearPanel() {{
            const options = yearPanel.querySelectorAll('.calendar-year-option');
            options.forEach((button) => {{
              button.classList.toggle('active', Number(button.dataset.year) === state.year);
            }});
          }}

          function renderGrid() {{
            const firstDay = new Date(state.year, state.month - 1, 1).getDay();
            const daysInMonth = new Date(state.year, state.month, 0).getDate();
            const cells = [];

            for (let blank = 0; blank < firstDay; blank += 1) {{
              cells.push('<span class="calendar-day muted"></span>');
            }}

            for (let day = 1; day <= daysInMonth; day += 1) {{
              const dateKey = `${{state.year}}-${{pad(state.month)}}-${{pad(day)}}`;
              const total = dayTotals[dateKey] || 0;
              const selectedClass = dateKey === selectedDate ? ' selected' : '';
              const caloriesLabel = total ? `<small>${{total}} cal</small>` : '';
              cells.push(`
                <a class="calendar-day${{selectedClass}}" href="/details.html?date=${{dateKey}}">
                  <strong>${{day}}</strong>
                  ${{caloriesLabel}}
                </a>
              `);
            }}

            grid.innerHTML = cells.join('');
            yearTrigger.textContent = monthLabel(state.year, state.month);
            renderYearPanel();
          }}

          function toggleYearPanel(forceOpen) {{
            const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : yearPanel.classList.contains('hidden');
            yearPanel.classList.toggle('hidden', !shouldOpen);
          }}

          yearTrigger.addEventListener('click', function () {{
            toggleYearPanel();
          }});

          navButtons.forEach((button) => {{
            button.addEventListener('click', function () {{
              const step = Number(button.dataset.step || 0);
              const nextDate = new Date(state.year, state.month - 1 + step, 1);
              state.year = nextDate.getFullYear();
              state.month = nextDate.getMonth() + 1;
              renderGrid();
            }});
          }});

          yearPanel.addEventListener('click', function (event) {{
            const button = event.target.closest('.calendar-year-option');
            if (!button) return;
            state.year = Number(button.dataset.year || state.year);
            yearPanel.classList.add('hidden');
            renderGrid();
          }});

          document.addEventListener('click', function (event) {{
            if (!event.target.closest('.calendar-year-trigger') && !event.target.closest('.calendar-year-panel')) {{
              yearPanel.classList.add('hidden');
            }}
          }});

          renderGrid();
        }})();
      </script>
    """


def details_page(data, date_key, user=None):
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
    return shell(data, "tracker", body, user)


def edit_meal_page(data, meal, user=None):
    meal_type = meal.get("type", "Breakfast")
    unit = meal.get("unit", "piece")
    body = f"""
      <section class="topbar">
        <div>
          <p class="eyebrow">Food Log</p>
          <h2>Edit Meal</h2>
        </div>
      </section>
      <section class="panel edit-meal-panel">
        <div class="panel-heading">
          <div><p class="eyebrow">Meal Input</p><h2>Update meal details</h2></div>
          <a class="ghost-link" href="/">Cancel</a>
        </div>
        <form class="meal-form" method="post" action="/edit-meal">
          <input name="id" type="hidden" value="{esc(meal.get('id', ''))}" />
          <label>Dish name
            <input name="dish_name" type="text" list="dishSuggestions" value="{esc(meal.get('name', ''))}" required />
            <datalist id="dishSuggestions">{''.join(f'<option value="{esc(title_case(dish["name"]))}"></option>' for dish in DISHES)}</datalist>
          </label>
          <div class="form-row">
            <label>Quantity<input name="quantity" type="number" min="1" max="5000" step="1" value="{esc(meal.get('quantity', 1))}" /></label>
            <label>Unit<select name="unit">{''.join(option(item, item, unit) for item in UNITS)}</select></label>
            <label>Meal type<select name="meal_type">{''.join(option(item, item, meal_type) for item in MEAL_TYPES)}</select></label>
          </div>
          <label>Date<input name="date" type="date" value="{esc(meal.get('date', TODAY))}" /></label>
          <div class="estimate-box">
            <strong>Calories and protein will be recalculated when you save.</strong>
            <span>The meal will move automatically if you change its date or meal type.</span>
          </div>
          <button class="primary-action" type="submit">Save Changes</button>
        </form>
      </section>"""
    return shell(data, "tracker", body, user)


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
          <div class="meal-actions">
            <a class="edit-meal" href="/edit-meal?id={esc(meal.get('id', ''))}">Edit</a>
            <form method="post" action="/delete-meal"><input type="hidden" name="id" value="{esc(meal.get('id', ''))}" /><button class="delete-meal" type="submit" title="Delete meal" aria-label="Delete meal">&times;</button></form>
          </div>
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

    def redirect(self, path, cookie=None):
        self.send_response(303)
        self.send_header("Location", path)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def html_response(self, content, status=200):
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def json_response(self, payload, status=200):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def session_token(self):
        cookie = self.headers.get("Cookie", "")
        for part in cookie.split(";"):
            key, separator, value = part.strip().partition("=")
            if separator and key == "befit_session":
                return value
        return ""

    def current_user(self):
        email = SESSIONS.get(self.session_token())
        if not email:
            return None
        return next((user for user in load_users() if user.get("email") == email), None)

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
        user = self.current_user()
        if parsed.path == "/styles.css":
            self.file_response("styles.css")
        elif parsed.path == "/manifest.webmanifest":
            self.file_response("manifest.webmanifest")
        elif parsed.path == "/service-worker.js":
            self.file_response("service-worker.js")
        elif parsed.path == "/api/dashboard":
            payload = {
                "selected_date": data.get("selected_date", TODAY),
                "goal": data.get("goal", "loss"),
                "profile": data.get("profile", {}),
                "meals": data.get("meals", []),
                "activity": data.get("activity", {}),
                "totals": totals(data),
                "activity_today": get_day_activity(data, data.get("selected_date", TODAY)),
            }
            self.json_response(payload)
        elif parsed.path in ["/login", "/login.html"]:
            if user:
                self.redirect("/")
            else:
                self.html_response(auth_page("login"))
        elif parsed.path in ["/forgot", "/forgot.html"]:
            if user:
                self.redirect("/")
            else:
                self.html_response(forgot_page())
        elif parsed.path in ["/verify-reset", "/verify-reset.html"]:
            if user:
                self.redirect("/")
            else:
                query = parse_qs(parsed.query)
                token = query.get("token", [""])[0]
                self.html_response(verify_reset_page(token))
        elif parsed.path in ["/reset-password", "/reset-password.html"]:
            if user:
                self.redirect("/")
            else:
                query = parse_qs(parsed.query)
                token = query.get("token", [""])[0]
                self.html_response(reset_password_page(token))
        elif parsed.path in ["/signup", "/signup.html"]:
            if user:
                self.redirect("/")
            else:
                self.html_response(auth_page("signup"))
        elif not user:
            self.redirect("/login")
        elif parsed.path in ["/", "/index.html"]:
            self.html_response(tracker_page(data, user))
        elif parsed.path in ["/details", "/details.html"]:
            query = parse_qs(parsed.query)
            date_key = query.get("date", [data.get("selected_date", TODAY)])[0]
            data["selected_date"] = date_key
            save_data(data)
            self.html_response(details_page(data, date_key, user))
        elif parsed.path == "/edit-meal":
            query = parse_qs(parsed.query)
            meal_id = query.get("id", [""])[0]
            meal = next((item for item in data["meals"] if item.get("id") == meal_id), None)
            if not meal:
                self.send_error(404, "Meal not found")
            else:
                self.html_response(edit_meal_page(data, meal, user))
        elif parsed.path in ["/history", "/history.html"]:
            self.redirect("/")
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/sync":
            content_type = self.headers.get("Content-Type", "")
            if "application/json" not in content_type:
                self.json_response({"ok": False, "error": "JSON body required"}, 400)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                self.json_response({"ok": False, "error": "Invalid JSON payload"}, 400)
                return
            data = load_data()
            sync_device_activity(data, payload)
            save_data(data)
            self.json_response({
                "ok": True,
                "selected_date": data.get("selected_date", TODAY),
                "activity": get_day_activity(data, payload.get("date") or data.get("selected_date", TODAY)),
            })
            return

        form = self.read_form()

        if path == "/signup":
            name = text(form, "name").strip()
            email = normalize_email(text(form, "email"))
            phone = normalize_phone(text(form, "phone"))
            password = text(form, "password")
            confirm_password = text(form, "confirm_password")
            values = {"name": name, "email": email, "phone": phone}
            users = load_users()
            if len(name) < 2:
                self.html_response(auth_page("signup", "Please enter your full name.", values), 400)
            elif "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                self.html_response(auth_page("signup", "Enter a valid email address.", values), 400)
            elif len(password) < 8:
                self.html_response(auth_page("signup", "Password must be at least 8 characters.", values), 400)
            elif password != confirm_password:
                self.html_response(auth_page("signup", "Passwords do not match.", values), 400)
            elif any(user.get("email") == email for user in users):
                self.html_response(auth_page("signup", "An account with this email already exists.", values), 409)
            else:
                salt, password_hash = hash_password(password)
                user_record = {"name": name, "email": email, "salt": salt, "password_hash": password_hash}
                if phone:
                    user_record["phone"] = phone
                users.append(user_record)
                save_users(users)
                token = secrets.token_urlsafe(32)
                SESSIONS[token] = email
                self.redirect("/", f"befit_session={token}; Path=/; HttpOnly; SameSite=Lax")
            return

        if path == "/forgot":
            reset_method = text(form, "reset_method", "email")
            email = normalize_email(text(form, "email"))
            phone = normalize_phone(text(form, "phone"))
            values = {"email": email, "phone": phone, "reset_method": reset_method}
            users = load_users()
            user = None
            if reset_method == "phone":
                if not phone:
                    self.html_response(forgot_page("Enter your phone number for verification.", values), 400)
                    return
                user = next((item for item in users if normalize_phone(item.get("phone")) == phone), None)
            else:
                if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                    self.html_response(forgot_page("Enter a valid email address.", values), 400)
                    return
                user = next((item for item in users if item.get("email") == email), None)

            if not user:
                self.html_response(forgot_page("No account found with that email or phone number.", values), 404)
                return
            token = secrets.token_urlsafe(32)
            otp = f"{secrets.randbelow(1000000):06d}"
            contact = phone if reset_method == "phone" else email
            RESET_CODES[token] = {
                "user_email": user["email"],
                "method": reset_method,
                "contact": contact,
                "otp": otp,
                "verified": False,
                "expires": time.time() + 300,
            }
            if reset_method == "email":
                try:
                    send_reset_email(email, otp)
                except Exception as exc:
                    self.html_response(forgot_page(f"Unable to send verification email. Check SMTP settings: {esc(str(exc))}", values), 500)
                    return
            self.redirect(f"/verify-reset?token={token}")
            return

        if path == "/verify-reset":
            token = text(form, "token")
            otp = text(form, "otp")
            record = get_reset_record(token)
            if not record:
                self.html_response(forgot_page("Verification session expired. Please start again."), 400)
                return
            if otp != record["otp"]:
                self.html_response(verify_reset_page(token, "The code entered is incorrect. Please try again.", {"otp": otp}), 400)
                return
            record["verified"] = True
            self.redirect(f"/reset-password?token={token}")
            return

        if path == "/reset-password":
            token = text(form, "token")
            password = text(form, "password")
            confirm_password = text(form, "confirm_password")
            record = get_reset_record(token)
            if not record or not record.get("verified"):
                self.html_response(forgot_page("Verification required. Please start over."), 400)
                return
            if len(password) < 8:
                self.html_response(reset_password_page(token, "Password must be at least 8 characters."), 400)
                return
            if password != confirm_password:
                self.html_response(reset_password_page(token, "Passwords do not match."), 400)
                return
            users = load_users()
            user = next((item for item in users if item.get("email") == record["user_email"]), None)
            if not user:
                self.html_response(forgot_page("Unable to find your account. Please start again."), 400)
                return
            salt, password_hash = hash_password(password)
            user["salt"] = salt
            user["password_hash"] = password_hash
            save_users(users)
            RESET_CODES.pop(token, None)
            session_token = secrets.token_urlsafe(32)
            SESSIONS[session_token] = user["email"]
            self.redirect("/", f"befit_session={session_token}; Path=/; HttpOnly; SameSite=Lax")
            return

        if path == "/login":
            email = normalize_email(text(form, "email"))
            password = text(form, "password")
            user = next((item for item in load_users() if item.get("email") == email), None)
            if not user or not password_matches(password, user):
                self.html_response(auth_page("login", "Email or password is incorrect.", {"email": email}), 401)
            else:
                token = secrets.token_urlsafe(32)
                SESSIONS[token] = email
                self.redirect("/", f"befit_session={token}; Path=/; HttpOnly; SameSite=Lax")
            return

        if path == "/logout":
            SESSIONS.pop(self.session_token(), None)
            self.redirect("/login", "befit_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0")
            return

        if not self.current_user():
            self.redirect("/login")
            return

        data = load_data()
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
        elif path == "/edit-meal":
            meal_id = text(form, "id", "")
            meal = next((item for item in data["meals"] if item.get("id") == meal_id), None)
            if not meal:
                self.send_error(404, "Meal not found")
                return
            date = text(form, "date", meal.get("date", TODAY))
            estimate = meal_estimate(
                text(form, "dish_name", meal.get("name", "")),
                number(form, "quantity", meal.get("quantity", 1)),
                text(form, "unit", meal.get("unit", "piece")),
            )
            meal.update({
                "name": estimate["name"],
                "calories": estimate["calories"],
                "protein": estimate["protein"],
                "quantity": estimate["quantity"],
                "unit": estimate["unit"],
                "type": text(form, "meal_type", meal.get("type", "Breakfast")),
                "date": date,
            })
            data["selected_date"] = date
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
