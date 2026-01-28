-- ===============================
-- Create Database
-- ===============================
CREATE DATABASE IF NOT EXISTS mealdb;
USE mealdb;

-- ===============================
-- Users Table
-- ===============================
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ===============================
-- Favorites Table
-- ===============================
CREATE TABLE favorites (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    meal_id VARCHAR(50) NOT NULL,
    meal_name VARCHAR(200),
    meal_image TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ===============================
-- Meal Planner Table
-- ===============================
CREATE TABLE meal_plan (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    meal_id VARCHAR(50) NOT NULL,
    meal_name VARCHAR(200),
    meal_image TEXT,
    meal_date DATE NOT NULL,
    meal_type VARCHAR(20) NOT NULL,  -- Breakfast / Lunch / Dinner / Snack
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ===============================
-- Least Ingredient Cache (Optional)
-- ===============================
CREATE TABLE least_ingredient_meals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    meal_id VARCHAR(50),
    meal_name VARCHAR(200),
    ingredient_count INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE recipe_nutrition (
    meal_id VARCHAR(50) PRIMARY KEY,
    calories FLOAT,
    protein FLOAT,
    fat FLOAT
);
