let checkbox = document.querySelectorAll(".form-check-input");
let n = checkbox.length;
document.querySelector("#f").onsubmit = function () {
    let start = document.querySelector("#start");
    let end = document.querySelector("#end");
    if (end.value <= start.value) {
        alert("End time must be after start time.");
        return false;
    }
    let state = 0;
    for (let i = 0; i < n; i++) {
        if (checkbox[i].checked) {
            state++;
        }
    }
    if (state == 0) {
        alert("Please choose at least one day.");
        return false;
    }
}