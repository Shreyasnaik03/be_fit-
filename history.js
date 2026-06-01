const allMealTypes = ["Breakfast", "Lunch", "Snack", "Dinner", "Cheat Meal"];
const todayKey = localDateKey(new Date());

const state = {
  theme: localStorage.getItem("befitTheme") || "fresh",
  selectedDate: localStorage.getItem("befitSelectedDate") || todayKey,
  calendarMonth: localStorage.getItem("befitSelectedDate") || todayKey,
  meals: JSON.parse(localStorage.getItem("befitMeals") || "[]")
};

const els = {
  themeChoice: document.querySelector("#themeChoice"),
  selectedDate: document.querySelector("#selectedDate"),
  selectedDateLabel: document.querySelector("#selectedDateLabel"),
  calendarGrid: document.querySelector("#calendarGrid"),
  calendarMonth: document.querySelector("#calendarMonth"),
  prevMonth: document.querySelector("#prevMonth"),
  nextMonth: document.querySelector("#nextMonth"),
  calorieTotal: document.querySelector("#calorieTotal"),
  proteinTotal: document.querySelector("#proteinTotal"),
  mealCount: document.querySelector("#mealCount"),
  mealList: document.querySelector("#mealList"),
  clearLog: document.querySelector("#clearLog")
};

state.meals = state.meals.map((meal) => ({ ...meal, date: meal.date || todayKey }));
els.themeChoice.value = state.theme;
els.selectedDate.value = state.selectedDate;

function localDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    };
    return replacements[char];
  });
}

function formatQuantity(quantity, unit) {
  return `${quantity} ${unit}`;
}

function selectedMeals() {
  return state.meals.filter((meal) => (meal.date || todayKey) === state.selectedDate);
}

function dateTitle(dateKey) {
  const date = new Date(`${dateKey}T00:00:00`);
  const label = date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric"
  });
  return dateKey === todayKey ? `Today, ${label}` : label;
}

function save() {
  localStorage.setItem("befitTheme", state.theme);
  localStorage.setItem("befitSelectedDate", state.selectedDate);
  localStorage.setItem("befitMeals", JSON.stringify(state.meals));
}

function totals() {
  return selectedMeals().reduce(
    (sum, meal) => ({
      calories: sum.calories + meal.calories,
      protein: sum.protein + meal.protein
    }),
    { calories: 0, protein: 0 }
  );
}

function setSelectedDate(dateKey) {
  state.selectedDate = dateKey;
  state.calendarMonth = dateKey;
  els.selectedDate.value = dateKey;
  render();
}

function renderTheme() {
  document.body.dataset.theme = state.theme;
  els.themeChoice.value = state.theme;
}

function renderSummary() {
  const total = totals();
  const meals = selectedMeals();
  els.selectedDateLabel.textContent = dateTitle(state.selectedDate);
  els.selectedDate.value = state.selectedDate;
  els.calorieTotal.textContent = total.calories;
  els.proteinTotal.textContent = `${total.protein}g`;
  els.mealCount.textContent = meals.length;
}

function renderCalendar() {
  const monthDate = new Date(`${state.calendarMonth.slice(0, 7)}-01T00:00:00`);
  const year = monthDate.getFullYear();
  const month = monthDate.getMonth();
  const firstDay = new Date(year, month, 1);
  const start = new Date(firstDay);
  start.setDate(firstDay.getDate() - firstDay.getDay());
  const mealCounts = state.meals.reduce((counts, meal) => {
    const key = meal.date || todayKey;
    counts[key] = (counts[key] || 0) + 1;
    return counts;
  }, {});

  els.calendarMonth.textContent = monthDate.toLocaleDateString("en-IN", {
    month: "long",
    year: "numeric"
  });

  const days = [];
  for (let index = 0; index < 42; index++) {
    const date = new Date(start);
    date.setDate(start.getDate() + index);
    const key = localDateKey(date);
    const count = mealCounts[key] || 0;
    const classes = [
      "calendar-day",
      date.getMonth() === month ? "" : "muted",
      key === state.selectedDate ? "selected" : ""
    ]
      .filter(Boolean)
      .join(" ");
    days.push(`
      <button class="${classes}" type="button" data-date="${key}">
        <strong>${date.getDate()}</strong>
        <small>${count ? `${count} meal${count === 1 ? "" : "s"}` : ""}</small>
      </button>`);
  }

  els.calendarGrid.innerHTML = days.join("");
}

function renderMeals() {
  const dayMeals = selectedMeals();
  if (!dayMeals.length) {
    els.mealList.className = "meal-list empty-state";
    els.mealList.textContent = `No meals added for ${dateTitle(state.selectedDate)}.`;
    return;
  }

  els.mealList.className = "meal-list";
  els.mealList.innerHTML = allMealTypes
    .map((type) => {
      const meals = dayMeals.filter((meal) => meal.type === type);
      const items = meals.length
        ? meals
            .map((meal) => {
              const mealName = escapeHtml(meal.name);
              const quantityText = meal.quantity ? formatQuantity(meal.quantity, meal.unit) : `${meal.serving || 1} serving(s)`;
              return `
      <article class="meal-item ${meal.type === "Cheat Meal" ? "cheat" : ""}">
        <div class="meal-row">
          <div class="meal-title">
            <span>${mealName}</span>
            <small class="meal-meta">${escapeHtml(quantityText)}</small>
          </div>
          <button class="delete-meal" type="button" data-id="${meal.id}" aria-label="Delete ${mealName}">&times;</button>
        </div>
        <div class="meal-stats">
          <span class="stat-chip">${meal.calories} cal</span>
          <span class="stat-chip">${meal.protein}g protein</span>
        </div>
      </article>`;
            })
            .join("")
        : `<div class="empty-state">No ${type.toLowerCase()} items yet.</div>`;

      return `
        <section class="meal-group">
          <h3>${type}<span>${meals.length} item${meals.length === 1 ? "" : "s"}</span></h3>
          ${items}
        </section>`;
    })
    .join("");
}

function render() {
  renderTheme();
  renderSummary();
  renderCalendar();
  renderMeals();
  save();
}

els.themeChoice.addEventListener("change", () => {
  state.theme = els.themeChoice.value;
  render();
});

els.selectedDate.addEventListener("change", () => {
  if (!els.selectedDate.value) return;
  setSelectedDate(els.selectedDate.value);
});

els.calendarGrid.addEventListener("click", (event) => {
  const button = event.target.closest(".calendar-day");
  if (!button) return;
  setSelectedDate(button.dataset.date);
});

els.prevMonth.addEventListener("click", () => {
  const date = new Date(`${state.calendarMonth.slice(0, 7)}-01T00:00:00`);
  date.setMonth(date.getMonth() - 1);
  state.calendarMonth = localDateKey(date);
  render();
});

els.nextMonth.addEventListener("click", () => {
  const date = new Date(`${state.calendarMonth.slice(0, 7)}-01T00:00:00`);
  date.setMonth(date.getMonth() + 1);
  state.calendarMonth = localDateKey(date);
  render();
});

els.mealList.addEventListener("click", (event) => {
  const button = event.target.closest(".delete-meal");
  if (!button) return;
  state.meals = state.meals.filter((meal) => meal.id !== button.dataset.id);
  render();
});

els.clearLog.addEventListener("click", () => {
  state.meals = state.meals.filter((meal) => (meal.date || todayKey) !== state.selectedDate);
  render();
});

render();
