// Function to automatically dismiss alerts after a certain period

function dismissMessages() {
    setTimeout(function() {
        $('.alert').fadeOut('fast');
    }, 2000);  // time in milliseconds
}
