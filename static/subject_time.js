let tds = document.querySelectorAll("td");
for (let i = 0; i < tds.length; i++) {
    tds[i].style.verticalAlign = "middle";
}
let time = document.querySelectorAll(".time");
for (let i = 0, n = time.length; i < n; i++) {
    let minutes = parseInt(time[i].innerHTML[3]) * 10 + parseInt(time[i].innerHTML[4]);
    if (minutes < 10) {
        minutes = "0" + minutes;
    }
    let hours = parseFloat(time[i].innerHTML);
    let suffix = hours >= 12 ? " PM" : " AM";
    hours = ((hours + 11) % 12 + 1);
    time[i].innerHTML = hours + ":" + minutes + suffix;
}

