//Drop Down in the Nav Bar
function toggleDropdown(event) { 
    const menu = document.getElementById('dropdown-menu');
    const button = event.currentTarget;
    menu.classList.toggle('hidden');
    const isExpanded = menu.classList.contains('hidden') ? 'false' : 'true';
    button.setAttribute('aria-expanded', isExpanded);
}

document.addEventListener('click', function(event) {
    const parentDiv = document.getElementById('dropdown-parent');
    const menu = document.getElementById('dropdown-menu');
    if (menu && !menu.classList.contains('hidden') && parentDiv && !parentDiv.contains(event.target)) {
        menu.classList.add('hidden');
        const button = parentDiv.querySelector('.drop-down-menu-icon-btn');
        if (button) {
                button.setAttribute('aria-expanded', 'false');
        }
    }
});

// Progress Bar Updates
let activeBookId = 1;

function getBookData(bookId) {
    if (!window.currentReads) return null;
    return window.currentReads[bookId] || null;
}

function getCurrentProgress(bookId) {
    const progressBar = document.getElementById('progress-bar-' + bookId);
    if (progressBar && progressBar.style.width) {
        return parseFloat(progressBar.style.width.replace('%', ''));
    }
    return 0;
}

function openModal(bookId) {
    activeBookId = bookId;
    const modal = document.getElementById('progress-modal');
    const input = document.getElementById('page-input');
    const error = document.getElementById('error-message');
    const totalPagesLabel = document.getElementById('total-pages-label');
    const currentPercent = getCurrentProgress(bookId);
    const bookData = getBookData(bookId);
    const totalPages = bookData?.page_count;
    error.classList.add('hidden');

    if (totalPages && totalPagesLabel) {
        totalPagesLabel.textContent = `Total pages: ${totalPages}`;
        const approxPage = Math.round((currentPercent / 100) * totalPages);
        input.value = approxPage || '';
        input.max = totalPages;

    } else {
        if (totalPagesLabel) totalPagesLabel.textContent = '';
        input.value = '';
        input.removeAttribute('max');
    }

    if (modal) {
        modal.classList.remove('hidden');

    } else {
        console.error("Modal element with ID 'progress-modal' not found");
    }
}

let currentRating = 0;
const starContainer = document.getElementById('star-rating-container');
const stars = starContainer.querySelectorAll('span[data-rating]');
const selectedRatingText = document.getElementById('selected-rating');

function updateStarDisplay(rating, isHover) {
    stars.forEach(star => {
        const starValue = parseInt(star.dataset.rating);
        // Highlight stars up to the given rating value
        if (starValue <= rating) {
            star.classList.add('highlighted-star');

        } else {
            star.classList.remove('highlighted-star');
        }
    });
    // Update the explanatory text
    if (rating > 0) {
        selectedRatingText.textContent = isHover 
            ? `Preview: ${rating} Star${rating > 1 ? 's' : ''}` 
            : `Selected: ${rating} Star${rating > 1 ? 's' : ''}`;
    } else {
        selectedRatingText.textContent = "Click a star to rate";
    }
}

starContainer.addEventListener('mouseover', (event) => {
        const star = event.target.closest('span[data-rating]');
        if (star) {
            const hoverRating = parseInt(star.dataset.rating);
            updateStarDisplay(hoverRating, true);
        }
    });

    starContainer.addEventListener('mouseout', () => {
        updateStarDisplay(currentRating, false); 
    });

    starContainer.addEventListener('click', (event) => {
        const star = event.target.closest('span[data-rating]');
        if (star) {
            currentRating = parseInt(star.dataset.rating);
            updateStarDisplay(currentRating, false); 
        }
    });
    updateStarDisplay(currentRating, false);

function closeRatingModal() {
    const modal = document.getElementById('rating-modal');
    modal.classList.add('hidden');
    currentRating = 0;
    updateStarDisplay(currentRating,false);
}

function openRatingModal() {
    const ratingModal = document.getElementById('rating-modal');
    if (ratingModal) {
        ratingModal.classList.remove('hidden');
    }
}

function saveRating() {
    if (currentRating === 0){
        alert("Please select a star rating");
        return;
    }
    // where the rating data is sent to db
    alert(`Rating submitted for book ${activeBookId}!`);
    closeRatingModal();
}

function closeModal() {
    const modal = document.getElementById('progress-modal');
    modal.classList.add('hidden')
}

function closeModalOnOutsideClick(event) {
    if (event.target.id === 'progress-modal') {
        closeModal();
    }
}

function updateProgress() {
    const input = document.getElementById('page-input');
    const error = document.getElementById('error-message');
    const pagesRead = parseInt(input.value, 10);
    const bookData = getBookData(activeBookId);
    const totalPages = bookData?.page_count;

    if (!bookData || !totalPages) {
        error.textContent = 'Sorry, this book is missing a total page count.';
        error.classList.remove('hidden');
        return;
    }

    if (isNaN(pagesRead) || pagesRead < 0 || pagesRead > totalPages) {
        error.textContent = `Please enter a page between 0 and ${totalPages}.`;
        error.classList.remove('hidden');
        return;
    }

    const newPercentage = (pagesRead / totalPages) * 100;
    const currentPercent = getCurrentProgress(activeBookId);
    const progressBar = document.getElementById('progress-bar-' + activeBookId);
    const progressText = document.getElementById('progress-text-' + activeBookId);

    if (progressBar) {
        const displayPercentage = newPercentage.toFixed(newPercentage % 1 !== 0 ? 1 : 0);
        progressBar.style.width = displayPercentage + '%';

        if (progressText) {
            progressText.textContent = displayPercentage + '%';

            if (newPercentage < 25) {
                progressText.classList.remove('text-white');
                progressText.classList.add('text-dark-brown');
                progressText.style.textShadow = 'none';
            } else {
                progressText.classList.remove('text-dark-brown');
                progressText.classList.add('text-white');
                progressText.style.textShadow = '1px 1px 2px rgba(0, 0, 0, 0.5)';
            }
        }
    }
    closeModal();
    if (newPercentage >= 100 && currentPercent < 100) {openRatingModal();}
}
