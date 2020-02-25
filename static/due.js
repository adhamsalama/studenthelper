function verify_due() {
    return confirm("Are you sure you want to delete this due?");
}
let d1 = new Date(); //"now"
let deadlines = document.querySelectorAll(".deadline");
let dates = document.querySelectorAll(".time-left");
for (let i = 0; i < deadlines.length; i++) {
    let d2 = new Date(deadlines[i].innerHTML);
    let diffTime = d2 - d1;
    let diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
    if (diffDays == 0) {
        dates[i].innerHTML = "Today";
    }
    else if (diffDays == 1) {
        dates[i].innerHTML = "Tomorrow";
    }
    else if (diffDays == -1) {
        dates[i].innerHTML = "Yesterday";
    }
    else if (diffDays % 7 == 0) {
        if (diffDays == 7) {
            dates[i].innerHTML = "1 week";
        }
        else {
            dates[i].innerHTML = diffDays / 7 + " weeks"
        }
    }
    else {
        dates[i].innerHTML = diffDays + " days";
    }
}
