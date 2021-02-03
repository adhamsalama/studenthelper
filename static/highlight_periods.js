function highlight_periods() {
    // highlight current running period
    let time = new Date().toTimeString().slice(0, 7); // get local time string 
    let table = document.querySelector("#today_periods"); // select today periods table
    if(table != null) {
        let rows = table.rows; // get the rows
        for(let i=1; i < rows.length; i++) { // start from 1 because 0 is the table header
            let times = rows[i].querySelectorAll(".time");
            // period is running
            if(time >= times[0].innerText && time <= times[1].innerText)
                rows[i].className = "bg-primary";
            // period ended
            else if(time > times[0].innerText)
                rows[i].className = "bg-success";
        }
    }
    else
        console.log("cant find table");
}