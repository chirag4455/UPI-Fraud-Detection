// MLBFD Main JavaScript
console.log("MLBFD Fraud Detection System Loaded");

// Auto-refresh alerts every 30 seconds
if (window.location.pathname === "/alerts") {
    setTimeout(function() { location.reload(); }, 30000);
}

// Animate numbers on load
document.querySelectorAll(".stat-value").forEach(function(el) {
    var final_val = parseInt(el.textContent);
    if (!isNaN(final_val) && final_val > 0 && final_val < 10000) {
        var current = 0;
        var step = Math.ceil(final_val / 30);
        var timer = setInterval(function() {
            current += step;
            if (current >= final_val) {
                el.textContent = final_val;
                clearInterval(timer);
            } else {
                el.textContent = current;
            }
        }, 30);
    }
});
