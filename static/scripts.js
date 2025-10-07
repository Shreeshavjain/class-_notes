// Auto-hide flash messages after 3 seconds
document.addEventListener("DOMContentLoaded", function() {
    const flash = document.querySelector(".flash-message");
    if(flash){
        setTimeout(() => {
            flash.style.display = "none";
        }, 3000); // 3 seconds
    }
});

// Confirm before deleting a subject
function confirmDelete(subjectName){
    return confirm(`Are you sure you want to delete "${subjectName}"?`);
}

// Preview selected file name
function previewFile(inputId, labelId){
    const input = document.getElementById(inputId);
    const label = document.getElementById(labelId);
    if(input.files.length > 0){
        label.textContent = input.files[0].name;
    } else {
        label.textContent = "Choose file...";
    }
}
