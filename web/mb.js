
document.addEventListener('DOMContentLoaded', () => {
    const fabButton = document.getElementById('new-list-btn');
    const modal = document.getElementById('list-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const createListBtn = document.getElementById('create-list-btn');
    const listNameInput = document.getElementById('list-name-input');
    const toggleModal = (show) => {
        if (show) {
            modal.classList.remove('hidden-modal');
        } else {
            modal.classList.add('hidden-modal');
            listNameInput.value = ''
        }
    };

    // 1. Open the modal when the NLB button is clicked
    fabButton.addEventListener('click', () => {
        toggleModal(true);
    });

    // 2. Close the modal when the 'Cancel' button is clicked
    closeModalBtn.addEventListener('click', () => {
        toggleModal(false);
    });

    // 3. Close the modal when the user clicks the dark backdrop
    modal.addEventListener('click', (event) => {
        if (event.target === modal) {
            toggleModal(false);
        }
    });

    // 4. Handle the 'Create' action
    createListBtn.addEventListener('click', () => {
        const listName = listNameInput.value.trim();

        if (listName) {
            console.log(`✅ New List Created: "${listName}"`);
            alert(`List "${listName}" created successfully! (Check console for full action)`);
            toggleModal(false);
        } else {
            alert("Please enter a name for your new list.");
            listNameInput.focus(); 
        }
    });
});