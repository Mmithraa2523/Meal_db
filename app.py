from flask import Flask, render_template, request, redirect, session, jsonify
from flask_mysqldb import MySQL
import requests
from config import *

app = Flask(__name__)
app.secret_key = SECRET_KEY

#============================
# base url
#================================
MEALDB_BASE_URL = "https://www.themealdb.com/api/json/v1/1"



# ===============================
# MySQL Configuration
# ===============================
app.config['MYSQL_HOST'] = MYSQL_HOST
app.config['MYSQL_USER'] = MYSQL_USER
app.config['MYSQL_PASSWORD'] = MYSQL_PASSWORD
app.config['MYSQL_DB'] = MYSQL_DB
mysql = MySQL(app)

# ===============================
# AUTHENTICATION
# ===============================

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT id FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = cur.fetchone()
        cur.close()

        if user:
            # ✅ USE SAME SESSION KEY EVERYWHERE
            session['user_id'] = user[0]
            return redirect('/dashboard')   # or /discover

        else:
            return render_template(
                'login.html',
                error="Invalid email or password"
            )

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
            (name, email, password)
        )
        mysql.connection.commit()
        cur.close()

        return redirect('/')
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ===============================
# DASHBOARD
# ===============================

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/')
    return render_template('dashboard.html')

# ===============================
# MEAL SEARCH (MealDB)
# ===============================

@app.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()

    if not query:
        return render_template('meals.html', meals=[])

    meals = []

    # 1️⃣ First letter search
    if len(query) == 1 and query.isalpha():
        data = requests.get(
            f"{MEALDB_BASE_URL}/search.php?f={query}"
        ).json()
        meals = data.get('meals') or []

    else:
        # 2️⃣ Search by meal name
        data = requests.get(
            f"{MEALDB_BASE_URL}/search.php?s={query}"
        ).json()
        meals = data.get('meals') or []

        # 3️⃣ Search by category (if name not found)
        if not meals:
            data = requests.get(
                f"{MEALDB_BASE_URL}/filter.php?c={query}"
            ).json()
            basic = data.get('meals') or []

            # filter.php gives only id & image → need full details
            for m in basic:
                lookup = requests.get(
                    f"{MEALDB_BASE_URL}/lookup.php?i={m['idMeal']}"
                ).json()
                if lookup.get('meals'):
                    meals.append(lookup['meals'][0])

    return render_template('meals.html', meals=meals)


# ===============================
# RECIPE DETAILS + NUTRITION
# ===============================

@app.route('/recipe/<meal_id>')
def recipe_details(meal_id):
    meal_url = f"{MEALDB_BASE_URL}/lookup.php?i={meal_id}"
    meal = requests.get(meal_url).json()['meals'][0]

    nutrition = calculate_nutrition(meal)

    return render_template(
        'recipe_details.html',
        meal=meal,
        nutrition=nutrition
    )

# ===============================
# USDA NUTRITION CALCULATION
# ===============================

def calculate_nutrition(meal):
    meal_id = meal['idMeal']

    cur = mysql.connection.cursor()

    # 1️⃣ Check cache
    cur.execute(
        "SELECT calories, protein, fat FROM recipe_nutrition WHERE meal_id=%s",
        (meal_id,)
    )
    cached = cur.fetchone()

    if cached:
        cur.close()
        return {
            "calories": cached[0],
            "protein": cached[1],
            "fat": cached[2]
        }

    # 2️⃣ Calculate nutrition
    total_cal = total_protein = total_fat = 0

    for i in range(1, 21):
        ingredient = meal.get(f"strIngredient{i}")
        if ingredient:
            params = {
                "query": ingredient,
                "api_key": USDA_API_KEY,
                "pageSize": 1
            }
            r = requests.get(USDA_BASE_URL, params=params).json()

            if r.get('foods'):
                food = r['foods'][0]
                for n in food.get('foodNutrients', []):
                    if n['nutrientName'] == 'Energy':
                        total_cal += n.get('value', 0)
                    elif n['nutrientName'] == 'Protein':
                        total_protein += n.get('value', 0)
                    elif n['nutrientName'] == 'Total lipid (fat)':
                        total_fat += n.get('value', 0)

    # 3️⃣ Insert OR Update safely
    cur.execute("""
        INSERT INTO recipe_nutrition (meal_id, calories, protein, fat)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            calories = VALUES(calories),
            protein = VALUES(protein),
            fat = VALUES(fat)
    """, (
        meal_id,
        round(total_cal),
        round(total_protein, 1),
        round(total_fat, 1)
    ))

    mysql.connection.commit()
    cur.close()

    return {
        "calories": round(total_cal),
        "protein": round(total_protein, 1),
        "fat": round(total_fat, 1)
    }

# ===============================
# QUICK MEALS (Least Ingredients)
# ===============================

