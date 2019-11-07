let username = document.querySelector('#username');
let email = document.querySelector("#email")
let password = document.querySelector("#password");
let confirmation = document.querySelector("#confirmation");
let form = document.querySelector('form');
form.onsubmit = function() {
    if (!username.value) {
        return false;
    }
    /* extra form validation (before sending ajax request) inspired by https://www.the-art-of-web.com/javascript/validate-password/
       and editied to work better with my bootstrap validation */
    if (password.value != "" && password.value == confirmation.value) {
        if (password.value.length < 6) {
            alert("Password must be longer than 6 characters.");
            password.focus();
            password.classList.add("is-invalid");
            password.style.borderColor = "#dc3545";
            return false;
        }
        if (password.value == username.value) {
            alert("Error: Password must be different from Username!");
            password.focus();
            password.classList.add("is-invalid");
            password.style.borderColor = "#dc3545";
            return false;
        }
        re = /[0-9]/;
        if (!re.test(password.value)) {
            alert("Error: password must contain at least one number (0-9)!");
            password.focus();
            password.classList.add("is-invalid");
            password.style.borderColor = "#dc3545";
            return false;
        }
        re = /[a-z]/;
        if (!re.test(password.value)) {
            alert("Error: password must contain at least one lowercase letter (a-z)!");
            password.focus();
            password.classList.add("is-invalid");
            password.style.borderColor = "#dc3545";
            return false;
        }
        re = /[A-Z]/;
        if (!re.test(password.value)) {
            alert("Error: password must contain at least one uppercase letter (A-Z)!");
            password.focus();
            password.classList.add("is-invalid");
            password.style.borderColor = "#dc3545";
            return false;
        }
    } else {
        alert("Error: Please check that you've entered and confirmed your password!");
        password.focus();
        confirmation.classList.add("is-invalid");
        confirmation.style.borderColor = "#dc3545";
        return false;
    }
    $.ajax({
        url: '/check?username=' + username.value + '&email=' + email.value,
        type: 'GET',
        success: function(data) {
            console.log(data);
            if (data == true) {
                
                form.submit();
            }
            else {
                alert(data);
                $('#username').focus();
                return false;

            }

        },
        error: function(error) {
            console.log(error);

        }
    });


    return false;

};

