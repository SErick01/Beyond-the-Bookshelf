/** 
 * Drop down in nav bar
 */

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


let activeBookId = 1;

/**
 * Helper function to safely get the current percentage from the progress bar style.
 * Uses parseFloat() for non-integer percentages (like 57.6%).
 */
function getCurrentProgress(bookId) {
    const progressBar = document.getElementById('progress-bar-' + bookId);
    if (progressBar && progressBar.style.width) {
        // Use parseFloat to handle decimals (like 57.6%)
        return parseFloat(progressBar.style.width.replace('%', ''));
    }
    return 0;
}


function openModal(bookId){
    activeBookId = bookId;
    const modal = document.getElementById('progress-modal');
    const input = document.getElementById('percentage-input');
    const error = document.getElementById('error-message');
    const currentPercent = getCurrentProgress(bookId);

    input.value = currentPercent; 
    error.classList.add('hidden');
    
    if(modal){
        modal.classList.remove('hidden');
    } else {
        console.error("Modal element with ID 'progress-modal' not found")
    }
}

function closeModal() {
    const modal = document.getElementById('progress-modal');
    modal.classList.add('hidden')
}

function closeRatingModal() {
    const modal = document.getElementById('rating-modal');
    modal.classList.add('hidden');
}

function closeModalOnOutsideClick(event) {
    if (event.target.id === 'progress-modal') {
        closeModal();
    }
}

function openRatingModal() {
    const ratingModal = document.getElementById('rating-modal');
    if (ratingModal) {
        ratingModal.classList.remove('hidden');
    }
}

function saveRating() {
    // where the rating data is sent to db
    alert(`Rating submitted for book ${activeBookId}!`);
    closeRatingModal();
}


function updateProgress() {
    const input = document.getElementById('percentage-input');
    const error = document.getElementById('error-message');
    const newPercentage = parseFloat(input.value); 
    const currentPercent = getCurrentProgress(activeBookId);

    // 1. Validation Check
    if (isNaN(newPercentage) || newPercentage < 0 || newPercentage > 100) {
        error.textContent = 'Please enter a valid percentage between 0 and 100.';
        error.classList.remove('hidden');
        return; 
    }
    const progressBar = document.getElementById('progress-bar-' + activeBookId);
    const progressText = document.getElementById('progress-text-' + activeBookId);

    // 2. Update Progress Bar and Text
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
    if (newPercentage === 100 && currentPercent < 100) {
        openRatingModal();
    }
}