const dishes = [
  { name: "poha", calories: 250, protein: 6, unit: "g", quantity: 200 },
  { name: "upma", calories: 270, protein: 7, unit: "g", quantity: 220 },
  { name: "idli sambar", calories: 310, protein: 11, unit: "plate", quantity: 1 },
  { name: "masala dosa", calories: 420, protein: 10, unit: "piece", quantity: 1 },
  { name: "plain dosa", calories: 300, protein: 8, unit: "piece", quantity: 1 },
  { name: "dosa", calories: 300, protein: 8, unit: "piece", quantity: 1 },
  { name: "oats", calories: 220, protein: 8, unit: "g", quantity: 50 },
  { name: "boiled eggs", calories: 78, protein: 6, unit: "piece", quantity: 1 },
  { name: "omelette", calories: 230, protein: 16, unit: "piece", quantity: 1 },
  { name: "dal rice", calories: 420, protein: 14, unit: "g", quantity: 300 },
  { name: "rice", calories: 260, protein: 5, unit: "g", quantity: 200 },
  { name: "rajma chawal", calories: 480, protein: 17, unit: "g", quantity: 350 },
  { name: "chole rice", calories: 520, protein: 18, unit: "g", quantity: 350 },
  { name: "curd rice", calories: 330, protein: 10, unit: "g", quantity: 300 },
  { name: "veg pulao", calories: 360, protein: 9, unit: "g", quantity: 280 },
  { name: "chicken biryani", calories: 650, protein: 32, unit: "g", quantity: 350 },
  { name: "veg biryani", calories: 520, protein: 12, unit: "g", quantity: 350 },
  { name: "paneer tikka", calories: 360, protein: 22, unit: "g", quantity: 180 },
  { name: "paneer butter masala", calories: 520, protein: 20, unit: "g", quantity: 250 },
  { name: "grilled chicken", calories: 280, protein: 45, unit: "g", quantity: 180 },
  { name: "fish curry rice", calories: 520, protein: 29, unit: "plate", quantity: 1 },
  { name: "roti sabzi", calories: 320, protein: 10, unit: "plate", quantity: 1 },
  { name: "chapati", calories: 110, protein: 3, unit: "piece", quantity: 1 },
  { name: "dal", calories: 180, protein: 11, unit: "g", quantity: 200 },
  { name: "khichdi", calories: 340, protein: 13, unit: "g", quantity: 300 },
  { name: "sprouts salad", calories: 180, protein: 13, unit: "g", quantity: 180 },
  { name: "fruit salad", calories: 160, protein: 2, unit: "g", quantity: 200 },
  { name: "protein shake", calories: 180, protein: 25, unit: "ml", quantity: 300 },
  { name: "tea", calories: 80, protein: 2, unit: "ml", quantity: 150 },
  { name: "coffee", calories: 90, protein: 3, unit: "ml", quantity: 150 },
  { name: "milk", calories: 122, protein: 6, unit: "ml", quantity: 200 },
  { name: "peanut butter sandwich", calories: 390, protein: 15, unit: "piece", quantity: 1 },
  { name: "burger", calories: 540, protein: 22, unit: "piece", quantity: 1 },
  { name: "pizza", calories: 700, protein: 28, unit: "piece", quantity: 2 },
  { name: "samosa", calories: 260, protein: 5, unit: "piece", quantity: 1 },
  { name: "vada pav", calories: 310, protein: 7, unit: "piece", quantity: 1 },
  { name: "maggie", calories: 390, protein: 9, unit: "plate", quantity: 1 }
];

