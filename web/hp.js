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

function openModal(bookId){
    activeBookId = bookId;
    const modal = document.getElementById('progress-modal');
    const input = document.getElementById('percentage-input');
    const error = document.getElementById('error-message');
   
    const progressBar = document.getElementById('progress-bar-' + activeBookId);
    
    let currentPercent = 0;
    if (progressBar && progressBar.style.width) {
        currentPercent = parseInt(progressBar.style.width.replace('%', ''), 10);
    }

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

function closeModalOnOutsideClick(event) {
    if (event.target.id === 'progress-modal') {
        closeModal();
    }
}

function updateProgress() {
    const input = document.getElementById('percentage-input');
    const error = document.getElementById('error-message');
    const newPercentage = parseInt(input.value);
    if (isNaN(newPercentage) || newPercentage < 0 || newPercentage > 100) {
        error.textContent = 'Please enter a valid percentage between 0 and 100.';
        error.classList.remove('hidden');
        return; 
    }

    const progressBar = document.getElementById('progress-bar-' + activeBookId);
    const progressText = document.getElementById('progress-text-' + activeBookId);

    if (progressBar) {
        progressBar.style.width = newPercentage + '%';
    }

    if (progressText) {
        progressText.textContent = newPercentage + '%';
                
        if (newPercentage < 25) {
            progressText.classList.remove('text-white');
            progressText.classList.add('text-dark-brown'); 
            progressText.style.textShadow = 'none';
        } else {
            progressText.classList.remove('text-dark-brown');
            progressText.classList.add('text-white');
        }
    }

    closeModal();
}