@app.route('/quick-meals')
def quick_meals():
    query = request.args.get('q', '').strip().lower()

    if not query:
        return render_template('quick_meals.html', meals=[], summary=None)

    meals_data = []

    # 1️⃣ Starting letter
    if len(query) == 1 and query.isalpha():
        data = requests.get(
            f"{MEALDB_BASE_URL}/search.php?f={query}"
        ).json()
        meals_data = data.get('meals') or []

    else:
        # 2️⃣ Meal name
        data = requests.get(
            f"{MEALDB_BASE_URL}/search.php?s={query}"
        ).json()
        meals_data = data.get('meals') or []

        # 3️⃣ Ingredient
        if not meals_data:
            data = requests.get(
                f"{MEALDB_BASE_URL}/filter.php?i={query}"
            ).json()
            basic = data.get('meals') or []

            for m in basic:
                lookup = requests.get(
                    f"{MEALDB_BASE_URL}/lookup.php?i={m['idMeal']}"
                ).json()
                if lookup.get('meals'):
                    meals_data.append(lookup['meals'][0])

        # 4️⃣ Category
        if not meals_data:
            data = requests.get(
                f"{MEALDB_BASE_URL}/filter.php?c={query}"
            ).json()
            basic = data.get('meals') or []

            for m in basic:
                lookup = requests.get(
                    f"{MEALDB_BASE_URL}/lookup.php?i={m['idMeal']}"
                ).json()
                if lookup.get('meals'):
                    meals_data.append(lookup['meals'][0])

    if not meals_data:
        return render_template('quick_meals.html', meals=[], summary=None)

    meals = []
    for meal in meals_data:
        count = sum(
            1 for i in range(1, 21)
            if meal.get(f"strIngredient{i}") and meal[f"strIngredient{i}"].strip()
        )

        meals.append({
            "id": meal["idMeal"],
            "name": meal["strMeal"],
            "image": meal["strMealThumb"],
            "ingredients": count
        })

    min_count = min(m["ingredients"] for m in meals)
    quick_meals = [m for m in meals if m["ingredients"] == min_count]

    summary = {
        "count": min_count,
        "total": len(quick_meals)
    }

    return render_template(
        "quick_meals.html",
        meals=quick_meals,
        summary=summary
    )


# ===============================
# FAVORITES
# ===============================

@app.route('/favorite/<meal_id>')
def add_favorite(meal_id):
    if 'user_id' not in session:
        return redirect('/')

    meal_url = f"{MEALDB_BASE_URL}/lookup.php?i={meal_id}"
    meal = requests.get(meal_url).json()['meals'][0]

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO favorites(user_id, meal_id, meal_name, meal_image)
        VALUES(%s,%s,%s,%s)
    """, (
        session['user_id'],
        meal_id,
        meal['strMeal'],
        meal['strMealThumb']
    ))
    mysql.connection.commit()
    cur.close()

    return redirect('/favorites')


@app.route('/favorites')
def favorites():
    if 'user_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, meal_id, meal_name, meal_image
        FROM favorites
        WHERE user_id=%s
    """, (session['user_id'],))
    meals = cur.fetchall()
    cur.close()

    return render_template('favorites.html', meals=meals)


@app.route('/remove-favorite/<int:id>')
def remove_favorite(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM favorites WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()
    return redirect('/favorites')

# ===============================
# MEAL PLANNER
# ===============================

@app.route('/meal-plan')
def meal_plan():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id, day, meal_type, meal_name
        FROM meal_plan
        WHERE user_id=%s
    """, (user_id,))
    rows = cur.fetchall()
    cur.close()

    plan = {}
    for pid, day, meal_type, meal_name in rows:
        plan.setdefault(day, {})[meal_type] = {
            "id": pid,
            "name": meal_name
        }

    return render_template('meal_plan.html', plan=plan)



@app.route('/add-meal-plan', methods=['POST'])
def add_meal_plan():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    day = request.form['day']
    meal_type = request.form['meal_type']
    meal_id = request.form['meal_id']
    meal_name = request.form['meal_name']
    meal_image = request.form['meal_image']

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO meal_plan (user_id, day, meal_type, meal_id, meal_name, meal_image)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (user_id, day, meal_type, meal_id, meal_name, meal_image))

    mysql.connection.commit()
    cur.close()

    return redirect('/meal-plan')


@app.route('/remove-meal-plan/<int:plan_id>')
def remove_meal_plan(plan_id):
    if 'user_id' not in session:
        return redirect('/login')

    cur = mysql.connection.cursor()
    cur.execute(
        "DELETE FROM meal_plan WHERE id=%s AND user_id=%s",
        (plan_id, session['user_id'])
    )
    mysql.connection.commit()
    cur.close()

    return redirect('/meal-plan')



# ===============================
# RUN APP
# ===============================

if __name__ == "__main__":
    app.run(debug=True)
