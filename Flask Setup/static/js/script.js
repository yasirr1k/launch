
document.addEventListener('DOMContentLoaded', function () {
    const form = document.querySelector('form');
    form.addEventListener('submit', function (e) {

        if (form.username.value === '' || form.password.value === '') {
            alert('Please fill out all fields.');
            e.preventDefault(); 
        }
    });
});
