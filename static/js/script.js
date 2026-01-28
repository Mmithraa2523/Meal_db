// ===============================
// GLOBAL ALERT
// ===============================
function showAlert(message) {
    alert(message);
}

// ===============================
// FAVORITES
// ===============================
function addToFavorite(mealId) {
    fetch(`/favorite/${mealId}`)
        .then(res => {
            if (res.ok) showAlert("❤️ Added to favorites");
            else showAlert("❌ Failed to add");
        });
}

function removeFavorite(favId) {
    fetch(`/remove-favorite/${favId}`)
        .then(res => {
            if (res.ok) {
                showAlert("🗑️ Removed from favorites");
                location.reload();
            }
        });
}

// ===============================
// MEAL PLANNER MODAL
// ===============================
function openMealModal(day, mealType) {
    document.getElementById("mealModal").style.display = "flex";

    // IMPORTANT
    document.getElementById("dayInput").value = day;
    document.getElementById("typeInput").value = mealType;

    console.log("Day:", day, "Meal:", mealType);
}

function closeMealModal() {
    document.getElementById("mealModal").style.display = "none";
}

// Close modal when clicking outside
window.onclick = function (event) {
    const modal = document.getElementById("mealModal");
    if (event.target === modal) {
        modal.style.display = "none";
    }
};

// ===============================
// OPTIONAL: CONFIRM DELETE
// ===============================
function confirmDelete() {
    return confirm("Are you sure?");
}
function openPlanner() {
    document.getElementById("plannerModal").style.display = "flex";
}

function closePlanner() {
    document.getElementById("plannerModal").style.display = "none";
}

