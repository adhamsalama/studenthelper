function get_weather_data() {
    navigator.geolocation.getCurrentPosition(getLatLon);
    function getLatLon(position) {
        var latitude = position.coords.latitude;
        var longitude = position.coords.longitude;
        let request = "https://api.openweathermap.org/data/2.5/weather?lat=" + latitude + "&lon=" + longitude + "&units=metric&mode=html&appid=aaacf01424b1f47c7dadcd2a1f8eb254";
        $("#weather").load(request, function () {
            document.querySelector("#weather").style.display = "inline-block";
        });
    }
}