const dietPlans = {
  loss: [
    ["Morning", "Warm water, fruit, or black coffee. Keep it light before breakfast."],
    ["Breakfast", "Protein-rich option like eggs, sprouts, idli sambar, oats, or paneer with vegetables."],
    ["Lunch", "2 chapatis or rice, dal/lean protein, sabzi, curd, and salad."],
    ["Snack", "Fruit, buttermilk, roasted chana, sprouts, or a protein shake."],
    ["Dinner", "Early dinner with grilled paneer/chicken/fish/tofu, vegetables, soup, or khichdi."],
    ["Rule", "Limit fried snacks and sweets to planned cheat meals. Walk 20-30 minutes daily."]
  ],
  gain: [
    ["Morning", "Banana, milk, soaked nuts, or peanut butter toast."],
    ["Breakfast", "Oats with milk, eggs, paneer paratha, dosa, or poha with added peanuts."],
    ["Lunch", "Rice or chapati, dal, curd, sabzi, and paneer/chicken/fish/tofu."],
    ["Snack", "Smoothie, protein shake, peanut butter sandwich, sprouts, or dry fruits."],
    ["Dinner", "Balanced carbs plus protein: rice/roti with dal and a protein-rich curry."],
    ["Rule", "Add calories slowly, train strength 3-5 days weekly, and prioritize sleep."]
  ]
};

const activityLevels = {
  sedentary: { label: "No regular workout", factor: 1.2 },
  light: { label: "Light workout", factor: 1.375 },
  moderate: { label: "Moderate workout", factor: 1.55 },
  active: { label: "Active routine", factor: 1.725 },
  athlete: { label: "Athlete routine", factor: 1.9 }
};

const allUnits = ["piece", "plate", "g", "kg", "ml", "L"];

