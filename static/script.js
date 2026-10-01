const searchInput = document.getElementById("searchInput");
const cards = document.querySelectorAll(".website-card");
const categoryButtons = document.querySelectorAll(".category-btn");
const noResults = document.getElementById("noResults");

let selectedCategory = "all";


// Search + category filtering
function filterWebsites() {

    const searchText = searchInput.value.toLowerCase().trim();

    let visibleCards = 0;

    cards.forEach(function (card) {

        const cardText = card.innerText.toLowerCase();
        const category = card.dataset.category;

        const matchesSearch = cardText.includes(searchText);
        const matchesCategory =
            selectedCategory === "all" ||
            category === selectedCategory;

        if (matchesSearch && matchesCategory) {

            card.style.display = "block";
            visibleCards++;

        } else {

            card.style.display = "none";

        }

    });


    // Show / hide "No websites found"
    if (visibleCards === 0) {

        noResults.style.display = "block";

    } else {

        noResults.style.display = "none";

    }
}


// Search box
if (searchInput) {

    searchInput.addEventListener("input", function () {

        filterWebsites();

    });

}


// Category buttons
categoryButtons.forEach(function (button) {

    button.addEventListener("click", function () {

        // Remove active from all buttons
        categoryButtons.forEach(function (btn) {

            btn.classList.remove("active");

        });


        // Add active to clicked button
        button.classList.add("active");


        // Get selected category
        selectedCategory = button.dataset.category;


        // Filter cards
        filterWebsites();

    });

});