function localDateKey(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const todayKey = localDateKey(new Date());

const state = {
  goal: localStorage.getItem("befitGoal") || "loss",
  theme: localStorage.getItem("befitTheme") || "fresh",
  selectedDate: localStorage.getItem("befitSelectedDate") || todayKey,
  calendarMonth: localStorage.getItem("befitSelectedDate") || todayKey,
  meals: JSON.parse(localStorage.getItem("befitMeals") || "[]"),
  profile: JSON.parse(
    localStorage.getItem("befitProfile") ||
      '{"weight":70,"height":170,"age":25,"gender":"male","routine":"sedentary"}'
  )
};

const els = {
  goalOptions: document.querySelectorAll(".goal-option"),
  goalLabel: document.querySelector("#goalLabel"),
  bodyWeight: document.querySelector("#bodyWeight"),
  bodyHeight: document.querySelector("#bodyHeight"),
  userAge: document.querySelector("#userAge"),
  userGender: document.querySelector("#userGender"),
  workoutRoutine: document.querySelector("#workoutRoutine"),
  updatePlan: document.querySelector("#updatePlan"),
  themeChoice: document.querySelector("#themeChoice"),
  profileSummary: document.querySelector("#profileSummary"),
  calorieTarget: document.querySelector("#calorieTarget"),
  proteinTarget: document.querySelector("#proteinTarget"),
  selectedDate: document.querySelector("#selectedDate"),
  selectedDateLabel: document.querySelector("#selectedDateLabel"),
  calendarGrid: document.querySelector("#calendarGrid"),
  calendarMonth: document.querySelector("#calendarMonth"),
  prevMonth: document.querySelector("#prevMonth"),
  nextMonth: document.querySelector("#nextMonth"),
  dishName: document.querySelector("#dishName"),
  foodQuantity: document.querySelector("#foodQuantity"),
  foodUnit: document.querySelector("#foodUnit"),
  mealType: document.querySelector("#mealType"),
  mealForm: document.querySelector("#mealForm"),
  estimateBox: document.querySelector("#estimateBox"),
  dishSuggestions: document.querySelector("#dishSuggestions"),
  calorieTotal: document.querySelector("#calorieTotal"),
  proteinTotal: document.querySelector("#proteinTotal"),
  mealCount: document.querySelector("#mealCount"),
  calorieMeter: document.querySelector("#calorieMeter"),
  proteinMeter: document.querySelector("#proteinMeter"),
  calorieProgressText: document.querySelector("#calorieProgressText"),
  proteinProgressText: document.querySelector("#proteinProgressText"),
  mealList: document.querySelector("#mealList"),
  clearLog: document.querySelector("#clearLog"),
  dietSheet: document.querySelector("#dietSheet"),
  suggestions: document.querySelector("#suggestions"),
  mainInsight: document.querySelector("#mainInsight")
};

const savedCalories = localStorage.getItem("befitCalorieTarget");
const savedProtein = localStorage.getItem("befitProteinTarget");
if (savedCalories) els.calorieTarget.value = savedCalories;
if (!savedCalories && state.goal === "gain") els.calorieTarget.value = 2600;
if (savedProtein) els.proteinTarget.value = savedProtein;
if (!savedProtein && state.goal === "gain") els.proteinTarget.value = 140;
els.bodyWeight.value = state.profile.weight;
els.bodyHeight.value = state.profile.height;
els.userAge.value = state.profile.age;
els.userGender.value = state.profile.gender;
els.workoutRoutine.value = state.profile.routine;
els.themeChoice.value = state.theme;
document.body.dataset.theme = state.theme;
els.selectedDate.value = state.selectedDate;
state.meals = state.meals.map((meal) => ({ ...meal, date: meal.date || todayKey }));
if (!savedCalories || !savedProtein) applySuggestedTargets();

dishes.forEach((dish) => {
  const option = document.createElement("option");
  option.value = titleCase(dish.name);
  els.dishSuggestions.appendChild(option);
});
updateUnitOptions();

function titleCase(value) {
  return value.replace(/\w\S*/g, (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => {
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

function createMealId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function unitsForDish(dish) {
  const preferred = dish.unit || "piece";
  return [preferred, ...allUnits.filter((unit) => unit !== preferred)];
}

function formatQuantity(quantity, unit) {
  return `${quantity} ${unit}`;
}

function convertToBaseQuantity(quantity, selectedUnit, baseUnit) {
  const selectedMetric = selectedUnit === "kg" ? quantity * 1000 : selectedUnit === "L" ? quantity * 1000 : quantity;

  if (baseUnit === "g") {
    if (["g", "kg", "ml", "L"].includes(selectedUnit)) return selectedMetric;
    return quantity;
  }
  if (baseUnit === "ml") {
    if (["g", "kg", "ml", "L"].includes(selectedUnit)) return selectedMetric;
    return quantity;
  }
  if (["g", "kg", "ml", "L"].includes(selectedUnit)) {
    return selectedMetric / 100;
  }
  return quantity;
}

function findDish(name) {
  const normalized = name.trim().toLowerCase();
  const exact = dishes.find((dish) => dish.name === normalized);
  if (exact) return { ...exact, source: "matched" };

  const partial = dishes.find((dish) => normalized.includes(dish.name) || dish.name.includes(normalized));
  if (partial && normalized.length > 2) return { ...partial, source: "similar" };
  return null;
}

function updateUnitOptions() {
  const dish = findDish(els.dishName.value) || { unit: "piece", quantity: 1 };
  const currentUnit = els.foodUnit.value;
  const options = unitsForDish(dish);
  els.foodUnit.innerHTML = options.map((unit) => `<option value="${unit}">${unit}</option>`).join("");
  els.foodUnit.value = options.includes(currentUnit) ? currentUnit : dish.unit;
  if (!els.foodQuantity.value || Number(els.foodQuantity.value) <= 0) {
    els.foodQuantity.value = dish.quantity;
  }
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

function setSelectedDate(dateKey) {
  state.selectedDate = dateKey;
  state.calendarMonth = dateKey;
  els.selectedDate.value = dateKey;
  render();
}

function readProfile() {
  state.profile = {
    weight: Number(els.bodyWeight.value) || 70,
    height: Number(els.bodyHeight.value) || 170,
    age: Number(els.userAge.value) || 25,
    gender: els.userGender.value,
    routine: els.workoutRoutine.value
  };
  return state.profile;
}

function calculatePlan() {
  const profile = readProfile();
  const heightM = profile.height / 100;
  const bmi = profile.weight / (heightM * heightM);
  const healthyLow = 18.5 * heightM * heightM;
  const healthyHigh = 24.9 * heightM * heightM;
  const heightInches = profile.height / 2.54;
  const inchesOverFiveFeet = Math.max(0, heightInches - 60);
  const devineBase = profile.gender === "female" ? 45.5 : profile.gender === "male" ? 50 : 47.75;
  const idealWeight = devineBase + 2.3 * inchesOverFiveFeet;
  const bmrOffset = profile.gender === "female" ? -161 : profile.gender === "male" ? 5 : -78;
  const bmr = 10 * profile.weight + 6.25 * profile.height - 5 * profile.age + bmrOffset;
  const activity = activityLevels[profile.routine] || activityLevels.sedentary;
  const maintenance = bmr * activity.factor;
  const calorieTarget = state.goal === "loss" ? maintenance - 450 : maintenance + 350;
  const proteinMultiplier = state.goal === "loss" ? 1.7 : 1.8;
  const workoutBonus = ["active", "athlete"].includes(profile.routine) ? 0.2 : 0;
  const proteinTarget = profile.weight * (proteinMultiplier + workoutBonus);

  return {
    bmi,
    healthyLow,
    healthyHigh,
    idealWeight,
    maintenance,
    calorieTarget: Math.round(Math.max(1200, Math.min(4200, calorieTarget)) / 50) * 50,
    proteinTarget: Math.round(Math.max(45, Math.min(240, proteinTarget)) / 5) * 5,
    activityLabel: activity.label
  };
}

function applySuggestedTargets() {
  const plan = calculatePlan();
  els.calorieTarget.value = plan.calorieTarget;
  els.proteinTarget.value = plan.proteinTarget;
  return plan;
}

function getDishEstimate(name) {
  const normalized = name.trim().toLowerCase();
  const matchedDish = findDish(name);
  if (matchedDish) return matchedDish;

  const words = normalized.split(/\s+/).filter(Boolean);
  let calories = 300;
  let protein = 9;

  if (words.some((word) => ["chicken", "fish", "egg", "eggs"].includes(word))) {
    calories += 90;
    protein += 22;
  }
  if (words.some((word) => ["paneer", "tofu", "dal", "sprouts", "chana", "rajma"].includes(word))) {
    calories += 70;
    protein += 12;
  }
  if (words.some((word) => ["rice", "biryani", "pulao", "paratha", "noodles", "pasta"].includes(word))) {
    calories += 150;
    protein += 4;
  }
  if (words.some((word) => ["fried", "butter", "pizza", "burger", "samosa", "vada"].includes(word))) {
    calories += 180;
    protein += 5;
  }
  if (words.some((word) => ["salad", "soup", "fruit"].includes(word))) {
    calories -= 110;
    protein -= 2;
  }

  return {
    name: normalized || "custom dish",
    calories: Math.max(120, calories),
    protein: Math.max(3, protein),
    unit: "piece",
    quantity: 1,
    source: "estimated"
  };
}

function currentEstimate() {
  const estimate = getDishEstimate(els.dishName.value);
  const quantity = Number(els.foodQuantity.value) || estimate.quantity || 1;
  const unit = els.foodUnit.value || estimate.unit || "piece";
  const baseQuantity = estimate.quantity || 1;
  const convertedQuantity = convertToBaseQuantity(quantity, unit, estimate.unit);
  const multiplier = convertedQuantity / baseQuantity;

  return {
    name: titleCase(els.dishName.value.trim() || estimate.name),
    calories: Math.round(estimate.calories * multiplier),
    protein: Math.round(estimate.protein * multiplier),
    source: estimate.source,
    quantity,
    unit
  };
}

function updateEstimate() {
  if (!els.dishName.value.trim()) {
    els.estimateBox.innerHTML = "<strong>Enter a dish to estimate nutrition.</strong><span>Calories and protein are calculated from common serving averages.</span>";
    return;
  }

  const estimate = currentEstimate();
  const label = estimate.source === "matched" ? "Database match" : estimate.source === "similar" ? "Similar dish match" : "Smart estimate";
  els.estimateBox.innerHTML = `<strong>${estimate.calories} calories &bull; ${estimate.protein}g protein</strong><span>${label} for ${formatQuantity(estimate.quantity, estimate.unit)}. This will be added only after you submit.</span>`;
}

function totals() {
  return selectedMeals().reduce(
    (sum, meal) => ({
      calories: sum.calories + meal.calories,
      protein: sum.protein + meal.protein,
      cheats: sum.cheats + (meal.type === "Cheat Meal" ? 1 : 0)
    }),
    { calories: 0, protein: 0, cheats: 0 }
  );
}

function save() {
  localStorage.setItem("befitGoal", state.goal);
  localStorage.setItem("befitTheme", state.theme);
  localStorage.setItem("befitSelectedDate", state.selectedDate);
  localStorage.setItem("befitMeals", JSON.stringify(state.meals));
  localStorage.setItem("befitProfile", JSON.stringify(state.profile));
  localStorage.setItem("befitCalorieTarget", els.calorieTarget.value);
  localStorage.setItem("befitProteinTarget", els.proteinTarget.value);
}

function renderMeals() {
  const dayMeals = selectedMeals();
  if (!dayMeals.length) {
    els.mealList.className = "meal-list empty-state";
    els.mealList.textContent = `No meals added for ${dateTitle(state.selectedDate)}.`;
    return;
  }

  els.mealList.className = "meal-list";
  const mealTypes = ["Breakfast", "Lunch", "Snack", "Dinner", "Cheat Meal"];
  els.mealList.innerHTML = mealTypes
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

function renderDietSheet() {
  const plan = calculatePlan();
  const goalText = state.goal === "loss" ? "fat loss" : "healthy weight gain";
  const personalized = [
    ["Calories", `Aim for about ${plan.calorieTarget} calories daily for ${goalText}. Maintenance is around ${Math.round(plan.maintenance)} calories.`],
    ["Protein", `Target about ${plan.proteinTarget}g protein daily. Spread it across 3-5 meals.`],
    ["Workout", `${plan.activityLabel}: keep meals timed around training, especially protein after workouts.`]
  ];

  els.dietSheet.innerHTML = [...personalized, ...dietPlans[state.goal]]
    .map(([time, text]) => `<div class="diet-item"><strong>${time}</strong><span>${text}</span></div>`)
    .join("");
}

function buildSuggestions(total, calorieTarget, proteinTarget) {
  const suggestions = [];
  const remainingCalories = calorieTarget - total.calories;
  const proteinGap = proteinTarget - total.protein;

  if (!selectedMeals().length) {
    suggestions.push(["Start simple", "Log breakfast, lunch, snack, and dinner today. Patterns become visible after one full day."]);
  } else if (remainingCalories < -150 && state.goal === "loss") {
    suggestions.push(["Calorie control", "You are over your loss target. Keep dinner lighter with soup, salad, dal, or grilled protein."]);
  } else if (remainingCalories > 400 && state.goal === "gain") {
    suggestions.push(["Add fuel", "You still have room for calories. Add milk, nuts, rice, roti, banana, or a smoothie."]);
  } else {
    suggestions.push(["Good pacing", "Your calorie intake is close to the selected goal. Keep the next meal balanced."]);
  }

  if (proteinGap > 20) {
    suggestions.push(["Protein gap", "Add paneer, tofu, dal, eggs, chicken, fish, sprouts, curd, or a protein shake."]);
  } else {
    suggestions.push(["Protein habit", "Protein is moving well today. Spread it across meals for better fullness and recovery."]);
  }

  if (total.cheats > 1) {
    suggestions.push(["Cheat meal balance", "Multiple cheat meals today. Add water, vegetables, and a walk; return to routine at the next meal."]);
  } else {
    suggestions.push(["Consistency", "Plan cheat meals instead of reacting to cravings. That keeps the routine realistic."]);
  }

  return suggestions;
}

function renderProgress() {
  const plan = calculatePlan();
  const total = totals();
  const calorieTarget = Number(els.calorieTarget.value) || 1800;
  const proteinTarget = Number(els.proteinTarget.value) || 110;
  const caloriePercent = Math.min(100, Math.round((total.calories / calorieTarget) * 100));
  const proteinPercent = Math.min(100, Math.round((total.protein / proteinTarget) * 100));

  els.calorieTotal.textContent = total.calories;
  els.proteinTotal.textContent = `${total.protein}g`;
  els.mealCount.textContent = selectedMeals().length;
  els.calorieMeter.style.width = `${caloriePercent}%`;
  els.proteinMeter.style.width = `${proteinPercent}%`;
  els.calorieProgressText.textContent = `${total.calories} / ${calorieTarget}`;
  els.proteinProgressText.textContent = `${total.protein}g / ${proteinTarget}g`;
  els.profileSummary.innerHTML = `
    <div class="summary-card"><strong>${plan.bmi.toFixed(1)}</strong><span>BMI</span></div>
    <div class="summary-card"><strong>${plan.idealWeight.toFixed(1)} kg</strong><span>Ideal body weight</span></div>
    <div class="summary-card"><strong>${plan.healthyLow.toFixed(1)}-${plan.healthyHigh.toFixed(1)} kg</strong><span>Healthy BMI range</span></div>
    <div class="summary-card"><strong>${Math.round(plan.maintenance)}</strong><span>Maintenance calories</span></div>
  `;

  const suggestions = buildSuggestions(total, calorieTarget, proteinTarget);
  els.mainInsight.textContent = suggestions[0][1];
  els.suggestions.innerHTML = suggestions
    .map(([title, text]) => `<article class="suggestion-card"><strong>${title}</strong><span>${text}</span></article>`)
    .join("");
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

  els.selectedDateLabel.textContent = dateTitle(state.selectedDate);
  els.selectedDate.value = state.selectedDate;
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

function renderGoal() {
  els.goalOptions.forEach((button) => button.classList.toggle("active", button.dataset.goal === state.goal));
  els.goalLabel.textContent = state.goal === "loss" ? "Weight Loss" : "Weight Gain";
}

function renderTheme() {
  document.body.dataset.theme = state.theme;
  els.themeChoice.value = state.theme;
}

function render() {
  renderTheme();
  renderGoal();
  renderCalendar();
  renderDietSheet();
  renderMeals();
  renderProgress();
  save();
}

els.goalOptions.forEach((button) => {
  button.addEventListener("click", () => {
    state.goal = button.dataset.goal;
    applySuggestedTargets();
    render();
  });
});

["input", "change"].forEach((eventName) => {
  els.dishName.addEventListener(eventName, () => {
    updateUnitOptions();
    updateEstimate();
  });
  els.foodQuantity.addEventListener(eventName, updateEstimate);
  els.foodUnit.addEventListener(eventName, updateEstimate);
  els.calorieTarget.addEventListener(eventName, () => {
    renderProgress();
    save();
  });
  els.proteinTarget.addEventListener(eventName, () => {
    renderProgress();
    save();
  });
  [els.bodyWeight, els.bodyHeight, els.userAge, els.userGender, els.workoutRoutine].forEach((field) => {
    field.addEventListener(eventName, () => {
      applySuggestedTargets();
      render();
    });
  });
});

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

els.updatePlan.addEventListener("click", () => {
  applySuggestedTargets();
  render();
});

els.mealForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const estimate = currentEstimate();
  state.meals.unshift({
    id: createMealId(),
    name: estimate.name,
    calories: estimate.calories,
    protein: estimate.protein,
    quantity: estimate.quantity,
    unit: estimate.unit,
    type: els.mealType.value,
    date: state.selectedDate
  });
  els.mealForm.reset();
  updateUnitOptions();
  updateEstimate();
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

document.querySelectorAll(".nav-link").forEach((link) => {
  link.addEventListener("click", () => {
    document.querySelectorAll(".nav-link").forEach((item) => item.classList.remove("active"));
    link.classList.add("active");
  });
});

render();
